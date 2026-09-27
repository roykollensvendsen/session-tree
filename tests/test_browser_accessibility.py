"""The demo page passes axe-core's accessibility rules, or no worse than the baseline (ADR-ST-007).

axe-core is Deque's accessibility rules engine, run inside the page. What it
found when the check was added is kept in accessibility_baseline.json, as the
number of elements each rule flags, per screen width. A rule that is not in the
baseline, or that flags more elements than it did, fails. When a fix brings a
count down, the baseline is lowered with it, so it can only shrink.
"""

import json
import pathlib

import pytest

pytestmark = pytest.mark.browser

BASELINE = pathlib.Path(__file__).parent / "accessibility_baseline.json"


def test_the_page_has_no_new_accessibility_problems(page):
    from axe_playwright_python.sync_playwright import Axe  # noqa: PLC0415 - only this test needs it

    width = "phone" if page.viewport_size["width"] < 600 else "wide"
    found = {v["id"]: len(v["nodes"]) for v in Axe().run(page).response["violations"]}
    allowed = json.loads(BASELINE.read_text())[width] if BASELINE.exists() else {}
    worse = {rule: n for rule, n in found.items() if n > allowed.get(rule, 0)}
    assert not worse, f"on a {width}: new or more accessibility problems than the baseline allows: {worse}"
