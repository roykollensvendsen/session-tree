#!/usr/bin/env python3
"""Put what is merged on main live in the viewer running on this machine.

The viewer does not run from the clone you work in. It runs from the one the
skill lives in, ~/.claude/skills/session-tree, so a merged change is not live
until that clone has it. Forgetting that step looks exactly like a fix that did
not work.

    python3 scripts/deploy_local.py            # fast-forward, restart if needed, check
    python3 scripts/deploy_local.py --restart  # restart even if only the page changed

It finds every viewer server on this machine, however many addresses it
listens on, and restarts each one with the address it had. A restart is only
needed when Python changed: the page is read from disk on every request.
Then it fetches the page from each address and compares it with the clone's
copy, and exits 1 if one differs. Linux only: it reads /proc.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.request

CLONE = pathlib.Path(os.environ.get("SESSION_TREE_CLONE", "~/.claude/skills/session-tree")).expanduser()
PAGE = "src/session_tree/index.html"
STOP_TIMEOUT = 5.0


def needs_restart(changed: list[str]) -> bool:
    """Whether these changed files include code the running server loaded at start."""
    return any((f.startswith("src/") and f.endswith(".py")) or f == "pyproject.toml" for f in changed)


def git(*args: str) -> str:
    """Run git in the viewer's clone and return what it printed."""
    return subprocess.run(  # noqa: S603 - fixed arguments, no shell
        ["git", "-C", str(CLONE), *args],  # noqa: S607 - git from PATH, as the developer runs it
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def servers() -> list[tuple[int, str, int, pathlib.Path]]:
    """Every running viewer server: pid, host, port and the directory it runs from."""
    found = []
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            cmd = (proc / "cmdline").read_bytes().split(b"\0")
            if b"session_tree.server" not in cmd:
                continue
            env = dict(
                line.split("=", 1) for line in (proc / "environ").read_text().split("\0") if "=" in line
            )
            cwd = (proc / "cwd").resolve()
        except OSError:
            continue
        found.append(
            (
                int(proc.name),
                env.get("SESSION_TREE_HOST", "127.0.0.1"),
                int(env.get("SESSION_TREE_PORT", "8787")),
                cwd,
            )
        )
    return found


def stop(pid: int) -> None:
    """Ask a server to stop, and wait until it has."""
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + STOP_TIMEOUT
    while time.monotonic() < deadline and pathlib.Path(f"/proc/{pid}").exists():
        time.sleep(0.1)


def served(host: str, port: int) -> bytes:
    """The page a running server hands out."""
    with urllib.request.urlopen(f"http://{host}:{port}/", timeout=5) as response:
        return response.read()


def main(argv: list[str] | None = None) -> int:
    """Fast-forward the clone, restart what needs it, and check every address. Returns an exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--restart", action="store_true", help="restart even if only the page changed")
    args = parser.parse_args(argv)

    if git("status", "--porcelain"):
        sys.stderr.write(f"{CLONE} has uncommitted changes; not touching it\n")
        return 1
    if git("branch", "--show-current") != "main":
        sys.stderr.write(f"{CLONE} is not on main; not touching it\n")
        return 1
    before = git("rev-parse", "--short", "HEAD")
    git("fetch", "-q", "origin")
    git("merge", "-q", "--ff-only", "origin/main")
    after = git("rev-parse", "--short", "HEAD")
    changed = git("diff", "--name-only", before, after).splitlines()
    sys.stdout.write(f"clone: {before} -> {after}\n" if before != after else f"clone: already on {after}\n")

    running = servers()
    if not running:
        sys.stdout.write(f"no viewer is running; start one with {CLONE}/scripts/session-tree start\n")
        return 0
    for _, host, port, cwd in running:
        if cwd != CLONE.resolve():
            sys.stderr.write(f"the viewer on {host}:{port} runs from {cwd}, not {CLONE}; left alone\n")
    running = [s for s in running if s[3] == CLONE.resolve()]

    sys.stdout.flush()  # before the restart's own output, so the report reads in order
    if args.restart or needs_restart(changed):
        for pid, host, port, _ in running:
            stop(pid)
            subprocess.run(  # noqa: S603
                [str(CLONE / "scripts/session-tree"), "start", "--host", host, "--port", str(port)],
                check=True,
                cwd=CLONE,
            )
    else:
        sys.stdout.write("no Python changed, so no restart: the page is read on every request\n")

    page = (CLONE / PAGE).read_bytes()
    stale = [f"{host}:{port}" for _, host, port, _ in running if served(host, port) != page]
    for _, host, port, _ in running:
        verdict = "does NOT serve the page of" if f"{host}:{port}" in stale else "serves the page of"
        sys.stdout.write(f"http://{host}:{port}/ {verdict} {after}\n")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
