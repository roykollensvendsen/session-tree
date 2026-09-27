"""Every task state can be told apart without full colour vision, and reads clearly.

The page draws each state with an outline, a fill and a text colour, all kept in
one table, STATE, in index.html. This reads that table and checks it the way the
research note describes (docs/research/design-review-for-a-live-graph-dashboard.md):

- two states must differ in more than hue: a distinct cue (a glyph, a dash, a
  pulse), or colours far enough apart after each colour-vision simulation
  Chromium offers, using Chromium's own matrices in linear RGB;
- an outline needs 3:1 against its fill (WCAG 1.4.11), and the text on a node
  4.5:1 (WCAG 1.4.3), on the goal card the graph is drawn on.

No browser is needed: the matrices and formulas are public and fixed.
"""

import itertools
import math
import pathlib
import re

import pytest

PAGE = (pathlib.Path(__file__).parent.parent / "src/session_tree/index.html").read_text()
# the goal card a graph is drawn on (--panel2)
CARD = (0x1B, 0x21, 0x2B)
# ΔEOK of 0.02 is one just-noticeable difference (CSS Color 4); a glance at a
# small outline needs many, and five is a choice, not a standard
MIN_DISTANCE = 0.10

# Chromium's feColorMatrix values, third_party/blink/renderer/core/css/vision_deficiency.cc
SIMULATIONS = {
    "normal": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "protanopia": ((0.152, 1.053, -0.205), (0.115, 0.786, 0.099), (-0.004, -0.048, 1.052)),
    "deuteranopia": ((0.367, 0.861, -0.228), (0.280, 0.673, 0.047), (-0.012, 0.043, 0.969)),
    "tritanopia": ((1.256, -0.077, -0.179), (-0.078, 0.931, 0.148), (0.005, 0.691, 0.304)),
    "achromatopsia": ((0.213, 0.715, 0.072),) * 3,
}


def states() -> dict[str, dict]:
    """The STATE table from the page, one state per line."""
    table = PAGE.split("const STATE={", 1)[1].split("\n};", 1)[0]
    found = {}
    for name, body in re.findall(r"^\s*(\w+):\s*\{(.*)\},?\s*$", table, re.MULTILINE):
        pairs = re.findall(r"(\w+):\s*(?:'([^']*)'|([\d.]+))", body)
        found[name] = {key: text or number for key, text, number in pairs}
    return found


def rgba(value: str) -> tuple[tuple[float, ...], float]:
    """A '#rrggbb' or 'rgba(r,g,b,a)' as 0-255 channels and an alpha."""
    if value.startswith("#"):
        return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5)), 1.0
    *rgb, alpha = (float(x) for x in re.findall(r"[\d.]+", value))
    return tuple(rgb), alpha


def over(top: str, below: tuple[float, ...], alpha: float | None = None) -> tuple[float, ...]:
    """A colour laid over another, as the browser blends it."""
    rgb, a = rgba(top)
    a = a if alpha is None else alpha
    return tuple(c * a + b * (1 - a) for c, b in zip(rgb, below, strict=True))


def linear(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[float, ...]) -> float:
    r, g, b = (linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def oklab(lin: tuple[float, ...]) -> tuple[float, ...]:
    """Oklab from linear sRGB (CSS Color 4, color-conversion-code)."""
    r, g, b = lin
    lms = (
        0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b,
        0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b,
        0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b,
    )
    l_, m_, s_ = (math.copysign(abs(x) ** (1 / 3), x) for x in lms)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def seen(rgb: tuple[float, ...], matrix) -> tuple[float, ...]:
    """What a colour looks like under a simulation, in Oklab."""
    lin = [linear(c) for c in rgb]
    return oklab(
        tuple(min(1.0, max(0.0, sum(m * c for m, c in zip(row, lin, strict=True)))) for row in matrix)
    )


def outline(look: dict) -> tuple[float, ...]:
    """The outline as drawn: its colour, at its opacity, over the node's fill on the card."""
    fill = over(look["fill"], CARD)
    return over(look["stroke"], fill, float(look["strokeOpacity"]))


def test_the_table_has_every_state():
    assert set(states()) == {
        "pending",
        "waiting",
        "in_progress",
        "completed",
        "stalled",
        "blocked",
        "abandoned",
    }


@pytest.mark.parametrize("name", sorted(states()))
def test_an_outline_stands_out_from_its_fill(name):
    look = states()[name]
    ratio = contrast(outline(look), over(look["fill"], CARD))
    assert ratio >= 3, f"{name}: the outline is {ratio:.2f}:1 against its fill, below 3:1"


@pytest.mark.parametrize("name", sorted(states()))
def test_the_text_on_a_node_can_be_read(name):
    look = states()[name]
    fill = over(look["fill"], CARD)
    ratio = contrast(rgba(look["text"])[0], fill)
    assert ratio >= 4.5, f"{name}: its text is {ratio:.2f}:1 against its fill, below 4.5:1"
    id_colour = re.search(r"\.node \.id\{[^}]*fill:(#[0-9a-f]{6})", PAGE)
    assert id_colour, "the task number's colour is not a plain colour the test can read"
    ratio = contrast(rgba(id_colour.group(1))[0], fill)
    assert ratio >= 4.5, f"{name}: the task number is {ratio:.2f}:1 against its fill, below 4.5:1"


@pytest.mark.parametrize("sim", sorted(SIMULATIONS))
def test_two_states_differ_in_more_than_hue(sim):
    table = states()
    alike = []
    for a, b in itertools.combinations(sorted(table), 2):
        if table[a]["cue"] != table[b]["cue"]:
            continue  # a glyph, a dash or a thick outline tells them apart
        distance = math.dist(
            seen(outline(table[a]), SIMULATIONS[sim]), seen(outline(table[b]), SIMULATIONS[sim])
        )
        if distance < MIN_DISTANCE:
            alike.append(f"{a}~{b} ({distance:.3f})")
    assert not alike, f"under {sim}, states told apart by colour alone look alike: {alike}"


def test_every_glyph_cue_is_drawn():
    draw = PAGE.split("const drawNode=", 1)[1].split("\n  };", 1)[0]
    assert "look.cue" in draw, "the cue in the table is never drawn on a task"


def test_only_a_question_fills_a_task_with_colour():
    """Every alarm should need the reader; a blocked task rarely does (the research note, alarm design)."""
    table = states()
    assert table["blocked"]["fill"] == table["pending"]["fill"], "a blocked task is still filled with red"
    assert rgba(table["stalled"]["fill"])[1] <= 0.06, "a stalled task is still filled as strongly as an alarm"
    asks = re.search(r"\.node\.asks>rect\{[^}]*fill:(rgba\([^)]*\))", PAGE)
    assert asks, "a task with a question is not filled"
    assert rgba(asks.group(1))[1] >= 0.12, "a task with a question is filled no more strongly than the rest"
