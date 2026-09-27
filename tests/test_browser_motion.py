"""Nothing moves when the phone or computer asks for reduced motion.

People who get dizzy or distracted by movement turn on "reduce motion", and the
browser tells the page through prefers-reduced-motion. The page pulses a few
things to draw the eye: the task being worked on, the live dot, a waiting
question. With the setting on, none of that may run (WCAG 2.3.3).
"""

import pytest

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("width", [390, 1400], ids=["phone", "wide"])
def test_nothing_animates_with_reduced_motion(chromium, demo_url, width):
    context = chromium.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce")
    page = context.new_page()
    page.goto(demo_url)
    page.wait_for_selector(".sess .node")
    running = page.evaluate(
        "() => document.getAnimations().map(a => (a.animationName || a.constructor.name)"
        " + ' on ' + (a.effect && a.effect.target ? a.effect.target.className.baseVal"
        " ?? a.effect.target.className : '?'))"
    )
    context.close()
    assert not running, f"{len(running)} animations still run with reduced motion, e.g. {running[:4]}"


def test_only_a_task_with_a_question_moves(page):
    moving = page.evaluate(
        "() => document.getAnimations().map(a => a.effect && a.effect.target)"
        ".map(t => t ? !!t.closest('.node.asks') : false)"
    )
    assert moving, "nothing moves, not even a task with a question for you"
    assert all(moving), f"{moving.count(False)} animations run on things that do not need you"
