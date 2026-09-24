"""A resting pointer keeps its node lit while the graph redraws under it.

A live session redraws the whole graph each time its transcript grows, so the
node under a still pointer is replaced by a new one that has seen no pointer
event. The graph is drawn by inline JavaScript, which no test here can run.
What can be checked is that SKILL.md makes the promise and that the page carries
the mechanism that keeps it: remembering where the pointer is, and after every
redraw handing the node now under it the same event again.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
SKILL = (ROOT / "SKILL.md").read_text()


def test_the_skill_promises_a_resting_pointer_keeps_its_highlight():
    assert "stays while the pointer rests" in SKILL


def test_the_page_remembers_where_the_pointer_is():
    assert re.search(r"document\.addEventListener\('mousemove'.*POINTER=", PAGE), (
        "the page does not keep the pointer's last position"
    )


def test_a_redraw_hands_the_node_under_the_pointer_its_event_again():
    body = PAGE.split("function render(", 1)[1].split("\nfunction ", 1)[0]
    assert "rehover(" in body, "render() does not restore the hover after redrawing"
    assert "elementFromPoint" in PAGE, "nothing finds the node now under the pointer"
