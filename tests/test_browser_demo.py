"""The demo sessions open in a real browser (ADR-ST-007).

The first browser test, and the ground the others stand on: the page loads,
draws every demo session and its graphs, and writes nothing to the console as
an error, on a phone and on a wide screen.
"""

import pytest

pytestmark = pytest.mark.browser


def test_every_demo_session_is_drawn(page):
    assert page.locator(".sess").count() == 7, "not every demo session is on the page"
    assert page.locator(".sess .node").count() > 100, "the graphs are not drawn"


def test_the_page_raises_no_error(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.reload()
    page.wait_for_selector(".sess .node")
    assert not errors, f"the page raised: {errors}"
