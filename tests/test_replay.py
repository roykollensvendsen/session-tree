"""The replay engine lives in the page, so the tests run the page's own copy.

Extracting the functions and evaluating them in node keeps a second
implementation from existing: a Python port would be the thing actually tested,
and the browser would run something else.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from session_tree.state import TranscriptReader, _apply_views, _components

if TYPE_CHECKING:
    from tests.conftest import Transcript

PAGE = Path(__file__).resolve().parents[1] / "src" / "session_tree" / "index.html"
NODE = shutil.which("node")

HARNESS = """
const fs=require('fs');
const html=fs.readFileSync(PAGE,'utf8');
const js=html.split('<script>')[1].split('</script>')[0];
const grab=n=>{const i=js.indexOf('function '+n+'(');let d=0,s=-1;
  for(let k=i;k<js.length;k++){if(js[k]==='{'){if(d===0)s=k;d++}
    else if(js[k]==='}'){d--;if(d===0)return js.slice(i,k+1)}}};
eval(grab('stateAt')+'\\n'+grab('evAt'));
const session=JSON.parse(fs.readFileSync(STATE,'utf8'));
const out=[];
for(const e of session.events){
  const goals=stateAt(session,e.at);
  out.push({at:e.at,nodes:goals.flatMap(g=>g.nodes).map(n=>({id:n.id,view:n.view,status:n.status}))});
}
out.push({at:session.spanEnd,final:true,
  nodes:stateAt(session,session.spanEnd).flatMap(g=>g.nodes).map(n=>({id:n.id,view:n.view,status:n.status}))});
console.log(JSON.stringify(out));
"""


def session_payload(transcript: Transcript) -> dict[str, Any]:
    """Build the object the page receives, from a synthetic transcript."""
    reader = TranscriptReader(transcript.path)
    reader.read()
    nodes = list(reader.tasks.values())
    _apply_views(nodes, quiet=1, now=0)
    events = sorted(reader.events, key=lambda e: e["at"])
    return {
        "goals": _components(nodes),
        "events": events,
        "spanStart": events[0]["at"],
        "spanEnd": events[-1]["at"] + 1000,
    }


def replay_frames(tmp_path: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the page's own stateAt over every event, returning each frame."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(payload))
    script = tmp_path / "harness.js"
    script.write_text(
        f"const PAGE={json.dumps(str(PAGE))};const STATE={json.dumps(str(state_file))};" + HARNESS,
    )
    result = subprocess.run(
        [str(NODE), str(script)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    frames: list[dict[str, Any]] = json.loads(result.stdout)
    return frames


pytestmark = pytest.mark.skipif(NODE is None, reason="node is needed to run the page's own engine")


def test_a_node_never_appears_before_it_was_created(built: Transcript, tmp_path: Path) -> None:
    frames = replay_frames(tmp_path, session_payload(built))
    counts = [len(f["nodes"]) for f in frames]
    assert counts == sorted(counts), "nodes vanished as time moved forward"


def test_a_node_is_never_green_before_it_finished(built: Transcript, tmp_path: Path) -> None:
    payload = session_payload(built)
    done_at = {e["taskId"]: e["at"] for e in payload["events"] if e["kind"] == "status:completed"}
    for frame in replay_frames(tmp_path, payload):
        for node in frame["nodes"]:
            if node["view"] == "completed":
                assert node["id"] in done_at
                assert done_at[node["id"]] <= frame["at"]


def test_finished_work_does_not_become_unfinished(built: Transcript, tmp_path: Path) -> None:
    seen: set[str] = set()
    for frame in replay_frames(tmp_path, session_payload(built)):
        for node in frame["nodes"]:
            if node["view"] == "completed":
                seen.add(node["id"])
            elif node["id"] in seen:
                assert node["status"] == "abandoned", f"#{node['id']} became unfinished again"


def test_the_last_frame_equals_the_live_picture(built: Transcript, tmp_path: Path) -> None:
    payload = session_payload(built)
    final = next(f for f in replay_frames(tmp_path, payload) if f.get("final"))
    replayed = {n["id"]: n["status"] for n in final["nodes"]}
    live = {n["id"]: n["status"] for g in payload["goals"] for n in g["nodes"]}
    assert replayed == live


def test_an_abandoned_branch_appears_then_is_struck_through(built: Transcript, tmp_path: Path) -> None:
    payload = session_payload(built)
    frames = replay_frames(tmp_path, payload)
    states = [next((n["status"] for n in f["nodes"] if n["id"] == "5"), "absent") for f in frames]
    assert states[0] == "absent", "the dropped branch existed before it was thought of"
    assert "pending" in states, "the dropped branch was never live"
    assert states[-1] == "abandoned", "the dropped branch did not end up struck through"
