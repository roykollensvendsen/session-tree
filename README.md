# session-tree

A live picture of what your coding agents are doing — Claude Code and Codex, in
this session and in every other one on your machine, across every project — in
its own window, beside the terminal.

![Three sessions, each drawn as a task graph](assets/screenshot.png)

*Synthetic sessions. Red is blocked by an open dependency, blue is being worked
now, green is done, and the struck-through node is a branch that was tried and
dropped.*

Each session's work is drawn as a task graph. Nodes go blue while worked, green
when done, amber when nothing has moved, red when blocked, and struck through
when a branch was tried and dropped. A slider walks any session back through
its own history, with your own prompts on the timeline, so what happened and
why is recoverable hours later.

## The problem it solves

An agent session is a scroll. Twenty minutes in, the plan is above the fold and
the reason for it is further up still. Several sessions at once, and there is no
place at all that says what is in flight. You end up asking the agent what it is
doing, which is the question the tool should already be answering.

## Getting started

<!-- not run: starts a background server and opens a browser window -->
```bash
uv tool install session-tree      # or: pipx install session-tree
session-tree open                 # own window, live
```

Leave the window open. It updates itself as the work happens; there is nothing
to refresh and nothing to rebuild.

The same picture in the terminal, and what it says when nothing is serving:

```console
$ session-tree --port 9099 status
not running (start it with: session-tree start)
```

## How it works

What each agent already writes, so **no hook has to be installed and nothing
can be forgotten**:

| Source | What it gives |
|---|---|
| `~/.claude/sessions/<pid>.json` | every live Claude Code session: id, directory, name, status |
| `~/.claude/projects/<slug>/<session>.jsonl` | its transcript, appended as it happens |
| `~/.codex/state_*.sqlite` | every Codex thread: id, directory, title, timestamps |
| `~/.codex/thread_history_*.sqlite` | its turns, with status and duration, and what each one changed |

The Codex filenames carry a schema version that moves when it upgrades, so the
newest match is read rather than a fixed name.

`TaskCreate` and `TaskUpdate` calls in the transcript replay into nodes and
edges. Because the source is the transcript rather than a hook, the view works
backwards too: a session that ran last week still draws, and a session that had
never heard of this tool appears anyway.

Transcripts reach tens of megabytes, so each is read forward from a remembered
byte offset and never re-parsed. A change reaches an open window in about a
hundredth of a second.

## One graph on its own

A goal card shows its graph at the width the card has. Click the goal's title
and the same graph opens alone, filling the window, drawn live like the card.
There the mouse wheel zooms around the pointer, a drag pans, a double-click
fits the whole graph again, and Esc or the ✕ closes it. A graph of a hundred
nodes is readable that way, and still updates while it is open.

On a phone the graph covers exactly the part of the page you can see, even when
the page was pinched in before it opened, so the ✕ and **⤢** (fit) stay on
screen. The phone's back button or back gesture closes it too.

There is room to spare, so the nodes are drawn larger than in the card, with up
to three lines of each subject instead of one clipped line. It opens fitted,
with the whole graph on screen; on a phone a big graph is then small, and you
pinch in on the part you want.

Steps that wait on the same things share a level, drawn side by side. When a
level has more steps than fit at a readable width, it wraps onto more rows
instead of squeezing them: in a card, as many per row as the card has room for;
enlarged, at most six per row, so a level of seventy steps becomes a page to
scroll rather than a ribbon twenty thousand pixels wide.

## On your phone

The page fits a phone: one goal at a time, thumb-sized buttons, and the
focused graph pinches to zoom. When a session has more than one independent
goal, a pager shows one decomposition at a time — swipe left or right, tap a
dot, or use the arrow keys on a keyboard; **☰** shows every goal at once
again. The page you were on is remembered per session.

A quick tap on a node lights its arrows and what they reach, and dims the
rest, the way a resting mouse does; the highlight stays while the graph
redraws. A tap on the same node again, or on empty space, puts it out. Hold a
finger on a node for half a second to open its popover, which has a ✕ to close
it. A press that turns into a scroll or a pinch does neither. The popover is
always placed wholly on the screen, next to the node where there is room, and
scrolls inside itself when it is taller than the screen; that holds when the
page is pinched in too.

The server listens on localhost only. To reach it from a phone, bind it to
your [Tailscale](https://tailscale.com) address instead, so that only devices
on your own tailnet can connect:

<!-- not run: binds a server to this machine's tailnet address -->
```bash
SESSION_TREE_HOST=$(tailscale ip -4) session-tree start
```

Then open `http://<that address>:8787/` on the phone. `--host` does the same
from the command line. **There is no authentication**: the page shows every
session's prompts and file paths to whoever can reach it, so bind it to the
tailnet address only, never to `0.0.0.0` on a network you share.

## Codex

Codex records turns, not tasks. A thread is drawn as a band of turns along time
— coloured by status, sized by duration, carrying which files each turn changed
and which commands exited non-zero.

It does have a checklist tool, `update_plan`, but three things stand in the way
and none of them is on by default: the tool's config defaults to off, the call
is never kept as a thread item so it exists only inside the rollout file, and
the checklist has no edges — each step is a string and a status, with no
identifier and nothing to point at.

<!-- not run: writes into ~/.codex and needs Codex restarted afterwards -->
```bash
session-tree install-codex-hook
```

That turns the tool on, registers a `PostToolUse` hook that catches every plan
as it is written, and adds a note to `AGENTS.md` asking the model to put the
dependencies in the explanation:

    deps: 2<-1; 3<-2; 4<-2

Nothing is overwritten — an existing file is backed up first, and a block that
is already there is left alone.

**Codex will not run a newly configured hook until it is trusted.** Start
`codex` once afterwards and approve it when asked; the answer is remembered.
Until then the plan is never captured and nothing says why. For automation,
`codex exec --dangerously-bypass-hook-trust` skips the check for one run.

Those edges are text a model wrote, not a field anything validated, so an edge
pointing at a step that does not exist is **shown on the card** rather than
quietly dropped. A plan with no dependencies at all says so too, because
listing steps in an order is not the same as one waiting for another.

## What is not automatic

**The graph is the agent's decomposition. Nothing else supplies it.** A Claude
Code session that never calls `TaskCreate` shows up as a card with no picture —
correctly, because nothing knows what it was trying to do.

The accompanying skill (`SKILL.md`, for `~/.claude/skills/`) is what teaches the
agent to decompose before starting, wire real `blockedBy` dependencies, put
separate goals on separate graphs, and leave abandoned branches on the picture
instead of deleting them.

One state is inferred rather than reported: a node in progress whose transcript
has been silent for fifteen minutes goes amber on its own. It is the only state
that cannot be faked by forgetting to update a task, which is why it is there.

## Subagents, and what a session needs from you

A node that spawned subagents carries them inside it, one line each, blue while
running and green when done — so a step that fanned out into a six-seat review
panel looks like one, without being opened.

Agents started before the work was decomposed at all belong to the session
rather than to a node. A review panel usually is one: the seats run, and the
tasks are created from what they found. Hanging them under whichever node
happened to be open would invent a tie that is not there.

Each session header says what it needs from a person. `ledig` means the agent
is idle with the process alive: it has finished its turn, and has not
necessarily asked you anything. `står
stille` means the session claims to be busy while nothing has been written for
fifteen minutes, which is the one case where going in and looking is worth
doing.

## A question waiting on you

`ledig` only says a session is idle, and a session that has finished
looks the same as one that asked you something. A question gets its own mark,
**`?`**, wherever it is waiting:

- **On the session**, with the question itself, when the agent has an open
  question box (`AskUserQuestion` with no answer yet), or when it has gone idle
  after writing a line that starts with `needs input:`.
- **On a node, and on its goal's header**, when the agent set
  `metadata: {"ask": "<the question>"}` on the node it is waiting for. Setting
  `ask` to `null` clears it. The question shows in the node's popover.

With several sessions open, a line at the top of the page counts the questions
waiting — `? 2 venter på svar` — and lists each one: the project, the session,
the goal and the question. Tapping one scrolls to the session, opens the goal
on its own and lights the node. The same place has an address of its own,
`?s=<session id>&n=<node id>`, so a question can be linked to, and the list
shows each session's working directory, so the terminal it runs in can be found.

A question can outlive its answer. When work moves to another session that
carried on from a summary, the answer lands there, and the first session's node
keeps asking. **⊘** (avvis) beside a question in the list puts it away: the server
keeps the dismissal in `~/.claude/session-tree/dismissed.json`, so it is gone
on every device, and the session is no longer marked as asking on its account.
The node's popover still shows the question, marked `avvist`. A dismissal is of
that question's text; if the agent asks something new on the same node, it
shows again ([ADR-ST-006](decisions/ADR-ST-006-a-question-can-be-dismissed.md)).

## A breakdown folded into its node

When an agent hands part of a goal on, the steps of that part say which node
they belong to: `metadata: {"parent": "<task id>"}`. The view then draws them
folded into that node, which carries **`▸ 3/5`** (done and total) in the colour
of the worst of its steps, so a red step still shows. A tap unfolds it: the node
becomes a box, its own subject the heading, with its steps drawn inside as a
small graph of their own, and the chip, now `▾`, in its top right corner. In the
full-screen view the chip stays where the finger tapped it. The node is the part of the
network it stands for, folded or not: an arrow into it meets the top of the box and
an arrow out of it leaves from the bottom. A second tap folds it again, and the
choice is remembered. If a node outside the breakdown depends on one of its steps, the
breakdown is drawn unfolded from the start, because folding would hide that
dependency. A node that is done while one of its steps is still open says so
with a `!` on the chip.

Work handed to **another session** is linked rather than folded. The other
session's steps carry `"parent": "<session id>#<task id>"`, or the node that
handed the work on carries `"session": "<session id>"`. The node gets
**`↗ 2/4`**, and a tap opens the other session's goal; that goal's card shows
**`↖`** with the node it serves, and a tap goes back. A `parent` that names a
node or session that does not exist is listed on the card as a broken link.

## Hiding finished goals

A long-running goal fills up with work that is done. Press **✓**
(skjul ferdige) in the header, struck through while it is on, and every
finished node leaves its graph, along with the arrows from it, since a finished
node no longer holds anything up. A finished node
with a step that is still running stays, so that work does not vanish with it.
The count of finished nodes on each goal is unchanged, and a goal with nothing
left shows a single line saying so. The choice is remembered in that browser;
it starts off, so nothing is hidden until you ask.

## Replay

**⏱** (replay) on a session header turns the graph into a recording of itself. The
slider is linear in time, so the gaps show where the thinking went; playback
steps event by event, because a real-time replay of a forty-minute session takes
forty minutes.

Your own prompts sit on the timeline in green beside the node changes. That is
the point of it: a node turning green tells you *what* happened, and the prompt
three ticks earlier tells you *why*.

## Development

The server is shared by every window, so stopping it interrupts nobody:

<!-- not run: starts and stops a background server -->
```bash
session-tree start      # server only, no window
session-tree restart    # after upgrading the package
session-tree stop
```

<!-- not run: the suite is what this command runs; running it here would nest -->
```bash
uv sync --all-extras
uv run pytest -q
uv run ruff check . && uv run mypy src
python scripts/mutate.py          # proves each rule's test can fail
```

The replay engine lives in the page, and its tests run *that* copy through
node rather than a Python port, so the thing tested is the thing shipped.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
