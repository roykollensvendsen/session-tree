"""What the reader must get right, tested on synthetic transcripts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from session_tree.state import STALL_SECONDS, TranscriptReader, _apply_views, _components, epoch_ms

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
