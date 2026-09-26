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


def test_on_a_phone_the_questions_scroll_away_and_the_header_brings_them_back():
    assert "a **? 3** in the header brings it back" in README, "the README does not say where the list goes"
    phone = PAGE.split("@media (max-width:640px){", 1)[1].split("\n  }\n", 1)[0]
    assert "#asks{position:static" in phone, "the question list stays stuck over the page on a phone"
    header = PAGE.split("<header>", 1)[1].split("</header>", 1)[0]
    assert 'id="askcount"' in header, "the header has no count of the questions"
    render = PAGE.split("function renderAsks(", 1)[1].split("\nfunction ", 1)[0]
    assert "askcount" in render, "the count in the header is not kept up to date"


def test_the_header_stays_at_the_top_however_far_down_the_page_goes():
    assert "html,body{margin:0;height:100%}" not in PAGE, "a body one screen tall lets the header scroll away"
