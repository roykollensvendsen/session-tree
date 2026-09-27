---
name: design-review
description: Review how the session-tree viewer looks and reads, against the demo sessions, for what the automatic checks cannot judge — whether the page says at a glance which session needs you, whether only those states look like alarms, and whether the graphs make sense to someone who cannot see colour or the graph at all. Use when a change alters what the user sees, when asked for a design, UX or accessibility review of the viewer, or before a release. Produces a ranked list of findings, each with a picture.
---

# Design review of the viewer

The automatic checks already cover what can be measured: contrast and
colour-blind distance of every state (`tests/test_palette.py`), keyboard reach
(`tests/test_browser_keyboard.py`), reduced motion
(`tests/test_browser_motion.py`), what a screen reader hears
(`tests/test_browser_screen_reader.py`) and axe-core with WCAG 2.2
(`tests/test_browser_accessibility.py`). Do not redo them. This review is for
what needs judgement. Why each step is here, with sources, is in
[`docs/research/design-review-for-a-live-graph-dashboard.md`](../../../docs/research/design-review-for-a-live-graph-dashboard.md).

## 1. Get the pictures

<!-- not run: starts a browser and writes screenshots -->
```
python3 scripts/review_shots.py /tmp/review
```

It writes the demo at 390 and 1400 px, as it is and under Chromium's four
colour-vision simulations, plus the biggest graph opened full screen. CI keeps
the same set as the `review-shots` artefact of each run. For anything that
moves or needs a tap, serve the demo and use it (`scripts/demo-viewer`, see
`CONTRIBUTING.md`).

## 2. The three-second glance

Look at the first screen of `phone-page-none.png` and `wide-page-none.png` —
the top 900 and 1000 px, what shows before any scrolling — for three seconds
each, then look away and answer:

- Which session needs you, and for what?
- Is anything stuck?

The page exists to answer these. If the answer took longer than a glance, was
wrong, or needed scrolling, that is the first finding. (The first run found a
stalled session below the first screen this way.) Matthews and colleagues define
glanceable as understood "with low cognitive effort", and name four
principles: match expectations, use abstraction, make visuals distinct, keep
them consistent.

## 3. Situation awareness, level by level

Endsley's three levels, put as questions about this page:

1. **Perception.** Can you see every session, and the state of each task?
2. **Comprehension.** Can you tell which session needs you *without working
   it out*? Labels such as `? N`, `står stille` and `ledig` put this on screen
   directly; check they are the first thing the eye finds.
3. **Projection.** Can you tell what happens next — which waiting task frees
   up when the current one finishes?

## 4. Only what needs you looks like an alarm

From alarm-management practice (the UK HSE sheet in the research note): every
alarm should need an action from the reader, and a page where much is red or
pulsing is an alarm flood that trains people to ignore it.

- Count what is red, amber or pulsing on the wide page. Which of it needs the
  reader? Blocked is red but usually needs nothing from them.
- Does a question waiting stand out more than anything else on the page?

## 5. What Chartability asks that no test here checks

From Chartability's heuristics for visualisations (critical ones first):

- **No explanation for how to read it.** Could a newcomer read the graph from
  the page alone? Is the key reachable on a phone (ⓘ)?
- **No table.** Is the same information available without the graph (the
  popover, the screen-reader names), and is it enough?
- **Small text.** After the graph is scaled to fit, is any text under 12 px?
  Look at the phone pictures and the full-screen graph.
- **Meaningful elements can be told apart.** Look at the four simulation
  pictures side by side: does any state disappear into another?
- **Changes are not easy to follow.** When a live session redraws, can you
  keep your place? Stills cannot show this: serve the demo, keep the page
  open while a session changes (or while `scripts/demo-viewer` is restarted),
  and watch what moves. Say plainly when this was not checked.

## 6. A model may go first; a person decides

A vision model can take a first pass over the pictures with the questions
above. Published evaluations of agentic accessibility audits report high
recall and low precision (86 % and 56 % in the 2026 study cited in the
research note), so expect false findings. A person confirms every finding
before it is written down.

## 7. Write the findings

One finding per problem, ranked by how much it gets in the way of the page's
job — seeing who needs you and where the work stands. For each: the problem,
who it hits, a suggestion, its size, and the picture that shows it. Publish
the list as a report the user can scroll through, and ask which to take first.

Where a finding can be measured, propose the test that would have caught it,
so the next review does not have to find it again. Fixes go through the
`ship-change` skill.
