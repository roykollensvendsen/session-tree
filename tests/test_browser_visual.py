"""The page looks as it did, unless a change meant it to look different.

The other browser tests check that a mechanism works; none of them would notice
a button hidden by a stray style rule, the bug that started ADR-ST-007. This
compares pictures of the demo's first screen -- what shows before any
scrolling, where ADR-ST-008 puts what needs you -- with the ones kept in
tests/visual/. Only the first screen, so the kept pictures stay small and
change only when the page's look is meant to.

Fonts differ between machines, so the kept pictures are made in CI and only CI
compares (SESSION_TREE_VISUAL=check); elsewhere this skips. What changes by
itself is kept out of the picture: animations are stopped, and times and ages
are masked. A difference beyond a small share of pixels fails, and the new
pictures and a picture of the difference are written to visual-results/, which
CI keeps as an artefact. To accept a change on purpose, copy the new pictures
from that artefact into tests/visual/ and commit them.
"""

import os
import pathlib

import pytest

pytestmark = pytest.mark.browser

MODE = os.environ.get("SESSION_TREE_VISUAL", "")
KEPT = pathlib.Path(__file__).parent / "visual"
RESULTS = pathlib.Path(__file__).parent.parent / "visual-results"
# a channel difference below this is antialiasing, not a change
NOISE = 40
# the share of pixels that may differ before it counts as a change
SHARE = 0.002
# what changes on its own between two runs: ages, durations, the clock
MASKED = ".pill, .now span, #conn, .tasklist td.time, .rp .t"


def _shrink(path: pathlib.Path) -> None:
    """Save a picture with a small palette, so the kept copies stay light."""
    from PIL import Image  # noqa: PLC0415 - only this test needs Pillow

    Image.open(path).convert("RGB").quantize(colors=256).save(path, optimize=True)


def difference(kept: pathlib.Path, now: pathlib.Path, out: pathlib.Path) -> float:
    """The share of pixels that differ; writes a picture of where to out."""
    from PIL import Image, ImageChops  # noqa: PLC0415 - only this test needs Pillow

    a = Image.open(kept).convert("RGB")
    b = Image.open(now).convert("RGB")
    if a.size != b.size:
        return 1.0
    diff = ImageChops.difference(a, b)
    marks = diff.convert("L").point(lambda v: 255 if v > NOISE else 0)
    marks.save(out)
    changed = marks.histogram()[255]
    return changed / (a.size[0] * a.size[1])


@pytest.mark.skipif(MODE != "check", reason="pictures are compared in CI only, where they were made")
def test_the_page_looks_as_it_did(page):
    width = "phone" if page.viewport_size["width"] < 600 else "wide"
    RESULTS.mkdir(exist_ok=True)
    now = RESULTS / f"{width}.png"
    page.screenshot(path=now, animations="disabled", mask=[page.locator(MASKED)])
    _shrink(now)
    kept = KEPT / f"{width}.png"
    assert kept.exists(), f"no kept picture for a {width}; take {now.name} from the visual-results artefact"
    share = difference(kept, now, RESULTS / f"{width}-difference.png")
    assert share <= SHARE, (
        f"on a {width} {share:.2%} of the page changed; if that was meant, take {now.name} "
        "from the visual-results artefact into tests/visual/"
    )
