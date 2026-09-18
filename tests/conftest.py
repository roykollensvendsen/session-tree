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
