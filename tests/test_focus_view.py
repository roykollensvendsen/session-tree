"""The README promises gestures for the focused graph; the page must bind them.

The graph is drawn by inline JavaScript, which no test here can run. What can
be checked is that every gesture the README names has a handler in the page,
so the document and the code cannot drift apart silently.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
README = (ROOT / "README.md").read_text()


def test_the_readme_describes_the_focused_graph():
    block = re.search(r"## One graph on its own\n(.*?)\n## ", README, re.DOTALL)
    assert block, "README.md no longer has the section on the focused graph"
    for word in ("wheel", "drag", "double-click", "Esc"):
        assert word in block.group(1), f"the README section does not mention {word}"


def test_every_gesture_the_readme_names_has_a_handler_in_the_page():
    handlers = {
        "wheel": "'wheel'",
        "drag": "'pointerdown'",
        "double-click": "'dblclick'",
        "Esc": "'Escape'",
    }
    for gesture, needle in handlers.items():
        assert needle in PAGE, f"README promises {gesture}; no {needle} handler in index.html"


def test_the_goal_title_opens_the_focus_and_the_focus_can_close():
    assert "openFocus(" in PAGE
    assert "closeFocus(" in PAGE
    assert 'id="focus"' in PAGE
