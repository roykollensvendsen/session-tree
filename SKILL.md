---
name: session-tree
description: >-
  A live picture, in its own window, of what your coding agents are doing right
  now — Claude Code and Codex, in this session and in every other one on this
  machine, across all projects. The
  work decomposes into a task graph whose nodes go blue while worked, green when
  done, amber when nothing has moved, red when blocked, and struck through when
  a branch was tried and dropped. It also replays: a slider walks a session back
  through its own history, with the user's own prompts on the timeline, so what
  happened and why is recoverable after the fact. Use when the user asks what
  you are working on, wants to see progress, asks to open or start the session
  view, says they have lost track of what you were doing or what they were
  doing, wants to watch several sessions at once, asks where the work stands, or
  wants to replay, scrub through, rewind or review what happened earlier in a
  session. Also read it before starting any piece of work longer than a step or
  two: the task list you keep is what draws the graph, and it has to stay
  current and readable by someone who was not in the conversation.
---

# Session tree

<!-- not run: opens a browser window and leaves a server running -->
```bash
~/.claude/skills/session-tree/scripts/session-tree open     # own window, live
~/.claude/skills/session-tree/scripts/session-tree status   # same picture in the terminal
```

No install step: the script runs the package straight out of the clone.

Leave the window open beside the terminal. It updates itself as the work
happens; there is nothing to refresh and nothing to rebuild.

## Where the picture comes from

Two files Claude Code already maintains, so no hook has to fire and nothing can
be forgotten:

- `~/.claude/sessions/<pid>.json` — every live session: id, cwd, name, status.
- `~/.claude/projects/<slug>/<session>.jsonl` — the transcript, appended as it
  happens. `TaskCreate` / `TaskUpdate` calls replay into nodes and edges.

Because the source is the transcript, the view also works backwards: a session
that ran last week still draws, and a session that was never told about this
skill still appears. Transcripts reach tens of megabytes, so the reader keeps a
byte offset per file and never re-reads one.

## Codex

Codex threads are read from `~/.codex/state_*.sqlite` and
`~/.codex/thread_history_*.sqlite`, and appear beside the Claude Code ones with
a `codex` badge. Codex keeps no task list, so those sessions show a band of
turns along time instead of a graph: status, duration, the files each turn
changed, and any command that exited non-zero. That absence is stated on the
card, so an empty graph area reads as a property of the source rather than as
nothing having happened.

To draw a Codex thread's plan as a graph rather than a band of turns, run
`session-tree install-codex-hook` once. It enables `update_plan` (off by
default), registers a `PostToolUse` hook that catches each plan, and asks the
model in `AGENTS.md` to write `deps: 2<-1; 3<-2` in the explanation. Those edges
are free text, so one pointing at a missing step is shown on the card instead of
being dropped.

Codex will not run the hook until it is trusted: start `codex` once after
installing and approve it when asked. Until then nothing is captured and
nothing says why.

## The one thing that is not automatic

**The graph is your decomposition. Nothing else supplies it.** A session that
never calls `TaskCreate` shows up as a card with no picture — correctly, because
nothing knows what it was trying to do. So do it always, for any piece of work
longer than a step or two, and keep it true for as long as the work lasts:

- **Decompose before starting**, not while finishing. A node is a piece of work
  with an outcome someone could check, not a keystroke.
- **Wire the real dependencies** with `addBlockedBy`. The vertical axis *is*
  those edges: it is the order the work has to happen in, and a graph with no
  edges collapses into a list, which is what the terminal already gives you.
- **Keep it current.** Start a node before working on it, and complete it once
  it is checked rather than when it feels done. Each new request from the user
  becomes a node of its own, and a changed plan changes the nodes. A graph that
  drifts from the work shows what was planned, not what is happening.
- **Write the subject for someone who was not there, and the description for
  whoever does the work.** A node has two readers. The person watching the graph
  has not read the conversation and may not be the one who asked, and the
  subject is all they see at a glance. So the subject is an outcome someone could
  check, in plain words, naming the thing itself. "The threshold box links to the
  figure that details it" is a subject; "work on figure 1" and "fix T16 driver"
  are not. Goal names follow the same rule: say what the goal is for, and for
  whom. The agent doing the work needs the opposite: the file, the branch, the
  commit, the command, and how it will know it is done. That goes in the
  description, which the popover shows. Open it with one plain sentence, then
  give the working detail. Nothing the work depends on should be dropped to make
  the graph readable. It moves to where it does not get in the way.
- **Put separate goals on separate graphs** with `metadata: {"goal": "<name>"}`.
  Without it the view falls back to connected components, which is usually right
  and occasionally merges two unrelated goals that happen to share a node.
- **Break delegated work down in your own graph, before the agent starts.** A
  subagent's own steps are not drawn: it hangs on the node that spawned it as
  one pulsing dot. So a goal handed to an agent gets its checkable sub-goals as
  nodes here, wired in order (reproduced, failing test, fix, green, looked at,
  the user tried it, committed), and you move them as the agent reports. Start
  the node the agent works on before you spawn it: the view hangs an agent on
  whichever node is in progress at that moment, so an agent spawned while
  another goal's node is open is drawn under the wrong goal. Ask the agent to
  report against those same sub-goals, or its report will not map back onto the
  picture. Give each sub-goal `metadata: {"parent": "<the goal's task id>"}`:
  the view folds them into that node behind `▸ done/total`, so the goal's graph
  keeps the size of the goal. When the work goes to another session instead,
  pass it `<your session id>#<task id>` (the id is in `CLAUDE_CODE_SESSION_ID`)
  and ask it to put that in its own nodes' `parent`; the node then links to the
  other session's graph.
- **Mark the node you are waiting on.** When the work stops for an answer from
  the user, set `metadata: {"ask": "<the question, in plain words>"}` on the
  node that waits for it, and `{"ask": null}` once it is answered. The view
  puts a `?` on that node, on its goal and at the top of the page, so someone
  with several sessions open can see where they are needed and get there. A
  question asked only in the conversation is found only by reading it. A turn
  that ends waiting for the user's go-ahead is waiting on a question too, even
  when it is worded as an offer ("say merge when you want it", "shall I
  deploy?"): the step that needs the go-ahead gets a node of its own with the
  `ask` set, before the turn ends. With no node to hang it on, end with a line
  starting `needs input:` instead.
- **Say when you are stuck.** Set the node back to `pending` and create a node
  describing the blocker, or leave it `in_progress` and let it go amber. Do not
  mark something completed to keep the picture green — a green graph that is
  wrong is worse than no graph, because it is the thing being trusted.
- **Do not delete a node you abandoned.** `status: deleted` keeps it on the
  picture, struck through. What the user forgets is rarely what finished; it is
  the branch that took forty minutes and went nowhere.

## What the colours mean

`blue, pulsing` worked on now · `green` done · `grey` waiting its turn ·
`red` blocked by an open dependency · `amber` in_progress but the transcript has
been silent 15 minutes · `struck through` abandoned.

Amber is inferred, not reported. It is the one state that cannot be faked by
forgetting to update a task, which is why it is there.

## Replay

`⏱ replay` on a session header turns the graph into a recording of itself. The
slider is linear in time, so the gaps show where the thinking went; playback
steps **event by event**, because a real-time replay of a forty-minute session
takes forty minutes.

The timeline carries the user's own prompts, in green, beside the node changes.
That is the point of it: a node turning green tells you *what* happened, and the
prompt three ticks earlier tells you *why*. Nodes appear only once they were
created and wear the status they had at that moment, so a graph mid-session
shows what was known then, not what is known now — including branches that had
not been thought of yet.

`?rp=<0..1>` opens replay at a fraction of the session's span, which is how to
link someone to a moment. `live ⏏` returns to the stream; while replay is open
that session stops following it, and the others keep updating.

## Subagents and attention

A node shows the subagents it spawned, running ones pulsing. Agents spawned
before any task existed — a review panel usually is — belong to the session, not
to a node, and say so.

The session header carries what it needs from a person: `venter på deg` when the
agent is idle and alive, `står stille` when it claims to be busy while nothing
has been written for fifteen minutes, and `?` with the question when one is
waiting: an open question box, an idle session whose last message has a
`needs input:` line, or a node marked with `ask`. The top of the page lists
every question waiting, across sessions, and a tap goes to it.

## Reading it

Hovering a node lights only its own wires, rings what they reach, and opens the
description, how long it has taken, and what it is waiting on. That popover is
the only place the detail lives — the graph itself stays a shape you can read at
a glance from across the desk.

The highlight stays while the pointer rests on the node, even as the picture
updates underneath it. A live session redraws the graph every time its
transcript grows, and a resting pointer must not have to move to get its node
back.

Sessions are ordered active first. Clicking a header collapses it, and the
choice is remembered.

## Ports and processes

One server, `127.0.0.1:8787` (`--port`, or `SESSION_TREE_PORT`, to change it),
started on demand and shared by every window. `session-tree stop` ends it; no
session owns it, so stopping it never interrupts work.

This directory is a clone of
[roykollensvendsen/session-tree](https://github.com/roykollensvendsen/session-tree).
Changes made here are commits, and land through a pull request.
