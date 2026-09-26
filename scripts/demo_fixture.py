"""Build a fake ~/.claude with demo sessions that show every case the viewer draws.

The goals are everyday ones -- a birthday party, moving house, a garden, a book
club, a street clean-up, a dinner -- so anyone can read the graphs without
knowing any code. Between them they cover every state a task can be drawn in,
every label a session can carry, one goal and many, a single task and eighty,
a wide level and a long chain, breakdowns folded, unfolded and nested,
questions of every kind, agents running and finished, and a task whose work
happens in another session. tests/test_demo_fixture.py checks that list.

    python3 scripts/demo_fixture.py [directory]

writes the fake home into the directory (a new temporary one if none is given)
and prints its path. scripts/demo-viewer builds one and serves it.
"""

from __future__ import annotations

import itertools
import json
import os
import sys
import tempfile
import time
from pathlib import Path

NOW = time.time()
MINUTE = 60


def living_pids(count: int) -> list[int]:
    """Real process ids, so the demo's sessions read as alive."""
    found = [int(p.name) for p in Path("/proc").iterdir() if p.name.isdigit()]
    return sorted(found)[:count] or [1] * count


def dead_pid() -> int:
    """A process id nothing is using, so a session reads as ended."""
    pid = 4_000_000
    while Path(f"/proc/{pid}").exists():
        pid += 1
    return pid


def stamp(ago: float) -> str:
    """ISO stamp this many seconds before now."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(NOW - ago)) + ".000Z"


class Fake:
    """Writes one synthetic session: its register entry and its transcript."""

    def __init__(self, home: Path, sid: str, pid: int, name: str, *, status: str) -> None:
        """Register the session; status is what Claude Code declares, busy or idle."""
        cwd = "/home/demo/" + name.replace(" ", "-")
        self.home, self.sid = home, sid
        self.lines: list[str] = []
        self.n = 0
        self.task = 0
        self.last = 0.0
        slug = cwd.replace("/", "-")
        self.path = home / ".claude" / "projects" / slug / f"{sid}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        (home / ".claude" / "sessions").mkdir(parents=True, exist_ok=True)
        entry = {"pid": pid, "sessionId": sid, "cwd": cwd, "name": name, "kind": "interactive"}
        entry |= {"startedAt": int((NOW - 3 * 3600) * 1000), "status": status}
        (home / ".claude" / "sessions" / f"{pid}.json").write_text(json.dumps(entry))

    def _w(self, entry: dict[str, object]) -> None:
        self.lines.append(json.dumps(entry))

    def _use(self, name: str, payload: dict[str, object], ago: float) -> str:
        self.n += 1
        use = f"toolu_{self.n:04d}"
        content = [{"type": "tool_use", "id": use, "name": name, "input": payload}]
        self._w(
            {
                "type": "assistant",
                "timestamp": stamp(ago),
                "message": {"role": "assistant", "content": content},
            }
        )
        return use

    def _result(self, use: str, text: str, ago: float) -> None:
        content = [{"type": "tool_result", "tool_use_id": use, "content": text}]
        self._w({"type": "user", "timestamp": stamp(ago), "message": {"role": "user", "content": content}})

    def say(self, text: str, ago: float) -> None:
        """Record something the user said."""
        self._w({"type": "user", "timestamp": stamp(ago), "message": {"role": "user", "content": text}})

    def write(self, text: str, ago: float) -> None:
        """Record something the agent wrote back."""
        content = [{"type": "text", "text": text}]
        self._w(
            {
                "type": "assistant",
                "timestamp": stamp(ago),
                "message": {"role": "assistant", "content": content},
            }
        )

    def add(self, subject: str, ago: float, goal: str, desc: str = "", **meta: object) -> str:
        """Record a TaskCreate and its result; extra metadata such as parent or ask."""
        self.task += 1
        self.last = ago
        payload = {"subject": subject, "description": desc, "metadata": {"goal": goal, **meta}}
        use = self._use("TaskCreate", payload, ago)
        self._result(use, f"Task #{self.task} created successfully: {subject}", ago)
        return str(self.task)

    def set(self, task: str, ago: float, **fields: object) -> None:
        """Record a TaskUpdate."""
        self._use("TaskUpdate", {"taskId": task, **fields}, ago)

    def after(self, task: str, *deps: str) -> None:
        """Make a task wait on others, just after the last task was created."""
        self.set(task, self.last - 1, addBlockedBy=list(deps))

    def spawn(self, description: str, ago: float, *, done_ago: float | None = None) -> None:
        """Record a subagent started from the task in progress; done_ago finishes it."""
        use = self._use("Agent", {"description": description, "subagent_type": "general-purpose"}, ago)
        if done_ago is not None:
            self._result(use, "done", done_ago)

    def ask_box(self, question: str, ago: float) -> None:
        """Record a question box that has not been answered."""
        self._use("AskUserQuestion", {"questions": [{"question": question}]}, ago)

    def close(self, quiet: float) -> None:
        """Flush the transcript and age it, which is how silence is judged."""
        self.path.write_text("\n".join(self.lines) + "\n")
        os.utime(self.path, (NOW - quiet, NOW - quiet))


def birthday(home: Path, pid: int) -> tuple[str, str]:
    """One goal, six tasks, one in each basic state. Returns the dinner task."""
    s = Fake(
        home,
        "d0000001-0000-4000-8000-000000000001",
        pid,
        "birthday party",
        status="busy",
    )
    s.say("help me plan Maja's birthday party on Saturday", 50 * MINUTE)
    goal = "Maja's birthday party is ready on Saturday"
    guests = s.add("The guest list is agreed", 48 * MINUTE, goal)
    invites = s.add("Every guest has an invitation", 47 * MINUTE, goal)
    cake = s.add("The cake is ordered", 46 * MINUTE, goal)
    dinner = s.add("Dinner is cooked", 45 * MINUTE, goal, "The cooking is planned in its own session.")
    room = s.add("The room is decorated", 44 * MINUTE, goal)
    clown = s.add("A clown is booked", 43 * MINUTE, goal, "Dropped: Maja is scared of clowns.")
    s.after(invites, guests)
    s.after(dinner, guests)
    s.after(room, invites)
    s.set(guests, 40 * MINUTE, status="in_progress")
    s.set(guests, 30 * MINUTE, status="completed")
    s.set(clown, 29 * MINUTE, status="deleted")
    s.set(invites, 2 * MINUTE, status="in_progress")
    # the cake is ready to start; the room waits on the invitations
    del cake, room
    s.close(quiet=20)
    return s.sid, dinner


def moving(home: Path, pid: int) -> None:
    """Five goals of one to four tasks, one of them finished; the session is idle."""
    s = Fake(home, "d0000002-0000-4000-8000-000000000002", pid, "moving house", status="idle")
    s.say("we move on the first of next month, help me keep track", 3 * 60 * MINUTE)
    pack = "Everything is packed"
    boxes = s.add("Enough boxes are collected", 170 * MINUTE, pack)
    kitchen = s.add("The kitchen is packed", 169 * MINUTE, pack)
    books = s.add("The books are packed", 168 * MINUTE, pack)
    label = s.add("Every box is labelled with its room", 167 * MINUTE, pack)
    s.after(kitchen, boxes)
    s.after(books, boxes)
    s.after(label, kitchen, books)
    van = "A van is ready on moving day"
    quotes = s.add("Three quotes for a van are in", 160 * MINUTE, van)
    book_van = s.add("The cheapest van is booked", 159 * MINUTE, van)
    s.after(book_van, quotes)
    post = "Post reaches the new address"
    notice = s.add("The post office knows the new address", 150 * MINUTE, post)
    bank = s.add("The bank knows the new address", 149 * MINUTE, post)
    old = "The old flat is handed back clean"
    scrub = s.add("The old flat is cleaned", 140 * MINUTE, old)
    inspect = s.add("The landlord has inspected it", 139 * MINUTE, old)
    s.after(inspect, scrub)
    keys = s.add(
        "The keys to the new flat are collected", 130 * MINUTE, "The keys to the new flat are in hand"
    )
    for task in (boxes, quotes, scrub, inspect):
        s.set(task, 100 * MINUTE, status="in_progress")
        s.set(task, 90 * MINUTE, status="completed")
    del notice, bank, keys
    s.write("Packing can start whenever you are ready.", 60 * MINUTE)
    s.close(quiet=55 * MINUTE)


def garden(home: Path, pid: int) -> None:
    """Breakdowns: one folded, one unfolded with one nested inside it, arrows in and out of a box."""
    s = Fake(home, "d0000003-0000-4000-8000-000000000003", pid, "garden season", status="busy")
    s.say("let's get the vegetable garden going this spring", 90 * MINUTE)
    goal = "Vegetables are growing in the garden"
    plan = s.add("The beds are planned", 88 * MINUTE, goal)
    build = s.add("A raised bed is built", 87 * MINUTE, goal)
    plant = s.add("Tomatoes are planted", 86 * MINUTE, goal)
    water = s.add("The bed is watered every evening", 85 * MINUTE, goal)
    # the plan's steps: nothing outside uses them, so it starts folded
    sun = s.add("The sunniest spot is found", 84 * MINUTE, goal, parent=plan)
    size = s.add("The bed's size is chosen", 83 * MINUTE, goal, parent=plan)
    crops = s.add("The crops are chosen", 82 * MINUTE, goal, parent=plan)
    s.after(size, sun)
    # the bed's steps: planting waits on one of them, so it starts unfolded
    timber = s.add("The timber is bought", 81 * MINUTE, goal, parent=build)
    frame = s.add("The frame is screwed together", 80 * MINUTE, goal, parent=build)
    soil = s.add("The bed is filled with soil", 79 * MINUTE, goal, parent=build)
    s.after(frame, timber)
    s.after(soil, frame)
    # buying the timber has steps of its own: a breakdown inside a breakdown
    measure = s.add("The planks are measured", 78 * MINUTE, goal, parent=timber)
    shop = s.add("The planks are fetched from the shop", 77 * MINUTE, goal, parent=timber)
    s.after(shop, measure)
    s.after(build, plan)
    s.after(plant, soil)
    s.after(water, build)
    for task in (sun, size, crops, plan, measure):
        s.set(task, 70 * MINUTE, status="in_progress")
        s.set(task, 60 * MINUTE, status="completed")
    s.set(shop, 5 * MINUTE, status="in_progress")
    s.close(quiet=30)


def book_club(home: Path, pid: int) -> None:
    """Questions: one on a task, one put away, an open question box, a needs input line."""
    sid = "d0000004-0000-4000-8000-000000000004"
    s = Fake(home, sid, pid, "book club", status="idle")
    s.say("sort out next month's book club meeting", 40 * MINUTE)
    book = "Next month's book is chosen"
    shortlist = s.add("Three books are shortlisted", 38 * MINUTE, book)
    pick = s.add("One book is picked", 37 * MINUTE, book, ask="Which of the three books do you like best?")
    s.after(pick, shortlist)
    meeting = "The meeting is booked"
    room = s.add("A room is booked", 36 * MINUTE, meeting, ask="Should we meet at the library again?")
    snacks = s.add("Someone brings snacks", 35 * MINUTE, meeting)
    s.after(snacks, room)
    s.set(shortlist, 30 * MINUTE, status="in_progress")
    s.set(shortlist, 25 * MINUTE, status="completed")
    s.set(pick, 24 * MINUTE, status="in_progress")
    s.ask_box("Is it all right to invite two new members?", 12 * MINUTE)
    s.write(
        "I have shortlisted three books.\n\nneeds input: Should the meeting move to Thursday?", 10 * MINUTE
    )
    s.close(quiet=9 * MINUTE)
    # the library question was answered somewhere else, and put away in the viewer
    key = json.dumps([sid, "node", room, "Should we meet at the library again?"], ensure_ascii=False)
    kept = home / ".claude" / "session-tree" / "dismissed.json"
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text(json.dumps([key], ensure_ascii=False))


def clean_up(home: Path, pid: int) -> None:
    """Eighty tasks: sixty side by side, a chain of twelve, one stalled and one blocked."""
    s = Fake(
        home,
        "d0000005-0000-4000-8000-000000000005",
        pid,
        "street clean-up",
        status="busy",
    )
    s.say("organise the spring clean-up for the whole neighbourhood", 5 * 60 * MINUTE)
    goal = "The neighbourhood is clean after the spring clean-up"
    streets = ["Oak", "Elm", "Birch", "Maple", "Pine", "Ash", "Cedar", "Willow", "Rowan", "Alder"]
    sweeps = [
        s.add(f"{street} Street, block {block}, is swept", 280 * MINUTE, goal)
        for street in streets
        for block in range(1, 7)
    ]
    steps = [
        "A date is agreed with the council",
        "The residents are told the date",
        "Volunteers have signed up",
        "Teams are formed",
        "Each team has its streets",
        "Gloves and bags are bought",
        "The kit is handed out",
        "The skip is ordered",
        "The skip is delivered",
        "The rubbish is in the skip",
        "The skip is collected",
        "Everyone is thanked",
    ]
    chain = [s.add(step, 270 * MINUTE, goal) for step in steps]
    for before, then in itertools.pairwise(chain):
        s.after(then, before)
    report = [
        s.add("Photos of the clean streets are taken", 260 * MINUTE, goal),
        s.add("A short report goes to the council", 259 * MINUTE, goal),
        s.add("The report is posted in the residents' group", 258 * MINUTE, goal),
        s.add("Next year's date is pencilled in", 257 * MINUTE, goal),
        s.add("Leftover bags are stored", 256 * MINUTE, goal),
        s.add("Lost gloves are returned", 255 * MINUTE, goal),
        s.add("The volunteers' hours are counted", 254 * MINUTE, goal),
        s.add("A thank-you card goes to the council", 253 * MINUTE, goal),
    ]
    s.after(report[1], report[0])
    s.after(report[2], report[1])
    s.after(chain[-1], *sweeps)
    for task in chain[:5] + sweeps[:20]:
        s.set(task, 200 * MINUTE, status="in_progress")
        s.set(task, 150 * MINUTE, status="completed")
    # started, and nothing has happened for a long time
    s.set(chain[5], 100 * MINUTE, status="in_progress")
    # started while what it waits on is still open
    s.set(chain[8], 90 * MINUTE, status="in_progress")
    s.close(quiet=40 * MINUTE)


def dinner(home: Path, pid: int, party: str, cook: str) -> None:
    """Agents running and finished, and a goal that is the work of a task in the party session."""
    s = Fake(
        home,
        "d0000006-0000-4000-8000-000000000006",
        pid,
        "birthday dinner",
        status="busy",
    )
    s.say("plan the dinner for the birthday party", 30 * MINUTE)
    goal = "The birthday dinner is cooked"
    link = f"{party}#{cook}"
    menu = s.add("The menu is chosen", 28 * MINUTE, goal, parent=link)
    shop = s.add("The shopping is done", 27 * MINUTE, goal, parent=link)
    cook_it = s.add("The food is cooked", 26 * MINUTE, goal, parent=link)
    s.after(shop, menu)
    s.after(cook_it, shop)
    s.set(menu, 25 * MINUTE, status="in_progress")
    s.spawn("Find three child-friendly recipes", 24 * MINUTE, done_ago=20 * MINUTE)
    s.spawn("Check the recipes for nuts", 23 * MINUTE, done_ago=19 * MINUTE)
    s.set(menu, 18 * MINUTE, status="completed")
    s.set(shop, 3 * MINUTE, status="in_progress")
    s.spawn("Compare prices at two shops", 2 * MINUTE)
    s.close(quiet=10)


def old_session(home: Path, pid: int) -> None:
    """A session whose process has ended."""
    s = Fake(home, "d0000007-0000-4000-8000-000000000007", pid, "bike repair", status="idle")
    s.say("the back tyre keeps going flat", 26 * 60 * MINUTE)
    goal = "The bike rides again"
    find = s.add("The puncture is found", 25 * 60 * MINUTE, goal)
    patch = s.add("The tube is patched", 25 * 60 * MINUTE, goal)
    s.after(patch, find)
    for task in (find, patch):
        s.set(task, 24 * 60 * MINUTE, status="in_progress")
        s.set(task, 23 * 60 * MINUTE, status="completed")
    s.close(quiet=23 * 60 * MINUTE)


def build(home: Path) -> None:
    """Write every demo session into this fake home."""
    pids = living_pids(6)
    party, cook = birthday(home, pids[0])
    moving(home, pids[1])
    garden(home, pids[2])
    book_club(home, pids[3])
    clean_up(home, pids[4])
    dinner(home, pids[5], party, cook)
    old_session(home, dead_pid())


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="st-demo-"))
    build(target)
    sys.stdout.write(str(target) + "\n")
