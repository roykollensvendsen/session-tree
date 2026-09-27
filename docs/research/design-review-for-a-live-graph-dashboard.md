# Design review for a live graph dashboard

*Research note, 2026-09-27. The question: what does a thorough, current design
review of a live, graph-based monitoring page check, and which parts of it can
be automated in this repository?*

The page in question is session-tree's viewer: one HTML file with inline
JavaScript and CSS ([`src/session_tree/index.html`](../../src/session_tree/index.html)).
It draws each coding-agent session as an SVG task graph on a dark background.
It is read on a desktop and on a phone. A task's state is shown by colour:
blue while worked (with a pulsing outline), green when done, amber when
stalled, red when blocked, grey when ready, grey with ⏳ when waiting, and a
dashed, struck-through grey when abandoned.

What already runs ([ADR-ST-007](../../decisions/ADR-ST-007-the-viewer-is-tested-in-a-browser.md)):
Playwright for Python drives Chromium against generated demo sessions
([`scripts/demo_fixture.py`](../../scripts/demo_fixture.py)) at 390 px and
1400 px wide. One test runs axe-core through `axe-playwright-python` and fails
on anything worse than a per-rule baseline
([`tests/accessibility_baseline.json`](../../tests/accessibility_baseline.json)).

Every claim below links to the source that owns it. Where a number comes from
running something against this repository rather than from a source, the text
says so. Those measurements were made on 2026-09-27 against the demo, with
Playwright 1.63.0, axe-playwright-python 0.1.8 (which bundles axe-core 4.12.1)
and the system Chromium.

## 1. Accessibility of the graph itself

### Chartability

Chartability is "a set of heuristics (testable questions) for ensuring that
data visualizations, systems, and interfaces are accessible". Frank Elavsky
made it; it is licensed CC-BY-SA
([chartability.fizz.studio](https://chartability.fizz.studio/)). The
peer-reviewed description is Elavsky, Bennett and Moritz, "How accessible is my
visualization? Evaluating visualization accessibility with Chartability",
EuroVis 2022, *Computer Graphics Forum* 41(3)
([author PDF](https://www.domoritz.de/papers/2022-Chartability.pdf),
[Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.14522)).

It extends WCAG's four principles (Perceivable, Operable, Understandable,
Robust) with three of its own: Compromising, Assistive and Flexible. The site
counts 50 heuristics and offers a quick audit of 14 tests
([chartability.fizz.studio](https://chartability.fizz.studio/)). The full list,
with the critical ones marked, is in the workbook
([POUR-CAF workbook](https://chartability.github.io/POUR-CAF/)).

The heuristics that bite on this viewer, quoted from the workbook:

- **Low contrast** (critical): "Geometries and large text must have >3:1
  contrast against background, Regular text must have >4.5:1."
- **Content is only visual** (critical): information must be available
  without the visuals.
- **Small text size** (critical): "Text (any) must not be smaller than
  9pt/12px in size." The node id text here is 9 px and task labels 10.5 px
  (CSS in `index.html`, `.node .id` and `.node text`), before the SVG is
  scaled.
- **Color is used alone to communicate meaning**, **Not CVD-friendly**, and
  **Meaningful elements can be distinguished from each other**.
- **Interaction modality only has one input type** (critical): if the chart
  works with a mouse it must also work with a keyboard.
- **Keyboard focus indicator missing, obscured, or low contrast.**
- **Target pointer interaction size is too small.**
- **No explanation for purpose or for how to read** (critical).
- **No table** (critical): a human-readable version of the data must exist.
- **Changes are not easy to follow**, and **Long animations cannot be
  controlled**.

Chartability is a checklist for a person, not a tool. Several items (contrast,
colour distance, keyboard reach, animation control) can be turned into tests;
the rest stay a review step.

### WCAG 2.2 criteria that matter here

Quoted from [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and its Understanding
documents.

- **1.4.3 Contrast (Minimum), AA** ([#contrast-minimum](https://www.w3.org/TR/WCAG22/#contrast-minimum)):
  text at least 4.5:1, large text 3:1. The 1.4.11 Understanding page says text
  inside a graphic must meet 1.4.3 on its own
  ([Understanding 1.4.11, #required-for-understanding](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html#required-for-understanding)).
  So the task labels and ids inside the SVG are covered.
- **1.4.11 Non-text Contrast, AA** ([#non-text-contrast](https://www.w3.org/TR/WCAG22/#non-text-contrast)):
  3:1 against adjacent colours for UI components and for "parts of graphics
  required to understand the content". The Understanding page names "each line
  in a graph" as a graphical object, and says a colour change between states
  need not meet 3:1 when the states do not appear next to each other
  ([Understanding 1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html#graphical-objects)).
  A node's outline is what tells its state, so it counts.
- **1.4.1 Use of Color, A** ([Understanding 1.4.1](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)):
  colour must not be the only visual means. Colours that also differ clearly
  in lightness count as an extra distinction; the page gives 3:1 as the
  measure of "significant".
- **2.5.8 Target Size (Minimum), AA** ([Understanding 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)):
  24 × 24 CSS px, with Spacing, Equivalent, Inline, User agent control and
  Essential exceptions. The page treats pins on a map as Essential, because
  their position carries the meaning. Graph nodes are arguably the same case.
- **2.2.2 Pause, Stop, Hide, A** ([Understanding 2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html)):
  anything moving or blinking that starts by itself, lasts more than five
  seconds and sits beside other content needs a way to pause, stop or hide it.
  "Blinking" is switching between two states "in a way that is meant to draw
  attention". The Understanding page does not say that honouring
  `prefers-reduced-motion` is enough.
- **2.3.3 Animation from Interactions, AAA** ([#animation-from-interactions](https://www.w3.org/TR/WCAG22/#animation-from-interactions)):
  covers motion *triggered by interaction*. Technique C39
  (`prefers-reduced-motion`) is listed as sufficient for 2.3.3, not for 2.2.2
  ([C39](https://www.w3.org/WAI/WCAG22/Techniques/css/C39)). The pulsing here
  is not triggered by interaction, so 2.2.2 is the criterion that applies.
- **1.4.10 Reflow, AA** ([Understanding 1.4.10](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)):
  no two-dimensional scrolling at 320 CSS px, which equals 1280 px at 400 %
  zoom. Diagrams are named as content that needs two-dimensional layout and is
  excepted. The graph is excepted; the page around it is not.
- **2.4.7 Focus Visible, AA**, and **2.4.11 Focus Not Obscured (Minimum), AA**
  ([#focus-visible](https://www.w3.org/TR/WCAG22/#focus-visible),
  [#focus-not-obscured-minimum](https://www.w3.org/TR/WCAG22/#focus-not-obscured-minimum)).
  The page has sticky headers, which is the usual way focus gets obscured.
- **4.1.3 Status Messages, AA** ([#status-messages](https://www.w3.org/TR/WCAG22/#status-messages)):
  a live page that changes state should expose status changes to assistive
  technology without moving focus.

The contrast ratio is (L1 + 0.05) / (L2 + 0.05), with L the relative luminance
of the lighter and darker colour, as WCAG defines it
([WCAG 2.2, definitions](https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio)).

### What axe-core checks, and what it does not

From axe-core's rule list
([rule-descriptions.md](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)):

- `color-contrast` (wcag2aa, 1.4.3) is on by default.
- `target-size` (wcag22aa, 2.5.8) is **off by default**
  ([`lib/rules/target-size.json`](https://github.com/dequelabs/axe-core/blob/develop/lib/rules/target-size.json)
  has `"enabled": false`). It only looks at widgets
  (`widget-not-inline-matches`), so an SVG `<g>` with a click handler is
  outside it.
- `region` is a best-practice rule, not a WCAG criterion.
- There is no rule for 1.4.11 or 1.4.1 in general. The one colour-alone rule,
  `link-in-text-block`, is about links in text.

axe-core reads the text colour from CSS `color` (or
`-webkit-text-fill-color`), not from SVG `fill`
([`get-foreground-color.js`](https://github.com/dequelabs/axe-core/blob/develop/lib/commons/color/get-foreground-color.js)).
It treats an `<svg>` element behind text as an image, which leaves the
background unknown
([`element-has-image.js`](https://github.com/dequelabs/axe-core/blob/develop/lib/commons/color/element-has-image.js)).
Such cases are reported as **incomplete** ("needs review"), not as violations.

What that means here, measured on the demo at 1400 px: running
`color-contrast` on the SVGs alone gave 0 violations, 0 passes and **253
incomplete** results (reasons: `bgOverlap` 111, `imgNode` 110, `nonBmp` 32).
On the whole page, with `incomplete` among the requested `resultTypes`, the
rule reports 278 incomplete results at 390 px and 282 at 1400 px. With
`axe-playwright-python`'s default options, `resultTypes: ["violations"]`,
axe lists only one example node per other result type, which can make the
unchecked text look like a single case. The repository's test reads only `violations`, so the contrast of every label
inside the graph is at present unchecked. The 18 and 20 contrast failures in
the baseline are all HTML text outside the graph.

Computing it by hand from the colours in `index.html` (script method as in
section 2) gives these ratios against the node's own fill:

| State | Outline vs node fill | Outline vs card | `--faint` id text (#5b6678) vs fill |
|---|---|---|---|
| ready / waiting | 1.95 | 2.15 | 2.53 |
| working | 3.38 | 4.40 | 2.14 |
| done (outline at 45 % opacity) | 2.29 | 2.93 | 2.18 |
| stalled | 6.53 | 8.43 | 2.16 |
| blocked | 3.75 | 4.30 | 2.43 |
| abandoned | 1.43 | 1.58 | 2.53 |

So three outlines are below the 3:1 of 1.4.11, and the 9 px id text is below
4.5:1 on every state. The task label text (`--ink`, #e6edf6) is 10.5:1 or
better everywhere. These are hand computations on declared colours, not a
measurement of rendered pixels.

`target-size`, run on its own, passed 21 targets at 1400 px and 23 at 390 px,
with no violations. That covers the buttons only.

Automation has a known ceiling. Playwright's own guide says: "Automated
accessibility tests can detect some common accessibility problems such as
missing or invalid properties. But many accessibility problems can only be
discovered through manual testing"
([Playwright, accessibility testing](https://playwright.dev/docs/accessibility-testing)).
W3C says tools "can not *determine* accessibility, they can only *assist*"
([WAI, selecting tools](https://www.w3.org/WAI/test-evaluate/tools/selecting/)).
Deque reports that its automated rules found 57.38 % of issues by volume in
13,000+ audited pages
([Deque coverage report](https://www.deque.com/automated-accessibility-coverage-report/)).
That is the vendor measuring its own tool, on first-time audits of ordinary
pages, not SVG graphs.

## 2. Colour-vision deficiency

### What Chromium can simulate

The DevTools Protocol method `Emulation.setEmulatedVisionDeficiency` takes one
`type`: `none`, `blurredVision`, `reducedContrast`, `achromatopsia`,
`deuteranopia`, `protanopia` or `tritanopia`. The protocol definition says
best-effort emulations come first, then "physiologically accurate emulations
for medically recognized color vision deficiencies". It is not marked
experimental
([Emulation.pdl](https://github.com/ChromeDevTools/devtools-protocol/blob/master/pdl/domains/Emulation.pdl),
[protocol viewer](https://chromedevtools.github.io/devtools-protocol/tot/Emulation/#method-setEmulatedVisionDeficiency)).

Chromium implements it as an SVG `feColorMatrix` filter over the page. The
matrices come from Machado, Oliveira and Fernandes, "A Physiologically-based
Model for Simulation of Color Vision Deficiency", IEEE TVCG 15(6), 2009; the
achromatopsia matrix follows Nguyen and Brown, CVPR 2017
([`vision_deficiency.cc`](https://github.com/chromium/chromium/blob/main/third_party/blink/renderer/core/css/vision_deficiency.cc),
[Machado et al., project page](https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html)).
A filter primitive works in linear RGB unless told otherwise, because
`color-interpolation-filters` starts as `linearRGB`
([Filter Effects 1](https://www.w3.org/TR/filter-effects-1/#propdef-color-interpolation-filters)).
Only full dichromacy and achromatopsia are offered. The milder anomalous forms
are not.

Because the matrices are fixed and public, the same simulation can be run on
the palette in plain Python, with no browser. The browser route checks what is
actually drawn (alpha blending, opacity, filters); the Python route checks the
palette in milliseconds.

### Calling it from Playwright for Python

A CDP session comes from `page.context.new_cdp_session(page)`, and `send`
takes the method name and a parameter dict
([Playwright Python, CDPSession](https://playwright.dev/python/docs/api/class-cdpsession)).
CDP is a Chromium protocol, so this works only there. Puppeteer's
`page.emulateVisionDeficiency` wraps the same method and its documented
example takes screenshots after emulating
([Puppeteer docs](https://pptr.dev/api/puppeteer.page.emulatevisiondeficiency)).
Run against the demo here, the five settings gave five different screenshot
hashes, so the emulation does reach headless screenshots.

<!-- not run: a code sample for a future test, not a command -->
```python
cdp = page.context.new_cdp_session(page)
for kind in ("protanopia", "deuteranopia", "tritanopia", "achromatopsia"):
    cdp.send("Emulation.setEmulatedVisionDeficiency", {"type": kind})
    page.screenshot(path=f"cvd-{kind}.png", animations="disabled")
cdp.send("Emulation.setEmulatedVisionDeficiency", {"type": "none"})
```

### Turning it into a test

A sound test asks two questions for every pair of states that can sit side by
side:

1. **Are they still different colours after simulation?** Use a colour
   difference in a perceptual space. CSS Color 4 gives ΔEOK as the Euclidean
   distance in Oklab and says one just-noticeable difference (JND) is 0.02 in
   ΔEOK, or 2 in ΔE2000
   ([CSS Color 4, #color-difference-OK](https://www.w3.org/TR/css-color-4/#color-difference-OK),
   [gamut mapping, JND](https://www.w3.org/TR/css-color-4/#GMA-Binary-local-MINDE)).
   It also gives validated sample code for ΔE2000
   ([#color-difference-2000](https://www.w3.org/TR/css-color-4/#color-difference-2000))
   and for the Oklab conversion
   ([#color-conversion-code](https://www.w3.org/TR/css-color-4/#color-conversion-code)).
2. **Do they differ in more than hue?** Use the WCAG contrast ratio between
   the two state colours. 1.4.1 counts a lightness difference as a second cue
   ([Understanding 1.4.1](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)).
   Or check that the pair has another cue: a glyph (✓, ⏳), a dash pattern, a
   stroke width, motion.

A JND is the point where two colours can just be told apart side by side. A
glance at a small outline needs far more. No source found sets a threshold for
"distinct at a glance", so any number chosen (say 5 JND) is a judgement. That
is stated again under what this does not settle.

What the palette gives today, computed here by applying Chromium's matrices in
linear RGB to the colours in `index.html` (full-opacity legend swatches):

| Simulation | Closest pair | ΔEOK (JNDs) | Luminance ratio |
|---|---|---|---|
| none | ready ~ abandoned | 0.073 (3.7) | 1.36 |
| protanopia | done ~ stalled | 0.042 (2.1) | 1.00 |
| deuteranopia | done ~ blocked | 0.074 (3.7) | 1.31 |
| tritanopia | working ~ done | 0.107 (5.4) | 1.42 |
| achromatopsia | working ~ blocked | 0.005 (0.3) | 1.02 |

On the node outlines as drawn (done at 45 % opacity over its fill), protanopia
makes done and blocked nearly identical: ΔEOK 0.004, luminance ratio 1.02.
Done carries a ✓ and working pulses, so those pairs keep a second cue.
Blocked and stalled carry none: they differ from the rest by hue alone. Under
protanopia the screenshot legend shows "ferdig" and "står stille" as two
near-identical olive swatches.

## 3. Visual regression with screenshots

**Playwright Test (JavaScript)** has `expect(page).toHaveScreenshot()`. The
first run writes the baseline; later runs compare with pixelmatch
([Playwright, visual comparisons](https://playwright.dev/docs/test-snapshots)).
The options that make it stable
([toHaveScreenshot options](https://playwright.dev/docs/api/class-pageassertions#page-assertions-to-have-screenshot-1)):

- `animations: "disabled"` is the default. Finite animations are
  fast-forwarded; "infinite animations are canceled to initial state, and then
  played over after the screenshot."
- `caret: "hide"` is the default.
- `mask` covers given locators with a box of `maskColor` (default #FF00FF).
- `stylePath` injects a stylesheet to hide volatile parts.
- `threshold` (default 0.2, in YIQ space), `maxDiffPixels` and
  `maxDiffPixelRatio` set the tolerance.
- The assertion retakes screenshots until two in a row match, then compares.
- Baselines are named per browser and platform, and are updated with
  `--update-snapshots`.

The same page warns: "browser rendering can vary based on the host OS,
version, settings, hardware, power source (battery vs. power adapter),
headless mode, and other factors." Baselines only hold on the environment
they were made on.

**Playwright for Python** has no screenshot assertion. Its `PageAssertions`
offers title, URL and aria-snapshot checks only
([Python PageAssertions](https://playwright.dev/python/docs/api/class-pageassertions)).
The request was closed in 2023 and folded into issue #837, where a maintainer
wrote "We can't commit on any eta"
([playwright-python #1833](https://github.com/microsoft/playwright-python/issues/1833),
[#837](https://github.com/microsoft/playwright-python/issues/837)).
`page.screenshot` does take the same stabilising arguments: `animations`,
`caret`, `mask`, `mask_color`, `style`, `scale`
([Python Page.screenshot](https://playwright.dev/python/docs/api/class-page#page-screenshot)).
Time can be frozen with `page.clock`
([Python clock](https://playwright.dev/python/docs/clock)).

Third-party plugins, checked on PyPI and GitHub on 2026-09-27:

| Package | Last release | Repository activity | Note |
|---|---|---|---|
| [pytest-playwright-visual-snapshot](https://pypi.org/project/pytest-playwright-visual-snapshot/) | 0.5.1, 2026-02-05 | pushed 2026-09-26, 13 stars | Needs `pytest-playwright`, Pillow, pixelmatch. Masks, fails after `--update-snapshots` so images get reviewed. Its README calls the older plugins "long dead" ([repo](https://github.com/iloveitaly/pytest-playwright-visual-snapshot)). |
| [pytest-playwright-visual](https://pypi.org/project/pytest-playwright-visual/) | 2.1.2, 2022-04-28 | pushed 2025-04 | No release for four years. |
| [pytest-playwright-snapshot](https://pypi.org/project/pytest-playwright-snapshot/) | 1.0, 2021-08-19 | pushed 2022-05 | Unmaintained. |
| [pytest-image-snapshot](https://pypi.org/project/pytest-image-snapshot/) | 0.5.3, 2026-06-02 | pushed 2026-06 | Generic image comparison, not tied to Playwright. |

The live plugin depends on `pytest-playwright`'s `page` fixture. This
repository has its own `page` fixture in `tests/conftest.py`, so adopting the
plugin means reconciling the two, or writing the comparison by hand with
Pillow (about as long as the axe test).

Two things in this viewer make screenshots unstable, found by reading the code:

- The font is the system stack (`ui-sans-serif, -apple-system, "Segoe UI",
  Roboto, sans-serif`). It resolves to different fonts on an Arch desktop and
  on `ubuntu-latest`. Baselines would have to be made in CI, or in a pinned
  container.
- The demo stamps its events relative to `time.time()`, and the page shows
  relative times ("9 min siden"). Those need a frozen clock or a mask.

## 4. What a monitoring page is for

### Situation awareness (Endsley)

Mica Endsley defines situation awareness as "the perception of the elements in
the environment within a volume of time and space, the comprehension of their
meaning, and the projection of their status in the near future". The three
parts are Level 1 (perception), Level 2 (comprehension) and Level 3
(projection). Source: Endsley, "Toward a Theory of Situation Awareness in
Dynamic Systems", *Human Factors* 37(1), 32–64, 1995
([SAGE, doi:10.1518/001872095779049543](https://journals.sagepub.com/doi/10.1518/001872095779049543)).
The full text is closed access and could not be opened for this note; the
definition is the one quoted consistently in the literature.

Her design guidance is in the book *Designing for Situation Awareness: An
Approach to User-Centered Design*, by Endsley and Jones. The third edition
(CRC Press, 2025) advertises "60 detailed design principles", grouped around
supporting SA processes, information certainty, complexity and alarms,
automation and AI, and team SA
([Routledge](https://www.routledge.com/Designing-for-Situation-Awareness-An-Approach-to-User-Centered-Design-Third-Edition/Endsley-Jones/p/book/9781032482118)).
Principles often attributed to the book include "organize information around
goals", "present Level 2 information directly", "provide assistance for Level
3 projections" and "support global SA". **These names could not be checked
against the book text** and should be read as unconfirmed.

For this viewer the three levels translate plainly:

- Level 1: can the reader see which sessions exist and what state each task is
  in?
- Level 2: can the reader tell, without working it out, which session needs
  them now? The page's labels ("? N", "står stille", "ledig") are Level 2 put
  on screen directly, which is the right direction.
- Level 3: can the reader tell what happens next, for example which blocked
  task frees up when the current one finishes?

### Glanceability

Matthews, Forlizzi and Rohrbach define glanceable as "enabling users to
understand information with low cognitive effort", and keep it apart from
attention capture, which is done by "abrupt onset, flashing, bouncing, and
other motion". Their four principles: match user expectations, use
abstraction, make visuals distinct, and maintain consistency. On distinctness
a designer they interviewed put it as "elements have to be able to be
distinguished in an instant"
([UCB/EECS-2006-113](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2006/Archive/EECS-2006-113.pdf)).

For this viewer: the colour distances in section 2 measure "make visuals
distinct". The pulsing outline is attention capture, not glanceability, and
should be spent on the thing that needs the reader.

### Alarm design

The alarm standards themselves are paid documents. ANSI/ISA-18.2-2016 covers
the lifecycle of alarm systems in the process industries
([ISA product page](https://www.isa.org/products/ansi-isa-18-2-2016-management-of-alarm-systems-for)).
EEMUA 191 is in its 4th edition (November 2024); its free contents list has
sections on alarm priority markers, display filtering, avoiding alarm floods,
shelving and standing alarms
([EEMUA 191 contents, PDF](https://www.eemua.org/getattachment/9d3f8071-55c3-49bf-a74a-3bf6ad4a2e0f/Contents-EEMUA-Publication-191-Edition4-November-2024.pdf)).
Neither text could be read for this note.

The UK Health and Safety Executive's free sheet summarises the practice
([HSE, *Better alarm handling*, Chemicals Sheet No 6](https://www.hse.gov.uk/pubns/chis6.pdf)).
It came from the 1994 Milford Haven explosion, where two operators had to
handle 275 alarms in the last 11 minutes. It says:

- Every alarm should require operator action; "process status indicators
  should not be designated as alarms."
- Rate targets, citing EEMUA: in normal operation no more than one alarm every
  ten minutes on average, and no more than ten in the first ten minutes after
  a major upset.
- Use about three priorities, set by the consequence of not responding, in
  proportion roughly 5 % high, 15 % medium, 80 % low.
- Reduce standing alarms, and have a defined response to each alarm.

Those numbers are for plant operators, not for someone watching coding agents.
What carries over is the shape:

- Only "needs you" states should look like an alarm. Here that is a question
  waiting (? N) and, arguably, stalled. Blocked, working and done are status.
  Today blocked is red, the strongest alarm colour, though it usually needs
  nothing from the reader.
- Keep the alarming set small, so it keeps its meaning. A page where half the
  nodes are red or pulsing is an alarm flood.
- A long-standing alarm that nobody acts on trains people to ignore the
  colour. The "avvis" (dismiss) button for questions is the shelving mechanism
  of this page.

## 5. Keyboard and screen readers

### What can be automated

- **Keyboard traversal.** Playwright can press Tab and read
  `document.activeElement` after each press. Whether focus is shown can be
  read from the `:focus-visible` pseudo-class, which matches when "the UA has
  determined that a focus ring or other indicator should be drawn"
  ([Selectors 4](https://www.w3.org/TR/selectors-4/#the-focus-visible-pseudo)).
  Measured on the demo at 1400 px: 21 tab stops, all buttons, links and one
  `<summary>`, all matching `:focus-visible` with the browser's default ring.
  The 7 goal titles (which open the full-screen graph on click), the session
  headers (which collapse on click) and the 104 task nodes (details on hover
  or press) are never reached by the keyboard. axe-core cannot see this,
  because it does not know which elements have click handlers.
- **Accessible names and roles.** Playwright's aria snapshots give "a YAML
  representation of the accessibility tree", with roles, names and states
  such as pressed and expanded. `expect(locator).to_match_aria_snapshot()`
  compares against a template, allowing partial matches and regular
  expressions ([Python aria snapshots](https://playwright.dev/python/docs/aria-snapshots)).
  They arrived in Playwright 1.49; `/children` and `/url` in 1.52
  ([release notes](https://playwright.dev/python/docs/release-notes)).
  On the demo, each goal's graph is one `img` whose name is all its labels run
  together, for example
  `img: "gjort ↑ · gjenstår ↓ #1 The menu is chosen … #3 The food is cooked ⏳"`.
  No state word is in it, so a screen reader hears the tasks but not which is
  done or blocked. The pager buttons are named by their glyphs "‹" and "›".
- **Motion preferences.** `page.emulate_media(reduced_motion="reduce")` sets
  the media feature ([Python Page.emulate_media](https://playwright.dev/python/docs/api/class-page#page-emulate-media)),
  and `document.getAnimations()` lists what still runs. Measured: normally 6
  animations run (`outline` ×3, `pulse`, `beat`, `nudge`). With reduced motion
  2 remain: `beat` (the "live" dot) and `nudge` (the stalled badge and the
  replay "behind" button). The CSS only stops `.pulsing`.

### What must stay manual

The aria snapshot is Chromium's accessibility tree. It is not what NVDA,
VoiceOver or TalkBack say. The ARIA Authoring Practices Guide states "Testing
assistive technology interoperability is essential before using code from
this guide in production"
([APG, Read Me First](https://www.w3.org/WAI/ARIA/apg/practices/read-me-first/)).
The W3C ARIA-AT project publishes measured support per screen reader and
browser, because support differs
([APG, AT support tables](https://www.w3.org/WAI/ARIA/apg/about/at-support-tables/),
[w3c/aria-at](https://github.com/w3c/aria-at)). A protocol to drive screen
readers remotely, AT Driver, is still a draft
([w3c/at-driver](https://github.com/w3c/at-driver)).

Guidepup automates VoiceOver on macOS and NVDA on Windows
([guidepup](https://github.com/guidepup/guidepup)), with a Playwright
integration ([guidepup-playwright](https://github.com/guidepup/guidepup-playwright)).
It is JavaScript, needs macOS or Windows runners, and does not cover TalkBack.
It does not fit this repository's Python, Linux CI.

So a person has to listen to the page, at least with TalkBack on the phone the
viewer is actually used on.

## 6. LLM-assisted design review in 2026

There are tools and papers. The evidence that they work is thin and mixed.

- **Duan et al., CHI 2024.** GPT-4 in a Figma plugin checked mockups against
  written heuristics. Its input was a JSON description of the layers, not a
  screenshot. Three designers rated its suggestions on 51 UIs: 52 % accurate,
  19 % partly accurate, 29 % not accurate; 49 % helpful or very helpful. The
  raters agreed only slightly with each other (Fleiss' κ 0.112 for accuracy).
  Against 12 experts on 12 UIs, GPT-4 found 38 helpful violations, 9 of them
  missed by the experts, while the experts found 62 that GPT-4 missed. A
  single human had higher precision; GPT-4 slightly higher recall and slightly
  lower F1 ([paper, §5](https://people.eecs.berkeley.edu/~bjoern/papers/duan-heuristic-chi2024.pdf),
  [arXiv:2403.13139](https://arxiv.org/abs/2403.13139)).
- **UICrit, UIST 2024.** The same group states that "current LLM-based
  techniques do not yet match the performance of human evaluators", and
  reports a 55 % gain from few-shot and visual prompting with a dataset of
  3,059 critiques of 983 mobile UIs
  ([arXiv:2407.08850](https://arxiv.org/abs/2407.08850)).
- **Agentic WCAG auditing, preprint, September 2026.** One vision-language
  agent per WCAG criterion, operating the page. On 250 page-criterion records
  from expert audits of 11 sites, agents recovered 67 of 78 known failures
  (86 % recall) against 36 % for axe-core and 67 % for a non-interactive model.
  The abstract's precision figure, "at lower precision (56%)", is ambiguous
  about which system it belongs to. Agents found nine of ten keyboard cases
  both baselines missed ([arXiv:2609.09379](https://arxiv.org/abs/2609.09379)).
  Not peer reviewed; small dataset.
- **Systematic review, May 2026.** 38 peer-reviewed studies of LLMs for web
  accessibility. Evaluation practices "vary widely and often lack direct
  involvement of users with disabilities"; the work is mostly text-centric
  ([arXiv:2605.13873](https://arxiv.org/abs/2605.13873)).
- **LLM personas judging visualisations, June 2026.** Recommends using them
  for "early-stage design exploration and rapid comparative screening rather
  than summative evaluation" ([arXiv:2606.10095](https://arxiv.org/abs/2606.10095)).
- **Vendors.** Deque says its AI-run guided tests are "up to 4x faster than a
  standard IGT (and up to 60x faster than a manual test)"
  ([Deque blog, 2026-01-15](https://www.deque.com/blog/make-accessibility-testing-up-to-4x-faster-with-deques-new-ai-powered-features/)).
  No method or independent study is given. Treat it as a claim.

The reading: an LLM looking at screenshots is a useful second reader. It
catches things nobody wrote a rule for, and misses and invents things at rates
around one in two. It should produce findings for a person to confirm, never a
pass or a fail.

## What to adopt here, in order

Most value for least cost first. "Fails today" means the check would fail on
the current page; like the axe test, it would start from a baseline that can
only shrink.

1. **A palette test, in plain Python.** Read the state colours from
   `index.html` (the `COLOR` table and the fills). For each pair, apply
   Chromium's four matrices in linear RGB and compute ΔEOK and the luminance
   ratio. Require a minimum distance, unless the pair has a listed non-colour
   cue (✓, ⏳, dash, pulse). Also require 3:1 between each outline and its
   fill, and 4.5:1 for SVG text on each fill. *Catches:* done ~ stalled under
   protanopia, working ~ blocked under achromatopsia, ready ~ abandoned
   always, the 9 px id text at about 2.2:1, and any future colour edit that
   breaks these. *Costs:* about 60 lines, no dependency, milliseconds; not a
   browser test, so it can sit in the mutation check. Not flaky. *Kind:* CI
   check. Fails today.
2. **A keyboard test.** Tab through the page and require every element that
   acts on click to be reached, and every stop to match `:focus-visible` with
   a visible outline and to be inside the viewport (2.4.11). *Catches:* goal
   titles, session headers and nodes being mouse-only. *Costs:* one browser
   test on the existing fixture, a second or two. Low flakiness if it waits
   on the page. *Kind:* CI check. Fails today.
3. **A motion test.** With `reduced_motion="reduce"`,
   `document.getAnimations()` must be empty. Separately, decide whether the
   page needs a pause control for 2.2.2. *Catches:* `beat` and `nudge` still
   running. *Costs:* a few lines, one browser test. *Kind:* CI check. Fails
   today.
4. **Make the axe test see more.** Run with WCAG 2.2 AA tags so `target-size`
   is on, and record the count of `incomplete` results in the baseline, so a
   jump in "needs review" is at least seen. *Catches:* small buttons, and
   growth in unchecked contrast. *Costs:* a few lines, no new dependency.
   *Kind:* CI check.
5. **An aria-snapshot test of the graph.** Assert, with a partial
   `to_match_aria_snapshot` or a regex, that each graph's accessible name
   includes each task's state in words, and that icon buttons have word names.
   *Catches:* state conveyed only visually to screen-reader users (1.4.1,
   Chartability "content is only visual"). *Costs:* one browser test; snapshot
   text changes with the demo, so keep it partial. *Kind:* CI check. Fails
   today.
6. **Simulated-vision screenshots as artefacts.** Take the four CDP
   simulations at both widths and upload them from CI, or save them locally.
   Nothing asserts on them. *Catches:* what the palette test cannot, such as a
   whole view that reads as one grey mass. *Costs:* a few seconds per run and
   some storage. *Kind:* CI artefact feeding a skill checklist.
7. **A design-review checklist in a skill.** The Chartability critical
   heuristics, the three SA questions from section 4, the "only needs-you
   states look like alarms" rule, and a 3-second glance test: from a
   screenshot, name the session that needs you. An LLM can do a first pass on
   the screenshots from item 6; a person confirms each finding. *Catches:*
   meaning and priority problems no rule can state. *Costs:* writing the
   checklist once; minutes per UI change. *Kind:* skill checklist.
8. **Screenshot regression.** Only after the page settles. It needs frozen
   time (`page.clock`), masks for relative labels, baselines made on the CI
   image, and either `pytest-playwright-visual-snapshot` (which brings
   `pytest-playwright` and a clash with the existing `page` fixture) or a
   hand-written Pillow comparison. *Catches:* layout regressions like the
   hidden colour-key button that started ADR-ST-007. *Costs:* medium; the
   most flaky item here, and every intended change means reviewing new
   images. *Kind:* CI check.
9. **A manual screen-reader pass.** TalkBack on the phone first, then
   VoiceOver or NVDA, when a change touches structure, names or live updates.
   *Catches:* how the page actually sounds, including announcements of live
   changes (4.1.3). *Costs:* a person's half hour. *Kind:* manual step.

Left out on purpose: Lighthouse (rejected in ADR-ST-007 for unstable scores),
and Guidepup (JavaScript, no Linux, no TalkBack).

## What this does not settle

- **How far apart is "distinct at a glance".** CSS Color 4 fixes one JND, not
  a threshold for recognising a state in a small outline. The number in item 1
  is a choice, and should be set by looking at the simulated screenshots.
- **How good the simulations are.** Chromium offers only full dichromacy and
  achromatopsia. The milder, more common anomalous forms are not simulated,
  and whether passing the dichromat case implies passing them is not
  established here.
- **Whether the pulsing outline is "blinking" under 2.2.2**, and whether an OS
  reduced-motion setting counts as the "mechanism" 2.2.2 asks for. The
  Understanding document does not say.
- **Whether graph nodes fall under the Essential exception of 2.5.8.** The map
  pin example suggests so; no source says so for graphs.
- **Endsley's design principles** as worded in the book, which could not be
  read. The ISA-18.2 and EEMUA 191 texts were not read either; the rate
  numbers above come from HSE's summary of EEMUA's 1999 edition.
- **Whether alarm-management numbers transfer** from process plants to
  someone watching agent sessions. They are used here as shape, not as
  targets.
- **How well an LLM reviews this page.** The published results are on mobile
  mockups and ordinary web pages, not on live SVG graphs, and agree only
  roughly with human raters.
- **The measurements in this note** are from the demo sessions on one day.
  Real sessions have more nodes, longer labels and other mixes of state.
