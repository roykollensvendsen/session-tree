"""A goal can be read as a list of its tasks instead of a graph.

Chartability counts a chart with no table beside it as a critical problem: the
same information has to be there without the drawing. The switch beside a
goal's title turns its graph into a table of its tasks, with what needs you
first, and back again.
"""

import pytest

pytestmark = pytest.mark.browser

STATES = ("klar", "venter på noe", "jobber nå", "ferdig", "står stille", "blokkert", "forkastet")


def test_a_goal_turns_into_a_table_of_its_tasks_and_back(page):
    card = page.locator(".goal").filter(has_text="The neighbourhood is clean")
    tasks = card.locator(".node").count()
    toggle = card.get_by_role("button", name="vis som liste")
    toggle.click()
    rows = card.locator("table tbody tr")
    assert rows.count() == tasks, f"the list has {rows.count()} rows for {tasks} tasks"
    assert card.locator("svg").count() == 0, "the graph is still drawn beside the list"
    states = card.locator("table tbody tr td:first-child").all_inner_texts()
    assert all(any(word in s for word in STATES) for s in states), "a row does not say its state in words"
    assert "blokkert" in states[0] or "står stille" in states[0], (
        f"the list does not start with what is stuck: {states[0]}"
    )
    card.get_by_role("button", name="vis som graf").click()
    assert card.locator("svg .node").count() == tasks, "the graph did not come back"
