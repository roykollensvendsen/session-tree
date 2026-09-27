"""A screen reader hears each graph, each task and its state, and every button, in words.

A screen reader reads the page's accessibility tree, not its pixels. This reads
the same tree, through Playwright's aria snapshot, and checks three things: each
graph is a named group rather than one unnamed picture; each task in it is a
button whose name holds its subject and its state in words, since the state is
otherwise only a colour and a mark (WCAG 1.1.1, 1.4.1); and no button is named
only by a symbol such as an arrow or ⊞ (WCAG 4.1.2).
"""

import re

import pytest

pytestmark = pytest.mark.browser

STATES = ("klar", "venter på noe", "jobber nå", "ferdig", "står stille", "blokkert", "forkastet")


def test_each_graph_is_a_named_group_of_tasks_with_their_states(page):
    graph = page.locator(".goal svg").first
    tree = graph.aria_snapshot()
    # the snapshot is YAML, and quotes the line when the title holds an apostrophe
    assert re.match(r"\s*-\s*['\"]?group \"", tree), f"a graph is not a named group:\n{tree[:200]}"
    tasks = re.findall(r'- button "(#\d+ [^"]*)"', tree)
    assert tasks, f"the graph's tasks are not buttons a screen reader can reach:\n{tree[:300]}"
    stateless = [t for t in tasks if not t.endswith(STATES)]
    assert not stateless, f"tasks whose name does not say their state: {stateless[:3]}"


def test_no_button_is_named_only_by_a_symbol(page):
    tree = page.locator("body").aria_snapshot()
    names = re.findall(r'- button(?: "([^"]*)")?', tree)
    wordless = sorted({n for n in names if not re.search(r"[A-Za-zÆØÅæøå]{2}", n or "")})
    assert not wordless, f"buttons a screen reader can only call by a symbol or nothing: {wordless}"
