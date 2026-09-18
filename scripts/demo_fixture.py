"""Build a fake ~/.claude so the screenshots carry no real work.

Run it, then start the server with HOME pointed at the directory it prints.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

NOW = time.time()


def living_pids(count: int) -> list[int]:
    """Real process ids, so the fixture's sessions read as alive."""
    found = [int(p.name) for p in Path("/proc").iterdir() if p.name.isdigit()]
    return sorted(found)[:count] or [1] * count


PIDS = living_pids(3)


def stamp(offset: float) -> str:
    """ISO stamp this many seconds before now."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(NOW - offset)) + ".000Z"


class Fake:
    """Writes one synthetic session: its register entry and its transcript."""

    def __init__(self, home: Path, sid: str, pid: int, cwd: str, name: str) -> None:
        """Register the session and open its transcript."""
        self.lines: list[str] = []
        self.n = 0
        self.task = 0
        slug = cwd.replace("/", "-")
        self.path = home / ".claude" / "projects" / slug / f"{sid}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        (home / ".claude" / "sessions").mkdir(parents=True, exist_ok=True)
        (home / ".claude" / "sessions" / f"{pid}.json").write_text(json.dumps({
            "pid": pid, "sessionId": sid, "cwd": cwd, "name": name,
            "startedAt": int((NOW - 5400) * 1000), "kind": "bg", "status": "idle",
        }))

    def _w(self, entry: dict[str, object]) -> None:
        self.lines.append(json.dumps(entry))

    def say(self, text: str, ago: float) -> None:
        """Record something the user said."""
        self._w({"type": "user", "timestamp": stamp(ago),
                 "message": {"role": "user", "content": text}})

    def add(self, subject: str, ago: float, goal: str, desc: str = "") -> str:
        """Record a TaskCreate and its result."""
        self.n += 1
        self.task += 1
        use = f"toolu_{self.n:04d}"
        self._w({"type": "assistant", "timestamp": stamp(ago), "message": {"role": "assistant",
                 "content": [{"type": "tool_use", "id": use, "name": "TaskCreate",
                              "input": {"subject": subject, "description": desc,
                                        "metadata": {"goal": goal}}}]}})
        self._w({"type": "user", "timestamp": stamp(ago), "message": {"role": "user",
                 "content": [{"type": "tool_result", "tool_use_id": use,
                              "content": f"Task #{self.task} created successfully: {subject}"}]}})
        return str(self.task)

    def set(self, task: str, ago: float, **fields: object) -> None:
        """Record a TaskUpdate."""
        self.n += 1
        self._w({"type": "assistant", "timestamp": stamp(ago), "message": {"role": "assistant",
                 "content": [{"type": "tool_use", "id": f"toolu_{self.n:04d}", "name": "TaskUpdate",
                              "input": {"taskId": task, **fields}}]}})

    def close(self, mtime_ago: float) -> None:
        """Flush the transcript and age it, which is how idleness is judged."""
        self.path.write_text("\n".join(self.lines) + "\n")
        os.utime(self.path, (NOW - mtime_ago, NOW - mtime_ago))


def build(home: Path) -> None:
    """Write three sessions showing every state the view can draw."""
    a = Fake(home, "aaaa1111-0000-0000-0000-000000000001", PIDS[0],
             "/home/dev/orchard", "harvest scheduling rewrite")
    a.say("rewrite the scheduler so overlapping windows cannot both win", ago=5200)
    parse = a.add("Read the window definitions", 5100, "scheduler")
    solve = a.add("Resolve overlapping windows", 5000, "scheduler")
    apply_ = a.add("Apply the resolved plan", 4900, "scheduler")
    report = a.add("Report what changed", 4800, "scheduler")
    a.set(solve, 4790, addBlockedBy=[parse])
    a.set(apply_, 4780, addBlockedBy=[solve])
    a.set(report, 4770, addBlockedBy=[apply_])
    naive = a.add("Sort by start time and take the first", 4700, "scheduler",
                  "Dropped: two windows can start together, so this decides nothing.")
    a.set(parse, 4600, status="in_progress")
    a.set(parse, 4300, status="completed")
    a.set(naive, 4200, status="deleted")
    a.set(solve, 4100, status="in_progress")
    a.say("also write the migration notes", ago=3000)
    notes = a.add("Draft the migration notes", 2900, "notes")
    a.set(notes, 2800, status="in_progress")
    a.set(notes, 2400, status="completed")
    a.close(mtime_ago=3)

    b = Fake(home, "bbbb2222-0000-0000-0000-000000000002", PIDS[1],
             "/home/dev/orchard-web", "pricing page redesign")
    b.say("the pricing table breaks on narrow screens", ago=2600)
    measure = b.add("Measure the breakpoints", 2500, "pricing")
    rebuild = b.add("Rebuild the table as a grid", 2400, "pricing")
    check = b.add("Check it against the four widths", 2300, "pricing")
    b.set(rebuild, 2290, addBlockedBy=[measure])
    b.set(check, 2280, addBlockedBy=[rebuild])
    b.set(measure, 2200, status="in_progress")
    b.set(measure, 2000, status="completed")
    b.set(rebuild, 1900, status="in_progress")   # silent since: goes amber
    b.close(mtime_ago=2400)

    c = Fake(home, "cccc3333-0000-0000-0000-000000000003", PIDS[2],
             "/home/dev/almanac", "nightly import keeps timing out")
    c.say("the nightly import times out about one run in three", ago=900)
    find = c.add("Find which stage stalls", 800, "timeout")
    fix = c.add("Shorten that stage", 700, "timeout")
    prove = c.add("Prove it over ten runs", 600, "timeout")
    c.set(fix, 690, addBlockedBy=[find])
    c.set(prove, 680, addBlockedBy=[fix])
    c.set(fix, 300, status="in_progress")   # started while blocked: goes red
    c.close(mtime_ago=5)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="st-demo-"))
    build(target)
    sys.stdout.write(str(target) + "\n")
