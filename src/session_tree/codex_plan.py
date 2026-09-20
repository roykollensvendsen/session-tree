"""Turn a captured Codex plan into the graph the view already draws.

Codex's `update_plan` carries a flat checklist: each step is a string and a
status, with no identifier and no edges. Dependencies therefore have to travel
in text the model writes, either as a `deps:` line in the explanation or as a
`[2<-1]` prefix on a step.

That makes them a claim rather than a field a tool validated, so a reference to
a step that does not exist is kept and reported rather than dropped. A graph
missing an edge nobody mentioned is worse than one that says it is broken.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

PLAN_DIR = Path(
    os.environ.get("SESSION_TREE_PLAN_DIR", Path.home() / ".codex" / "session-tree-plans"),
)
#: `deps: 2<-1; 3<-2,4` anywhere in the explanation.
DEPS_LINE = re.compile(r"deps\s*:\s*([^\n]+)", re.IGNORECASE)
#: One `3<-1,2` clause inside that line.
DEPS_CLAUSE = re.compile(r"(\d+)\s*<-\s*([\d\s,]+)")
#: `[2<-1]` or `[2]` at the start of a step.
STEP_PREFIX = re.compile(r"^\s*\[\s*(\d+)\s*(?:<-\s*([\d\s,]*))?\]\s*")
STATUS_VIEW = {"completed": "completed", "in_progress": "in_progress", "pending": "pending"}


def _ids(raw: str) -> list[str]:
    return [p.strip() for p in raw.split(",") if p.strip().isdigit()]


def _from_explanation(explanation: str | None) -> dict[str, list[str]]:
    """Edges written as `deps: 2<-1; 3<-2,4`."""
    if not explanation:
        return {}
    line = DEPS_LINE.search(explanation)
    if not line:
        return {}
    edges: dict[str, list[str]] = {}
    for child, parents in DEPS_CLAUSE.findall(line.group(1)):
        edges.setdefault(child, []).extend(_ids(parents))
    return edges


def _from_prefixes(steps: list[dict[str, str]]) -> tuple[dict[str, list[str]], list[str]]:
    """Edges written as `[2<-1]` on the step itself; returns them and the cleaned text."""
    edges: dict[str, list[str]] = {}
    cleaned = []
    for index, entry in enumerate(steps, start=1):
        text = entry.get("step", "")
        match = STEP_PREFIX.match(text)
        if match:
            own = match.group(1)
            if match.group(2):
                edges.setdefault(own, []).extend(_ids(match.group(2)))
            text = text[match.end() :]
        cleaned.append(text or f"steg {index}")
    return edges, cleaned


def read_plan(session_id: str, plan_dir: Path | None = None) -> dict[str, Any] | None:
    """The plan captured for this thread, if the hook has written one."""
    path = (plan_dir or PLAN_DIR) / f"{session_id}.json"
    try:
        loaded = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _build_nodes(
    steps: list[dict[str, str]],
    texts: list[str],
    edges: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """One node per step, keeping any edge that points at a step that exists."""
    known = {str(i) for i in range(1, len(steps) + 1)}
    nodes: list[dict[str, Any]] = []
    dangling: list[str] = []
    for index, (entry, text) in enumerate(zip(steps, texts, strict=True), start=1):
        node_id = str(index)
        wanted = edges.get(node_id, [])
        dangling.extend(f"#{node_id}→#{d}" for d in wanted if d not in known)
        status = STATUS_VIEW.get(str(entry.get("status", "pending")), "pending")
        nodes.append(
            {
                "id": node_id,
                "subject": text,
                # The step text is all Codex records; there is no second field.
                "description": "",
                "status": status,
                "owner": "",
                "goal": None,
                "blockedBy": [d for d in wanted if d in known and d != node_id],
                "blocks": [],
                "history": [],
                "created": None,
                "started": None,
                "ended": None,
                "createdMs": None,
                "startedMs": None,
                "endedMs": None,
                "waitingOn": [],
                "view": status,
                "durationMs": None,
            }
        )
    return nodes, dangling


def _apply_views(nodes: list[dict[str, Any]]) -> None:
    """Fill in the reverse edges and the colour each node is drawn in."""
    by_id = {n["id"]: n for n in nodes}
    for node in nodes:
        for dep in node["blockedBy"]:
            by_id[dep]["blocks"].append(node["id"])

    open_ids = {n["id"] for n in nodes if n["status"] in ("pending", "in_progress")}
    for node in nodes:
        blocking = [d for d in node["blockedBy"] if d in open_ids]
        node["waitingOn"] = blocking
        if node["status"] == "in_progress" and blocking:
            node["view"] = "blocked"
        elif node["status"] == "pending" and blocking:
            node["view"] = "waiting"


def goals_from_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the goal list the view draws, or an empty list if there is no plan."""
    raw_steps = plan.get("steps")
    if not isinstance(raw_steps, list):
        return []
    steps = [s for s in raw_steps if isinstance(s, dict)]
    if not steps:
        return []

    prefix_edges, texts = _from_prefixes(steps)
    edges = _from_explanation(plan.get("explanation"))
    for child, parents in prefix_edges.items():
        edges.setdefault(child, []).extend(parents)

    nodes, dangling = _build_nodes(steps, texts, edges)
    _apply_views(nodes)
    return [
        {
            "id": "plan",
            "title": "plan",
            "nodes": nodes,
            "depth": _depths(nodes),
            # Said out loud: these edges are text the model wrote, not a field
            # anything validated, so a broken one is shown rather than swallowed.
            "danglingEdges": sorted(set(dangling)),
            "hasEdges": any(n["blockedBy"] for n in nodes),
        }
    ]


def _depths(nodes: list[dict[str, Any]]) -> dict[str, int]:
    by_id = {n["id"]: n for n in nodes}
    depth: dict[str, int] = {}

    def walk(node_id: str, seen: frozenset[str]) -> int:
        if node_id in depth:
            return depth[node_id]
        if node_id in seen or node_id not in by_id:
            return 0
        deps = [d for d in by_id[node_id]["blockedBy"] if d in by_id]
        value = 1 + max([walk(d, seen | {node_id}) for d in deps], default=-1)
        depth[node_id] = value
        return value

    for node in nodes:
        walk(node["id"], frozenset())
    return depth
