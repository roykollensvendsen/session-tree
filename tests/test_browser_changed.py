"""After a break, what changed since you last looked is marked.

When the page is left, the browser keeps the state of every task. On return, a
task whose state differs, or that is new, is marked until it is tapped or the
page is left again. This fakes a stored view in which one task was in another
state and one did not exist, and checks both are marked and nothing else.
"""

import json

import pytest

pytestmark = pytest.mark.browser

SNAPSHOT = """() => { const seen={}; for(const s of LAST.sessions){ seen[s.sessionId]={};
  for(const g of s.goals||[]) for(const n of g.nodes||[]) seen[s.sessionId][n.id]=n.view; }
  return seen; }"""


def test_a_task_that_changed_while_you_were_away_is_marked(page):
    seen = page.evaluate(SNAPSHOT)
    party = next(s for s in page.evaluate("() => LAST.sessions") if s["name"] == "birthday party")
    sid = party["sessionId"]
    seen[sid]["2"] = "pending"  # the invitations were not started yet when you last looked
    del seen[sid]["5"]  # and the room task did not exist
    # set when the new page starts, after the old one has kept what it saw on leaving
    page.context.add_init_script(f"localStorage.setItem('st.seen', {json.dumps(json.dumps(seen))})")
    page.reload()
    page.wait_for_selector(".sess .node")
    card = page.locator(".sess").filter(has=page.locator(".sname", has_text="birthday party"))
    marked = sorted(card.locator(".node.changed").evaluate_all("els => els.map(e => e.dataset.id)"))
    assert marked == ["2", "5"], f"marked {marked}, not the task that changed and the new one"
    assert "2 endret" in card.locator(".shead").inner_text(), "the header does not count what changed"
    others = page.locator(".sess .node.changed").count() - 2
    assert others == 0, f"{others} tasks marked that did not change"
    card.locator('.node[data-id="2"]').focus()
    page.keyboard.press("Enter")
    page.keyboard.press("Escape")
    assert card.locator('.node[data-id="2"].changed').count() == 0, (
        "opening a changed task did not clear its mark"
    )


def test_leaving_the_page_remembers_what_you_saw(page):
    page.evaluate("() => localStorage.removeItem('st.seen')")
    page.evaluate(
        "() => { Object.defineProperty(document,'visibilityState',{value:'hidden',configurable:true});"
        " document.dispatchEvent(new Event('visibilitychange')); }"
    )
    kept = page.evaluate("() => JSON.parse(localStorage.getItem('st.seen')||'{}')")
    assert kept, "leaving the page kept nothing"
    assert kept == page.evaluate(SNAPSHOT), "what was kept is not what the page showed"
