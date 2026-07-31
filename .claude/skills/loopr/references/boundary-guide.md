# Boundary guide

Condensed from `loopr-PRD.md` §A3. Read that for full detail.

## What the boundary does

Two jobs: it's the **scope arbiter** (how loopr decides "that's a later phase, not now" during
speccing) and it's the **fuel for the audit tier** (what a senior audit checks the review didn't let
slip, in the parked Phase B harness -- not built by this skill).

## Proposed, then confirmed -- never demanded upfront

loopr does not ask for a boundary cold; a stranger won't have one ready. After soft context
(`context.md`) exists, loopr analyzes what's been said so far and **proposes** a boundary in plain
language, states it, and asks the user to confirm or tweak. A shallow user accepts as-is; a deep user
sharpens it. Since loopr's own engine never calls an LLM directly (`PHASE_1_SPEC.md` §6.2), the
*proposing* is the invoking agent's job -- when Gate 2 fires with an empty boundary section, that's
the cue to draft a genuine proposal from the confirmed problem statement, acceptance criteria, and
scope edges so far, not a defect to work around.

## Preferred, not strictly mandatory

If there's genuinely no hard boundary for a project, the (parked) audit tier degrades gracefully to
auditing against the failure-mode catalogue only. loopr always proposes one and strongly prefers
having one; it survives without one.

## The escape hatch

`declined` is a distinct, recorded user action -- never inferred from silence or from the absence of
a boundary. A user who explicitly declines satisfies condition 4 the same way a confirmed boundary
does; the module never fabricates a boundary confirmation to force convergence.

## Confirmation is bound to exact text

`confirmed_hash` is the SHA-256 of `boundary.text` at the moment of confirmation. Any edit to the
text after confirmation invalidates it automatically (hash comparison, no separate dirty flag to
forget to set) -- condition 4 re-checks the hash every round, not just whether `confirmed` was ever
set `True` once.

## Brownfield: one added section, not a second gate

On an existing codebase, the same Gate 2 confirm moment also covers the proposed touched-surface
file list (see `conformance-classification-guide.md`) -- one added, boundable section in the same
confirmation, not a fourth gate. Boundary and touched-surface are the same kind of scope decision at
two altitudes (concept vs. code), so they share one confirm moment.
