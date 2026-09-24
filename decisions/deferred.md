# What is deliberately not done yet

A thing left undone with no trigger is a thing forgotten. Each row names what
would make it worth doing, so the question comes back on its own rather than
depending on someone remembering it. Nothing enforces a trigger; the list is
read whenever a decision record is written and when a phase ends.

| Not done | The trigger | Why not now |
|---|---|---|
| A coverage threshold in CI | Two months of measured coverage to set it below | A number picked before there is data is a guess with a gate on it |
| A code of conduct and issue templates | A second contributor, or the first outside issue | Boilerplate answering questions nobody has asked |
| A release workflow and publishing | The first release someone outside will install | A published name is claimed and a published version cannot be reused |
| `CODEOWNERS` | A second person who reviews | It would name one person as the owner of everything |
| `pre-commit` as a requirement rather than an option | A second contributor | The gates run in CI, and a hook one person installs is a hook one person maintains |
| A check against a real transcript, not only synthetic ones | Claude Code changes how it writes transcripts, or a user reports an empty graph | The tests would keep passing while the reader silently found nothing ([ADR-ST-001](ADR-ST-001-the-transcript-is-the-source.md)) |
| Failing the suite when node is missing rather than skipping | A CI runner without node, or a second person running the tests | Today it is always there, and a hard failure would block a contributor for a reason they did not cause ([ADR-ST-003](ADR-ST-003-replay-steps-by-event.md)) |
| Linking a session node to the commits and files it produced | Someone asks what a finished node actually changed | The data is in the transcript already; nobody has needed it yet |
| Watching sessions on another machine | A second machine, or a rack whose sessions matter | The server binds localhost by design ([ADR-ST-002](ADR-ST-002-server-sent-events.md)) |
| Drawing a helper agent's own task graph under the node that spawned it | Helper agents are given the task tools | They have none today, so there is nothing to draw ([ADR-ST-005](ADR-ST-005-a-node-can-hold-a-breakdown.md)) |
