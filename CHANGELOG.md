# Changelog

Every release, what changed in it, and why. Dates are the tag's date. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions follow [semantic versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Several independent goals in one session are pages: swipe, dots, arrow
  keys or "alle" for the wall. The page fits a phone, the focused graph
  pinches to zoom, and `SESSION_TREE_HOST` / `--host` bind the server to a
  tailnet address so the phone can reach it.
- Click a goal's title to open its graph alone in the window, with wheel
  zoom, drag pan, double-click to fit and Esc to close — large graphs are
  readable that way.
- The walking skeleton: the thinnest path through the whole system, end to
  end, green in CI on the first commit.
