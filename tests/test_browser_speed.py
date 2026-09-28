"""Drawing the page stays fast, however big a goal gets.

The page redraws every graph each time a live session changes, so a slow
drawing is felt all the time, not once. This times a full redraw of the demo,
and of a made-up goal of 300 and of 1000 tasks, against budgets five to seven
times what they took when this was written (about 20, 60 and 180 ms). That
leaves room for a slower machine, and still catches a change that makes drawing
several times slower. It does not catch every quadratic step: Chromium searched
a graph of 1000 tasks once per task within the budget.
"""

import pytest

pytestmark = pytest.mark.browser

# milliseconds for one full redraw: the demo as it is, and with one goal of n tasks
BUDGET = {"demo": 150, 300: 400, 1000: 1000}

REDRAW = """data => { const t=[];
  for(let k=0;k<5;k++){ const s=performance.now(); render(data); t.push(performance.now()-s); }
  return t.sort((a,b)=>a-b)[2]; }"""

WITH_A_GOAL_OF = """n => { const data=JSON.parse(JSON.stringify(LAST)); const s=data.sessions[0];
  const nodes=[];
  for(let i=1;i<=n;i++){ const deps=i>1&&i%5?[String(i-1)]:[];
    nodes.push({id:String(i),subject:'Step '+i+' of a long plan',status:'pending',
      view:i%7?'waiting':'pending',blockedBy:deps,blocks:[],agents:[],waitingOn:deps}); }
  const depth={}; nodes.forEach(x=>{ depth[x.id]=x.blockedBy.length?depth[x.blockedBy[0]]+1:0; });
  s.goals=[{id:'big',title:'A goal of '+n+' tasks',nodes,depth,hasEdges:true,danglingEdges:[]}];
  return data; }"""


def median_redraw(page, data_expr: str, arg=None) -> float:
    handle = page.evaluate_handle(data_expr, arg) if arg is not None else page.evaluate_handle("() => LAST")
    return page.evaluate(REDRAW, handle)


def test_the_demo_redraws_within_its_budget(page):
    took = median_redraw(page, "() => LAST")
    assert took <= BUDGET["demo"], f"a redraw of the demo took {took:.0f} ms, budget {BUDGET['demo']} ms"


@pytest.mark.parametrize("tasks", [300, 1000])
def test_a_big_goal_redraws_within_its_budget(page, tasks):
    took = median_redraw(page, WITH_A_GOAL_OF, tasks)
    assert took <= BUDGET[tasks], (
        f"a redraw with a goal of {tasks} tasks took {took:.0f} ms, budget {BUDGET[tasks]} ms"
    )
