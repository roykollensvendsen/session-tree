"""The popover stays on the screen, and the focused graph is drawn to be read.

Same shape as test_focus_view: the page is inline JavaScript no test here can
run, so what is checked is that the README makes the promises and that the page
carries the mechanisms behind them. The behaviour itself was checked in a
headless browser at a phone's size; see the pull request.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
README = (ROOT / "README.md").read_text()


def function(name: str) -> str:
    """The body of one top-level function in the page's script."""
    return PAGE.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]


def test_the_readme_promises_a_popover_wholly_on_the_screen():
    block = re.search(r"## On your phone\n(.*?)\n## ", README, re.DOTALL)
    assert block, "README.md no longer has the section on the phone"
    for words in ("wholly on the screen", "scrolls inside itself", "pinched"):
        assert words in block.group(1), f"the README section does not say {words!r}"


def test_the_popover_is_placed_inside_what_is_visible():
    body = function("showTip")
    assert "placeTip(" in body, "showTip does not place the popover through placeTip"
    assert "visualViewport" in PAGE, "a pinched page's visible part is not consulted"
    place = function("placeTip")
    assert "Math.min(" in place, "placeTip does not clamp to the visible area"
    assert "Math.max(" in place, "placeTip does not clamp to the visible area"


def test_a_popover_taller_than_the_screen_scrolls_inside_itself():
    body = function("showTip")
    assert "maxHeight" in body, "the popover's height is not capped to the screen"
    assert "maxWidth" in body, "the popover's width is not capped to the screen"
    assert re.search(r"\.tip\{[^}]*overflow:auto", PAGE), "the popover cannot scroll"


def test_the_readme_promises_a_readable_focused_graph():
    block = re.search(r"## One graph on its own\n(.*?)\n## ", README, re.DOTALL)
    assert block, "README.md no longer has the section on the focused graph"
    assert "three lines" in block.group(1)


def test_the_focused_graph_is_drawn_larger_than_the_card():
    assert "SIZE.large" in function("drawFocus"), "the focus draws at the card's size"
    assert "SIZE.card" in function("render"), "the card no longer names its own size"
    assert "wrapLines(" in function("renderGoal"), "a subject is not wrapped onto several lines"
