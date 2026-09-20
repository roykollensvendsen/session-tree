#!/usr/bin/env python3
"""Record every plan Codex writes, so session-tree can draw it.

Codex calls `update_plan` with a checklist, but the call is not kept as a
thread item: it exists only inside the rollout file. A PostToolUse hook is the
one place the plan can be caught as it happens.

Install it by pointing a PostToolUse hook with matcher `update_plan` at this
file; `session-tree install-codex-hook` writes that configuration.

The hook runs inside Codex's turn, so it must never be the reason a turn fails:
every path exits 0, and the file is replaced atomically so a reader never sees
half of one.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

PLAN_DIR = Path(os.environ.get("SESSION_TREE_PLAN_DIR", Path.home() / ".codex" / "session-tree-plans"))
MAX_STEPS = 200


def read_request() -> dict[str, object]:
    """The hook payload on stdin, or an empty mapping if it is unusable."""
    try:
        loaded = json.load(sys.stdin)
    except (ValueError, OSError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def steps_of(tool_input: object) -> list[dict[str, str]]:
    """The checklist, as {step, status} pairs, ignoring anything malformed."""
    if not isinstance(tool_input, dict):
        return []
    plan = tool_input.get("plan")
    if not isinstance(plan, list):
        return []
    steps = []
    for entry in plan[:MAX_STEPS]:
        if not isinstance(entry, dict):
            continue
        step = entry.get("step")
        if not isinstance(step, str):
            continue
        status = entry.get("status")
        steps.append({"step": step, "status": status if isinstance(status, str) else "pending"})
    return steps


def write_atomically(path: Path, payload: dict[str, object]) -> None:
    """Replace the file in one step, so a reader never sees a partial plan."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(dir=path.parent, prefix=".plan-", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(payload, out, ensure_ascii=False)
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    """Write the plan for this thread. Always succeeds, so a turn never fails here."""
    request = read_request()
    session_id = request.get("session_id")
    tool_input = request.get("tool_input")
    if not isinstance(session_id, str) or not session_id:
        return 0
    steps = steps_of(tool_input)
    if not steps:
        return 0

    explanation = tool_input.get("explanation") if isinstance(tool_input, dict) else None
    write_atomically(
        PLAN_DIR / f"{session_id}.json",
        {
            "sessionId": session_id,
            "turnId": request.get("turn_id") if isinstance(request.get("turn_id"), str) else None,
            "cwd": request.get("cwd") if isinstance(request.get("cwd"), str) else None,
            "at": int(time.time() * 1000),
            "explanation": explanation if isinstance(explanation, str) else None,
            "steps": steps,
        },
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001 - a hook must not break the turn
        sys.stderr.write(f"session-tree plan hook: {error!r}\n")
        sys.exit(0)
