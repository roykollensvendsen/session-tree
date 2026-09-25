"""The event stream pushes when the picture changes, not when only the clock moved."""

import threading
import time

from session_tree import server


def _picture(now: float, subject: str) -> dict:
    return {
        "now": now,
        "sessions": [
            {
                "statusAgeSeconds": round(now),
                "quietSeconds": round(now) % 97,
                "goals": [
                    {
                        "nodes": [
                            {
                                "id": "1",
                                "subject": subject,
                                "status": "in_progress",
                                "startedMs": 1000,
                                "durationMs": int(now * 1000) - 1000,
                            }
                        ]
                    }
                ],
            }
        ],
    }


def _run_watch(monkeypatch, pictures: list[dict], polls: int) -> list[str]:
    sent: list[str] = []
    it = iter(pictures)
    last = {"p": pictures[0]}

    def fake_build() -> dict:
        last["p"] = next(it, last["p"])
        return last["p"]

    monkeypatch.setattr(server, "build", fake_build)
    monkeypatch.setattr(server, "_broadcast", sent.append)
    monkeypatch.setattr(server, "POLL_SECONDS", 0.001)
    stop = threading.Event()
    t = threading.Thread(target=server.watch, args=(stop,))
    t.start()
    deadline = time.time() + 2
    while time.time() < deadline and len(pictures) and polls > 0:
        time.sleep(0.01)
        polls -= 1
    stop.set()
    t.join()
    return sent


def test_only_clocks_moving_sends_once(monkeypatch):
    # The picture's clock and running durations advance every poll, nothing else does.
    pictures = [_picture(1_000_000 + i * 0.4, "a") for i in range(30)]
    sent = _run_watch(monkeypatch, pictures, 50)
    assert len(sent) == 1


def test_a_real_change_is_sent(monkeypatch):
    pictures = [_picture(1_000_000 + i * 0.4, "a") for i in range(10)]
    pictures += [_picture(1_000_010 + i * 0.4, "b") for i in range(10)]
    sent = _run_watch(monkeypatch, pictures, 50)
    assert len(sent) == 2


def test_clock_only_pictures_still_refresh_now_and_then(monkeypatch):
    monkeypatch.setattr(server, "REFRESH_SECONDS", 0.0)
    pictures = [_picture(1_000_000 + i * 0.4, "a") for i in range(5)]
    sent = _run_watch(monkeypatch, pictures, 30)
    assert len(sent) >= 2
