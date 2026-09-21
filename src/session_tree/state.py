"""Reconstruct the live task graph of every Claude Code session on this machine.

Two sources, both maintained by Claude Code itself, so nothing here needs a hook
and nothing can be forgotten:

``~/.claude/sessions/<pid>.json``
    The session register: id, working directory, name, status.
``~/.claude/projects/<slug>/<id>.jsonl``
    The transcript, appended to as the session happens. ``TaskCreate`` and
    ``TaskUpdate`` calls replay into nodes and edges.

Transcripts reach tens of megabytes, so every file is read forward from a
remembered byte offset and never re-parsed.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, TypedDict

from session_tree import codex

HOME = Path.home()
SESSIONS_DIR = HOME / ".claude" / "sessions"
PROJECTS_DIR = HOME / ".claude" / "projects"

# An in_progress node nobody has touched for this long is not being worked on,
# whatever the task list claims. The view colours it as stalled. This is the one
# state that cannot be faked by forgetting to update a task.
STALL_SECONDS = 15 * 60
# A session whose transcript has been silent this long has stopped, even if the
# process is still sitting at a prompt.
IDLE_SECONDS = 2 * 60
BRANCH_CACHE_SECONDS = 20
GIT_TIMEOUT_SECONDS = 3

CREATED_RE = re.compile(r"Task #(\d+) created successfully")

Status = Literal["pending", "in_progress", "completed", "abandoned"]


class HistoryEntry(TypedDict):
    """One status a node was given, and when."""

    at: str
    atMs: int | None
    status: str


class Event(TypedDict):
    """One thing that happened in a session, for the replay timeline."""

    at: int
    kind: str
    text: str
    taskId: str | None
    iso: str


class Node(TypedDict, total=False):
    """One task. The keys are the contract the browser reads."""

    id: str
    subject: str
    description: str
    status: str
    owner: str
    goal: str | None
    blockedBy: list[str]
    blocks: list[str]
    history: list[HistoryEntry]
    created: str | None
    started: str | None
    ended: str | None
    createdMs: int | None
    startedMs: int | None
    endedMs: int | None
    waitingOn: list[str]
    view: str
    durationMs: int | None
    files: list[str]
    failures: list[str]


def epoch_ms(iso: str | None) -> int | None:
    """Convert an ISO-8601 stamp to epoch milliseconds, or None if unparsable."""
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso).timestamp() * 1000)
    except ValueError:
        return None


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open(errors="replace") as handle:
            loaded: Any = json.load(handle)
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _blocks(entry: dict[str, Any]) -> list[dict[str, Any]]:
    message = entry.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _result_text(block: dict[str, Any]) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


class TranscriptReader:
    """Replays one transcript into a task graph, resuming where it left off."""

    def __init__(self, path: Path) -> None:
        """Prepare to read one transcript, starting at its first byte."""
        self.path = path
        self.reset()

    def reset(self) -> None:
        """Forget everything read so far and start from the top of the file."""
        self.offset = 0
        self.tasks: dict[str, Node] = {}
        self.pending_creates: dict[str, tuple[dict[str, Any], str | None]] = {}
        self.last_activity: tuple[str | None, str] | None = None
        self.first_prompt: str | None = None
        self.turns = 0
        self.events: list[Event] = []
        #: The node last set to in_progress. What happens after that is
        #: attributed to it -- Claude Code has no turn id tying a tool call to
        #: a task, so this is "while the node was active", nothing stronger.
        self.active_node: str | None = None
        self.pending_bash: dict[str, str] = {}

    def read(self) -> None:
        """Consume whatever has been appended since the last call."""
        try:
            size = self.path.stat().st_size
        except OSError:
            return
        # RULE: a truncated transcript is reread from the top
        if size < self.offset:  # truncated or replaced: start over
            self.reset()
        if size == self.offset:
            return
        with self.path.open(errors="replace") as handle:
            handle.seek(self.offset)
            for line in handle:
                # RULE: a half written line is left for next time
                if not line.endswith("\n"):  # a half-written final line
                    break
                self.offset += len(line.encode("utf-8", "replace"))
                self._consume(line)

    def _event(self, at: str | None, kind: str, text: str, task_id: str | None = None) -> None:
        stamp = epoch_ms(at)
        if stamp is None or at is None:
            return
        self.events.append({"at": stamp, "kind": kind, "text": text, "taskId": task_id, "iso": at})

    def _node(self, task_id: str) -> Node:
        if task_id not in self.tasks:
            self.tasks[task_id] = {
                "id": task_id,
                "subject": "",
                "description": "",
                "status": "pending",
                "owner": "",
                "goal": None,
                "blockedBy": [],
                "blocks": [],
                "history": [],
                "created": None,
                "started": None,
                "ended": None,
                "files": [],
                "failures": [],
            }
        return self.tasks[task_id]

    def _apply_create(self, task_id: str, payload: dict[str, Any], stamp: str | None) -> None:
        node = self._node(task_id)
        node["subject"] = payload.get("subject", "")
        node["description"] = payload.get("description", "")
        node["created"] = stamp
        meta = payload.get("metadata")
        if isinstance(meta, dict) and meta.get("goal"):
            node["goal"] = str(meta["goal"])
        node["history"].append({"at": stamp or "", "atMs": epoch_ms(stamp), "status": "pending"})
        self._event(stamp, "create", payload.get("subject", ""), task_id)

    def _apply_update(self, payload: dict[str, Any], stamp: str | None) -> None:
        task_id = str(payload.get("taskId", "")).strip()
        if not task_id:
            return
        node = self._node(task_id)
        if payload.get("subject"):
            node["subject"] = str(payload["subject"])
        if payload.get("description"):
            node["description"] = str(payload["description"])
        if payload.get("owner"):
            node["owner"] = str(payload["owner"])
        meta = payload.get("metadata")
        if isinstance(meta, dict) and meta.get("goal"):
            node["goal"] = str(meta["goal"])
        for dep in payload.get("addBlockedBy") or []:
            if str(dep) not in node["blockedBy"]:
                node["blockedBy"].append(str(dep))
        for dep in payload.get("addBlocks") or []:
            if str(dep) not in node["blocks"]:
                node["blocks"].append(str(dep))
        self._apply_status(node, payload.get("status"), stamp, task_id)

    def _apply_status(
        self,
        node: Node,
        status: str | None,
        stamp: str | None,
        task_id: str,
    ) -> None:
        if not status:
            return
        # RULE: an abandoned task is kept not removed
        # A deleted task is not gone. It is a branch that was tried and dropped,
        # which is the thing hardest to remember and most worth keeping.
        node["status"] = "abandoned" if status == "deleted" else status
        node["history"].append(
            {"at": stamp or "", "atMs": epoch_ms(stamp), "status": node["status"]},
        )
        self._event(stamp, "status:" + node["status"], node["subject"], task_id)
        if status == "in_progress":
            self.active_node = task_id
            if not node["started"]:
                node["started"] = stamp
        elif status in ("completed", "deleted") and self.active_node == task_id:
            self.active_node = None
        if status in ("completed", "deleted"):
            node["ended"] = stamp

    def _consume_prompt(self, entry: dict[str, Any], stamp: str | None) -> None:
        message = entry.get("message")
        raw = message.get("content") if isinstance(message, dict) else None
        if isinstance(raw, str):
            text = raw
        else:
            text = " ".join(b.get("text", "") for b in _blocks(entry) if b.get("type") == "text")
        text = text.strip()
        # RULE: harness noise is not mistaken for a prompt
        noise = ("<local-command-stdout>", "<command-name>", "<system-reminder>")
        if not text or text.startswith("<") or any(n in text for n in noise):
            return
        self.turns += 1
        if not self.first_prompt:
            self.first_prompt = text[:400]
        self._event(stamp, "prompt", text[:300])

    def _consume(self, line: str) -> None:
        if '"toolu_' not in line and '"type"' not in line:
            return
        try:
            entry: Any = json.loads(line)
        except ValueError:
            return
        if not isinstance(entry, dict):
            return
        stamp = entry.get("timestamp")

        if entry.get("type") == "user" and not entry.get("isMeta"):
            self._consume_prompt(entry, stamp)

        for block in _blocks(entry):
            kind = block.get("type")
            if kind == "tool_use":
                self._consume_use(block, stamp)
            elif kind == "tool_result":
                self._consume_result(block)

    MAX_TRACKED = 40

    def _note_work(self, name: str, payload: dict[str, Any], use_id: str) -> None:
        """Record what a tool call did, against whichever node is active."""
        if name == "Bash":
            command = payload.get("command")
            if isinstance(command, str):
                self.pending_bash[use_id] = command[:120]
            return
        if name not in ("Edit", "Write", "NotebookEdit") or self.active_node is None:
            return
        path = payload.get("file_path") or payload.get("notebook_path")
        if not isinstance(path, str):
            return
        files = self.tasks[self.active_node]["files"] if self.active_node in self.tasks else None
        if files is None:
            return
        name_only = PurePosixPath(path).name
        if name_only and name_only not in files and len(files) < self.MAX_TRACKED:
            files.append(name_only)

    def _consume_use(self, block: dict[str, Any], stamp: str | None) -> None:
        name = block.get("name", "")
        if stamp:
            self.last_activity = (stamp, name)
        self._note_work(name, block.get("input") or {}, str(block.get("id", "")))
        if name == "TaskCreate":
            self.pending_creates[block.get("id", "")] = (block.get("input") or {}, stamp)
        elif name == "TaskUpdate":
            self._apply_update(block.get("input") or {}, stamp)

    def _consume_result(self, block: dict[str, Any]) -> None:
        use_id = block.get("tool_use_id")
        command = self.pending_bash.pop(str(use_id), None)
        if command and block.get("is_error") and self.active_node in self.tasks:
            failures = self.tasks[self.active_node]["failures"]
            if len(failures) < self.MAX_TRACKED:
                failures.append(command)
        if use_id not in self.pending_creates:
            return
        payload, created = self.pending_creates.pop(use_id)
        match = CREATED_RE.search(_result_text(block))
        if match:
            self._apply_create(match.group(1), payload, created)


_readers: dict[str, TranscriptReader] = {}
_branch_cache: dict[str, tuple[str, float]] = {}


def _branch(cwd: str) -> str:
    """Return the git branch for a directory, cached; this runs on every poll."""
    hit = _branch_cache.get(cwd)
    now = time.time()
    if hit and now - hit[1] < BRANCH_CACHE_SECONDS:
        return hit[0]
    name = ""
    try:
        completed = subprocess.run(  # noqa: S603
            ["git", "-C", cwd, "branch", "--show-current"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
        name = completed.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        name = ""
    _branch_cache[cwd] = (name, now)
    return name


def _transcript_for(session_id: str) -> Path | None:
    if not PROJECTS_DIR.is_dir():
        return None
    for slug in PROJECTS_DIR.iterdir():
        candidate = slug / f"{session_id}.jsonl"
        if candidate.exists():
            return candidate
    return None


def _alive(pid: int | str | None) -> bool:
    """Return whether a process with this id is still on the machine."""
    if pid is None:
        return False
    try:
        return Path(f"/proc/{int(pid)}").exists()
    except (TypeError, ValueError):
        return False


def _depths(nodes: list[Node]) -> dict[str, int]:
    """Return each node's band: how far down the dependency chain it sits."""
    by_id = {n["id"]: n for n in nodes}
    depth: dict[str, int] = {}

    def walk(node_id: str, seen: frozenset[str]) -> int:
        if node_id in depth:
            return depth[node_id]
        if node_id in seen or node_id not in by_id:
            return 0
        deps = [d for d in by_id[node_id]["blockedBy"] if d in by_id]
        value = 1 + max([walk(d, seen | {node_id}) for d in deps], default=-1)
        depth[node_id] = value
        return value

    for node in nodes:
        walk(node["id"], frozenset())
    return depth


class _DisjointSet:
    """Union-find over node ids, used to pick out independent goals."""

    def __init__(self, ids: list[str]) -> None:
        """Start with every id in a group of its own."""
        self.parent = {i: i for i in ids}

    def find(self, item: str) -> str:
        """Return the representative of the group this id belongs to."""
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: str, right: str) -> None:
        """Put two ids in the same group."""
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[b] = a


def _group(nodes: list[Node]) -> dict[str, list[Node]]:
    """Group nodes that share a dependency edge or an explicit goal label."""
    sets = _DisjointSet([n["id"] for n in nodes])
    for node in nodes:
        for dep in node["blockedBy"] + node["blocks"]:
            if dep in sets.parent:
                sets.union(node["id"], dep)

    first_of_goal: dict[str, str] = {}
    for node in nodes:
        goal = node["goal"]
        if not goal:
            continue
        if goal in first_of_goal:
            sets.union(first_of_goal[goal], node["id"])
        else:
            first_of_goal[goal] = node["id"]

    # RULE: independent goals are separate graphs
    groups: dict[str, list[Node]] = {}
    for node in nodes:
        groups.setdefault(sets.find(node["id"]), []).append(node)
    return groups


def _components(nodes: list[Node]) -> list[dict[str, Any]]:
    """Group nodes into independent goals.

    An explicit ``metadata.goal`` wins where it is set; otherwise the connected
    components of the dependency graph name themselves, which costs no
    discipline to maintain.
    """
    groups = _group(nodes)

    goals: list[dict[str, Any]] = []
    for root, members in groups.items():
        members.sort(key=lambda n: int(n["id"]) if n["id"].isdigit() else 0)
        label = next((m["goal"] for m in members if m["goal"]), None)
        if not label:
            live = [m for m in members if m["status"] != "abandoned"]
            label = (live or members)[0]["subject"]
        goals.append(
            {
                "id": root,
                "title": label,
                "nodes": members,
                "depth": _depths(members),
                # Ten nodes with no blockedBy between them draw as a graph and are
                # a list. The view says so rather than letting the shape imply it.
                "hasEdges": any(m["blockedBy"] for m in members),
                "danglingEdges": [],
            }
        )
    goals.sort(key=lambda g: min((int(n["id"]) for n in g["nodes"] if n["id"].isdigit()), default=0))
    return goals


def _apply_views(nodes: list[Node], quiet: float, now: float) -> None:
    """Set the colour each node is drawn in, and how long it has taken."""
    open_ids = {n["id"] for n in nodes if n["status"] in ("pending", "in_progress")}
    for node in nodes:
        blocking = [d for d in node["blockedBy"] if d in open_ids]
        node["waitingOn"] = blocking
        node["view"] = node["status"]
        if node["status"] == "in_progress":
            # RULE: a started node waiting on open work is blocked
            if blocking:
                node["view"] = "blocked"
            # RULE: a silent started node goes stalled
            elif quiet > STALL_SECONDS:
                node["view"] = "stalled"
        elif node["status"] == "pending" and blocking:
            node["view"] = "waiting"
        node["createdMs"] = epoch_ms(node["created"])
        node["startedMs"] = epoch_ms(node["started"])
        node["endedMs"] = epoch_ms(node["ended"])
        start, end = node["startedMs"], node["endedMs"]
        if start and end:
            node["durationMs"] = end - start
        elif start and node["status"] == "in_progress":
            node["durationMs"] = int(now * 1000) - start
        else:
            node["durationMs"] = None


def _sessions_on_disk() -> list[dict[str, Any]]:
    if not SESSIONS_DIR.is_dir():
        return []
    found = []
    for path in SESSIONS_DIR.glob("*.json"):
        info = _read_json(path)
        if info and info.get("sessionId"):
            found.append(info)
    return found


def _describe(info: dict[str, Any], reader: TranscriptReader, mtime: float, now: float) -> dict[str, Any]:
    quiet = now - mtime
    nodes = list(reader.tasks.values())
    _apply_views(nodes, quiet, now)
    cwd = info.get("cwd") or ""
    events = sorted(reader.events, key=lambda e: e["at"])
    return {
        "sessionId": info["sessionId"],
        "agent": "claude",
        "pid": info.get("pid"),
        "name": info.get("name") or "",
        "cwd": cwd,
        "project": Path(cwd).name or cwd,
        "branch": _branch(cwd) if cwd and Path(cwd).is_dir() else "",
        "kind": info.get("kind") or "",
        "jobId": info.get("jobId") or "",
        "declaredStatus": info.get("status") or "",
        "alive": _alive(info.get("pid", -1)),
        "active": _alive(info.get("pid", -1)) and quiet < IDLE_SECONDS,
        "quietSeconds": round(quiet),
        "startedAt": info.get("startedAt"),
        "lastActivity": reader.last_activity,
        "promptTurns": reader.turns,
        "firstPrompt": reader.first_prompt,
        "goals": _components(nodes),
        "taskCount": len(nodes),
        "turns": [],
        "turnCount": 0,
        "events": events,
        "spanStart": min((e["at"] for e in events), default=None) or info.get("startedAt"),
        "spanEnd": int(mtime * 1000) if mtime else None,
    }


def build(now: float | None = None) -> dict[str, Any]:
    """Return the current picture of every session, whichever agent ran it.

    Claude Code and Codex are read from different places and do not carry the
    same things: only one of them keeps a task list. Each session says which
    agent it came from, and the view shows what that agent actually recorded
    rather than a common shape neither of them fills.
    """
    now = now or time.time()
    sessions: list[dict[str, Any]] = []
    seen: set[str] = set()

    for info in _sessions_on_disk():
        session_id = str(info["sessionId"])
        if session_id in seen:
            continue
        seen.add(session_id)
        path = _transcript_for(session_id)
        if not path:
            continue
        reader = _readers.get(session_id)
        if reader is None:
            reader = _readers[session_id] = TranscriptReader(path)
        reader.read()
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        sessions.append(_describe(info, reader, mtime, now))

    try:
        sessions.extend(codex.build_sessions(now))
    except Exception as error:  # noqa: BLE001 - one agent must not hide the other
        sys.stderr.write(f"codex: {error!r}\n")

    sessions.sort(key=lambda s: (not s["active"], not s["alive"], -(s.get("startedAt") or 0)))
    return {"now": now, "sessions": sessions}
