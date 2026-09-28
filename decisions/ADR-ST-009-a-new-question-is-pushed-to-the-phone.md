# ADR-ST-009: A new question is pushed to the phone through ntfy

## Status

Accepted, Roy Kollen Svendsen, 2026-09-28.

## Context

A session that asks the user something stops until it gets an answer. The
viewer puts the question first on the page, following
[ADR-ST-008](ADR-ST-008-design-rules-for-the-viewer.md), but only if the page
is being looked at. The user often has several sessions running and is away
from the desk. A question can then wait for hours, and the session with it.

## Options considered

**A browser notification from the page.** Rejected. It needs a tab open in the
background, and a phone suspends background tabs. It also needs a secure
address, and the tailnet address the phone uses is plain http.

**Web Push through a service worker.** Rejected for now. It reaches a phone
with no tab open and encrypts what it sends. But it needs https, a service
worker, keys and a subscription store. That is a lot of machinery for one
message type.

**ntfy.** Chosen. ntfy is a small publish and subscribe service with a phone
app. The server makes one HTTP POST to a topic's address, and the app shows it.
No tab needs to be open, and there is nothing to install on the server side.

## Decision

- **Off unless set up.** The server sends nothing until it is given a topic
  address. It reads `SESSION_TREE_NTFY`, or else the first line of
  `~/.claude/session-tree/ntfy.url`. The file is there so the address survives
  the server being started from a shell that does not have the variable.
- **What is sent.** The title is "Spørsmål i" and the session's name. The body
  is the question, cut to 200 characters. If a second line in the file (or
  `SESSION_TREE_NTFY_CLICK`) names the viewer's address, a tap on the message
  opens it. The server cannot pick that address itself, because it may listen
  only on this machine.
- **One sender.** One server may run per address, and each sees the same
  questions. Only the one holding a lock file,
  `~/.claude/session-tree/ntfy.lock`, sends. If it stops, the next one to see a
  new question takes the lock.
- **Only new questions.** A question is new when its session, source, node and
  text did not wait a moment before. This is the same key a dismissal uses
  (ADR-ST-006). The questions already waiting when the server starts are not
  sent, so a restart does not bring a burst of old messages. A question that
  goes away and comes back is sent again.
- **Every new question, whether or not a page is open.** An open tab on the
  desk says nothing about whether anyone is looking at it.
- **Sending never holds up the picture.** Each message goes out on its own
  thread with a time limit. A failure is written to the server's error output
  and not retried.

## Consequences

The question's text leaves the machine. On the public ntfy.sh it passes a
third party, and anyone who knows the topic name can read it. The topic name
works as a password, so it has to be long and random. Anyone who wants the
text to stay at home can run their own ntfy server and point the address at
it.

A question asked while the server is down is not sent when it comes back up.
It is still on the page.

## Related

[ADR-ST-006](ADR-ST-006-a-question-can-be-dismissed.md),
[ADR-ST-008](ADR-ST-008-design-rules-for-the-viewer.md),
`src/session_tree/notify.py`, `src/session_tree/server.py`, <https://docs.ntfy.sh/publish/>.
