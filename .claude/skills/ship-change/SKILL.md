---
name: ship-change
description: Take a change to session-tree from the user's request to running in their own viewer — the graph in the viewer first, then branch, failing test, fix, pull request, green checks, merge on the user's word, and the local deploy that makes it visible. Use for every change to this repository, a one-line CSS fix included, and whenever the user says "fix this", "make it so", "ship it", "deploy it", "is it live?" or reports something wrong in the viewer. Use it before the first edit, because the steps people forget are the first one and the last one.
---

# Shipping a change to session-tree

The rules live in `CONTRIBUTING.md` and the pull request template. This page
does not repeat them. It is the order, and the three steps that were missed on
2026-09-26 while fixing one line of CSS: no graph until the user asked for one,
a push that failed a lint check nobody had run, and a merged fix that the
user's viewer never showed.

## 1. Draw the work before doing it

The user watches this session in the viewer, often from a phone. Before the
first tool call that does the work, create the nodes with `TaskCreate`, under
`metadata: {"goal": "..."}`, and wire them with `addBlockedBy`. The usual shape:

1. The fault is seen (reproduced, with how)
2. An automatic test fails while the fault is there
3. The thing the user sees works (the fix, looked at, not only tested)
4. The change is proposed for review
5. GitHub's automatic checks pass
6. The change is part of the main version — `ask` set: merge needs the user's word
7. The viewer on this machine shows it

**Write every subject for someone who was not in the conversation and does
not know the code.** Name what the user sees or gets, in everyday words. File
names, CSS selectors, function names, flags, commit hashes and PR numbers go in
the description, never in the subject. Read the subject alone and ask whether a
colleague would understand it at a glance.

| Not this | This |
|---|---|
| Fix .pager .dots min-width | On a phone, the buttons for turning between goals stay on screen |
| PR #25 CI green | GitHub's automatic checks pass on the fix |
| deploy_local.py on 8787 | The viewer on this machine shows the fix |

Keep it true as you go: `in_progress` before you start a node, `completed`
only once it is checked, `ask` on the node that waits for the user and `null`
once answered. A new request from the user is a new node.

## 2. Make the change

A branch, never `main`. Then the order `CONTRIBUTING.md` gives under "How a
change is made": decide, say it, a test seen red with the run recorded under
`evidence/tests/`, the smallest code that turns it green.

For anything the user sees, look at it. The page is inline JavaScript and CSS
that no test lays out, so a test that reads the stylesheet proves the rule is
there, not that it works. Render it in headless Chromium at the size that
matters (a phone is 360 px wide) and look at the screenshot.

## 3. Push only what would pass

The `pre-push` hook runs the gates when `core.hooksPath` is `.githooks`.
Check that once per clone:

<!-- not run: prints this clone's setting -->
```
git config core.hooksPath
```

If it prints nothing, run the gates by hand before pushing, all of them, as
`CONTRIBUTING.md` lists them. Running only the tests is how a lint failure
reached CI.

Commit messages and the pull request body go through the `write-commit` skill.

## 4. Merge on the user's word

Merging is outward-facing: ask, with `ask` set on the node, and wait. Merge by
rebase with `gh pr merge <n> --rebase --delete-branch`, then bring the working
clone's `main` up to date.

## 5. Make it visible, and check that it is

The user's viewer runs from `~/.claude/skills/session-tree`, not from the
clone you work in. Nothing the user sees has changed until that clone has it:

<!-- not run: restarts the viewer the user is looking at -->
```
python3 scripts/deploy_local.py
```

It fast-forwards that clone, restarts the viewer only if Python changed, and
checks every address the viewer listens on. It exits 1 if one of them still
serves an old page. Only then is the last node complete, and only then tell the
user it is live, naming the addresses it checked.
