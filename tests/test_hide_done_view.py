"""Finished goals can be hidden, so a goal's graph shows what is left.

Unlike the other view tests, this one runs the page's own functions in node,
when node is there: hiding is a rule about which nodes and edges survive, and
reading the source for keywords would not catch it getting that rule wrong.
"""

import json
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
README = (ROOT / "README.md").read_text()

NODE = shutil.which("node")


def function(name: str) -> str:
    """One top-level function of the page's script, with its keyword."""
    body = PAGE.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]
    return f"function {name}({body}"


def _node(n_id: str, view: str, **more: object) -> dict:
    return {"id": n_id, "subject": n_id, "view": view, "blockedBy": [], "blocks": [], **more}


# 1 is done and blocked 3. 2 is done, but one of its steps (4) is still running,
# so 2 stays; its other step (6) is done and goes.
GOAL = {
    "nodes": [
        _node("1", "completed", blocks=["3"]),
        _node(
            "2",
            "completed",
            breakdown={"children": ["4", "6"], "folded": False, "done": 1, "total": 2},
        ),
        _node("3", "pending", blockedBy=["1"]),
        _node("4", "in_progress", parent="2"),
        _node("6", "completed", parent="2"),
    ]
}


def shown(*, hide_done: bool) -> dict:
    """The nodes the page would draw, and what each still waits on."""
    script = "\n".join(
        [
            "let FOLD={};",
            "const foldKey=(sess,n)=>sess.sessionId+'/'+n.id;",
            # isFolded is followed in the page by the switch's own declaration
            function("isFolded"),
            function("finished"),
            function("hiddenBy"),
            function("liftEdges"),
            f"HIDE_DONE={json.dumps(hide_done)};",
            f"let goal={json.dumps(GOAL)};",
            "const sess={sessionId:'s'};",
            "const hidden=hiddenBy(goal,sess);",
            "if(hidden.size) goal=liftEdges(goal,hidden);",
            (
                "console.log(JSON.stringify(Object.fromEntries("
                "goal.nodes.map(n=>[n.id,[...n.blockedBy].sort()]))));"
            ),
        ]
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=False)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_everything_is_drawn_until_the_viewer_asks():
    assert shown(hide_done=False) == {"1": [], "2": [], "3": ["1"], "4": [], "6": []}


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_finished_goals_go_and_their_edges_with_them():
    # 1 and 6 are gone; 3 no longer waits on anything, since what it waited on
    # is done; 2 stays because a step inside it is still running
    assert shown(hide_done=True) == {"2": [], "3": [], "4": []}


def test_the_switch_is_in_the_header_and_remembered():
    header = PAGE.split("<header>", 1)[1].split("</header>", 1)[0]
    assert 'id="hidedone"' in header, "there is no switch in the header"
    assert "st.hideDone" in PAGE, "the viewer's choice is not remembered"


def test_the_readme_says_how_to_hide_finished_goals():
    block = re.search(r"## Hiding finished goals\n(.*?)\n## ", README, re.DOTALL)
    assert block, "README.md has no section on hiding finished goals"
    for words in ("skjul ferdige", "still running"):
        assert words in block.group(1), f"the README section does not say {words!r}"
