"""Start the server, print the picture, or open the window."""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from session_tree.install_codex import install as install_codex
from session_tree.state import build
from session_tree.summary import render_summary

DEFAULT_PORT = 8787
DEFAULT_HOST = "127.0.0.1"
STARTUP_TIMEOUT = 10.0
BROWSERS = ("firefox", "chromium", "google-chrome", "google-chrome-stable")
COMMANDS = ("open", "start", "stop", "restart", "status", "install-codex-hook")


def url(port: int, host: str = DEFAULT_HOST) -> str:
    """Return the base URL the server listens on."""
    return f"http://{host}:{port}/"


def run_dir() -> Path:
    """Return the directory holding the pid file and the server log."""
    base = os.environ.get("XDG_RUNTIME_DIR", "/tmp")  # noqa: S108
    path = Path(base) / "session-tree"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_running(port: int, host: str = DEFAULT_HOST) -> bool:
    """Return whether our server is already answering on this port."""
    try:
        with urllib.request.urlopen(url(port, host) + "api/ping", timeout=2) as response:  # noqa: S310
            return b"session-tree" in response.read()
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def start(port: int, host: str = DEFAULT_HOST) -> int:
    """Start the server unless it is already up. Returns a process exit code."""
    if is_running(port, host):
        sys.stdout.write(f"already running on {url(port, host)}\n")
        return 0
    log = (run_dir() / "server.log").open("ab")
    env = dict(os.environ, SESSION_TREE_PORT=str(port), SESSION_TREE_HOST=host)
    process = subprocess.Popen(
        [sys.executable, "-m", "session_tree.server"],
        stdout=log,
        stderr=log,
        start_new_session=True,
        env=env,
    )
    (run_dir() / "server.pid").write_text(str(process.pid))
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if is_running(port, host):
            sys.stdout.write(f"started on {url(port, host)}\n")
            return 0
        time.sleep(0.25)
    sys.stderr.write(f"did not come up; see {run_dir() / 'server.log'}\n")
    return 1


def stop(port: int, host: str = DEFAULT_HOST) -> int:
    """Stop the server if we started it. Returns a process exit code."""
    pid_file = run_dir() / "server.pid"
    if pid_file.exists():
        with contextlib.suppress(ProcessLookupError, ValueError, PermissionError):
            os.kill(int(pid_file.read_text()), signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
    sys.stdout.write(f"stopped {url(port, host)}\n")
    return 0


def open_window(port: int, host: str = DEFAULT_HOST) -> int:
    """Open the view in its own browser window, starting the server first."""
    code = start(port, host)
    if code:
        return code
    for name in BROWSERS:
        binary = shutil.which(name)
        if not binary:
            continue
        args = [binary, "--new-window", url(port, host)]
        subprocess.Popen(  # noqa: S603
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        sys.stdout.write(f"opened {url(port, host)} in {name}\n")
        return 0
    sys.stdout.write(f"no browser found; open {url(port, host)} yourself\n")
    return 0


def status(port: int, host: str = DEFAULT_HOST) -> int:
    """Print the same picture as the page, in the terminal."""
    if not is_running(port, host):
        sys.stdout.write("not running (start it with: session-tree start)\n")
        return 1

    sys.stdout.write(f"running on {url(port, host)}\n")
    sys.stdout.write(render_summary(build()))
    return 0


def install_codex_hook(port: int, host: str = DEFAULT_HOST) -> int:  # noqa: ARG001 - dispatched with the others
    """Set Codex up so its plans reach the view, and say what changed."""
    for line in install_codex():
        sys.stdout.write("  " + line + "\n")
    sys.stdout.write("restart Codex for the hook to take effect\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch. Returns a process exit code."""
    parser = argparse.ArgumentParser(prog="session-tree", description=__doc__)
    parser.add_argument(
        "action",
        nargs="?",
        default="open",
        choices=COMMANDS,
    )
    parser.add_argument("--port", type=int, default=int(os.environ.get("SESSION_TREE_PORT", DEFAULT_PORT)))
    parser.add_argument(
        "--host",
        default=os.environ.get("SESSION_TREE_HOST", DEFAULT_HOST),
        help="address to listen on; a tailnet address lets your phone in, 0.0.0.0 lets everyone in",
    )
    args = parser.parse_args(argv)

    if args.action == "restart":
        stop(args.port, args.host)
        time.sleep(0.5)
        return start(args.port, args.host)
    return {
        "open": open_window,
        "start": start,
        "stop": stop,
        "status": status,
        "install-codex-hook": install_codex_hook,
    }[args.action](args.port, args.host)


if __name__ == "__main__":
    sys.exit(main())
