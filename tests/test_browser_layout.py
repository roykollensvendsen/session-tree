"""A wide screen shows sessions side by side without leaving a column empty.

From 1100 px the sessions sit two to a row, and one with a big graph takes the
whole row. A small session that came just before a big one used to sit alone
in its row with the other half empty. Only the very last session may leave a
half row.
"""

import pytest

pytestmark = pytest.mark.browser

HALVES = """() => { const s=[...document.querySelectorAll('.sess')];
  const W=document.getElementById('root').clientWidth;
  return s.map(e => { const r=e.getBoundingClientRect();
    return {name:e.querySelector('.sname').textContent, top:Math.round(r.top), half:r.width < W*0.6}; }); }"""


def test_no_session_sits_alone_in_half_a_row(page):
    if page.viewport_size["width"] < 1100:
        pytest.skip("one column below 1100 px")
    boxes = page.evaluate(HALVES)
    alone = [
        b["name"]
        for i, b in enumerate(boxes[:-1])
        if b["half"] and not any(o["top"] == b["top"] for j, o in enumerate(boxes) if j != i)
    ]
    assert not alone, f"sessions alone in half a row, with the other half empty: {alone}"
