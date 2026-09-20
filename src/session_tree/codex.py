"""Read Codex sessions, which keep their history in SQLite rather than JSONL.

Codex stores more structure than Claude Code does: threads carry a working
directory and a title, turns carry a status and a duration, and items record
which files a change touched and what a command exited with.

What it does not store is a task list. There is a ``thread_goals`` table and it
stays empty, and no item type is a plan or a todo. So a Codex session has no
graph to draw, and this module returns none rather than inventing one from the
turns -- a picture that is wrong is worse than no picture, because it is the
one being trusted.

The database filenames carry a schema version that changes when Codex upgrades,
so the newest match is chosen rather than a name being hard-coded.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from session_tree.codex_plan import goals_from_plan, read_plan

CODEX_DIR = Path.home() / ".codex"
IDLE_SECONDS = 2 * 60
#: Turn statuses Codex writes, mapped to what the view calls them.
TURN_VIEW = {
    "completed": "completed",
    "failed": "failed",
    "interrupted": "interrupted",
    "inProgress": "in_progress",
}
MAX_EVENT_TEXT = 300


def _newest(root: Path, pattern: str) -> Path | None:
    """The highest-versioned database matching this name."""
    found = sorted(root.glob(pattern))
    return found[-1] if found else None


def _open(path: Path) -> sqlite3.Connection | None:
    """Open a database read-only, or give back None if it cannot be read.

    Codex may be running, so recent rows live in the write-ahead log; opening
    read-only still sees them, and a lock is never taken.
    """
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        con.row_factory = sqlite3.Row
    except sqlite3.Error:
        return None
    return con


def _iso(ms: int | None) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat() if ms else ""


def _event(at_ms: int | None, kind: str, text: str) -> dict[str, Any] | None:
    if not at_ms:
        return None
    return {"at": at_ms, "kind": kind, "text": text[:MAX_EVENT_TEXT], "taskId": None, "iso": _iso(at_ms)}


def _text_of(item: dict[str, Any]) -> str:
    """The readable part of an item, whatever shape it came in."""
    content = item.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if isinstance(c, dict)]
        return " ".join(p for p in parts if p)
    return str(item.get("text") or "")


class _Thread:
    """One Codex thread, assembled from its rows."""

    def __init__(self, row: sqlite3.Row) -> None:
        self.id = str(row["id"])
        self.cwd = str(row["cwd"] or "")
        self.title = str(row["title"] or "")
        self.created = int(row["created_at"] or 0) * 1000
        self.updated = int(row["updated_at"] or 0) * 1000
        self.turns: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.first_prompt: str | None = None
        self.item_count = 0


def _load_turns(history: sqlite3.Connection, threads: dict[str, _Thread]) -> None:
    for row in history.execute(
        "SELECT thread_id, turn_id, status, started_at, completed_at, duration_ms FROM thread_turns",
    ):
        thread = threads.get(str(row["thread_id"]))
        if thread is None:
            continue
        started = int(row["started_at"] or 0) * 1000
        thread.turns.append(
            {
                "id": str(row["turn_id"]),
                "status": TURN_VIEW.get(str(row["status"]), str(row["status"])),
                "startedMs": started or None,
                "endedMs": (int(row["completed_at"]) * 1000) if row["completed_at"] else None,
                "durationMs": int(row["duration_ms"]) if row["duration_ms"] is not None else None,
                "files": [],
                "failures": [],
            }
        )


def _on_prompt(thread: _Thread, item: dict[str, Any], at_ms: int) -> None:
    text = _text_of(item).strip()
    if not text:
        return
    if thread.first_prompt is None:
        thread.first_prompt = text[:400]
    event = _event(at_ms, "prompt", text)
    if event:
        thread.events.append(event)


def _on_file_change(
    thread: _Thread,
    turn: dict[str, Any] | None,
    item: dict[str, Any],
    at_ms: int,
) -> None:
    names = [Path(str(c.get("path", ""))).name for c in (item.get("changes") or []) if isinstance(c, dict)]
    names = [n for n in names if n]
    if turn is not None:
        turn["files"].extend(names)
    event = _event(at_ms, "files", ", ".join(names))
    if event:
        thread.events.append(event)


def _on_command(
    thread: _Thread,
    turn: dict[str, Any] | None,
    item: dict[str, Any],
    at_ms: int,
) -> None:
    if item.get("exitCode") in (0, None):
        return
    command = str(item.get("command") or "")
    if turn is not None:
        turn["failures"].append(command[:120])
    event = _event(at_ms, "command:failed", command)
    if event:
        thread.events.append(event)


def _record_item(thread: _Thread, by_turn: dict[str, dict[str, Any]], row: sqlite3.Row) -> None:
    """Fold one history item into its thread and its turn."""
    try:
        item = json.loads(row["item_json"])
    except (TypeError, ValueError):
        return
    thread.item_count += 1
    at_ms = int(row["created_at_ms"] or 0)
    turn = by_turn.get(str(row["turn_id"]))
    handler = {
        "userMessage": lambda: _on_prompt(thread, item, at_ms),
        "fileChange": lambda: _on_file_change(thread, turn, item, at_ms),
        "commandExecution": lambda: _on_command(thread, turn, item, at_ms),
    }.get(str(row["item_type"]))
    if handler:
        handler()


def _turn_events(thread: _Thread) -> None:
    """A turn ending is a thing that happened, so replay can step to it."""
    for turn in thread.turns:
        if turn["endedMs"]:
            event = _event(turn["endedMs"], "turn:" + str(turn["status"]), "")
            if event:
                thread.events.append(event)


def build_sessions(
    now: float | None = None,
    root: Path | None = None,
    plan_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Return every Codex thread, in the shape the view already reads."""
    now = now or time.time()
    base = root or CODEX_DIR
    state_path = _newest(base, "state_*.sqlite")
    history_path = _newest(base, "thread_history_*.sqlite")
    if state_path is None:
        return []
    state = _open(state_path)
    if state is None:
        return []

    try:
        rows = list(
            state.execute(
                "SELECT id, cwd, title, created_at, updated_at FROM threads",
            )
        )
    except sqlite3.Error:
        return []

    threads = {str(r["id"]): _Thread(r) for r in rows}

    history = _open(history_path) if history_path else None
    if history is not None:
        try:
            _load_turns(history, threads)
            by_turn = {t["id"]: t for th in threads.values() for t in th.turns}
            for row in history.execute(
                "SELECT thread_id, turn_id, item_type, item_json, created_at_ms"
                " FROM thread_items ORDER BY created_at_ms",
            ):
                thread = threads.get(str(row["thread_id"]))
                if thread is not None:
                    _record_item(thread, by_turn, row)
        except sqlite3.Error:
            pass

    sessions = []
    for thread in threads.values():
        _turn_events(thread)
        thread.turns.sort(key=lambda t: t["startedMs"] or 0)
        events = sorted(thread.events, key=lambda e: e["at"])
        quiet = now - thread.updated / 1000 if thread.updated else 1e9
        plan = read_plan(thread.id, plan_dir)
        goals = goals_from_plan(plan) if plan else []
        sessions.append(
            {
                "sessionId": thread.id,
                "agent": "codex",
                "pid": None,
                "name": thread.title or (thread.first_prompt or "")[:60],
                "cwd": thread.cwd,
                "project": Path(thread.cwd).name or thread.cwd,
                "branch": "",
                "kind": "",
                "jobId": "",
                "declaredStatus": "",
                "alive": quiet < IDLE_SECONDS,
                "active": quiet < IDLE_SECONDS,
                "quietSeconds": round(quiet),
                "startedAt": thread.created or None,
                "lastActivity": None,
                "turns": thread.turns,
                "turnCount": len(thread.turns),
                "firstPrompt": thread.first_prompt,
                # Codex keeps no task list, so there is nothing to draw here.
                # Codex keeps no task list of its own. If the plan hook caught an
                # `update_plan` call, that checklist is drawn instead.
                "goals": goals,
                "taskCount": sum(len(g["nodes"]) for g in goals),
                "events": events,
                "spanStart": min((e["at"] for e in events), default=None) or thread.created or None,
                "spanEnd": thread.updated or None,
            }
        )
    return sessions
