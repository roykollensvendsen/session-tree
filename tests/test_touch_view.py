"""On a touch screen a quick tap lights a node's arrows, and holding it opens the popover.

Same shape as test_focus_view: the handlers are inline JavaScript that needs a
browser and a finger, which no test here has. What is checked is that the
README makes the promises and that the page carries each mechanism behind
them. The behaviour itself was tried in headless Chromium with touch
emulation; see the pull request.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
README = (ROOT / "README.md").read_text()


def function(name: str) -> str:
    """The body of one top-level function in the page's script."""
    assert f"function {name}(" in PAGE, f"the page has no function {name}"
    return PAGE.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]


def test_the_readme_promises_tap_to_light_and_hold_for_details():
    block = re.search(r"## On your phone\n(.*?)\n## ", README, re.DOTALL)
    assert block, "README.md no longer has the section on the phone"
    for words in ("quick tap on a node lights its arrows", "Hold a", "✕", "scroll or a pinch does neither"):
        assert words in block.group(1), f"the README section does not say {words!r}"


def test_a_finger_does_not_open_the_popover_through_the_mouse_path():
    hover = PAGE.split("g.addEventListener('mousemove'", 1)[1].split("});", 1)[0]
    assert "if(TOUCH) return" in hover, "a tap still opens the popover through the synthesized mousemove"


def test_a_press_is_timed_and_a_move_cancels_it():
    assert re.search(r"const LONG_PRESS_MS=\d+", PAGE), "no named hold time"
    body = function("pressNode")
    assert "setTimeout(" in body, "a press is not timed"
    assert "LONG_PRESS_MS" in body, "a press is not timed by the named hold time"
    assert "PRESS_SLOP_PX" in PAGE, "no distance past which a press is a scroll"
    for event in ("'pointermove'", "'pointerup'", "'pointercancel'"):
        assert f"document.addEventListener({event}" in PAGE, f"a press does not follow {event} there"


def test_a_tap_lights_and_is_remembered_across_redraws():
    assert "TAPPED" in function("pressNode") or "TAPPED" in function("tapNode"), "a tap is not remembered"
    assert "TAPPED" in function("renderGoal"), "a redraw does not put a tapped highlight back"


def test_the_touch_popover_has_a_close_button():
    assert "tipclose" in function("showTip"), "a popover a finger opened has no close button"
    assert re.search(r"\.tip \.tipclose\{", PAGE), "the close button has no style"


def test_holding_a_node_does_not_open_the_phones_own_menu():
    assert "-webkit-touch-callout:none" in PAGE, "a long press opens the phone's own callout"
    assert "'contextmenu'" in PAGE, "a long press opens the context menu"
