"""What the reader must get right, tested on synthetic transcripts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from session_tree.state import (
    STALL_SECONDS,
    TranscriptReader,
    _apply_views,
    _attach_agents,
    _attention,
    _components,
    epoch_ms,
)

if TYPE_CHECKING:
    from tests.conftest import Transcript


def read(transcript: Transcript) -> TranscriptReader:
    reader = TranscriptReader(transcript.path)
    reader.read()
    return reader


def test_an_abandoned_task_is_kept_not_removed(built: Transcript) -> None:
    reader = read(built)
    dropped = reader.tasks["5"]
    assert dropped["status"] == "abandoned"
    assert dropped["subject"] == "Try websockets"


def test_a_started_node_waiting_on_open_work_is_blocked(built: Transcript) -> None:
    reader = read(built)
    nodes = list(reader.tasks.values())
    _apply_views(nodes, quiet=5, now=0)
    # #2 is in_progress but #1 completed, so nothing holds it
    assert reader.tasks["2"]["view"] == "in_progress"
    # make #1 open again and #2 must go red
    reader.tasks["1"]["status"] = "pending"
    _apply_views(list(reader.tasks.values()), quiet=5, now=0)
    assert reader.tasks["2"]["view"] == "blocked"


def test_a_silent_started_node_goes_stalled(built: Transcript) -> None:
    reader = read(built)
    nodes = list(reader.tasks.values())
    _apply_views(nodes, quiet=STALL_SECONDS + 1, now=0)
    assert reader.tasks["2"]["view"] == "stalled"
    _apply_views(nodes, quiet=STALL_SECONDS - 1, now=0)
    assert reader.tasks["2"]["view"] == "in_progress"


def test_independent_goals_are_separate_graphs(built: Transcript) -> None:
    reader = read(built)
    goals = _components(list(reader.tasks.values()))
    titles = sorted(str(g["title"]) for g in goals)
    assert titles == ["docs", "tool"]


def test_a_dependency_chain_gives_increasing_bands(built: Transcript) -> None:
    reader = read(built)
    goals = _components(list(reader.tasks.values()))
    tool = next(g for g in goals if g["title"] == "tool")
    depth = tool["depth"]
    assert depth["1"] < depth["2"] < depth["3"]


def test_reading_in_pieces_matches_reading_at_once(built: Transcript) -> None:
    whole = read(built)
    piecemeal = TranscriptReader(built.path)
    text = built.path.read_text()
    half = len(text) // 2
    built.path.write_text(text[: text.rindex("\n", 0, half) + 1])
    piecemeal.read()
    built.path.write_text(text)
    piecemeal.read()
    assert piecemeal.tasks == whole.tasks
    assert piecemeal.events == whole.events


def test_what_the_user_said_reaches_the_timeline(built: Transcript) -> None:
    reader = read(built)
    prompts = [e for e in reader.events if e["kind"] == "prompt"]
    assert [p["text"] for p in prompts] == ["build me a thing"]


def test_harness_noise_is_not_mistaken_for_a_prompt(transcript: Transcript) -> None:
    # The noise does not begin with the marker -- a leading "<" is caught by a
    # different check, and testing that instead would prove nothing about this.
    transcript.prompt("run the tests <system-reminder>be careful</system-reminder>", at=1)
    transcript.prompt("output was <local-command-stdout>ok</local-command-stdout>", at=2)
    transcript.prompt("a real question", at=3)
    reader = read(transcript)
    assert [e["text"] for e in reader.events if e["kind"] == "prompt"] == ["a real question"]


def test_a_truncated_transcript_is_reread_from_the_top(built: Transcript) -> None:
    reader = read(built)
    assert reader.tasks
    built.path.write_text("")
    reader.read()
    assert reader.tasks == {}


def test_a_half_written_line_is_left_for_next_time(transcript: Transcript) -> None:
    transcript.create("First", at=1)
    reader = read(transcript)
    with transcript.path.open("a") as handle:
        handle.write('{"type":"assistant","timest')
    reader.read()
    assert len(reader.tasks) == 1
    assert reader.offset == len(transcript.path.read_text().encode()) - len('{"type":"assistant","timest')


def test_a_stamp_with_a_zulu_suffix_parses() -> None:
    # The Z form is what transcripts carry; it must agree with the explicit
    # offset rather than be read as local time.
    assert epoch_ms("2026-09-18T20:00:00.000Z") == epoch_ms("2026-09-18T20:00:00.000+00:00")
    assert epoch_ms("2026-09-18T21:00:00.000Z") - epoch_ms("2026-09-18T20:00:00.000Z") == 3_600_000
    assert epoch_ms("not a date") is None
    assert epoch_ms(None) is None


def test_a_file_edited_while_a_node_was_active_is_kept_with_it(transcript: Transcript) -> None:
    """A green node that cannot say what came out of it answers half the question."""
    first = transcript.create("Write the parser", at=10)
    transcript.create("Write the server", at=11)
    transcript.update(first, at=20, status="in_progress")
    transcript.tool("Write", at=30, payload={"file_path": "/home/dev/app/parser.py"})
    transcript.tool("Edit", at=31, payload={"file_path": "/home/dev/app/parser.py"})
    transcript.tool("Edit", at=32, payload={"file_path": "/home/dev/app/settings.toml"})
    reader = read(transcript)
    assert reader.tasks["1"]["files"] == ["parser.py", "settings.toml"]
    assert reader.tasks["2"]["files"] == []


def test_a_failed_command_is_kept_with_the_node_that_ran_it(transcript: Transcript) -> None:
    first = transcript.create("Run the suite", at=10)
    transcript.update(first, at=20, status="in_progress")
    transcript.tool("Bash", at=30, payload={"command": "pytest -q"}, failed=True)
    transcript.tool("Bash", at=31, payload={"command": "ls"}, failed=False)
    reader = read(transcript)
    assert reader.tasks["1"]["failures"] == ["pytest -q"]


def test_work_done_with_no_node_active_is_attributed_to_none(transcript: Transcript) -> None:
    """Guessing an owner would put work under a node that was already finished."""
    first = transcript.create("Write the parser", at=10)
    transcript.update(first, at=20, status="in_progress")
    transcript.update(first, at=30, status="completed")
    transcript.tool("Write", at=40, payload={"file_path": "/home/dev/app/stray.py"})
    transcript.tool("Bash", at=41, payload={"command": "false"}, failed=True)
    reader = read(transcript)
    assert reader.tasks["1"]["files"] == []
    assert reader.tasks["1"]["failures"] == []


def test_a_graph_without_dependencies_says_it_has_none(built: Transcript) -> None:
    """Otherwise a list draws as a graph and nothing tells the reader which it is."""
    reader = read(built)
    goals = _components(list(reader.tasks.values()))
    tool = next(g for g in goals if g["title"] == "tool")
    docs = next(g for g in goals if g["title"] == "docs")
    assert tool["hasEdges"] is True
    assert docs["hasEdges"] is False


def test_a_session_waiting_on_an_answer_is_told_apart_from_one_working() -> None:
    """The point of the view is knowing which sessions need you, and when."""
    assert _attention("idle", quiet=5, alive=True) == "waiting"
    assert _attention("busy", quiet=5, alive=True) == "working"
    assert _attention("busy", quiet=STALL_SECONDS + 1, alive=True) == "stalled"
    assert _attention("busy", quiet=5, alive=False) == "ended"


def test_a_session_busy_but_silent_is_not_reported_as_working() -> None:
    """Claiming busy while nothing is written is the case worth going in for."""
    assert _attention("busy", quiet=STALL_SECONDS - 1, alive=True) == "working"
    assert _attention("busy", quiet=STALL_SECONDS + 1, alive=True) == "stalled"


def test_agents_spawned_before_any_task_belong_to_the_session(transcript: Transcript) -> None:
    """A review panel runs before the work is decomposed; inventing an owner would lie."""
    transcript.tool("Agent", at=5, payload={"description": "Requirements seat"})
    first = transcript.create("Collect the findings", at=10)
    transcript.update(first, at=20, status="in_progress")
    transcript.tool("Agent", at=30, payload={"description": "Adversary seat"})
    reader = read(transcript)
    loose = _attach_agents(list(reader.tasks.values()), reader.spawns, [])
    assert [a["description"] for a in loose] == ["Requirements seat"]
    assert [a["description"] for a in reader.tasks["1"]["agents"]] == ["Adversary seat"]


def test_an_agent_still_running_is_marked_as_such(transcript: Transcript) -> None:
    first = transcript.create("Run the panel", at=10)
    transcript.update(first, at=20, status="in_progress")
    transcript.tool("Agent", at=30, payload={"description": "Finished seat"})
    transcript.spawn_without_result("Still running seat", at=40)
    reader = read(transcript)
    _attach_agents(list(reader.tasks.values()), reader.spawns, [])
    agents = reader.tasks["1"]["agents"]
    assert [a["running"] for a in agents] == [False, True]


def test_agents_are_not_added_again_on_every_pass(transcript: Transcript) -> None:
    """The nodes outlive a poll; appending each time would multiply the panel."""
    first = transcript.create("Run the panel", at=10)
    transcript.update(first, at=20, status="in_progress")
    transcript.tool("Agent", at=30, payload={"description": "Only seat"})
    reader = read(transcript)
    nodes = list(reader.tasks.values())
    for _ in range(3):
        _attach_agents(nodes, reader.spawns, [])
    assert len(reader.tasks["1"]["agents"]) == 1
