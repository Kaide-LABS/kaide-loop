# context.md guide

Condensed from `loopr-PRD.md` §A2 (the split rule) and condition 5's amended rubric
(`docs/stopping-test-spec.md`). Read those for full detail.

## The split rule

**It belongs in `context.md` if it would change how the build is judged but cannot be expressed as
a spec requirement.** Examples: "my boss cares about X," "avoid pattern Y for political reasons,"
"the real audience is Z, not the stated one." Cramming politics into the baby PRD corrupts the spec;
losing it produces a technically-correct build that fails the real test anyway.

The test, applied as a judge call (Shape 2 -- the note plus `problem_statement`,
`acceptance_criteria`, `scope_edges`, `boundary`), in order:

1. **Relevance, first.** Does this note actually relate to the CONFIRMED problem statement,
   acceptance criteria, scope edges, or boundary for THIS build? If it is well-formed, confidently
   phrased, or even stated as settled fact, but has no bearing on any of those four fields, **reject
   it outright as off-topic** -- do not route it anywhere. Confident phrasing is not evidence of
   relevance. (Amended 2026-07-30 after a live proof run found the original rubric had no
   topical-relevance check at all -- see below.)
2. **Testable vs. soft, only for notes that pass relevance.** Does the note change how the finished
   build would be JUDGED without being expressible as a testable spec requirement? If it IS
   expressible as an existing or new acceptance criterion, it belongs there instead -- flagged
   **misplaced**, not failed outright. A misplaced note is folded into `acceptance_criteria` and
   removed from `context_notes` -- relocated, not duplicated.

Three outcomes per note: **genuine** (passes both checks -- rendered in `context.md`), **misplaced**
(relocated to the acceptance criteria list, removed from `context.md`), or **rejected** (off-topic --
stays in the audit log for traceability, but never rendered anywhere; it has no home).

## The explicit-none pass

Condition 5 must ask directly ("any boss-said/political/watch-out constraints, or is this a clean
slate?") and accept a real "none" as a valid pass, recorded as a sentinel note
(`"user confirmed no soft context"`). Never infer "none" from silence -- forcing a fishing expedition
on a genuinely clean-slate project is worse than accepting a real "none."

## Why the relevance check was added

A live brownfield proof run deliberately tested this: two off-topic notes (content copied from an
unrelated project, one phrased as settled fact -- "Confirmed... this is confirmed, not open") were
submitted as condition-5 answers. Both were correctly rejected, but only because the invoking judge
reasoned outside the rubric's literal text at the time ("does this relate to THIS build at all?" was
not actually part of the rubric). A more mechanical implementation would plausibly have accepted
either one, since neither failed the old testable-vs-soft distinction -- they simply had nothing to
do with the build, which the old rubric never checked. The relevance check closes that gap.

## Continuity across iterations

See `continuity-model.md` for how `context.md` stays readable (layered structure, supersession
pointers) as a project accumulates repeat loopr runs.
