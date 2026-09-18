# ADR-ST-001: The transcript is the source, not a hook

## Status

Accepted, Roy Kollen Svendsen, 2026-09-18.

## Context

The view needs to know what each Claude Code session is working on. Two places
carry that, and only one of them is written by the agent's own ordinary work.

Claude Code maintains `~/.claude/sessions/<pid>.json` for every live session and
appends to `~/.claude/projects/<slug>/<session>.jsonl` as the session happens.
The transcript records every `TaskCreate` and `TaskUpdate` call and its result,
which together carry ids, subjects, `blockedBy` edges, owners and metadata. The
task store itself holds no task data on disk: `~/.claude/tasks/<session>/`
contains only a `.highwatermark` and a `.lock`.

Transcripts are large. Twenty-seven megabytes was observed on a single session
in the repository this tool was built in.

## Options considered

**A hook on `TaskCreate`/`TaskUpdate` writing to a shared file.** Rejected. It
requires installing a hook in every environment, it only covers sessions started
after it was installed, and it is one more thing that must not be forgotten. It
also makes the tool's correctness depend on a configuration file the user edits.

**Polling the task store.** Rejected: there is nothing there to poll.

**Asking the agent to maintain a separate plan file.** Rejected. It is a promise
nothing enforces, and a graph that is wrong is worse than no graph, because it
is the thing being trusted.

**Doing nothing and reading the terminal.** Rejected; it is the problem.

## Decision

Read the two files Claude Code already maintains and replay the tool calls. No
hook, no configuration, no cooperation from the session being observed.

Transcripts are read forward from a remembered byte offset per file and never
re-parsed, which keeps an incremental poll at about a millisecond after the
first read.

## Consequences

The view works backwards over sessions that have already finished, and over
sessions that never heard of this tool.

What gets worse: the format is not a public interface. A change to how Claude
Code writes transcripts, or to the wording `Task #N created successfully`,
breaks the reader silently — it would simply show fewer nodes. The tests use
synthetic transcripts in the observed shape, so they would keep passing.
Mitigating that would need a check against a real transcript, which is
[deferred](deferred.md).

## Related

`src/session_tree/state.py`, `README.md`, `SKILL.md`.
