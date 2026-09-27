"""The design review has its pictures: the demo as each kind of eye sees it.

scripts/review_shots.py builds the demo sessions, serves them and photographs
the page at a phone's width and a wide screen's, as it is and under each of
Chromium's colour-vision simulations, plus the biggest graph opened full
screen. The design-review skill starts from these; CI keeps them as an
artefact. Nothing asserts on how they look: a person does that.
"""

import hashlib
import pathlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.browser

ROOT = pathlib.Path(__file__).parent.parent
VISIONS = ("none", "protanopia", "deuteranopia", "tritanopia", "achromatopsia")


def test_the_review_shots_cover_every_width_and_every_simulation(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "scripts/review_shots.py"), str(tmp_path)], check=True)
    for width in ("phone", "wide"):
        pictures = {v: tmp_path / f"{width}-page-{v}.png" for v in VISIONS}
        missing = [str(p.name) for p in pictures.values() if not p.exists()]
        assert not missing, f"no picture for {missing}"
        digests = {hashlib.sha256(p.read_bytes()).hexdigest() for p in pictures.values()}
        assert len(digests) == len(VISIONS), f"on a {width} some simulations gave the same picture"
        assert (tmp_path / f"{width}-enlarged-none.png").exists(), f"no full-screen graph on a {width}"
