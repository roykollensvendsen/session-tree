"""The README promises a phone-sized page and a pager between goals; the page must carry them.

Same shape as test_focus_view: the page is inline JavaScript no test can run,
so what is checked is that every gesture and switch the README names exists
in the page, and that the server can be told which address to listen on.
"""

import pathlib
import re
import socket

from session_tree import server

ROOT = pathlib.Path(__file__).parent.parent
PAGE = (ROOT / "src/session_tree/index.html").read_text()
README = (ROOT / "README.md").read_text()


def test_the_readme_has_a_section_for_the_phone():
    block = re.search(r"## On your phone\n(.*?)\n## ", README, re.DOTALL)
    assert block, "README.md no longer has the section on the phone"
    for word in ("SESSION_TREE_HOST", "tailscale ip -4", "no authentication", "swipe"):
        assert word in block.group(1), f"the README section does not mention {word}"


def test_the_page_is_sized_for_a_phone():
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in PAGE
    assert "@media (max-width:640px)" in PAGE.replace(" (max-width: 640px)", " (max-width:640px)")


def test_every_pager_gesture_the_readme_names_has_a_handler_in_the_page():
    for needle in ("'ArrowLeft'", "'ArrowRight'", "st.page", "className='pager'", "pagerAll"):
        assert needle in PAGE, f"no {needle} in index.html"
    assert "SWIPE_PX" in PAGE, "the swipe threshold is not named in the page"


def test_the_focused_graph_can_be_pinched():
    assert "pinch" in PAGE, "no two-finger zoom in the focused graph"


def test_the_server_listens_where_it_is_told(monkeypatch):
    monkeypatch.delenv("SESSION_TREE_HOST", raising=False)
    assert server.resolve_host() == "127.0.0.1"
    monkeypatch.setenv("SESSION_TREE_HOST", "100.64.0.9")
    assert server.resolve_host() == "100.64.0.9"
    assert server.resolve_host("10.0.0.2") == "10.0.0.2"
    with server.make_server(0, "127.0.0.1") as httpd:
        assert httpd.server_address[0] == "127.0.0.1"
        assert httpd.socket.family == socket.AF_INET


def test_many_goals_do_not_push_the_pager_buttons_off_a_phone():
    dots = re.search(r"\.pager \.dots\{([^}]*)\}", PAGE)
    assert dots, "no rule for the pager's dots"
    assert "flex-wrap:wrap" in dots.group(1), "the dots do not wrap, so many goals overflow"
    assert "min-width:0" in dots.group(1), "the dots cannot shrink, so next and alle go past the edge"
    phone = PAGE.split("@media (max-width:640px)", 1)[1].split("\n  }\n", 1)[0]
    assert ".pager{flex-wrap:wrap}" in phone, "on a phone the dots do not get a row of their own"


def test_with_every_goal_shown_only_the_switch_back_is_left():
    block = re.search(r"## On your phone\n(.*?)\n## ", README, re.DOTALL)
    assert "only the lit **☰** stays" in block.group(1), (
        "the README does not say what is left above every goal"
    )
    bar = PAGE.split("function pagerBar(", 1)[1].split("\nfunction ", 1)[0]
    head = bar.split("bar.innerHTML=", 1)[0]
    assert "if(pagerAll)" in head, "the pager draws its page controls even with every goal shown"
    keys = PAGE.split("'ArrowLeft'&&e.key!=='ArrowRight'", 1)[1].split("});", 1)[0]
    assert "pagerAll" in keys, "the arrow keys turn a page nobody can see"
