"""Everything that can be clicked can also be reached and used with the keyboard.

WCAG 2.1.1 asks that every function work from a keyboard, and 2.4.7 that the
place the keyboard is at can be seen. This tabs through the demo page and
checks both: every element that acts on a click is a stop, or holds one, and
each stop shows a focus mark while it is focused. Enter on a task lights its
arrows and opens its details, as a tap and a hold do on a phone.
"""

import pytest

pytestmark = pytest.mark.browser

CLICKABLE = """() => [...document.querySelectorAll('header *, #asks *, main *')]
  .filter(e => typeof e.onclick === 'function'
    || e.classList.contains('node') || e.classList.contains('chip'))
  .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
  .map((e, i) => { e.dataset.kb = String(i); return String(i); })"""

STOP = """() => { const e = document.activeElement; if (!e || e === document.body) return null;
  const mark = e.closest('[data-kb]'); const s = getComputedStyle(e);
  const rect = e.querySelector(':scope > rect');
  const ring = s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0
    || (rect && parseFloat(getComputedStyle(rect).strokeWidth) >= 3);
  const inside = [...document.querySelectorAll('[data-kb]')]
    .filter(c => c.contains(e)).map(c => c.dataset.kb);
  return {inside, ring, what: e.outerHTML.slice(0, 80)}; }"""


def test_every_clickable_thing_is_a_keyboard_stop_with_a_visible_focus_mark(page):
    wanted = set(page.evaluate(CLICKABLE))
    reached, no_ring = set(), []
    for _ in range(len(wanted) * 3 + 50):
        page.keyboard.press("Tab")
        stop = page.evaluate(STOP)
        if stop is None:
            continue
        reached.update(stop["inside"])
        if not stop["ring"]:
            no_ring.append(stop["what"])
    missing = page.evaluate(
        'ids => ids.map(i => document.querySelector(`[data-kb="${i}"]`).outerHTML.slice(0, 70))',
        sorted(wanted - reached),
    )
    assert not missing, f"{len(missing)} clickable things the keyboard never reaches, e.g. {missing[:3]}"
    assert not no_ring, f"{len(no_ring)} stops show no focus mark, e.g. {no_ring[:3]}"


def test_enter_on_a_task_lights_its_arrows_and_opens_its_details(page):
    node = page.locator(".sess .node").first
    node.focus()
    page.keyboard.press("Enter")
    assert page.locator(".edge.lit").count() + page.locator(".node.dim").count() > 0, "Enter lit nothing"
    assert page.locator("#tip.on").count() == 1, "Enter did not open the task's details"
    page.keyboard.press("Escape")
    assert page.locator("#tip.on").count() == 0, "Escape did not close the details"
