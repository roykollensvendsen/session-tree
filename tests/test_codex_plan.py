"""Turning a Codex checklist into a graph, including when the text lies.

The edges are written by the model into free text rather than into a field
anything validated, so the cases that matter are the malformed ones.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING, Any

from session_tree.codex_plan import goals_from_plan, read_plan

if TYPE_CHECKING:
    from pathlib import Path

HOOK = "hooks/codex-capture-plan.py"


def plan(steps: list[tuple[str, str]], explanation: str | None = None) -> dict[str, Any]:
    return {
        "explanation": explanation,
        "steps": [{"step": s, "status": st} for s, st in steps],
    }


def only(result: list[dict[str, Any]]) -> dict[str, Any]:
    assert len(result) == 1
    return result[0]


def test_a_dependency_written_in_the_explanation_becomes_an_edge() -> None:
    goal = only(
        goals_from_plan(
            plan(
                [("Read", "completed"), ("Build", "in_progress"), ("Draw", "pending")],
                explanation="deps: 2<-1; 3<-2",
            )
        )
    )
    assert [n["blockedBy"] for n in goal["nodes"]] == [[], ["1"], ["2"]]
    assert goal["hasEdges"] is True


def test_a_dependency_written_on_the_step_becomes_an_edge() -> None:
    goal = only(
        goals_from_plan(
            plan(
                [("[1] Read", "completed"), ("[2<-1] Build", "pending")],
            )
        )
    )
    assert goal["nodes"][1]["blockedBy"] == ["1"]
    # the marker is not left in the text the reader sees
    assert goal["nodes"][0]["subject"] == "Read"
    assert goal["nodes"][1]["subject"] == "Build"


def test_an_edge_to_a_step_that_does_not_exist_is_reported_not_dropped() -> None:
    """Silently discarding it would leave a graph nobody can tell is wrong."""
    goal = only(
        goals_from_plan(
            plan(
                [("Read", "completed"), ("Build", "pending")],
                explanation="deps: 2<-9",
            )
        )
    )
    assert goal["danglingEdges"] == ["#2→#9"]
    assert goal["nodes"][1]["blockedBy"] == []


def test_a_plan_with_no_dependencies_says_so() -> None:
    """Order is not dependency, and the view has to be able to say which it has."""
    goal = only(goals_from_plan(plan([("A", "pending"), ("B", "pending")])))
    assert goal["hasEdges"] is False
    assert all(not n["blockedBy"] for n in goal["nodes"])


def test_a_step_waiting_on_open_work_is_not_drawn_as_ready() -> None:
    goal = only(
        goals_from_plan(
            plan(
                [("Read", "pending"), ("Build", "in_progress")],
                explanation="deps: 2<-1",
            )
        )
    )
    assert goal["nodes"][1]["view"] == "blocked"
    goal = only(
        goals_from_plan(
            plan(
                [("Read", "completed"), ("Build", "in_progress")],
                explanation="deps: 2<-1",
            )
        )
    )
    assert goal["nodes"][1]["view"] == "in_progress"


def test_a_step_cannot_depend_on_itself() -> None:
    goal = only(goals_from_plan(plan([("A", "pending")], explanation="deps: 1<-1")))
    assert goal["nodes"][0]["blockedBy"] == []


def test_an_empty_plan_is_not_a_graph() -> None:
    assert goals_from_plan({"steps": []}) == []
    assert goals_from_plan({}) == []


def test_the_hook_writes_a_plan_the_reader_can_load(tmp_path: Path) -> None:
    """The hook and the reader are the two halves of one contract."""
    payload = {
        "session_id": "t-1",
        "turn_id": "x",
        "cwd": "/home/dev/x",
        "tool_name": "update_plan",
        "tool_input": {
            "explanation": "deps: 2<-1",
            "plan": [{"step": "A", "status": "completed"}, {"step": "B", "status": "pending"}],
        },
        "tool_response": {},
        "tool_use_id": "u",
    }
    result = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env={"SESSION_TREE_PLAN_DIR": str(tmp_path), "PATH": "/usr/bin"},
    )
    assert result.returncode == 0
    loaded = read_plan("t-1", tmp_path)
    assert loaded is not None
    assert only(goals_from_plan(loaded))["nodes"][1]["blockedBy"] == ["1"]


def test_the_hook_never_fails_a_turn_on_bad_input(tmp_path: Path) -> None:
    """It runs inside Codex's turn, so a crash here would be Codex's crash."""
    for bad in ("", "not json", "[]", '{"session_id": null}', '{"tool_input": {"plan": "x"}}'):
        done = subprocess.run(
            [sys.executable, HOOK],
            input=bad,
            text=True,
            capture_output=True,
            check=False,
            env={"SESSION_TREE_PLAN_DIR": str(tmp_path), "PATH": "/usr/bin"},
        )
        assert done.returncode == 0, f"non-zero exit on {bad!r}"
