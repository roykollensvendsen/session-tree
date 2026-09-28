# ADR-ST-008: The viewer's design rules

## Status

Accepted, Roy Kollen Svendsen, 2026-09-28.

## Context

The viewer's one job is to say, at a glance, which session needs you and where
the work stands. Between 2026-09-26 and 2026-09-27 two reviews against the demo
sessions found that it did this badly in places. A session waiting on an answer
was greyed out and sorted by age. Red, the strongest colour, went to blocked
work that rarely needs anyone. Four things pulsed at once, and yellow meant
both a question and the keyboard's focus. States were told apart by colour
alone.

Each was fixed in its own pull request, and most fixes now have a test. But
the reasons live only in commit messages and in
[`docs/research/design-review-for-a-live-graph-dashboard.md`](../docs/research/design-review-for-a-live-graph-dashboard.md).
The next change that adds a colour, a badge or an animation has nothing to
check itself against. A test catches a specific regression, but it does not
say why the rule exists or what a new case should do.

## Options considered

**Leave the rules in the commits and the tests.** Rejected. A test says what
must not happen. It does not tell someone adding something new what to do,
and a failing test with no stated reason gets its assertion loosened.

**Write them into README.md.** Rejected as the only place. The README tells a
user what the page does; these are the constraints on changing it.

**A decision record with the rules and the check behind each.** Chosen.

## Decision

These rules govern any change to what the viewer shows:

1. **The page says who needs you first.** A session with a question comes
   first, then one that stands still, then the working ones. Neither of the
   first two is ever drawn dimmer. The first screen, at a phone's width and a
   wide screen's, must answer "which session needs you?" and "is anything
   stuck?" without scrolling. Checked by `test_state.py` (order),
   `test_attention_view.py`, and the design-review skill's glance test.
2. **Only a question looks like an alarm.** Its task is the only one filled
   with colour, and the only thing on the page that moves. Blocked, stalled and
   working are marked, but quietly. Checked by `test_palette.py` and
   `test_browser_motion.py`.
3. **Yellow means a question, and nothing else.** No focus ring, badge or mark
   uses it for anything else. Checked by `test_palette.py`, which finds the
   yellow on any line not about a question, and `test_review_view.py`.
4. **Every state has a mark besides its colour**, such as ✓ ⏳ ⏸ ⛔, a dash or a
   thick outline, and passes the colour-blind distance and contrast checks.
   Checked by `test_palette.py`.
5. **Colours come from a fixed palette**: the `STATE` table, the CSS variables
   in `:root`, and the accents listed in `tests/palette_extras.json`. A new
   colour is added to that list on purpose, where review sees it. Checked by
   `test_palette.py`.
6. **Everything clickable works from a keyboard and has a name in words.**
   Checked by `test_browser_keyboard.py` and `test_browser_screen_reader.py`.
7. **Text a person reads in a card is at least 12 px**, and numbers and labels
   at least 11 px. Checked by `test_review_view.py`.
8. **A change the user sees is tried in a browser and against the demo**, and
   every new state or view gets a demo case
   ([ADR-ST-007](ADR-ST-007-the-viewer-is-tested-in-a-browser.md),
   `test_demo_fixture.py`).

A change that needs to break one of these rules supersedes this record first.

## Consequences

A new badge, colour or animation needs a reason that fits rule 2 or 3, and
that will sometimes feel like friction. Rule 1 fixes the page's priorities, so
an idea like sorting by project would have to argue with it.

What gets worse: the page is quieter, so the state of working sessions is less
eye-catching. That is deliberate: rule 2 spends attention only on what needs
you.

## Related

[ADR-ST-007](ADR-ST-007-the-viewer-is-tested-in-a-browser.md),
[`docs/research/design-review-for-a-live-graph-dashboard.md`](../docs/research/design-review-for-a-live-graph-dashboard.md),
`.claude/skills/design-review/SKILL.md`, `.claude/skills/ship-change/SKILL.md`,
`src/session_tree/index.html`.
