"""Set Codex up so its plans reach the view.

Three things have to be true, and none of them is on by default:

* `update_plan` is off unless asked for -- the tool's config struct defaults
  `enabled` to false.
* The call is not kept as a thread item, so a PostToolUse hook is the only
  place the plan can be caught.
* The checklist has no edges, so the dependencies have to be written by the
  model into text, which is what the note in AGENTS.md asks it to do.

Codex will not run a newly configured hook until it has been trusted, which is
a review prompt on the next interactive start. Until then the plan is simply
never captured, with nothing said about why -- so this prints the step rather
than leaving it to be discovered.

Nothing here overwrites: an existing file is backed up first, and a block that
is already present is left alone and reported.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

CODEX_DIR = Path.home() / ".codex"
MARKER = "# session-tree: capture Codex plans"

AGENTS_NOTE = """
## Writing a plan

When you call `update_plan`, put the dependencies between the steps in the
`explanation`, as `deps: <step><-<step>[,<step>]` separated by semicolons:

    deps: 2<-1; 3<-2; 4<-2

Numbers are the steps' positions in the list, counting from one. Write it only
where a step genuinely cannot start until another has finished; steps that can
be done in either order should have no entry, because listing them in an order
is not the same as one waiting for the other.

This is what lets the plan be drawn as a graph rather than a list. Leaving it
out costs nothing else -- the checklist still works.
"""


def _hook_block(hook_path: Path) -> str:
    return f"""
{MARKER}
[tools.update_plan]
enabled = true

[[hooks.PostToolUse]]
matcher = "update_plan"

[[hooks.PostToolUse.hooks]]
type = "command"
command = "{hook_path}"
timeout = 5
"""


def _back_up(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_suffix(path.suffix + f".bak-{int(time.time())}")
    shutil.copy2(path, backup)
    return backup


def _append(path: Path, block: str, marker: str) -> str:
    """Add the block unless its marker is already there. Returns what happened."""
    existing = path.read_text() if path.exists() else ""
    if marker in existing:
        return f"kept    {path} already has it"
    backup = _back_up(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    separator = "" if existing.endswith("\n") or not existing else "\n"
    path.write_text(existing + separator + block)
    return f"wrote   {path}" + (f" (backup {backup.name})" if backup else "")


def install(codex_dir: Path | None = None, hook: Path | None = None) -> list[str]:
    """Write the config and the note. Returns one line per file."""
    base = codex_dir or CODEX_DIR
    hook_path = hook or (Path(__file__).resolve().parents[2] / "hooks" / "codex-capture-plan.py")
    done = [
        _append(base / "config.toml", _hook_block(hook_path), MARKER),
        _append(base / "AGENTS.md", AGENTS_NOTE, "## Writing a plan"),
    ]
    if not hook_path.exists():
        done.append(f"MISSING {hook_path} -- the hook will not run")
    done.append("")
    done.append("Codex will not run this hook until it is trusted.")
    done.append("Start `codex` once and approve it when it asks; the answer is")
    done.append("remembered. Without that the plan is never captured and")
    done.append("nothing says why.")
    return done
