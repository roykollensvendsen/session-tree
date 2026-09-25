"""A question the user dismissed no longer waits (ADR-ST-006)."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from typing import TYPE_CHECKING

import pytest

from session_tree import server
from session_tree.state import (
    TranscriptReader,
    _mark_dismissed,
    _not_dismissed,
    _questions,
    add_dismissal,
    dismissal_key,
    load_dismissed,
)

if TYPE_CHECKING:
    from pathlib import Path

    from tests.conftest import Transcript


def read(transcript: Transcript) -> TranscriptReader:
    reader = TranscriptReader(transcript.path)
    reader.read()
    return reader


def _asked(transcript: Transcript, text: str) -> TranscriptReader:
    first = transcript.create("Roy approves the merge", at=10)
    transcript.update(first, at=20, status="in_progress", metadata={"ask": text})
    return read(transcript)


def test_a_dismissed_question_no_longer_waits(transcript: Transcript) -> None:
    """A question answered in another session can be put away from the list."""
    reader = _asked(transcript, "Merge #414?")
    asked = _questions(reader, idle=False)
    dismissed = {dismissal_key("s1", asked[0])}
    assert _not_dismissed("s1", asked, dismissed) == []


def test_a_new_question_on_a_dismissed_node_asks_again(transcript: Transcript) -> None:
    """The dismissal is of one question, not of the node for good."""
    reader = _asked(transcript, "Merge #414?")
    old = _questions(reader, idle=False)[0]
    transcript.update("1", at=30, metadata={"ask": "Push the branch?"})
    reader.read()
    asked = _questions(reader, idle=False)
    assert [q["text"] for q in _not_dismissed("s1", asked, {dismissal_key("s1", old)})] == [
        "Push the branch?",
    ]


def test_a_dismissal_is_one_sessions_own(transcript: Transcript) -> None:
    reader = _asked(transcript, "Merge #414?")
    asked = _questions(reader, idle=False)
    assert _not_dismissed("s2", asked, {dismissal_key("s1", asked[0])}) == asked


def test_a_dismissed_question_stays_on_its_node_marked(transcript: Transcript) -> None:
    """The node keeps its question for the tooltip, and says it was put away."""
    reader = _asked(transcript, "Merge #414?")
    asked = _questions(reader, idle=False)
    nodes = list(reader.tasks.values())
    _mark_dismissed(nodes, asked, _not_dismissed("s1", asked, {dismissal_key("s1", asked[0])}))
    assert [(n["ask"], n["askDismissed"]) for n in nodes] == [("Merge #414?", True)]
    _mark_dismissed(nodes, asked, asked)
    assert [n["askDismissed"] for n in nodes] == [False]


def test_a_dismissal_is_kept_across_reads(tmp_path: Path) -> None:
    path = tmp_path / "dismissed.json"
    question = {"source": "node", "node": "71", "text": "Merge #414?"}
    add_dismissal("s1", question, path=path)
    add_dismissal("s1", question, path=path)
    assert load_dismissed(path) == {dismissal_key("s1", question)}
    assert len(json.loads(path.read_text())) == 1


def test_a_missing_or_broken_file_dismisses_nothing(tmp_path: Path) -> None:
    assert load_dismissed(tmp_path / "absent.json") == set()
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    assert load_dismissed(broken) == set()


@pytest.fixture
def running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The real handler on a free port, writing dismissals under tmp_path."""
    path = tmp_path / "dismissed.json"
    monkeypatch.setattr(server, "DISMISSED_FILE", path)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", path
    httpd.shutdown()


def _post(url: str, body: dict, headers: dict[str, str]) -> int:
    request = urllib.request.Request(  # noqa: S310 - local test server
        url + "/api/dismiss", data=json.dumps(body).encode(), method="POST", headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - local test server
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


QUESTION = {"session": "s1", "source": "node", "node": "71", "text": "Merge #414?"}


def test_a_dismissal_needs_the_pages_own_header(running) -> None:
    """Another site's page cannot send the header without a preflight nobody answers."""
    url, path = running
    status = _post(url, QUESTION, {"Content-Type": "application/json"})
    assert status == HTTPStatus.FORBIDDEN
    assert not path.exists()


def test_the_page_can_dismiss_a_question(running) -> None:
    url, path = running
    headers = {"Content-Type": "application/json", "X-Session-Tree": "dismiss"}
    assert _post(url, QUESTION, headers) == HTTPStatus.NO_CONTENT
    q = {k: QUESTION[k] for k in ("source", "node", "text")}
    assert load_dismissed(path) == {dismissal_key("s1", q)}
