# session-tree

A live picture of what Claude Code is doing — in this session and in every
other session on your machine, across every project — in its own window, beside
the terminal.

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

Two files Claude Code already maintains, so **no hook has to be installed and
nothing can be forgotten**:

| Source | What it gives |
|---|---|
| `~/.claude/sessions/<pid>.json` | every live session: id, directory, name, status |
| `~/.claude/projects/<slug>/<session>.jsonl` | the transcript, appended as it happens |

`TaskCreate` and `TaskUpdate` calls in the transcript replay into nodes and
edges. Because the source is the transcript rather than a hook, the view works
backwards too: a session that ran last week still draws, and a session that had
never heard of this tool appears anyway.

Transcripts reach tens of megabytes, so each is read forward from a remembered
byte offset and never re-parsed. A change reaches an open window in about a
hundredth of a second.

## What is not automatic

**The graph is the agent's decomposition. Nothing else supplies it.** A session
that never calls `TaskCreate` shows up as a card with no picture — correctly,
because nothing knows what it was trying to do.

The accompanying skill (`SKILL.md`, for `~/.claude/skills/`) is what teaches the
agent to decompose before starting, wire real `blockedBy` dependencies, put
separate goals on separate graphs, and leave abandoned branches on the picture
instead of deleting them.

One state is inferred rather than reported: a node in progress whose transcript
has been silent for fifteen minutes goes amber on its own. It is the only state
that cannot be faked by forgetting to update a task, which is why it is there.

## Replay

`⏱ replay` on a session header turns the graph into a recording of itself. The
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
