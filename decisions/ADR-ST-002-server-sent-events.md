# ADR-ST-002: Server-sent events rather than websockets

## Status

Accepted, Roy Kollen Svendsen, 2026-09-18.

## Context

The page must update as the work happens, without the viewer refreshing. The
data flows one way: the server has news, the page draws it. The page never
sends anything back.

The tool is meant to run with no dependencies beyond the standard library, so
it can be installed and started without a build step.

## Options considered

**Polling from the browser.** Rejected. A one-second poll is visibly late on a
status change, and a faster one re-sends the whole picture constantly.

**Websockets.** Rejected. Two-way transport for one-way traffic. The standard
library has no websocket server, so it would mean a dependency or a hand-written
frame parser, and reconnection would have to be written by hand.

**Server-sent events.** Chosen. One-way by design, plain HTTP, and the browser
reconnects on its own.

## Decision

The server holds a queue per connected page and pushes a full snapshot whenever
the picture changes. A watcher thread polls the transcripts every 400 ms and
compares the serialised result, so an unchanged session sends nothing.

Measured: a status change reaches the page in about 0.01 s.

## Consequences

No dependencies, and a page that recovers from a restarted server by itself.

What gets worse: every update is the whole picture rather than a delta. With
six sessions that is tens of kilobytes per change, which is free on localhost
and would not be over a network. This forecloses running the server anywhere but
the machine being watched, which is also why it binds `127.0.0.1`.

## Related

`src/session_tree/server.py`, `src/session_tree/index.html`.
