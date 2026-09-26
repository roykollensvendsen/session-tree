"""When putting a merged change live has to restart the viewer, and when a reload is enough.

The server reads the page from disk on every request, so a change to the page
alone is live the moment the clone has it. Python is loaded once, at start.
"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import deploy_local


@pytest.mark.parametrize(
    "changed",
    [
        ["src/session_tree/index.html"],
        ["README.md", "CHANGELOG.md"],
        ["tests/test_state.py", "scripts/mutate.py"],
        [],
    ],
)
def test_a_change_the_server_reads_per_request_needs_no_restart(changed):
    assert not deploy_local.needs_restart(changed)


@pytest.mark.parametrize(
    "changed",
    [
        ["src/session_tree/server.py"],
        ["src/session_tree/index.html", "src/session_tree/state.py"],
        ["pyproject.toml"],
    ],
)
def test_a_change_to_the_servers_own_code_needs_a_restart(changed):
    assert deploy_local.needs_restart(changed)
