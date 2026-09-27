"""The demo page passes axe-core's accessibility rules (ADR-ST-007).

axe-core is Deque's accessibility rules engine, run inside the page, here with
the WCAG 2.2 AA rules and axe's best practices. Any violation fails. What axe
cannot decide, mostly text inside the graphs, is counted and may not grow past
the ceiling in accessibility_baseline.json; the graph's colours are checked by
test_palette.py instead.
"""

import json
import pathlib

import pytest

pytestmark = pytest.mark.browser

BASELINE = pathlib.Path(__file__).parent / "accessibility_baseline.json"
# WCAG 2.2 AA, so target-size runs, plus axe's best practices; and the
# undecided results in full, not one example of each
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]
OPTIONS = {"runOnly": {"type": "tag", "values": TAGS}, "resultTypes": ["violations", "incomplete"]}


def test_the_page_has_no_new_accessibility_problems(page):
    from axe_playwright_python.sync_playwright import Axe  # noqa: PLC0415 - only this test needs it

    width = "phone" if page.viewport_size["width"] < 600 else "wide"
    result = Axe().run(page, options=OPTIONS).response
    found = {v["id"]: len(v["nodes"]) for v in result["violations"]}
    baseline = json.loads(BASELINE.read_text())[width] if BASELINE.exists() else {}
    allowed = baseline.get("violations", {})
    worse = {rule: n for rule, n in found.items() if n > allowed.get(rule, 0)}
    assert not worse, f"on a {width}: new or more accessibility problems than the baseline allows: {worse}"
    # what axe could not decide, such as text inside the graph: not a failure,
    # but a jump in it is worth seeing
    unsure = sum(len(v["nodes"]) for v in result["incomplete"])
    assert unsure <= baseline.get("incomplete", 0), f"on a {width}: {unsure} results axe could not decide"
