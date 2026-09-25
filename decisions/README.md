# Decision records

A decision that costs more to reverse than to take is written down here before
the code that rests on it. A decision that only implements one already taken
is not; it is a commit message.

## The form

Every record is `ADR-ST-NNN-a-short-title.md`, with these sections in
this order:

| Section | Holds |
|---|---|
| Status | Accepted or Proposed, who decided, when; an objection returns it to Proposed |
| Context | what was true when the question arose, with sources where the facts are checkable |
| Options considered | every option weighed, including doing nothing, each with why it was not taken |
| Decision | what was chosen, in one paragraph |
| Consequences | what this costs, what it forecloses, and at least one thing that gets worse |
| Related | the pages it shapes |

Numbers are one sequence and never reused. A record is superseded by a later
one, never edited into a different decision.

Record the process choices too, not only the artefact ones. How a change is
made, and why, is what costs time on every future contribution, and it is the
decision nobody writes down.

## The records

| Id | Decides | Status |
|---|---|---|
| [ADR-ST-001](ADR-ST-001-the-transcript-is-the-source.md) | the transcript is the source, not a hook | Accepted |
| [ADR-ST-002](ADR-ST-002-server-sent-events.md) | server-sent events rather than websockets | Accepted |
| [ADR-ST-003](ADR-ST-003-replay-steps-by-event.md) | replay steps by event; the engine lives in the page | Accepted |
| [ADR-ST-004](ADR-ST-004-how-a-change-is-made-here.md) | how a change is made here | Accepted |
| [ADR-ST-005](ADR-ST-005-a-node-can-hold-a-breakdown.md) | a node can hold a breakdown, folded behind a symbol | Accepted |
| [ADR-ST-006](ADR-ST-006-a-question-can-be-dismissed.md) | a question can be dismissed, and the server keeps the dismissal | Accepted |

What is deliberately left undone, and what would make each worth doing, is
[`deferred.md`](deferred.md). A thing left undone with no trigger is a thing
forgotten.
