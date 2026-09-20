"""What the Codex reader must get right, on databases built for the test.

Codex keeps its history in SQLite, and the filenames carry a schema version
that moves when it upgrades. None of this reads the machine's real sessions.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from session_tree.codex import build_sessions

NOW_MS = 1_789_000_000_000


def write_state(root: Path, version: int, threads: list[dict[str, Any]]) -> None:
    """Write a state database in the shape Codex uses."""
    con = sqlite3.connect(root / f"state_{version}.sqlite")
    con.execute(
        "CREATE TABLE threads (id TEXT, rollout_path TEXT, created_at INT,"
        " updated_at INT, source TEXT, model_provider TEXT, cwd TEXT, title TEXT)",
    )
    for t in threads:
        con.execute(
            "INSERT INTO threads (id, created_at, updated_at, cwd, title) VALUES (?, ?, ?, ?, ?)",
            (t["id"], t["created"], t["updated"], t.get("cwd", "/home/dev/unnamed"), t.get("title", "")),
        )
    con.commit()
    con.close()


def write_history(
    root: Path,
    version: int,
    turns: list[dict[str, Any]],
    items: list[dict[str, Any]],
) -> None:
    """Write a thread-history database in the shape Codex uses."""
    con = sqlite3.connect(root / f"thread_history_{version}.sqlite")
    con.execute(
        "CREATE TABLE thread_turns (thread_id TEXT, turn_id TEXT, status TEXT,"
        " started_at INT, completed_at INT, duration_ms INT)",
    )
    con.execute(
        "CREATE TABLE thread_items (thread_id TEXT, turn_id TEXT, item_id TEXT,"
        " created_at_ms INT, item_json TEXT, item_type TEXT)",
    )
    for t in turns:
        con.execute(
            "INSERT INTO thread_turns VALUES (?, ?, ?, ?, ?, ?)",
            (t["thread"], t["turn"], t["status"], t["started"], t.get("completed"), t.get("duration")),
        )
    for i in items:
        con.execute(
            "INSERT INTO thread_items VALUES (?, ?, ?, ?, ?, ?)",
            (i["thread"], i.get("turn", ""), i.get("id", "x"), i["at"], json.dumps(i["json"]), i["type"]),
        )
    con.commit()
    con.close()


@pytest.fixture
def codex_home(tmp_path: Path) -> Path:
    """A Codex directory with one thread, two turns, a file change and a failure."""
    write_state(
        tmp_path,
        3,
        [
            {
                "id": "t1",
                "created": 1_789_000_000,
                "updated": 1_789_000_300,
                "cwd": "/home/dev/orchard",
                "title": "make the importer stop timing out",
            },
        ],
    )
    write_history(
        tmp_path,
        2,
        turns=[
            {
                "thread": "t1",
                "turn": "a",
                "status": "completed",
                "started": 1_789_000_010,
                "completed": 1_789_000_040,
                "duration": 30_000,
            },
            {
                "thread": "t1",
                "turn": "b",
                "status": "failed",
                "started": 1_789_000_100,
                "completed": 1_789_000_105,
                "duration": 5_000,
            },
        ],
        items=[
            {
                "thread": "t1",
                "turn": "a",
                "at": NOW_MS + 10_000,
                "type": "userMessage",
                "json": {"content": "the nightly import times out"},
            },
            {
                "thread": "t1",
                "turn": "a",
                "at": NOW_MS + 20_000,
                "type": "fileChange",
                "json": {
                    "changes": [
                        {"path": "/home/dev/orchard/importer.py"},
                        {"path": "/home/dev/orchard/settings.toml"},
                    ],
                    "status": "completed",
                },
            },
            {
                "thread": "t1",
                "turn": "b",
                "at": NOW_MS + 30_000,
                "type": "commandExecution",
                "json": {"command": "pytest -q", "exitCode": 1},
            },
            {
                "thread": "t1",
                "turn": "b",
                "at": NOW_MS + 31_000,
                "type": "commandExecution",
                "json": {"command": "ls", "exitCode": 0},
            },
        ],
    )
    return tmp_path


def only(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    assert len(sessions) == 1
    return sessions[0]


def test_a_codex_thread_is_read_without_inventing_a_graph(codex_home: Path) -> None:
    session = only(build_sessions(root=codex_home))
    assert session["agent"] == "codex"
    assert session["goals"] == []
    assert session["taskCount"] == 0
    assert session["name"] == "make the importer stop timing out"
    assert session["project"] == "orchard"


def test_the_newest_schema_version_is_the_one_read(codex_home: Path) -> None:
    # An upgrade leaves the old file in place; reading it would show stale threads.
    write_state(
        codex_home,
        4,
        [
            {
                "id": "t2",
                "created": 1_789_000_000,
                "updated": 1_789_000_000,
                "cwd": "/home/dev/newer",
                "title": "after the upgrade",
            },
        ],
    )
    assert only(build_sessions(root=codex_home))["name"] == "after the upgrade"


def test_a_turn_keeps_its_status_and_how_long_it_took(codex_home: Path) -> None:
    turns = only(build_sessions(root=codex_home))["turns"]
    assert [t["status"] for t in turns] == ["completed", "failed"]
    assert [t["durationMs"] for t in turns] == [30_000, 5_000]


def test_the_files_a_turn_touched_are_kept_with_it(codex_home: Path) -> None:
    turns = only(build_sessions(root=codex_home))["turns"]
    assert turns[0]["files"] == ["importer.py", "settings.toml"]
    assert turns[1]["files"] == []


def test_only_a_command_that_failed_is_recorded_as_one(codex_home: Path) -> None:
    turns = only(build_sessions(root=codex_home))["turns"]
    assert turns[1]["failures"] == ["pytest -q"]
    assert turns[0]["failures"] == []


def test_the_timeline_has_the_shape_replay_already_reads(codex_home: Path) -> None:
    session = only(build_sessions(root=codex_home))
    assert session["events"], "replay needs events"
    for event in session["events"]:
        assert set(event) == {"at", "kind", "text", "taskId", "iso"}
        assert isinstance(event["at"], int)
    assert [e["at"] for e in session["events"]] == sorted(e["at"] for e in session["events"])
    assert "prompt" in {e["kind"] for e in session["events"]}
    assert session["spanStart"] <= session["events"][0]["at"]


def test_a_directory_with_no_codex_is_not_an_error(tmp_path: Path) -> None:
    assert build_sessions(root=tmp_path) == []


def test_a_thread_with_no_history_still_appears(tmp_path: Path) -> None:
    """A thread that has only just started has no turns; it is still a session."""
    write_state(
        tmp_path,
        1,
        [
            {
                "id": "t9",
                "created": 1_789_000_000,
                "updated": 1_789_000_000,
                "cwd": "/home/dev/fresh",
                "title": "just opened",
            },
        ],
    )
    session = only(build_sessions(root=tmp_path))
    assert session["turns"] == []
    assert session["events"] == []
