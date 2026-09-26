"""A session that needs you is never dimmed.

A quiet session is drawn dimmer, so the eye goes to the busy ones. A session
waiting on your answer, or one that claims to work while nothing happens, is
quiet too, and those are the two the page most needs you to see.
"""

import pathlib

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
README = (ROOT / "README.md").read_text()


def test_the_readme_says_a_session_that_needs_you_is_not_dimmed():
    assert "never drawn\ndimmer" in README, "the README does not say a session with a question stays bright"


def test_the_page_does_not_dim_a_session_that_asks_or_stands_still():
    lines = PAGE.splitlines()
    at = next(i for i, x in enumerate(lines) if "el.className='sess'" in x)
    rule = "\n".join(lines[at - 2 : at + 1])
    assert "'asking'" in rule, "a session with a question is dimmed like any quiet one"
    assert "'stalled'" in rule, "a session that stands still is dimmed like any quiet one"
