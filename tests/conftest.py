"""Synthetic transcripts, so the tests never depend on a real session."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

START = datetime(2026, 9, 18, 20, 0, tzinfo=UTC)


def stamp(seconds: int) -> str:
    """Return an ISO stamp this many seconds into the fixture session."""
    return (START + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


class Transcript:
    """Builds the JSONL a session writes, one tool call at a time."""

    def __init__(self, path: Path) -> None:
        """Start an empty transcript at this path."""
        self.path = path
        self.lines: list[str] = []
        self.counter = 0
        self.next_task = 1

    def _write(self, entry: dict[str, object]) -> None:
        self.lines.append(json.dumps(entry))
        self.path.write_text("\n".join(self.lines) + "\n")

    def prompt(self, text: str, at: int) -> None:
        """Record something the user said."""
        self._write(
            {
                "type": "user",
                "timestamp": stamp(at),
                "message": {"role": "user", "content": text},
            }
        )

    def create(self, subject: str, at: int, goal: str | None = None, description: str = "") -> str:
        """Record a TaskCreate and its result; returns the task id."""
        self.counter += 1
        use_id = f"toolu_{self.counter:04d}"
        payload: dict[str, object] = {"subject": subject, "description": description}
        if goal:
            payload["metadata"] = {"goal": goal}
        self._write(
            {
                "type": "assistant",
                "timestamp": stamp(at),
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": use_id, "name": "TaskCreate", "input": payload},
                    ],
                },
            }
        )
        task_id = str(self.next_task)
        self.next_task += 1
        self._write(
            {
                "type": "user",
                "timestamp": stamp(at),
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": use_id,
                            "content": f"Task #{task_id} created successfully: {subject}",
                        },
                    ],
                },
            }
        )
        return task_id

    def tool(self, name: str, at: int, payload: dict[str, object], *, failed: bool = False) -> None:
        """Record any other tool call, and its result."""
        self.counter += 1
        use_id = f"toolu_{self.counter:04d}"
        self._write(
            {
                "type": "assistant",
                "timestamp": stamp(at),
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": use_id, "name": name, "input": payload},
                    ],
                },
            }
        )
        self._write(
            {
                "type": "user",
                "timestamp": stamp(at),
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": use_id,
                            "is_error": failed,
                            "content": "Exit code 1" if failed else "ok",
                        },
                    ],
                },
            }
        )

    def spawn_without_result(self, description: str, at: int) -> None:
        """An Agent call whose result has not come back: the agent is running."""
        self.counter += 1
        self._write(
            {
                "type": "assistant",
                "timestamp": stamp(at),
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": f"toolu_{self.counter:04d}",
                            "name": "Agent",
                            "input": {"description": description},
                        },
                    ],
                },
            }
        )

    def say(self, text: str, at: int) -> None:
        """Record something the agent wrote to the user, as plain text."""
        self._write(
            {
                "type": "assistant",
                "timestamp": stamp(at),
                "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
            }
        )

    def ask(self, question: str, at: int, *, answered_at: int | None = None) -> None:
        """An AskUserQuestion box; it has an answer only when answered_at is given."""
        self.counter += 1
        use_id = f"toolu_{self.counter:04d}"
        payload = {"questions": [{"question": question, "header": "Q", "options": []}]}
        self._write(
            {
                "type": "assistant",
                "timestamp": stamp(at),
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": use_id, "name": "AskUserQuestion", "input": payload},
                    ],
                },
            }
        )
        if answered_at is None:
            return
        self._write(
            {
                "type": "user",
                "timestamp": stamp(answered_at),
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": use_id, "content": "answered"},
                    ],
                },
            }
        )

    def update(self, task_id: str, at: int, **fields: object) -> None:
        """Record a TaskUpdate carrying any of status, addBlockedBy, metadata."""
        self.counter += 1
        self._write(
            {
                "type": "assistant",
                "timestamp": stamp(at),
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": f"toolu_{self.counter:04d}",
                            "name": "TaskUpdate",
                            "input": {"taskId": task_id, **fields},
                        },
                    ],
                },
            }
        )


@pytest.fixture
def transcript(tmp_path: Path) -> Transcript:
    """Return an empty transcript builder writing into a temporary file."""
    return Transcript(tmp_path / "session.jsonl")


@pytest.fixture
def built(transcript: Transcript) -> Transcript:
    """A session with a chain, a second goal, and one abandoned branch."""
    transcript.prompt("build me a thing", at=0)
    first = transcript.create("Parse the transcripts", at=10, goal="tool")
    second = transcript.create("Serve the page", at=20, goal="tool")
    third = transcript.create("Draw the graph", at=30, goal="tool")
    transcript.update(second, at=31, addBlockedBy=[first])
    transcript.update(third, at=32, addBlockedBy=[second])
    transcript.create("Write the docs", at=40, goal="docs")
    dropped = transcript.create("Try websockets", at=50, goal="tool")
    transcript.update(first, at=60, status="in_progress")
    transcript.update(first, at=120, status="completed")
    transcript.update(dropped, at=130, status="deleted")
    transcript.update(second, at=140, status="in_progress")
    return transcript


# --- A real browser on the demo sessions (ADR-ST-007) ---------------------------

ROOT = __import__("pathlib").Path(__file__).parent.parent
# Where Chromium may already be, when Playwright's own download is not there.
SYSTEM_CHROMIUM = ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome")


def _free_port() -> int:
    import socket  # noqa: PLC0415 - only the browser tests need these

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def demo_url(tmp_path_factory: pytest.TempPathFactory):
    """The demo sessions, served by the real server on a port of their own."""
    import os  # noqa: PLC0415
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415
    import time  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415

    home = tmp_path_factory.mktemp("demo-home")
    subprocess.run([sys.executable, str(ROOT / "scripts/demo_fixture.py"), str(home)], check=True)
    port = _free_port()
    env = {**os.environ, "HOME": str(home), "PYTHONPATH": str(ROOT / "src")}
    env |= {"SESSION_TREE_PORT": str(port), "SESSION_TREE_HOST": "127.0.0.1"}
    server = subprocess.Popen([sys.executable, "-m", "session_tree.server"], env=env)
    url = f"http://127.0.0.1:{port}/"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url + "api/ping", timeout=1).close()  # noqa: S310
            break
        except OSError:
            time.sleep(0.1)
    yield url
    server.terminate()
    server.wait(timeout=5)


@pytest.fixture(scope="session")
def chromium():
    """Chromium through Playwright. Skips without one, except in CI, where that is a failure."""
    import os  # noqa: PLC0415

    try:
        from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415
    except ImportError:
        pytest.skip("Playwright is not installed: uv sync --all-extras")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Error:
            found = next((c for c in SYSTEM_CHROMIUM if os.path.exists(c)), None)  # noqa: PTH110
            if found is None:
                if os.environ.get("CI"):
                    raise
                pytest.skip("no browser: uv run playwright install chromium")
            browser = p.chromium.launch(executable_path=found)
        yield browser
        browser.close()


PHONE = {"viewport": {"width": 390, "height": 900}, "has_touch": True, "is_mobile": True}
WIDE = {"viewport": {"width": 1400, "height": 1000}}


@pytest.fixture(params=[PHONE, WIDE], ids=["phone", "wide"])
def page(request: pytest.FixtureRequest, chromium, demo_url: str):
    """The demo page, loaded and drawn, on a phone and on a wide screen."""
    context = chromium.new_context(**request.param)
    tab = context.new_page()
    tab.goto(demo_url)
    tab.wait_for_selector(".sess .node")
    yield tab
    context.close()
