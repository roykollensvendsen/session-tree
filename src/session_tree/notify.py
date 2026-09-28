"""Push a new question to the phone through ntfy (ADR-ST-009).

The server shows every picture it builds to a Notifier. A question that was not
waiting in the picture before is sent as one message to an ntfy topic, whose
app shows it on the phone. Nothing is sent until a topic is set up.

Two servers can watch the same sessions, one per address. Only the one holding
a lock file sends, so the phone gets each message once, and the other takes
over if that one stops.
"""

from __future__ import annotations

import fcntl
import json
import os
import sys
import threading
import urllib.request
from dataclasses import dataclass
from typing import IO, TYPE_CHECKING, Any

from session_tree.state import HOME, dismissal_key

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

SETTINGS_FILE = HOME / ".claude" / "session-tree" / "ntfy.url"
LOCK_FILE = HOME / ".claude" / "session-tree" / "ntfy.lock"
MAX_TEXT = 200
TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class Settings:
    """Where to send: the topic's full address, and the page a tap opens ('' for none)."""

    topic: str
    click: str


def settings(env: Mapping[str, str] = os.environ, path: Path = SETTINGS_FILE) -> Settings | None:
    """The topic from SESSION_TREE_NTFY, else the file's first line; None when neither is set."""
    if env.get("SESSION_TREE_NTFY"):
        return Settings(topic=env["SESSION_TREE_NTFY"], click=env.get("SESSION_TREE_NTFY_CLICK", ""))
    try:
        lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    except OSError:
        return None
    if not lines:
        return None
    return Settings(topic=lines[0], click=lines[1] if len(lines) > 1 else "")


def post(url: str, body: dict[str, Any]) -> None:
    """Publish one message as JSON; a failure is reported, never raised."""
    request = urllib.request.Request(  # noqa: S310 - the user's own address
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS):  # noqa: S310 - the user's own address
            pass
    except Exception as error:  # noqa: BLE001 - the watcher must never die of a message
        sys.stderr.write(f"ntfy error: {error!r}\n")


def _in_background(job: Callable[[], None]) -> None:
    threading.Thread(target=job, daemon=True).start()


class Notifier:
    """Sends each question once, from the first picture after the one it was missing in."""

    def __init__(
        self,
        chosen: Settings,
        send: Callable[[str, dict[str, Any]], None] = post,
        spawn: Callable[[Callable[[], None]], None] = _in_background,
        lock: Path = LOCK_FILE,
    ) -> None:
        """Send through `send`, off the watcher's thread through `spawn`, if `lock` is ours."""
        self.settings = chosen
        self.send = send
        self.spawn = spawn
        self.lock = lock
        self.held: IO[str] | None = None
        self.seen: set[str] | None = None

    def _leads(self) -> bool:
        """Hold the lock, or try to take it; only the holder sends."""
        if self.held:
            return True
        self.lock.parent.mkdir(parents=True, exist_ok=True)
        handle = self.lock.open("a")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False
        self.held = handle
        return True

    def close(self) -> None:
        """Let go of the lock, so another server sends."""
        if self.held:
            self.held.close()
            self.held = None

    def look(self, picture: dict[str, Any]) -> None:
        """Send whatever question is new since the last picture."""
        waiting = {
            dismissal_key(str(session.get("sessionId")), question): (session, question)
            for session in picture.get("sessions") or []
            for question in session.get("questions") or []
        }
        # RULE: questions waiting at start up are not sent
        before = set(waiting) if self.seen is None else self.seen
        self.seen = set(waiting)
        # RULE: a question already sent is not sent again
        fresh = [asked for key, asked in waiting.items() if key not in before]
        if fresh and self._leads():
            for session, question in fresh:
                self._send(session, question)

    def _send(self, session: dict[str, Any], question: dict[str, Any]) -> None:
        base, _, topic = self.settings.topic.rstrip("/").rpartition("/")
        body: dict[str, Any] = {
            "topic": topic,
            "title": f"Spørsmål i {session.get('name') or session.get('project') or 'en økt'}",
            "message": str(question.get("text") or "")[:MAX_TEXT],
            "tags": ["question"],
        }
        if self.settings.click:
            body["click"] = self.settings.click
        self.spawn(lambda: self.send(base + "/", body))
