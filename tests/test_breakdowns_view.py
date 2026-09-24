"""A breakdown is drawn folded into its node, behind a chip that can be tapped.

Same shape as test_focus_view: the page is inline JavaScript no test here can
run, so what is checked is that the README makes the promises and that the page
carries the mechanisms behind them. The behaviour was checked in a headless
browser; see the pull request.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
README = (ROOT / "README.md").read_text()


def function(name: str) -> str:
    """The body of one top-level function in the page's script."""
    return PAGE.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]


def test_the_readme_promises_a_folded_breakdown():
    block = re.search(r"## A breakdown folded into its node\n(.*?)\n## ", README, re.DOTALL)
    assert block, "README.md has no section on folded breakdowns"
    for words in ('"parent"', "`▸ 3/5`", "`↗ 2/4`", "`↖`", "depends on one of its steps"):
        assert words in block.group(1), f"the README section does not say {words!r}"


def test_a_folded_breakdown_is_left_out_of_the_drawing():
    assert "hiddenBy(" in function("renderGoal"), "folded steps are still drawn"
    body = function("hiddenBy")
    assert "folded" in body, "what is hidden does not follow the fold"


def test_the_chip_folds_and_unfolds_and_remembers():
    body = function("toggleFold")
    assert "st.fold" in body, "the viewer's choice is not remembered"


def test_work_elsewhere_links_there_and_back():
    assert "n.remote" in function("renderGoal"), "a node does not link to the work elsewhere"
    assert "upstream" in function("renderSession"), "the work elsewhere does not link back"
