# ADR-ST-007: The viewer is tested in a real browser, accessibility included

## Status

Accepted, Roy Kollen Svendsen, 2026-09-27.

## Context

The viewer is one page of inline JavaScript and CSS
([`src/session_tree/index.html`](../src/session_tree/index.html)). Its tests
read that page as text and check that a mechanism is written there: that a
function exists, that a rule names a selector. None of them draws the page.

On 2026-09-27 that let a bug through. The button that opens the colour key on a
phone was in the page, and its test passed, but a style rule later in the file
hid it. It was found only by looking at a screenshot. Earlier the same day a
screenshot also found that the page's header scrolled away after one screen,
which no test could have seen.

A review of the page against the demo sessions (`scripts/demo_fixture.py`)
found fourteen problems, all by looking. Accessibility was not checked at all:
no test knows the contrast of the dim greys or whether a symbol-only button has
a name a screen reader can read.

Headless Chromium and Playwright have been used by hand throughout that work,
and the demo can be built and served by a script. The CI runs on
`ubuntu-latest`, where Playwright can install Chromium with its system
libraries. `axe-playwright-python` bundles Deque's axe-core, the common
accessibility rules engine, so no Node toolchain is needed.

## Options considered

**Keep testing the page as text, and look by hand.** Rejected. It is what let
the hidden button through, and looking by hand depends on someone remembering.

**Browser tests in the default suite.** Rejected as it stands: the mutation
check runs the whole suite once per rule, fourteen times, and a browser test
there multiplies CI time for no gain, since no rule it guards lives in the page.

**Lighthouse in CI.** Rejected. Its scores move between runs on the same page,
and a check that fails at random teaches people to ignore checks.

**Browser tests marked as such, run once per CI job, left out of the mutation
check; axe-core as one of them, against the demo.** Chosen.

## Decision

Tests that need a browser are marked `browser`. They build the demo, serve it
on a free port and drive Chromium through Playwright, at a phone's width and a
wide screen's. One of them runs axe-core on the page and fails on any finding
not listed in a baseline file; the baseline starts with what the page has today
and is emptied as those are fixed. The mutation check leaves browser tests out.
On a machine without a browser they skip, except in CI, where a missing browser
fails.

## Consequences

Playwright becomes a development dependency, and CI installs Chromium in each
job: roughly a minute more per job, and a cache to keep warm.

A browser test can fail for reasons of its own, such as timing, so they wait on
what the page shows rather than on a clock.

What gets worse: a contributor must install a browser once
(`uv run playwright install chromium`) to run the whole suite locally, and a
page change can now be refused by a rule written by someone else, axe-core's.

## Related

[ADR-ST-004](ADR-ST-004-how-a-change-is-made-here.md), `CONTRIBUTING.md`,
`.github/workflows/checks.yml`, `scripts/mutate.py`, `scripts/demo_fixture.py`.
