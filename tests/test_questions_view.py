"""A question waiting on the user is marked where it waits, and can be reached.

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


def test_the_readme_promises_a_mark_where_a_question_waits():
    block = re.search(r"## A question waiting on you\n(.*?)\n## ", README, re.DOTALL)
    assert block, "README.md has no section on questions waiting"
    for words in ("`?`", '"ask"', "needs input:", "?s=<session id>&n=<node id>"):
        assert words in block.group(1), f"the README section does not say {words!r}"


def test_a_session_asking_is_marked_apart_from_one_idle():
    body = function("renderSession")
    assert "asking" in body, "the session header does not tell asking from idle"
    assert "questions" in body, "the session header does not show its questions"


def test_a_node_with_a_question_carries_the_mark_and_the_question():
    body = function("renderGoal")
    assert "n.ask" in body, "a node's question is neither marked nor shown"


def test_the_top_of_the_page_lists_every_question_waiting():
    assert 'id="asks"' in PAGE, "there is no place at the top listing the questions"
    body = function("renderAsks")
    assert "questions" in body, "the list is not built from the sessions' questions"


def test_a_question_has_an_address_that_goes_to_it():
    body = function("goToQuestion")
    assert "openFocus(" in body, "going to a question does not open its goal"
    assert re.search(r"get\('s'\)", PAGE), "the page does not read ?s= on load"
    assert re.search(r"get\('n'\)", PAGE), "the page does not read &n= on load"


def test_a_question_in_the_list_can_be_dismissed():
    """ADR-ST-006: the button posts with the header the server insists on."""
    assert "dismiss" in function("renderAsks"), "the list offers no way to put a question away"
    body = function("dismiss")
    assert "/api/dismiss" in body, "dismissing does not reach the server"
    assert "'X-Session-Tree':'dismiss'" in body, "the dismissal lacks the page's own header"


def test_a_dismissed_question_no_longer_marks_its_node():
    body = function("renderGoal")
    assert "n.askDismissed" in body, "a dismissed question still marks its node as asking"
