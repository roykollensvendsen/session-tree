"""The demo sessions show every case the viewer has to draw.

scripts/demo_fixture.py writes a fake ~/.claude: sessions with everyday goals,
from a birthday party to a street clean-up, so anyone can read the graphs. It
is what a change to the viewer is looked at against. This builds it into an
empty home, reads it with the server's own code in a process of its own, as
the server would, and checks that each case on the list is there and that
every arrow points at a task that exists.
"""

from __future__ import annotations

import collections
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent
READ = "import json, sys; from session_tree import state; json.dump(state.build(), sys.stdout)"


@pytest.fixture(scope="module")
def picture(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """What the server would send for the demo home."""
    home = tmp_path_factory.mktemp("demo-home")
    env = {**os.environ, "HOME": str(home), "PYTHONPATH": str(ROOT / "src")}
    subprocess.run([sys.executable, str(ROOT / "scripts/demo_fixture.py"), str(home)], check=True, env=env)
    out = subprocess.run([sys.executable, "-c", READ], check=True, env=env, capture_output=True, text=True)
    return json.loads(out.stdout)


def goals(picture: dict) -> list[dict]:
    return [g for s in picture["sessions"] for g in s["goals"]]


def nodes(picture: dict) -> list[dict]:
    return [n for g in goals(picture) for n in g["nodes"]]


def test_every_state_a_task_can_be_drawn_in_is_there(picture):
    views = {n["view"] for n in nodes(picture)}
    for view in ("pending", "waiting", "in_progress", "blocked", "stalled", "completed", "abandoned"):
        assert view in views, f"no task is drawn as {view}"


def test_every_label_a_session_can_carry_is_there(picture):
    labels = {s["attention"] for s in picture["sessions"]}
    for label in ("working", "waiting", "stalled", "asking", "ended"):
        assert label in labels, f"no session is labelled {label}"


def test_there_are_sessions_with_one_goal_and_with_many(picture):
    counts = [len(s["goals"]) for s in picture["sessions"]]
    assert 1 in counts, "no session has a single goal"
    assert max(counts) >= 5, "no session has enough goals to page through"


def test_there_are_goals_small_large_and_finished(picture):
    sizes = [len(g["nodes"]) for g in goals(picture)]
    assert 1 in sizes, "no goal has a single task"
    assert max(sizes) >= 80, "no goal is big enough to strain the layout"
    finished = [g for g in goals(picture) if all(n["view"] in ("completed", "abandoned") for n in g["nodes"])]
    assert finished, "no goal is entirely done"


def test_there_is_a_wide_level_and_a_long_chain(picture):
    for g in goals(picture):
        widths = collections.Counter(g["depth"].values())
        if max(widths.values()) >= 60:
            break
    else:
        pytest.fail("no level holds sixty tasks side by side")
    assert max(max(g["depth"].values()) for g in goals(picture)) >= 11, "no chain is twelve tasks long"


def test_there_are_breakdowns_folded_unfolded_and_nested(picture):
    owners = [n for n in nodes(picture) if n.get("breakdown")]
    assert any(n["breakdown"]["folded"] for n in owners), "no breakdown starts folded"
    assert any(not n["breakdown"]["folded"] for n in owners), "no breakdown starts unfolded"
    parents = {n.get("parent") for n in nodes(picture)}
    assert any(n["id"] in parents and n.get("parent") for n in owners), "no breakdown sits inside another"
    waited_on = {d for n in nodes(picture) for d in n["blockedBy"]}
    boxed = [n for n in owners if n["blockedBy"] and n["id"] in waited_on]
    assert boxed, "no breakdown has arrows both into it and out of it"


def test_there_are_questions_of_every_kind(picture):
    sources = {q["source"] for s in picture["sessions"] for q in s["questions"]}
    for source in ("node", "box", "needs-input"):
        assert source in sources, f"no question comes from a {source}"
    assert any(n.get("askDismissed") for n in nodes(picture)), "no question has been put away"


def test_there_are_agents_running_and_finished(picture):
    agents = [a for n in nodes(picture) for a in n.get("agents", [])]
    assert any(a["running"] for a in agents), "no agent is running"
    assert any(not a["running"] for a in agents), "no agent has finished"


def test_a_task_links_to_work_in_another_session(picture):
    assert any(n.get("remote") for n in nodes(picture)), "no task links to another session"


def test_every_arrow_points_at_a_task_that_exists(picture):
    for g in goals(picture):
        ids = {n["id"] for n in g["nodes"]}
        for n in g["nodes"]:
            missing = [d for d in n["blockedBy"] if d not in ids]
            assert not missing, f"{g['title']}: #{n['id']} waits on {missing}, which are not there"
        assert not g["danglingEdges"], f"{g['title']}: links that point nowhere: {g['danglingEdges']}"


def test_every_subject_is_in_plain_words(picture):
    for n in nodes(picture):
        assert not re.search(r"[/_#`]|\.\w{2,3}\b", n["subject"]), f"{n['subject']!r} reads like code"
