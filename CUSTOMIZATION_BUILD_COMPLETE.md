# CUSTOMIZATION_BUILD_COMPLETE — loopr customization series (3 of 3 phases)

**Status:** All three phases built, reviewed, and approved. `CUSTOMIZATION_PHASE_3_SPEC.md` §0
confirms this is the final phase of the series (§0's amendment history: split from an original
"Phase 2 of 2" into three phases as real dependency boundaries were discovered — step10
customization, then step11/step12 customization from step10's output, then dispatch). There is no
Phase 4 in this series.

**Note on naming:** this file is deliberately `CUSTOMIZATION_BUILD_COMPLETE.md`, not
`BUILD_COMPLETE.md` — that name is already taken by loopr's own, unrelated base-module completion
marker at repo root (`88ec829`, 1-of-1 phase, a different build track entirely). Do not conflate
the two; a phase-discovery pass over this series must key off this file's own name.

**Approval commits:**
- Phase 1: `3e25f41` (`chore: Phase 1 review approved (LOOPR-CUSTOMIZATION)`)
- Phase 2: `0d5eb90` (`chore: Phase 2 review approved (LOOPR-CUSTOMIZATION)`) — **retroactive**, see
  "Disclosed process gap" below.
- Phase 3: `fa80008` (`chore: Phase 3 review approved (LOOPR-CUSTOMIZATION)`)

**GitHub SHA at completion:** `fa80008` (last commit before this file; this commit itself lands
immediately after).

---

## What was built

Three additive phases automating the step10/step11/step12 prompt-file workflow that was previously
hand-customized and hand-sequenced by the author:

- **Phase 1** (`src/loopr/customization/`, `models/customization.py`): `loopr customize --step 10`.
  Template discovery across three differently-conventioned templates, the two-layer (structural +
  judge) fidelity check, and native-subagent output (`.claude/agents/loopr-step10.md`, Opus-class).
- **Phase 2** (extends the same modules): `loopr customize --step 11/12`, gated on step10's actual
  execution artifacts existing on disk (not merely on step10 having been customized). Three new
  operation types beyond Phase 1's token fill — section deletion, conditional include-or-replace —
  and the corrected skeleton-subtraction fidelity rule. Outputs `.claude/agents/loopr-step11.md`
  (Sonnet, low effort) and `loopr-step12.md` (Sonnet, high effort).
- **Phase 3** (`src/loopr/dispatch/`, `models/dispatch.py`): `loopr dispatch` and its three
  companion commands (`dispatch-complete`, `dispatch-verify`, `dispatch-audit`). A pure, total,
  zero-LLM decision function over a ten-state finite state space that names which of the three
  already-generated subagents runs next, with the Opus-tier `loopr-step10` escalation boundary
  enforced at the type level (an unwarranted step10 decision is unconstructable, not merely
  disallowed by convention).

## Install / invocation

loopr is a CLI and importable Python library, not a hosted service — there is no deployment URL.

```
pip install -e .          # from the kaide-loop repo root (editable install)
loopr init                --repo <path-to-target-project> --mode {greenfield,brownfield}
loopr step                --state <path>/.loopr-state/state.json [--judge-response|--gate-response|--answer FILE]
loopr customize            --state <path>/.loopr-state/state.json --step {10,11,12} [--out DIR]
loopr dispatch             --state <path>/.loopr-state/state.json [--json] [--dry-run] [--remodernize]
loopr dispatch-complete    --state <path>/.loopr-state/state.json [--verdict {clean,minor,spec_violating}]
loopr dispatch-verify      --fixtures tests/fixtures/dispatch
loopr dispatch-audit       --log <path>/.loopr-state/dispatch-log.jsonl
loopr status / emit / replay   (unchanged since the base module)
```

## Final acceptance-suite results (CUSTOMIZATION_PHASE_3_SPEC.md §8, all ten criteria)

1. **State set enumerated and complete.** `DispatchStateId` has exactly ten members; `decide()`
   routes every one in the spec'd match order; the two architect-derived states (`S0_TERMINAL`,
   `S5_STEP11_DONE`) are labelled as such in the spec and in the fixture files. **PASS.**
2. **One fixture per state.** `tests/fixtures/dispatch/*.json` — ten files, each a data file (input
   state, two disk facts, pre-written `expected` block), verified 1:1 against `DispatchStateId`'s
   membership by `test_exactly_one_fixture_per_state`. **PASS.**
3. **`dispatch-verify` shown passing and failing.** Run directly against the real fixture
   directory: `10/10 fixture(s) matched`, exit 0. A fixture's `expected.target` was then
   deliberately corrupted and re-run: `MISMATCH s7_step12_clean.json: expected {...loopr-step10...}
   got {...loopr-step11...}`, exit 40. **PASS, both directions demonstrated live, not merely
   present in pytest.**
4. **All six user pre-written answers hold unchanged.** Diffed against the routing table directly:
   before step10 has run → `loopr-step10`; step10 done/clean → `loopr-step11`; step11 mid-round →
   `loopr-step11`; step12 clean → `loopr-step11`; step12 minor → `loopr-step11`; step12
   spec-violating → `loopr-step11` (not `loopr-step10`). **PASS.**
5. **Incoherent states HALT and dispatch nothing.** C1 and C3 triggered directly against a live
   throwaway state file: exit 40, `state.json` byte-unchanged, no `dispatch-log.jsonl` created, and
   `loopr-step10` absent from the rendered output. C2 (shadowed by C1 given `DispatchState`'s own
   validator — verdict-set implies `build_round >= 1`) confirmed independently correct via the
   executor's own `model_construct`-bypassed test rather than only via C1's superset coverage.
   **PASS.**
6. **§6.4 transition trace reproduces exactly.** Hand-run against a real throwaway repo via the
   actual CLI (`loopr dispatch` / `dispatch-complete` in sequence, not the pytest mirror of it):
   `(None,0,None)→S3→step11→(STEP_11,0,None)→S4(resume)→complete→(None,1,None)→S5→step12→...` through
   to the closing `(None,3,None)→S5→step12`, including the clearing rule (verdict reset on step11
   dispatch) and the completion-timed `build_round` increment. Zero step10 dispatches across the
   entire trace. **PASS.**
7. **Zero unwarranted step10 calls, both directions.** `dispatch-audit` against the trace's own log:
   `0 loopr-step10 dispatch(es) found, all carrying a valid warrant`, exit 0. A record with
   `target: "loopr-step10"`, `step10_warrant: null` was then planted into the log and re-audited:
   `HALT: 1 loopr-step10 dispatch(es) found with a missing or unrecognised warrant`, exit 40.
   **PASS.**
8. **`schema_version` migration behaves as designed.** `_CURRENT_SCHEMA_VERSION = 2` in both
   `models/interrogation.py` and `state/store.py`; no upgrade path exists in `store.py`; a
   well-formed v1 payload (real `InterrogationState`, `schema_version` forced to 1, `dispatch` field
   removed to match a genuine pre-Phase-3 payload) raises `StateVersionError`
   (`test_well_formed_v1_payload_raises_state_version_error`). **PASS.**
9. **Dogfood legibility check — the one a green suite cannot catch.** **UPDATE (2026-08-05): first
   real data point recorded — not the "unverified, no signal yet" state this entry originally
   described.** The first real `loopr dispatch --state .loopr-state/state.json` session against this
   project's own state did not reach the legibility question at all: it HALTed immediately on
   `find_step10_execution_artifacts`'s ambiguity check, correctly detecting that this repo carries two
   genuine phase-spec-shaped files (`PHASE_1_SPEC.md`, from loopr's own earlier core-module build, and
   `CUSTOMIZATION_PHASE_3_SPEC.md`, this Phase 3 series' real deliverable) that both legitimately claim
   provenance from `loopr-PRD.md`. That is a **genuine functional gap, not a legibility concern**:
   `customize` had gained a `--modernized-prd-path`/`--phase-1-spec-path` override mechanism for
   exactly this ambiguity in a prior fix (`bebdce3`), but `dispatch` called the same detector directly
   with no arguments and no way for the operator to resolve it. Fixed by threading the same override
   flags into `dispatch` (see `CUSTOMIZATION_PHASE_3_SPEC.md` §4.1's amendment note and §8 criterion
   9's own amendment). Re-run after the fix: `loopr dispatch --state .loopr-state/state.json --dry-run
   --phase-1-spec-path CUSTOMIZATION_PHASE_3_SPEC.md` produced a normal `DISPATCH`/`STATE`/`WHY`/
   `NOT-STEP10` block, re-verified by hand in a single look — **zero re-verifications beyond that one,
   well within the ≤ 2 threshold.** Legibility itself: **PASS**, on the one real run now on record.
   The broader signal — that a green fixture suite and hand-run trace genuinely did not catch this,
   exactly as this criterion's own framing warned — stands as the concrete justification for why this
   criterion existed as behavioural, not mechanical, in the first place.

   **Second amendment (2026-08-05, same dogfood session): a second, independent finding, more
   concerning in kind.** Re-running the exact acceptance check from the first amendment
   (`--phase-1-spec-path CUSTOMIZATION_PHASE_3_SPEC.md`, no `--build-complete-path`) did not HALT —
   it printed `s0_terminal`, "the build is complete," exit `50`. Correct verdict, wrong reason: `WHY`
   named `BUILD_COMPLETE.md` — the *base module's* unrelated, permanent completion marker, not this
   customization series' own `CUSTOMIZATION_BUILD_COMPLETE.md`. `cli.py` had hardcoded
   `(repo_root / "BUILD_COMPLETE.md").exists()`, with no relationship to the project the given
   `--state` file actually tracks. Where the first finding was a **loud refusal** (a HALT, impossible
   to miss), this one was a **silent, coincidentally-correct pass** — the dangerous direction (this
   series genuinely mid-build while the base module's unrelated marker still sat at repo root, which
   it does right now) was never exercised because both builds happened to finish at the same time.
   Nothing short of running the real command against the real repo state surfaced it; no fixture or
   unit test had reason to, since none modeled two completion markers coexisting. Fixed with a
   `--build-complete-path` override flag (default behaviour unchanged when omitted — criterion 4/6's
   existing fixtures and trace stay green untouched) and `render_human()`'s `WHY` line now naming
   whichever marker actually fired. Re-run with both flags:
   `loopr dispatch --state .loopr-state/state.json --dry-run --phase-1-spec-path
   CUSTOMIZATION_PHASE_3_SPEC.md --build-complete-path CUSTOMIZATION_BUILD_COMPLETE.md` — still
   `s0_terminal`, exit `50`, but `WHY` now correctly names `CUSTOMIZATION_BUILD_COMPLETE.md`.
   Legibility status unchanged (**PASS**, one re-verification), but the underlying fact this criterion
   was watching for — a green suite plus one real run genuinely surfacing something nothing else
   caught — now has two independent data points from a single dogfood session, not one.
10. **`mypy --strict` clean; full suite green.** `mypy --strict src/`: 0 errors, 45 source files.
    `pytest`: 358 passed, 2 skipped, 93% overall coverage (`dispatch/controller.py` 96%,
    `dispatch/log.py` / `dispatch/render.py` 100%). `test_no_paid_dependency.py` /
    `test_no_hardcoded_domain.py`: passing — runtime dependency set unchanged (`{"pydantic"}`).
    `tests/test_dispatch_boundary.py` (G1–G3, G5, G7, G8, executable): all passing. **PASS.**

**Net: 10 of 10 criteria independently verified and passing.** Criterion 9 moved from disclosed-
unverified to verified-pass on 2026-08-05, on the strength of the first real `loopr dispatch` session
against this project's own state — which incidentally surfaced and closed a genuine functional gap
(`dispatch` had no way to resolve the same step10-artifact ambiguity `customize` already had an
override flag for), not merely a legibility data point.

## Citation-gate summary

**N/A**, for two independent reasons stated in `CUSTOMIZATION_PHASE_3_SPEC.md`'s own PHASE
ADVANCEMENT reasoning, not merely restated here: first, the dispatch controller's design rests on a
closed-enum type-safety argument (`Step10Warrant`, `DispatchDecision`'s unconstructability), not a
literature claim that could later be falsified — there is nothing in this phase's own spec content
for a re-verification gate to check. Second, this is the final phase of the series, so the
"generate next spec" branch that would otherwise invoke the gate does not execute at all this
dispatch. The two arXiv citations grounding §6 B6's design (`arXiv:2604.12262` cascade-routing
escalation, `arXiv:2605.18796` confidence miscalibration, plus the disclosed `[UNVERIFIED]`-tagged
`arXiv:2604.17025`) were verified at Step 10 time (`docs/modernization_log.md`, 2026-08-04 entry) —
prior to this build, not re-litigated by this review.

## Disclosed process gap: retroactive Phase 2 approval

Phase 2 (`f39315b` implementation, `74eea57` review patch) never received its own
`chore: Phase 2 review approved (LOOPR-CUSTOMIZATION)` commit before Phase 3 implementation began —
a real deviation from this project's own phase-gating discipline (each phase is meant to be
reviewed and approved before the next begins). This was caught during Phase 3's review, precisely
because phase discovery found no intermediate approval commit to bound the diff against; the
Phase 3 review therefore necessarily read the full diff back to `3e25f41` (Phase 1's approval),
which meant Phase 2's code was read in full, not skipped over.

Phase 2 was verified against `CUSTOMIZATION_PHASE_2_SPEC.md` §5's seven acceptance criteria as part
of that same pass (all seven independently confirmed — see `0d5eb90`'s commit body for the
criterion-by-criterion detail) and approved retroactively, alongside Phase 3, rather than left
open. Recorded here rather than silently repaired so a future reader of this series' git history
understands why Phase 2's approval commit postdates Phase 3's implementation commit.

## Demo-recording handoff

**Not applicable.** loopr is a local CLI tool, not a hosted service with a UI to record — the
operational proof for this phase is criterion 9's real dogfooding run (above), now recorded rather
than pending, not a separate recorded demo of already-working behaviour.

## Ready for architect review

This document and the full commit history since `3e25f41` (Phase 1's approval, the start of this
series) are ready for review. All ten criteria are now independently verified and passing, including
criterion 9's real dogfooding run — which found and closed a genuine functional gap
(step10-artifact-ambiguity override flags, present on `customize` but missing from `dispatch`) rather
than the legibility failure it was originally watching for. No open items remain.
