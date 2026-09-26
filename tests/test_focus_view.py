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


def test_the_readme_promises_a_way_out_of_the_enlarged_graph_on_a_phone():
    block = re.search(r"## One graph on its own\n(.*?)\n## ", README, re.DOTALL)
    assert block, "README.md no longer has the section on the enlarged graph"
    for words in ("part of the page you can see", "pinched in", "back gesture closes it"):
        assert words in block.group(1), f"the README section does not say {words!r}"


def test_the_enlarged_graph_covers_what_is_visible_of_a_pinched_page():
    body = (
        PAGE.split("function coverVisible(", 1)[1].split("\nfunction ", 1)[0]
        if "function coverVisible(" in PAGE
        else ""
    )
    assert body, "nothing lays the enlarged graph over the visible part of the page"
    for word in ("offsetLeft", "offsetTop", "scale"):
        assert word in body, f"coverVisible does not use the visual viewport's {word}"
    assert "coverVisible()" in PAGE.split("function openFocus(", 1)[1].split("\nfunction ", 1)[0], (
        "opening the graph does not lay it over what is visible"
    )
    assert re.search(r"visualViewport\.addEventListener\('(resize|scroll)',[^\n]*coverVisible", PAGE), (
        "a pinch while the graph is open does not move it along"
    )


def test_back_closes_the_enlarged_graph():
    assert "history.pushState(" in PAGE.split("function openFocus(", 1)[1].split("\nfunction ", 1)[0], (
        "opening the graph leaves nothing for back to undo"
    )
    assert re.search(r"addEventListener\('popstate'[^\n]*closeFocus", PAGE), "back does not close the graph"


def test_the_enlarged_graph_opens_fitted():
    block = re.search(r"## One graph on its own\n(.*?)\n## ", README, re.DOTALL)
    assert block, "README.md no longer has the section on the enlarged graph"
    assert "It opens fitted" in block.group(1), "the README does not say the graph opens fitted"
    draw = PAGE.split("function drawFocus(", 1)[1].split("\nfunction ", 1)[0]
    assert "if(!FOCUS.view) FOCUS.view={...FOCUS.base}" in draw, "the graph does not open on its fitted view"
