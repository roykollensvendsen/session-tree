"""The page's buttons show a symbol, and say in words what they do when hovered or read aloud.

A word on a button costs room a phone does not have. A symbol alone can be
guessed wrong, so each keeps its word as the title a pointer shows and the
label a screen reader reads.
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
README = (ROOT / "README.md").read_text()

# symbol, the word it replaces
BUTTONS = [
    ("⤢", "tilpass"),
    ("⏱", "replay"),
    ("⏏", "tilbake til live"),
    ("⊞", "alle målene på én gang"),
    ("⊟", "ett mål om gangen"),
    ("⊘", "avvis"),
    ("✓", "skjul ferdige"),
]


def buttons() -> list[str]:
    """Every button element the page writes, markup and templates alike."""
    return re.findall(r"<button\b[^>]*>.*?</button>", PAGE)


@pytest.mark.parametrize(("symbol", "word"), BUTTONS, ids=[w for _, w in BUTTONS])
def test_the_button_shows_its_symbol_and_keeps_its_word(symbol, word):
    found = [b for b in buttons() if f'title="{word}' in b or f"'{word}'" in b.split(">", 1)[0]]
    assert found, f"no button titled {word!r}"
    label = re.sub(r"<[^>]+>", "", found[0]).strip()
    assert symbol in label, f"the {word!r} button shows {label!r}, not {symbol}"
    assert word.split()[0] not in label, f"the {word!r} button still shows the word"
    assert "aria-label=" in found[0], f"the {word!r} button has nothing for a screen reader"


def test_replay_has_one_button_back_to_now():
    assert "**⏏ 23** goes back to now" in README, "the README does not say how replay returns to now"
    back = [b for b in buttons() if 'title="tilbake til live"' in b]
    assert len(back) == 1, "replay has more than one way back to now, or none"
    assert "${behind" in back[0], "the way back does not say how much has happened since"
    assert 'title="hopp til nå"' not in PAGE, "the second button back to now is still there"
