# Changelog

Every release, what changed in it, and why. Dates are the tag's date. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions follow [semantic versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- The live stream pushed the whole picture (~0.7 MB) 2.5 times a second even
  when nothing happened, because the clock and running durations are part of
  it: 97 MB a minute to every open page, and a browser tab that grew to 20 GB
  in a day. Now only a change outside those fields pushes (at most every 30 s
  otherwise), and the page ages running work itself.

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
