# ADR-ST-006: A question can be dismissed, and the dismissal is kept by the server

## Status

Accepted, Roy Kollen Svendsen, 2026-09-25.

## Context

The view lists every question a session is waiting on, at the top of the page
and on the session's card, and marks the session as asking. Three things count
as a question: an unanswered question box, a node the agent marked with `ask`,
and a `needs input:` line in an idle session's last reply
(`questions` in `src/session_tree/state.py`).

On 2026-09-25 the list showed a question that had been answered hours earlier.
The work had moved from an interactive session to a background job that carried
on from a summary. The answer came in the job, the job completed its own copy of
the node, and the interactive session's node kept its `ask`. Nothing the job
does can reach the first session's transcript, so the question stood. The user
asked the job what it was waiting for, and it was waiting for nothing.

The rule that a finished node no longer asks
([`state.py`](../src/session_tree/state.py)) does not help, because the node in
the first session is not finished; only its copy is.

The user watches the view on a desktop and on a phone, through the tailnet
address the server can listen on (`--host`).

## Options considered

**Doing nothing.** Rejected. A stale question costs the user a question to the
agent and teaches them to ignore the list, which is the one part of the page
that asks something of them.

**Keeping the dismissal in the browser** (`localStorage`). Rejected. The view
stays read-only, but a question dismissed on the desktop still stands on the
phone, and dismissing it twice defeats the point.

**Telling the first session that the node is done**, so it clears `ask` itself.
Kept as advice, rejected as the mechanism: it needs that session to be alive
and the user to go there, and the list is where the user notices the problem.

**Recognising a session carried on in another**, by matching task subjects,
directory and branch, and taking the newer session's state. Deferred, not
rejected. It removes the cause for this pattern, but a wrong match hides a real
question, so it needs testing against real sessions first. It is in
[`deferred.md`](deferred.md).

## Decision

The viewer can dismiss a question, and the server keeps the dismissal.

- A question in the list gets a button, **avvis**. Pressing it sends
  `POST /api/dismiss` with the question's session, source, node and text.
- The server stores the dismissal in `~/.claude/session-tree/dismissed.json`
  and leaves the question out of `questions` from then on, so the session is no
  longer drawn as asking on its account. The node keeps its `ask` text in the
  tooltip, marked as dismissed.
- A dismissal is keyed on the text as well as the node. If the agent asks
  something new on the same node, it shows again.
- The endpoint accepts only a JSON body with the header
  `X-Session-Tree: dismiss`. A page on another site cannot send that header
  without a preflight the server does not answer, so it cannot dismiss
  questions from a browser the user has open.

## Consequences

A stale question can be cleared from wherever the user is looking, in one tap,
and stays cleared on every device.

What gets worse:

- **The view is no longer read-only.** The transcript stays the source of the
  graph ([ADR-ST-001](ADR-ST-001-the-transcript-is-the-source.md)), but what is
  shown as a question now also depends on a file the server writes.
- **A real question can be hidden by mistake.** The dismissal is one tap, and
  nothing brings a dismissed question back except the agent asking again in
  other words. The node's tooltip still shows it, marked as dismissed.
- **Anyone who can reach the server can dismiss.** On the tailnet address that
  is every device on the tailnet. The worst they can do is hide a question.
  [`SECURITY.md`](../SECURITY.md) says so.
- **The file grows.** Dismissals are never pruned. A line per dismissal is
  small, and pruning is listed in `deferred.md` with the trigger that would make
  it worth doing.

## Related

`src/session_tree/server.py`, `src/session_tree/state.py`,
`src/session_tree/index.html`, `SECURITY.md`, `decisions/deferred.md`,
[ADR-ST-001](ADR-ST-001-the-transcript-is-the-source.md).
