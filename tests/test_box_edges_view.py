"""An arrow out of an unfolded box leaves from the bottom of the box, not from under its heading.

An unfolded breakdown draws the node as a box round its own steps, with the
node's subject as the heading. An arrow from that node to what waits on it
started just under the heading, so it ran down through the steps inside. Like
test_wide_level_view, this runs the page's own layout and edge code under Node.
"""

import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
START, END = "const SIZE={", "\n/* A breakdown folded into its node"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node to run the page's layout")


def run(goal: dict, size: str) -> dict:
    """Lay the goal out as a nested graph and return the ends of every arrow."""
    code = PAGE[PAGE.index(START) : PAGE.index(END, PAGE.index(START))]
    script = (
        "globalThis.document={createElement:()=>({getContext:()=>"
        "({font:'',measureText:t=>({width:t.length*6})})})};\n"
        "function chipOf(){return null;}\n"
        + code
        + f"\nconst G={json.dumps(goal)}, L=layoutNested(G,800,SIZE.{size}), out={{}};"
        "\nG.nodes.forEach(n=>(n.blockedBy||[]).forEach(d=>{"
        " out[d+'>'+n.id]=edgeEnds(L.pos[d],L.pos[n.id]); }));"
        "\nprocess.stdout.write(JSON.stringify({pos:L.pos,ends:out}));"
    )
    done = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


GOAL = {
    "title": "a box between two steps",
    "nodes": [
        {"id": "before", "subject": "Comes first", "blockedBy": []},
        {"id": "box", "subject": "The part with steps", "blockedBy": ["before"]},
        {"id": "s1", "subject": "Step one", "parent": "box", "blockedBy": []},
        {"id": "s2", "subject": "Step two", "parent": "box", "blockedBy": ["s1"]},
        {"id": "after", "subject": "Comes last", "blockedBy": ["box"]},
    ],
}


@pytest.mark.parametrize("size", ["card", "large"])
def test_an_arrow_out_of_an_unfolded_box_leaves_from_its_bottom(size):
    drawn = run(GOAL, size)
    frame = drawn["pos"]["box"]["frame"]
    start = drawn["ends"]["box>after"]
    assert start["y1"] == pytest.approx(frame["y"] + frame["h"]), (
        f"the arrow leaves at {start['y1']}, inside a box that ends at {frame['y'] + frame['h']}"
    )


@pytest.mark.parametrize("size", ["card", "large"])
def test_an_arrow_into_an_unfolded_box_ends_at_its_top(size):
    drawn = run(GOAL, size)
    assert drawn["ends"]["before>box"]["y2"] == pytest.approx(drawn["pos"]["box"]["y"])


@pytest.mark.parametrize("size", ["card", "large"])
def test_an_arrow_between_plain_nodes_is_unchanged(size):
    drawn = run(GOAL, size)
    a, b = drawn["pos"]["s1"], drawn["pos"]["s2"]
    ends = drawn["ends"]["s1>s2"]
    assert (ends["x1"], ends["y1"], ends["x2"], ends["y2"]) == pytest.approx(
        (a["cx"], a["y"] + a["h"], b["cx"], b["y"])
    )
