"""The same picture as the page, for when a browser is not what you want."""

from __future__ import annotations

from typing import Any

MARK = {"in_progress": "->", "blocked": "!!", "stalled": "~~"}
NAME_WIDTH = 44
PROJECT_WIDTH = 22
SUBJECT_WIDTH = 48


def render_summary(state: dict[str, Any]) -> str:
    """Render the state built by :func:`session_tree.state.build` as text."""
    lines: list[str] = []
    for session in state["sessions"]:
        nodes = [n for goal in session["goals"] for n in goal["nodes"]]
        live = [n for n in nodes if n["view"] != "abandoned"]
        done = len([n for n in live if n["view"] == "completed"])
        mark = "ACTIVE" if session["active"] else ("alive " if session["alive"] else "ended ")
        # Codex keeps no task list, so "0/0 done" would read as nothing having
        # happened. Its turns are what it did record.
        turns = session.get("turns") or []
        if not live and turns:
            finished = len([t for t in turns if t.get("status") == "completed"])
            tally = f"{finished:>2}/{len(turns):<2} turns"
        else:
            tally = f"{done:>2}/{len(live):<2} done "
        lines.append(
            f"  [{mark}] {session['project'][:PROJECT_WIDTH]:<{PROJECT_WIDTH}} "
            f"{tally} {(session['name'] or '')[:NAME_WIDTH]}",
        )
        for node in nodes:
            if node["view"] in MARK:
                waiting = node.get("waitingOn") or []
                tail = (" (waiting on #" + ", #".join(waiting) + ")") if waiting else ""
                lines.append(
                    f"           {MARK[node['view']]} #{node['id']} {node['subject'][:SUBJECT_WIDTH]}{tail}",
                )
    return "\n".join(lines) + "\n" if lines else "  no sessions found\n"
