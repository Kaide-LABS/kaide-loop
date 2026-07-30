# Brownfield proof run — FINDINGS

Target project: kaide-loop itself (`--repo "C:\Users\hp\kaide-loop"`, `--mode brownfield`). Real,
interactive interrogation run in chat; every judge verdict was rendered honestly per rubric by the
invoking agent, not pre-scripted. This run stands in for both the scope-creep-catch signal the
greenfield run couldn't demonstrate AND the required brownfield classification-quality proof
(§8.4), per instruction.

**Two blocking bugs were found and fixed before this run could even start** (see the two commits
immediately preceding this proof): the C5 misplaced-note duplication (found during the greenfield
run) and a brownfield `cmd_init` crash (`InterrogationState(mode=BROWNFIELD, ...)` was constructed
before `.brownfield` was set, tripping `check_mode_coherent` at construction — brownfield mode could
not be initialized via the CLI at all until fixed). Both are committed, tested, and green.

## Round / gate / judge-call summary

- **11 rounds used against a `max_rounds` of 8** — the round cap was reached and passed without
  triggering force-resolution (see Finding 3 below).
- **18 judge calls total**: 3 condition calls (C1×2, C2×2, C3×1) + 1 `bf_relevance` + 8 `bf_classify`
  + 4 `c5_soft_context` (one misplaced, two rejected-off-topic, one genuine pass).
- **Gate 2 (boundary)** confirmed once, no re-fire needed. **Gate 3 correctly never fired** — all 8
  classified patterns were CONFORM, zero CONFLICTs, so `gate_3_required` never became `True`. This is
  a real, live demonstration of acceptance criterion B-3 (graceful degradation when no conflict
  exists), not merely a fixture test. **Gate 1** fired last, confirmed on the first showing.
- **Zero assumptions, zero unresolved open questions** — every condition converged on genuine
  judge/structural passes, never a forced guess.

## Touched-surface discovery — sensible for a real change

Stage 1 (keyword/dependency prefilter) cast the entire repo as candidates (deliberately wide, per
spec). Stage 2 (`bf_relevance` judge call) selected exactly 8 files: `checks/structural.py`,
`checks/conditions.py`, `interrogation/questions.py`, `rubrics/texts.py`,
`models/interrogation.py`, `tests/test_structural_checks.py`, `tests/test_conditions.py`, and
`docs/stopping-test-spec.md`. This is the correct surface for "add a keyword-pattern vagueness check
to C2" — nothing from Docker, brownfield, gates, judge-envelope, or unrelated tests was pulled in.
Selection was not padded for safety, as instructed.

## Pattern classification quality — the real signal (§8.4, D-1/D-2/D-3)

**8 patterns discovered, all 8 classified CONFORM by the module's judge calls. I agreed with every
single one**, having independently reasoned through each: `@dataclass` (internal result types,
distinct from pydantic models used for validated state), `model_validator` (backs the load-bearing
two-layer invariant and other model coherence checks), `from __future__ import annotations`
(universal boilerplate), and five internal-module imports (`dataclasses`, `judge.envelope`,
`models.common`, `models.interrogation`, `models.judge`) that any new code touching this surface
would need too. None showed cruft signals (all single-file/single-day-old, single-author — expected
for a young solo project, not itself a red flag); none conflicted with the stated intent.

**Honest caveat on what this run does and doesn't prove:** every evidence bundle in this run had
`occurrence_count` at or barely above the minimum threshold (3–7), all `git_last_touched_days_ago=1`
(the whole repo is freshly modified), single-author, no deprecation markers. This touched surface
never exercised the harder discriminations the classifier exists for — no stale-but-stable code, no
deprecation-marked "on-hold" debt, no genuinely conflicting pattern, no AMBIGUOUS case. **All 8 were
easy CONFORM calls with no real cruft signal present.** This run demonstrates the classifier doesn't
false-positive on an easy case, not that it can tell a real convention from real cruft under
ambiguity — that would need a touched surface with actual staleness/deprecation/conflict signal
present, which this repo (young, actively developed, single author) cannot supply. Per §8.4's own
framing, this is exactly the kind of thing to report plainly rather than oversell: D-3's "which
signals actually carried the verdict" answer here is centrality and recency, not the harder signals
(staleness-with-qualifier, deprecation-as-ambiguity-trigger, commit-ownership-concentration) that the
2026-07-28 research pass specifically added.

## The deliberate stress test — smuggling attempt, caught twice, by agent judgment not mechanism

Two smuggling attempts were made and both were caught:

1. A note framed as loopr's own C5 answer that was actually the greenfield meeting-bot project's
   soft context (Islamic-lecture tonal register, "hukm," "MSA," audience framing) — entirely
   unrelated to this build's problem statement or boundary.
2. A second attempt, resubmitted with confident, boundary-sounding phrasing ("Confirmed... this is
   confirmed, not open") about STT/Zoom scope — again, content from the other project, not this one.

**Both were rejected — but not by any mechanism in loopr itself.** The C5 rubric, as written, asks
only "does this note change how the build is judged without being testable spec content" — it has
**no check for whether the note is even about the stated problem**. Nothing in `ALLOWED_INPUTS`,
`check_c5_soft_context`, or the rubric text tests topical relevance to `problem_statement`,
`acceptance_criteria`, or `boundary`. I caught both attempts only because I, as the invoking judge,
reasoned outside the literal rubric text ("this has zero connection to the confirmed problem for
THIS build") — a less careful invoking agent, or one instructed to be lenient, would very plausibly
have rubber-stamped either note as "a valid watch-out" on a literal reading of the rubric. **This is
a real gap, not a near-miss:** the mechanism relies entirely on the invoking agent's own scrutiny to
catch domain/scope leakage into C5; it has no structural backstop. This is precisely the "Boundary
over-fit to examples" / G-3 / G-12 failure mode (`loopr-PRD.md` §10), just demonstrated on loopr's
own build rather than a downstream project.

The genuine, on-topic soft-context answer (heightened review standard given blast radius) passed on
the very first non-smuggled wording — the fallback clean-slate answer was never needed.

## Confirmed bugs found live during this run

**Finding 1 (fixed before this run started): C5 misplaced-note duplication.** Already committed
(`f461c1d`). Verified during this run: the misplaced note from this run's own C5 exchange did NOT
duplicate into `context.md` — confirms the fix works.

**Finding 2 (fixed before this run started): brownfield `cmd_init` crash.** Already committed
(`cff3057`). Without this fix, this proof run could not have started at all.

**Finding 3 (new, confirmed, NOT fixed — found live in this run): a preloaded judge/gate/question
response can be silently discarded if a brownfield precondition item (relevance or classification)
is still outstanding.** `step()`'s brownfield-precondition block (`interrogation/loop.py` lines
159–198) runs unconditionally at the top of every invocation, before the condition-evaluation
section. `ResumingJudgeClient` only consumes its one preloaded response if it happens to match the
very first `judge.ask()` call made inside that invocation. Concretely: I submitted an honest
`misplaced=true` response to a pending C5 request twice, and both times it was silently thrown away
— never applied, never logged in `judge_log`, no error, no warning — because the classify loop
found a still-unclassified brownfield pattern and asked about that instead. The invoking agent has no
way to detect this without independently diffing `judge_log`. It only resolved once every one of the
8 discovered patterns had been classified (confirmed by direct inspection of `state.json` at each
step — see the round-by-round trace in this conversation). **This is systemic, not a one-off**: it
will recur on any brownfield run where a condition-level judge call becomes pending while brownfield
patterns remain unclassified, which given the classify loop processes exactly one pattern per
invocation (§6.7.3, "never batched," intentional), is the common case, not an edge case.

**Finding 4 (new, confirmed, NOT fixed — found live in this run, and worse than Finding 3 because it
lands in a shipped artifact): rejected C5 notes are never removed from `context_notes` and get
rendered into the final `context.md` as if they were valid, accepted soft context.**
`artifacts/context_md.py`'s `render_context_md` iterates `state.context_notes` unconditionally, with
no filter on judge outcome. This run proves it concretely: `proofs/brownfield/context.md` (committed
alongside this findings file) contains, verbatim, both explicitly-rejected smuggled notes (the
hukm/register one appears twice — it was resubmitted once — and the STT/Zoom one once) rendered
under "Soft context" with no marking that they were rejected as off-topic. A downstream reader of
`context.md` cannot tell an accepted watch-out from one loopr's own judge explicitly threw out. This
is a real defect, distinct from and more consequential than Finding 1 (which only affected the
misplaced case and is fixed) — a rejected note should never reach the emitted artifact at all.

**Finding 5 (new, confirmed, NOT fixed): the round cap does not actually cap the whole
interrogation.** `_force_resolve_round_cap` (§6.8) only force-resolves `OpenQuestion` entries — it
has no effect on a condition like C5 that keeps failing without ever creating an `OpenQuestion`. This
run reached round 11 against `max_rounds=8` with no force-resolution triggered, because C5's repeated
failures never produced an open question for the cap to act on. Per `docs/stopping-test-spec.md`
§Condition 6B, this is consistent with how the round cap was specified (it's explicitly a backstop
for condition 6's unresolved-question ledger) — but it means `max_rounds=8` is *not* a hard ceiling
on interrogation length in general, contrary to what a plain reading of "round cap" suggests. Worth
being explicit about in any user-facing documentation of the six-condition test.

## Acceptance signals (loopr-PRD.md §3)

**C-1, TL;DR moment:** Worked — confirmed on the first showing, no correction needed, faithfully
carried the actual scoped change (C2-only, keyword-pattern, no auto-rewrite).

**C-2, scope-creep catch — genuinely demonstrated this time, unlike the greenfield run.** Two
distinct smuggling attempts were made and caught. This is the stronger form of the signal the
greenfield run couldn't produce. But per Finding 3-adjacent honesty: the catch came from agent
judgment, not from a mechanism inside loopr — worth weighing that into how much credit this signal
earns the module itself versus the invoking agent's discipline.

**C-3, no-rework readiness:** The baby PRD and ledger look buildable and honestly scoped. However,
this run surfaced two real defects (Findings 3 and 4) in loopr's *own* engine that a build against
this spec would inherit silently if not caught here — which is itself the intended payoff of running
a real proof rather than a fixture: it found genuine gaps a synthetic/scripted run would not have
surfaced (the fixture-based test suite never exercises the interleaving of a pending non-brownfield
judge call with an outstanding brownfield classification, and never emits `context.md` after a
rejected — not misplaced — C5 note).

## Recommendation

Do not treat this phase as clean. Findings 3, 4, and 5 are real, reproducible, and independent of the
C2 vagueness-detection feature this run was ostensibly about — they're pre-existing defects in the
brownfield/round-cap machinery, surfaced only because this was a genuine, non-scripted, brownfield
run against a real repo. Recommend fixing Findings 3 and 4 before any brownfield acceptance claim is
made about Phase 1, given both compromise the trustworthiness of what gets logged and what gets
shipped into `context.md`. Finding 5 is more a documentation/expectation gap than a functional bug,
but still worth a one-line clarification wherever `max_rounds` is described.
