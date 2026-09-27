"""Findings 4 to 14 of the review of the viewer against the demo sessions.

Each test is one finding. The page is inline JavaScript and CSS no test here can
run, so what is checked is that the page carries the mechanism behind each fix;
every one was also looked at in the demo, on a phone and a wide screen.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
README = (ROOT / "README.md").read_text()
SKILL = (ROOT / "SKILL.md").read_text()


def function(name: str) -> str:
    """The body of one top-level function in the page's script."""
    assert f"function {name}(" in PAGE, f"the page has no function {name}"
    return PAGE.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]


def test_a_task_that_waits_looks_different_from_one_that_can_start():
    assert "`grey with ⏳` waiting" in SKILL, "SKILL.md does not tell ready from waiting"
    draw = PAGE.split("const drawNode=", 1)[1].split("\n  };", 1)[0]
    assert re.search(r"view==='waiting'\)[^\n]*'⏳'", draw), "a waiting task carries no ⏳"
    assert "pending:'klar'" in PAGE, "a task that can start is still called 'venter'"
    key = PAGE.split('<span class="key">', 1)[1].split("</span>\n</header>", 1)[0]
    assert "klar" in key, "the colour key has no 'klar'"
    assert "⏳" in key, "the colour key does not show ⏳"


def test_the_colour_key_can_be_opened_on_a_phone():
    assert "**ⓘ** in the header shows it" in README, "the README does not say where the key is on a phone"
    header = PAGE.split("<header>", 1)[1].split("</header>", 1)[0]
    assert 'id="keybtn"' in header, "there is no button for the key"
    phone = PAGE.split("@media (max-width:640px){", 1)[1].split("\n  }\n", 1)[0]
    assert "header.showkey .key" in phone, "the button cannot bring the key back on a phone"
    assert "header button.keybtn{display:inline-block}" in phone, "the button stays hidden on a phone"
