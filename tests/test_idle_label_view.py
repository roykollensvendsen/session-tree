"""An idle session is labelled 'ledig', not 'venter på deg'.

The label is shown for a session whose agent has finished its turn with the
process alive. That is not a request for input: a question has its own mark.
'venter på deg' read as one, so a session that had simply finished looked as if
it needed something.
"""

import pathlib

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
DOCS = {name: (ROOT / name).read_text() for name in ("README.md", "SKILL.md")}


def test_an_idle_session_is_labelled_ledig():
    assert '<span class="att waiting">ledig</span>' in PAGE, "an idle session is not labelled 'ledig'"


def test_nothing_says_venter_pa_deg_any_more():
    assert "venter på deg" not in PAGE, "the page still says 'venter på deg'"
    for name, text in DOCS.items():
        assert "venter på deg" not in text, f"{name} still says 'venter på deg'"
