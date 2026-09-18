# ADR-ST-004: How a change is made here

## Status

Accepted, Roy Kollen Svendsen, 2026-09-18.

## Context

This is a one-person tool that other people may end up running. The process
choices are the ones nobody writes down, and they are what costs time on every
future contribution.

The repository is public, so the forge can enforce branch protection; on a
private repository under a free account it would refuse, and the contributing
guide would then be claiming a gate that does not exist.

## Options considered

**Direct pushes to `main`.** Rejected now that protection is available. It was
the honest option only while the repository was going to be private.

**Pull requests with review.** Not chosen yet: there is one person. A required
review would be a rule that blocks rather than one that catches.

**Pull requests, self-merged, with CI required.** Chosen.

## Decision

Every change lands through a pull request that CI has passed. Merges are rebase
only, so history stays a line and each commit remains a thing that can be
reverted on its own. `main` cannot be force-pushed.

Commit messages follow the conventional form and are written for a stranger:
everyday words first, mechanical detail at the bottom.

A rule the tooling enforces gets a row in `scripts/mutations.toml` and a test
named after it, and `scripts/mutate.py` must report it killed by that test
rather than by another one.

## Consequences

The evidence for each rule is reproducible by someone who was not here.

What gets worse: a one-line fix costs a branch, a pull request and a CI run.
With one contributor that is pure overhead, and the temptation to bypass it is
real — which is why it is the forge that refuses rather than this document.

## Related

`CONTRIBUTING.md`, `.github/workflows/checks.yml`, `scripts/mutations.toml`.
