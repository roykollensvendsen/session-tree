# ADR-ST-003: Replay steps event by event, and the engine lives in the page

## Status

Accepted, Roy Kollen Svendsen, 2026-09-18.

## Context

Replay exists because the scroll is not a memory: twenty minutes into a session
the plan is above the fold and the reason for it is further up still.

A session's own history is already in the data — every node carries the stamp of
each status it was given — so no extra recording is needed.

## Options considered

**Real-time playback.** Rejected: a replay of a forty-minute session takes forty
minutes, and most of it is nothing happening.

**Fixed-interval frames.** Rejected: the interval is either too coarse for a
busy minute or too slow for a quiet hour.

**Server-side reconstruction, asking for the state at time T.** Rejected: a
round trip per slider position makes scrubbing feel dead.

**Porting the engine to Python so it can be tested with the rest.** Rejected,
and this is the one worth stating. A port would be the thing tested while the
browser ran something else, which is the defect the whole repository is about.

## Decision

Playback steps from event to event. The slider stays linear in time, so the gaps
between events are visible as gaps — where the thinking went.

The engine stays in the page as one copy, and the tests extract those functions
and run them under node against synthetic sessions. The user's own prompts are
on the timeline beside the node changes, because a node turning green says what
happened and the prompt three ticks earlier says why.

## Consequences

The tests exercise the code that ships.

What gets worse: the test suite needs node, and skips without it. If CI ever ran
somewhere without node, the replay invariants would silently stop being checked
while the suite still reported green.

## Related

`src/session_tree/index.html`, `tests/test_replay.py`.
