"""A new question is pushed to the phone through ntfy, once (ADR-ST-009)."""

import io
import json
import threading
import time
import urllib.error

from session_tree import notify, server


def _picture(*questions: tuple[str, str], name: str = "moving house") -> dict:
    """A picture with one session asking each (node, text) given."""
    return {
        "sessions": [
            {
                "sessionId": "s1",
                "name": name,
                "project": "home",
                "questions": [{"source": "node", "node": node, "text": text} for node, text in questions],
            }
        ]
    }


def _notifier(tmp_path, click: str = "http://100.66.86.99:8787/", lock: str = "ntfy.lock"):
    sent: list[tuple[str, dict]] = []
    settings = notify.Settings(topic="https://ntfy.sh/a-long-random-topic", click=click)
    return (
        notify.Notifier(
            settings,
            send=lambda url, body: sent.append((url, body)),
            spawn=lambda job: job(),
            lock=tmp_path / lock,
        ),
        sent,
    )


def test_questions_waiting_at_start_up_are_not_sent(tmp_path):
    notifier, sent = _notifier(tmp_path)
    notifier.look(_picture(("3", "Which boxes go first?")))
    assert sent == []


def test_a_new_question_is_sent_with_its_session_and_text(tmp_path):
    notifier, sent = _notifier(tmp_path)
    notifier.look(_picture())
    notifier.look(_picture(("3", "Which boxes go first? " + "x" * 300)))
    assert len(sent) == 1
    url, body = sent[0]
    assert url == "https://ntfy.sh/"
    assert body["topic"] == "a-long-random-topic"
    assert body["title"] == "Spørsmål i moving house"
    assert body["message"].startswith("Which boxes go first?")
    assert len(body["message"]) <= notify.MAX_TEXT
    assert body["click"] == "http://100.66.86.99:8787/"


def test_a_session_with_no_name_is_called_by_its_project(tmp_path):
    notifier, sent = _notifier(tmp_path)
    notifier.look(_picture(name=""))
    notifier.look(_picture(("3", "Now?"), name=""))
    assert sent[0][1]["title"] == "Spørsmål i home"


def test_a_question_already_sent_is_not_sent_again(tmp_path):
    notifier, sent = _notifier(tmp_path)
    notifier.look(_picture())
    for _ in range(3):
        notifier.look(_picture(("3", "Which boxes go first?")))
    assert len(sent) == 1


def test_a_question_that_comes_back_is_sent_again(tmp_path):
    notifier, sent = _notifier(tmp_path)
    notifier.look(_picture())
    notifier.look(_picture(("3", "Which boxes go first?")))
    notifier.look(_picture())
    notifier.look(_picture(("3", "Which boxes go first?")))
    assert len(sent) == 2


def test_no_link_is_sent_when_none_is_set_up(tmp_path):
    notifier, sent = _notifier(tmp_path, click="")
    notifier.look(_picture())
    notifier.look(_picture(("3", "Now?")))
    assert "click" not in sent[0][1]


def test_only_the_server_holding_the_lock_sends(tmp_path):
    """Two servers watch the same sessions, one per address; the phone gets one message."""
    first, sent_first = _notifier(tmp_path)
    second, sent_second = _notifier(tmp_path)
    for n in (first, second):
        n.look(_picture())
    for n in (first, second):
        n.look(_picture(("3", "Now?")))
    assert len(sent_first) + len(sent_second) == 1


def test_the_other_server_takes_over_when_the_sender_stops(tmp_path):
    first, sent_first = _notifier(tmp_path)
    second, sent_second = _notifier(tmp_path)
    for n in (first, second):
        n.look(_picture())
    first.close()
    second.look(_picture(("3", "Now?")))
    assert (len(sent_first), len(sent_second)) == (0, 1)


def test_nothing_is_set_up_without_an_address(tmp_path):
    assert notify.settings(env={}, path=tmp_path / "missing") is None


def test_the_address_comes_from_the_environment_first(tmp_path):
    kept = tmp_path / "ntfy.url"
    kept.write_text("https://ntfy.sh/from-file\n")
    found = notify.settings(env={"SESSION_TREE_NTFY": "https://ntfy.sh/from-env"}, path=kept)
    assert found == notify.Settings(topic="https://ntfy.sh/from-env", click="")


def test_the_address_and_link_can_be_kept_in_a_file(tmp_path):
    kept = tmp_path / "ntfy.url"
    kept.write_text("https://ntfy.sh/from-file\nhttp://100.66.86.99:8787/\n")
    found = notify.settings(env={}, path=kept)
    assert found == notify.Settings(topic="https://ntfy.sh/from-file", click="http://100.66.86.99:8787/")


def test_a_failed_send_is_reported_not_raised(monkeypatch, capsys):
    def refuse(_request, **_kwargs):
        reason = "no network"
        raise urllib.error.URLError(reason)

    monkeypatch.setattr(notify.urllib.request, "urlopen", refuse)
    notify.post("https://ntfy.sh/", {"topic": "t", "message": "m"})
    assert "no network" in capsys.readouterr().err


def test_a_message_is_posted_as_json(monkeypatch):
    seen = {}

    def accept(request, timeout):
        seen["url"], seen["body"], seen["timeout"] = request.full_url, request.data, timeout
        return io.BytesIO(b"{}")

    monkeypatch.setattr(notify.urllib.request, "urlopen", accept)
    notify.post("https://ntfy.sh/", {"topic": "t", "title": "Spørsmål i ø", "message": "m"})
    assert seen["url"] == "https://ntfy.sh/"
    assert json.loads(seen["body"])["title"] == "Spørsmål i ø"
    assert seen["timeout"] == notify.TIMEOUT_SECONDS


def test_watch_shows_every_picture_to_the_notifier(monkeypatch):
    looked: list[dict] = []

    class Watching:
        def look(self, picture: dict) -> None:
            looked.append(picture)

    monkeypatch.setattr(server, "build", lambda: _picture(("3", "Now?")))
    monkeypatch.setattr(server, "_broadcast", lambda _payload: None)
    monkeypatch.setattr(server, "POLL_SECONDS", 0.001)
    stop = threading.Event()
    t = threading.Thread(target=server.watch, args=(stop, Watching()))
    t.start()
    time.sleep(0.05)
    stop.set()
    t.join()
    assert looked
    assert looked[0]["sessions"][0]["questions"][0]["text"] == "Now?"
