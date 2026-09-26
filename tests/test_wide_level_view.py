"""A level with more steps than fit side by side wraps onto rows instead of squeezing them.

Unlike the other view tests, this one runs the page's own layout code: the
functions that place the boxes need nothing from a browser but a way to measure
text, so the stretch of the script that holds them is cut out and run under
Node with a stand-in measurer. What is checked is what a viewer sees: every box
wide enough to read, no box on top of another, and a drawing no wider than the
room it is given, so nothing is scaled down to fit.
"""

import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
README = (ROOT / "README.md").read_text()
START, END = "const SIZE={", "\n/* A breakdown folded into its node"
# the narrowest box a subject can still be read in, in a card and enlarged
READABLE = {"card": 100, "large": 250}

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node to run the page's layout")


def layout_code() -> str:
    """The part of the page's script that sizes and places the boxes."""
    assert START in PAGE, "the page no longer defines SIZE"
    return PAGE[PAGE.index(START) : PAGE.index(END, PAGE.index(START))]


def place(goal: dict, width: int, size: str, *, nested: bool) -> dict:
    """Run the page's layout on a goal and return where every box went."""
    script = (
        "globalThis.document={createElement:()=>({getContext:()=>"
        "({font:'',measureText:t=>({width:t.length*6})})})};\n"
        "function chipOf(){return null;}\n"
        + layout_code()
        + f"\nconst L=(({json.dumps(nested)})?layoutNested:layout)({json.dumps(goal)},{width},SIZE.{size});"
        "\nprocess.stdout.write(JSON.stringify({W:L.W,pos:L.pos}));"
    )
    run = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def a_wide_goal(*, nested: bool) -> dict:
    """Seventy-seven steps that wait on nothing, and one that waits on them all."""
    nodes = [{"id": str(i), "subject": f"Step {i} of the plan", "blockedBy": []} for i in range(77)]
    nodes.append({"id": "end", "subject": "Everything is done", "blockedBy": [str(i) for i in range(77)]})
    if nested:
        nodes += [{"id": f"k{i}", "subject": f"Part {i}", "parent": "0", "blockedBy": []} for i in range(3)]
    depth = {n["id"]: (1 if n["id"] == "end" else 0) for n in nodes}
    return {"title": "wide", "nodes": nodes, "depth": depth}


def overlapping(pos: dict) -> list[tuple[str, str]]:
    """Pairs of top-level boxes that cover each other."""
    boxes = [(k, p) for k, p in pos.items() if not k.startswith("k")]
    return [
        (a, b)
        for i, (a, p) in enumerate(boxes)
        for b, q in boxes[i + 1 :]
        if p["x"] < q["x"] + q["w"]
        and q["x"] < p["x"] + p["w"]
        and p["y"] < q["y"] + q["h"]
        and q["y"] < p["y"] + p["h"]
    ]


def test_the_readme_says_a_wide_level_wraps():
    assert "wraps onto more rows" in README, "README.md does not say what happens to a level too wide to fit"


@pytest.mark.parametrize("nested", [False, True], ids=["flat", "with a breakdown open"])
@pytest.mark.parametrize(("size", "width"), [("card", 340), ("card", 1000), ("large", 350), ("large", 1400)])
def test_a_wide_level_keeps_every_step_readable(size, width, nested):
    drawn = place(a_wide_goal(nested=nested), width, size, nested=nested)
    narrow = [k for k, p in drawn["pos"].items() if not k.startswith("k") and p["w"] < READABLE[size] - 1]
    assert not narrow, f"{len(narrow)} steps are narrower than {READABLE[size]} px"
    assert not overlapping(drawn["pos"]), "steps are drawn on top of each other"
    if size == "card":
        assert drawn["W"] <= width, f"the drawing is {drawn['W']} px wide in {width} px, so it is scaled down"
    else:
        assert drawn["W"] <= 6 * (250 + 18) + 40, f"the enlarged drawing is {drawn['W']} px wide"
