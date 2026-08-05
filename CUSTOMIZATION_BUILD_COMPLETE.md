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
9. **Dogfood legibility check — the one a green suite cannot catch.** **UNVERIFIED, disclosed
   explicitly, not marked pass or fail.** Confirmed directly with the operator: no real
   `loopr dispatch` session has occurred yet in this project — every step10/11/12 invocation up to
   and including this review was chosen manually by a human/architect session, which is exactly the
   manual step this phase exists to replace. There is therefore no genuine re-verification-count
   signal to report, positive or negative, and none was fabricated. The hand-run trace above
   (criterion 6) and the golden-output shape tests (≤ 6 lines, fixed label order, `NOT-STEP10`/
   `WARRANT` present on every relevant decision) are the strongest synthetic proxies available, and
   both passed — but neither substitutes for what criterion 9 actually measures, which is the
   operator's own re-verification behaviour under real use. **Recorded as an open item, pending the
   first real dispatch session** — if that session shows re-verification more than once or twice,
   the fix is `render_human()`'s shape (§4.3), not the routing logic, per the spec's own remedy
   clause.
10. **`mypy --strict` clean; full suite green.** `mypy --strict src/`: 0 errors, 45 source files.
    `pytest`: 358 passed, 2 skipped, 93% overall coverage (`dispatch/controller.py` 96%,
    `dispatch/log.py` / `dispatch/render.py` 100%). `test_no_paid_dependency.py` /
    `test_no_hardcoded_domain.py`: passing — runtime dependency set unchanged (`{"pydantic"}`).
    `tests/test_dispatch_boundary.py` (G1–G3, G5, G7, G8, executable): all passing. **PASS.**

**Net: 9 of 10 criteria independently verified and passing; criterion 9 disclosed as unverified by
design, not silently dropped and not fabricated.**

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
operational proof for this phase is criterion 9's real dogfooding run (above), which is the thing
still pending, not a separate recorded demo of already-working behaviour.

## Ready for architect review

This document and the full commit history since `3e25f41` (Phase 1's approval, the start of this
series) are ready for review. The one open item is criterion 9: the first real `loopr dispatch`
session against a genuine multi-phase build should be watched for how many times the operator
re-verifies the printed decision by hand. More than once or twice per the spec's own threshold is a
fail on `render_human()`'s shape specifically, not on the routing logic this review already
independently verified clean.
