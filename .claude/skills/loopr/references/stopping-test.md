# The six-condition stopping test

Condensed from `docs/stopping-test-spec.md`. Read that file for full rubric wording and worked
detail; this preserves every substantive rule.

## Design approach

Two-layer check per condition: **structural** (deterministic, cheap, runs first -- a field exists,
is non-empty, passes a minimal shape check) then **judge** (LLM-as-judge, runs only if structural
passes; returns `{passed, reason, missing}`). A condition is TRUE only if both layers pass. If
either fails, the module asks a targeted follow-up aimed specifically at that condition -- never a
generic "anything else?" -- and re-checks both layers next round.

Two judge-call shapes:
- **Shape 1** (conditions 1, 2, 3): judge sees ONLY the field under test plus its rubric. No chat
  history, no other fields. Fully reproducible in isolation.
- **Shape 2** (conditions 5, 6): judge sees the field under test PLUS the specific cross-referenced
  fields its rubric names -- condition 5 additionally reads `problem_statement`,
  `acceptance_criteria`, `scope_edges`, `boundary`; condition 6 reads `acceptance_criteria`,
  `scope_edges`, `boundary`. Still scoped, still reproducible -- these two conditions are inherently
  relational and cannot be judged from the field alone.

Conditions are checked every round, not gated in strict 1→6 order -- a later answer can
opportunistically close an earlier gap. When multiple conditions are false, the module asks toward
the LOWEST-numbered false condition first.

## The six conditions

**1. Outcome-stated problem.** Structural: `problem_statement` non-empty; a solution-shaped
pre-filter runs but only ever sets an advisory flag passed to the judge -- it never hard-blocks.
Judge: does the statement describe a desired outcome (what becomes true, for whom), not prescribe a
solution as the primary subject? A stated solution is fine ONLY if subordinate to a named outcome.
**Anti-loop guard:** after 2 consecutive judge failures, the module surfaces the judge's last two
`reason` strings verbatim and asks the user to restate the outcome directly, rather than a third
open-ended question.

**2. ≥1 testable acceptance criterion.** Structural: at least one criterion is non-empty and
contains an observable predicate (a comparator/observable verb -- "returns", "shows", "matches",
etc; this keyword list is illustrative/untuned, a known live calibration gap). Judge: could a third
party check it by observation, without asking the builder for a judgment call? Pass condition is
**per-list**: as soon as ONE criterion clears both layers, the condition passes -- the rest can
remain weaker. This is deliberate design, not a bug.

**3. Named scope edges.** Structural: ≥1 edge tagged `out`/`deferred`, non-empty `item` and
`reason` (an edge with an empty reason auto-fails). Judge: is each edge specific enough that a
builder later knows unambiguously whether a new request falls inside or outside it? Rejects vague
edges ("nothing fancy") lacking a concrete boundary object (a feature, an integration, a threshold).

**4. Proposed-and-confirmed boundary.** Pure state-machine check, **no judge call** -- boundary
quality is judged once, at proposal time (Gate 2), not re-litigated here. Passes iff
`boundary.confirmed == True` against the CURRENT boundary text's hash (any edit invalidates prior
confirmation automatically). Escape hatch: an explicit `declined` (never inferred from silence) also
satisfies this condition; downstream audit then degrades to failure-mode-catalogue-only.

**5. Captured soft context.** See `context-md-guide.md` for the full split rule and the relevance
check. Explicit "none" is a valid pass if the user is asked directly and confirms a clean slate.

**6. No load-bearing unknown remains.** Every question raised is logged as an `OpenQuestion`
(`status`: open/resolved/deferred_non_load_bearing; `load_bearing`: bool|None). Judge (Shape 2):
given the current acceptance criteria/scope/boundary, would a plausible alternative answer require a
materially different value in any of those three? Structural: no open question has
`load_bearing == True`.

## The round cap -- termination guarantee

`max_rounds = 8` (configurable, calibratable, not an empirical optimum). **At the round cap:**

- **Original mechanism (condition 6):** every remaining `open` question -- load-bearing or not -- is
  force-resolved: the module drafts its own best-guess answer, states it plainly as a visible
  `Assumption` in the baby PRD's "Assumptions" section, sets `status = deferred_non_load_bearing`.
  Never silent -- the assumption-count parity guard asserts every force-resolution renders.
- **Generalized (2026-07-30 amendment, B2):** ANY of conditions 1-5 still false at the cap, not only
  condition 6's ledger, is force-resolved the same way -- a visible, tagged `Assumption` naming which
  condition it resolves, and that condition is marked satisfied-by-assumption rather than genuinely
  passed. This closed a real gap: a condition that never produces an `OpenQuestion` (condition 5 is
  the concrete case that surfaced it) previously had no termination guarantee at all and could run
  past the cap indefinitely.

The user sees every forced assumption at Gate 1 and can kick any of them back into a real question.

## Condition 5's relevance check (2026-07-30 amendment)

Condition 5's judge rubric now checks relevance FIRST, before the testable-vs-soft-context check:
does the note actually relate to the confirmed `problem_statement`/`acceptance_criteria`/
`scope_edges`/`boundary` for THIS build? Confidently-phrased or settled-sounding content with no
bearing on any of those four fields is REJECTED outright as off-topic, not routed anywhere. This
closed a real gap found in a live proof run: two deliberately off-topic notes (content from an
unrelated project) were originally caught only because the invoking judge reasoned outside the
literal rubric text -- a mechanical implementation would plausibly have passed either one. See
`context-md-guide.md` for the full rubric.
