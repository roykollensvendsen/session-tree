"""A node can hold a breakdown of the work handed on from it (ADR-ST-005)."""

from __future__ import annotations

from typing import Any

from session_tree.state import (
    TranscriptReader,
    _apply_views,
    _components,
    _link_sessions,
)
from tests.conftest import Transcript


def goals(transcript: Transcript) -> list[dict[str, Any]]:
    reader = TranscriptReader(transcript.path)
    reader.read()
    nodes = list(reader.tasks.values())
    _apply_views(nodes, quiet=0, now=0)
    return _components(nodes)


def node(found: list[dict[str, Any]], task_id: str) -> dict[str, Any]:
    return next(n for g in found for n in g["nodes"] if n["id"] == task_id)


def handed_on(transcript: Transcript) -> tuple[str, list[str]]:
    """A goal node with three steps under it: one done, one working, one open."""
    goal = transcript.create("Fix the popover on phones", at=10, goal="mobile")
    steps = [transcript.create(s, at=11 + i) for i, s in enumerate(("Reproduce", "Fix", "Test"))]
    for step in steps:
        transcript.update(step, at=20, metadata={"parent": goal})
    transcript.update(steps[1], at=21, addBlockedBy=[steps[0]])
    transcript.update(steps[2], at=22, addBlockedBy=[steps[1]])
    transcript.update(steps[0], at=30, status="in_progress")
    transcript.update(steps[0], at=40, status="completed")
    transcript.update(steps[1], at=50, status="in_progress")
    return goal, steps


def test_a_step_names_the_node_it_belongs_to(transcript: Transcript) -> None:
    goal, steps = handed_on(transcript)
    assert node(goals(transcript), steps[0])["parent"] == goal


def test_a_step_is_drawn_with_its_parents_goal(transcript: Transcript) -> None:
    """The steps carry no goal of their own; without the tie each is a graph of one."""
    goal, steps = handed_on(transcript)
    found = goals(transcript)
    mobile = next(g for g in found if g["title"] == "mobile")
    assert {n["id"] for n in mobile["nodes"]} == {goal, *steps}


def test_a_breakdown_is_counted_on_its_node(transcript: Transcript) -> None:
    goal, steps = handed_on(transcript)
    held = node(goals(transcript), goal)["breakdown"]
    assert held["children"] == steps
    assert (held["done"], held["total"]) == (1, 3)


def test_a_breakdown_nothing_outside_uses_is_folded(transcript: Transcript) -> None:
    """The user's rule: fold what only the goal itself uses."""
    goal, _ = handed_on(transcript)
    assert node(goals(transcript), goal)["breakdown"]["folded"] is True


def test_a_breakdown_used_from_outside_is_drawn_unfolded(transcript: Transcript) -> None:
    """Folding would hide the dependency, and a hidden dependency is a wrong picture."""
    goal, steps = handed_on(transcript)
    release = transcript.create("Release", at=60, goal="mobile")
    transcript.update(release, at=61, addBlockedBy=[steps[2]])
    assert node(goals(transcript), goal)["breakdown"]["folded"] is False


def test_an_edge_from_the_parent_itself_does_not_unfold_it(transcript: Transcript) -> None:
    """A goal waiting on its own steps is the breakdown, not a use from outside."""
    goal, steps = handed_on(transcript)
    transcript.update(goal, at=60, addBlockedBy=[steps[2]])
    assert node(goals(transcript), goal)["breakdown"]["folded"] is True


def test_the_worst_step_colours_the_breakdown(transcript: Transcript) -> None:
    goal, steps = handed_on(transcript)
    transcript.update(steps[2], at=60, status="in_progress")  # started, still waiting on step 2
    abandoned = transcript.create("Try a canvas", at=61)
    transcript.update(abandoned, at=62, metadata={"parent": goal}, status="deleted")
    held = node(goals(transcript), goal)["breakdown"]
    assert held["worst"] == "blocked"
    assert held["total"] == 3, "an abandoned step is not counted"


def test_a_node_done_while_a_step_is_open_says_so(transcript: Transcript) -> None:
    """A green node over an open step is the picture being wrong; the chip says it."""
    goal, _ = handed_on(transcript)
    transcript.update(goal, at=60, status="in_progress")
    transcript.update(goal, at=61, status="completed")
    assert node(goals(transcript), goal)["breakdown"]["disagrees"] is True


def test_a_parent_that_does_not_exist_is_a_broken_link(transcript: Transcript) -> None:
    step = transcript.create("Orphan step", at=10, goal="mobile")
    transcript.update(step, at=11, metadata={"parent": "99"})
    mobile = next(g for g in goals(transcript) if g["title"] == "mobile")
    assert mobile["danglingEdges"] == [f"#{step} → #99"]


def session(session_id: str, found: list[dict[str, Any]]) -> dict[str, Any]:
    return {"sessionId": session_id, "name": session_id, "goals": found}


def test_work_in_another_session_links_both_ways(transcript: Transcript, tmp_path: Any) -> None:
    """The node that handed the work on points to it, and the work points back."""
    goal = transcript.create("Review PR 397", at=10, goal="review")
    other = Transcript(tmp_path / "other.jsonl")
    first = other.create("Refute finding one", at=10, goal="refuter")
    second = other.create("Refute finding two", at=11, goal="refuter")
    for step in (first, second):
        other.update(step, at=12, metadata={"parent": f"A#{goal}"})
    other.update(first, at=13, status="completed")
    sessions = [session("A", goals(transcript)), session("B", goals(other))]
    _link_sessions(sessions)
    remote = node(sessions[0]["goals"], goal)["remote"]
    assert (remote["sessionId"], remote["done"], remote["total"]) == ("B", 1, 2)
    upstream = sessions[1]["goals"][0]["upstream"]
    assert (upstream["sessionId"], upstream["nodeId"]) == ("A", goal)


def test_a_node_can_point_at_the_session_doing_its_work(transcript: Transcript, tmp_path: Any) -> None:
    goal = transcript.create("Build the fix", at=10, goal="fix")
    transcript.update(goal, at=11, metadata={"session": "B"})
    other = Transcript(tmp_path / "other.jsonl")
    other.create("Write the test", at=10, goal="fix-work")
    sessions = [session("A", goals(transcript)), session("B", goals(other))]
    _link_sessions(sessions)
    remote = node(sessions[0]["goals"], goal)["remote"]
    assert (remote["sessionId"], remote["total"]) == ("B", 1)


def test_a_link_to_a_missing_session_is_a_broken_link(transcript: Transcript) -> None:
    goal = transcript.create("Build the fix", at=10, goal="fix")
    transcript.update(goal, at=11, metadata={"session": "gone"})
    sessions = [session("A", goals(transcript))]
    _link_sessions(sessions)
    assert sessions[0]["goals"][0]["danglingEdges"] == [f"#{goal} → økt gone"]
