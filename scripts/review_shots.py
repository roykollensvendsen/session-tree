#!/usr/bin/env python3
"""Photograph the demo sessions for a design review.

    python3 scripts/review_shots.py [directory]

Builds a fresh set of demo sessions, serves them on a free port, and saves the
page at a phone's width (390 px) and a wide screen's (1400 px): as it is, and
as Chromium simulates it for protanopia, deuteranopia, tritanopia and
achromatopsia. It also saves the biggest graph opened full screen. The pictures
are named <width>-<view>-<vision>.png, and the directory (a new temporary one if
none is given) is printed at the end.

The design-review skill (.claude/skills/design-review) starts from these, and CI
keeps them as an artefact. Needs Playwright and Chromium, as the browser tests
do (ADR-ST-007); a system Chromium is used if Playwright's own is missing.
"""

from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import Error, sync_playwright

ROOT = pathlib.Path(__file__).parent.parent
VISIONS = ("none", "protanopia", "deuteranopia", "tritanopia", "achromatopsia")
WIDTHS = {"phone": {"width": 390, "height": 900}, "wide": {"width": 1400, "height": 1000}}
SYSTEM_CHROMIUM = ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome")
BIGGEST = "The neighbourhood is clean"


def serve_demo(home: pathlib.Path) -> tuple[subprocess.Popen[bytes], str]:
    """Build the demo into home and start the server on a free port."""
    subprocess.run([sys.executable, str(ROOT / "scripts/demo_fixture.py"), str(home)], check=True)  # noqa: S603 - fixed arguments
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {**os.environ, "HOME": str(home), "PYTHONPATH": str(ROOT / "src")}
    env |= {"SESSION_TREE_PORT": str(port), "SESSION_TREE_HOST": "127.0.0.1"}
    server = subprocess.Popen([sys.executable, "-m", "session_tree.server"], env=env)
    url = f"http://127.0.0.1:{port}/"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url + "api/ping", timeout=1).close()  # noqa: S310
            break
        except OSError:
            time.sleep(0.1)
    return server, url


def main(out: pathlib.Path) -> None:
    """Take every picture into out."""
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="st-review-") as home:
        server, url = serve_demo(pathlib.Path(home))
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch()
                except Error:
                    found = next((c for c in SYSTEM_CHROMIUM if pathlib.Path(c).exists()), None)
                    if found is None:
                        raise
                    browser = p.chromium.launch(executable_path=found)
                for name, viewport in WIDTHS.items():
                    page = browser.new_page(viewport=viewport, reduced_motion="reduce")
                    page.goto(url)
                    page.wait_for_selector(".sess .node")
                    cdp = page.context.new_cdp_session(page)
                    for vision in VISIONS:
                        cdp.send("Emulation.setEmulatedVisionDeficiency", {"type": vision})
                        page.screenshot(path=out / f"{name}-page-{vision}.png", full_page=True)
                    cdp.send("Emulation.setEmulatedVisionDeficiency", {"type": "none"})
                    page.locator(".gtitle", has_text=BIGGEST).click()
                    page.wait_for_selector("#focus.on svg")
                    page.screenshot(path=out / f"{name}-enlarged-none.png")
                    page.close()
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=5)
    sys.stdout.write(f"{out}\n")


if __name__ == "__main__":
    main(
        pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(tempfile.mkdtemp(prefix="st-shots-"))
    )
