# Changelog

Every release, what changed in it, and why. Dates are the tag's date. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
versions follow [semantic versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- On a phone, a quick tap on a node lights its arrows without covering the
  graph, and holding a finger on it for half a second opens its details, which
  now have a **✕** to close them. Before, every tap opened the details.

- **avvis** beside a question in the list at the top puts away a question that
  was answered somewhere the session cannot see, such as a background job that
  carried the work on. The server keeps the dismissal, so it holds on every
  device; the node still shows the question, marked `avvist`
  ([ADR-ST-006](decisions/ADR-ST-006-a-question-can-be-dismissed.md)).

- A **skjul ferdige** switch in the header hides finished nodes and the
  arrows from them, so a long goal's graph shows what is left. A finished node
  with a step still running stays. Off by default, remembered per browser.

### Fixed

- On a phone, a page pinched in before a graph was opened full screen put
  its **✕** and **tilpass** off screen, and the graph took every pinch for its
  own zoom, so there was no way back. The graph now covers exactly the part of
  the page that is visible, and the phone's back gesture closes it too.

- An arrow out of an unfolded breakdown started just under the box's heading
  and ran down through the steps inside it. It now leaves from the bottom of
  the box.

- A goal with many steps on the same level, such as seventy that wait on
  nothing, drew them as slivers a few pixels wide, so the graph looked like a
  handful of lines. A level too wide to fit now wraps onto more rows, each step
  wide enough to read, in the card and in the enlarged graph.

- On a narrow phone, a session with many goals pushed the **›** button
  and **alle** off the right edge of the screen, because the row of dots
  could not shrink. The dots now wrap onto a row of their own under the
  buttons.

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
