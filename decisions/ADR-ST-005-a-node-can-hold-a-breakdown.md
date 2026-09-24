# ADR-ST-005: A node can hold a breakdown, folded behind a symbol

## Status

Accepted, Roy Kollen Svendsen, 2026-09-24.

## Context

The view draws one graph per goal, from the task list the session keeps. A goal
is often handed on, and two things happen to it.

**It goes to a helper agent in the same session.** Helpers have no task tools:
a helper told to create two tasks found no `TaskCreate`, `TaskUpdate` or
`TaskList` (probe, 2026-09-24, Claude Code 2.1.280). So the breakdown of
delegated work can only live in the delegating session's own graph, which is
what `SKILL.md` has asked for since
[#14](https://github.com/roykollensvendsen/session-tree/pull/14). The cost is
that the goal's graph fills with steps nothing else in it uses. A bug fix handed
to a helper added eight nodes to a graph that needed one.

**It goes to another session**, such as a background job or a second terminal.
That session keeps its own list and is drawn as its own card. Nothing connects
the card to the node it serves, so the person following the first graph sees a
node that is in progress and cannot find where the work is happening.

Two facts make a connection possible. Every agent can read its own session id
from `CLAUDE_CODE_SESSION_ID`. And a task's `metadata` is free-form, recorded in
the transcript with the rest of the call, and already carries `goal`.

The request came from the user watching the view on a phone: link a node to the
graph that breaks it down, or unfold that breakdown into the original graph.
Draw it into the original only when other nodes there use the sub-goals
directly. And mark such a node with a symbol that can be tapped.

## Options considered

**Doing nothing.** Rejected. The same-session breakdown stays flat and crowds
the goal. The cross-session one stays invisible from the node it serves.

**Always unfolding the breakdown into the parent graph.** Rejected. It is the
crowding above, made permanent.

**Only linking, never unfolding.** Rejected for the same-session case. There is
no other graph to link to, because the helper cannot keep one.

**Inferring the breakdown from the edges**, for example treating a chain that
hangs off a single node as its breakdown. Rejected. A chain of steps and a
breakdown look the same in the edges, and a tie the view invents is worse than
none. That is the same reason `_attach_agents` leaves unplaced helpers loose
rather than guessing a node for them.

**A plan file or a hook that records the hierarchy.** Rejected for the reasons
in [ADR-ST-001](ADR-ST-001-the-transcript-is-the-source.md): a second file the
agent must remember to keep, or a hook that must be installed.

## Decision

The breakdown is declared, not inferred.

- **In the same session**, a sub-goal carries `metadata: {"parent": "<task id>"}`.
- **In another session**, the goal's nodes carry
  `metadata: {"parent": "<session id>#<task id>"}`. The delegating agent passes
  that reference in its prompt. Where it knows the other session's id, it can
  instead set `{"session": "<id>"}` on its own node. Either end is enough.

A breakdown is drawn **folded** under its parent node unless a node outside the
breakdown has an edge to or from one of its sub-goals. In that case it is drawn
unfolded, because folding would hide a real dependency. That is the user's
rule, stated as a test on the edges. The viewer can fold or unfold any
breakdown, and the choice is remembered the way a collapsed session is.

A folded node shows a symbol large enough for a finger:

- **`▸ 4/7`** (done and total) for a breakdown in the same session. Tapping it
  unfolds the breakdown in place.
- **`↗`** for one in another session. Tapping it opens that session's graph.
  That graph's header points back to the node it serves with a **`↖`** symbol.

The symbol takes the colour of the worst state among the sub-goals. A red or
amber sub-goal shows on the folded node. The node's own status is left as the
agent set it. If the node is green while a sub-goal is still open, the symbol
shows the disagreement instead of hiding it.

## Consequences

A goal's graph stays the size of the goal, and delegated work can be followed
from the node that delegated it, into another session if need be.

What gets worse:

- **The hierarchy depends on the agent writing `parent`.** That is a promise
  nothing enforces, which is the weakness ADR-ST-001 held against a plan file.
  It is smaller here: the promise lives in the ordinary task call, and a missing
  tag leaves today's flat picture rather than a wrong one.
- **A wrong reference must be visible.** A `parent` that names a missing node
  or session is drawn as a dangling link and said to be one, as a Codex `deps:`
  entry pointing at a missing step already is.
- **Replay must decide what folded means in the past.** Folding is view state,
  not history, so the current choice applies to every frame.
- **The skill's delegation rule gains a step:** tag each sub-goal with `parent`,
  and pass `<session id>#<task id>` to another session.

Drawing a helper's own graph stays impossible while helpers have no task tools.
It is listed in [`deferred.md`](deferred.md).

## Related

`src/session_tree/state.py`, `src/session_tree/index.html`, `SKILL.md`,
[ADR-ST-001](ADR-ST-001-the-transcript-is-the-source.md).
