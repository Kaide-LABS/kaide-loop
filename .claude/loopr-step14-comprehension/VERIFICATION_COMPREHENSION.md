# VERIFICATION_COMPREHENSION.md

**This is a functional verification run of the `loopr-step14` subagent prompt, dispatched manually
to prove the customized prompt works -- it is NOT an official phase closure the real driver loop
triggered, and it does NOT replace or update the real `COMPREHENSION.md` at repo root (which does
not exist yet, since this subagent has never run officially). No commit was made for this run,
per the dispatching instruction. Phase comprehended: `CUSTOMIZATION_PHASE_3_SPEC.md`, the final
phase of the already-shipped, already-approved LOOPR-CUSTOMIZATION series (approval commit
`fa80008`, "chore: Phase 3 review approved (LOOPR-CUSTOMIZATION)"), read as it stands now --
including the post-approval rework-stall-cap amendment (`4aa40c4`) that the spec file itself
documents inline as a same-series amendment, not a separate phase.

---

## 1. Plain-language walkthrough

kaide-loop is a command-line tool that makes an AI assistant ask better questions before writing
code, so a project gets built to spec instead of the assistant guessing at what "done" means. Once
a project's plan is written and the assistant is building it in rounds, someone has to decide, after
every round, which of three helpers should run next: the one that writes the plan, the one that
writes the code, or the one that checks the code. Until this piece was built, a person made that
choice by hand, every round.

This piece is that decision-maker. It looks at a small set of facts -- has the plan-writer already
run, is a code-writer or checker currently mid-task, and did the last check come back clean, come
back with a small fix already made, or come back saying the work doesn't match the plan -- and it
picks exactly one next step from those facts alone. It never guesses, and it never asks a second
opinion. If the facts don't add up to a clean picture (for example, a check happened but the plan
was never written), it refuses to guess and instead stops and says so, so a person can look.

There is one rule this piece protects above all others: it must almost never call in the most
expensive helper (the plan-writer) unless there is genuine evidence the plan hasn't been written yet,
or a person explicitly asked to redo the plan. Confusion is never allowed to be treated as a reason
to call the expensive helper "just in case" -- confusion is a reason to stop and ask a person instead.

A second, newer rule protects against a different failure: if the checker keeps rejecting the same
piece of work three times in a row, the tool stops routing it back for another attempt and instead
flags it as stuck, so a person decides what to do rather than the loop spinning forever.

## 2. Architecture walkthrough

The controller lives in `src/loopr/dispatch/` (package init at `src/loopr/dispatch/__init__.py`):

- `src/loopr/dispatch/controller.py` -- the pure decision logic. `check_coherence(state,
  artifacts_present)` runs first and returns a failure string (or `None`) for three cross-disk-truth
  checks a Pydantic validator cannot see on its own (artifacts absent combined with a built round, a
  recorded verdict, or an in-flight step11/step12). `decide(state, artifacts_present,
  build_complete_present)` is the actual routing table: a sequence of guard-clause `if`/`return`
  branches with no `else`, `default`, or `try`/`except` anywhere, ending in a `match` over
  `Step12Verdict` whose final arm is `typing.assert_never`. Also holds the three pure state-transition
  helpers: `apply_dispatch_transition`, `apply_remodernize_reset`, `apply_completion_transition`.
- `src/loopr/dispatch/log.py` -- the append-only JSONL audit trail. `append_decision()` writes one
  line per acted-on decision (never for a dry-run or a HALT), stamping `ts` itself so
  `DispatchDecision` stays byte-stable. `read_log()` reads it back (empty list if the file doesn't
  exist yet). `audit_step10_calls()` is the Opus-avoidance check: it walks the log for every
  `loopr-step10` record and flags any whose warrant is missing or not one of the two real
  `Step10Warrant` values.
- `src/loopr/dispatch/render.py` -- the human-facing and machine-facing output shapes.
  `render_human()` produces the fixed label-order block (`DISPATCH`/`STATE`/`WHY`/`NOT-STEP10` or
  `WARRANT`, plus a blank line and `RUN`), with distinct shapes for `S0_TERMINAL` and (added
  2026-08-06) `S10_REWORK_STALLED`, both of which omit the `RUN` line since neither names a target.
  `render_json()` is `DispatchDecision.model_dump_json(indent=2)` verbatim. `render_halt()` renders
  an incoherent-state HALT with the offending state dumped underneath.
- `src/loopr/models/dispatch.py` -- `DispatchState` (the three confirmed-boundary fields
  `active_step`, `build_round`, `last_step12_verdict`, plus `consecutive_spec_violating` added
  2026-08-06) and `DispatchDecision` (one routing outcome). Both carry `@model_validator(mode="after")`
  invariants that make the hard boundary structurally unconstructable rather than merely
  convention: a `DispatchDecision` naming `STEP_10` as target cannot exist without a
  `Step10Warrant`, and a non-`STEP_10` decision cannot exist without `step10_declined_because` set.
- `src/loopr/models/common.py` -- the four enums the controller runs on: `DispatchTarget` (three
  members, subagent names), `Step10Warrant` (two members, closed), `Step12Verdict` (three members),
  `DispatchStateId` (eleven members as of the rework-stall-cap amendment, including the two
  originally architect-derived states `S0_TERMINAL`/`S5_STEP11_DONE` and the 2026-08-06 addition
  `S10_REWORK_STALLED`).
- `src/loopr/models/interrogation.py` -- `InterrogationState.dispatch: DispatchState`, non-optional
  with `default_factory`; `schema_version` default bumped `1` -> `2`.
- `src/loopr/state/store.py` -- `_CURRENT_SCHEMA_VERSION` bumped to `2` in lockstep, no migration
  path (a v1 payload hard-fails with `StateVersionError`, confirmed by
  `tests/test_state_store.py::test_well_formed_v1_payload_raises_state_version_error`).
- `src/loopr/cli.py` -- four subcommands wired to the above: `cmd_dispatch` (calls
  `check_coherence` then `decide`, renders, appends to the log, saves state -- unless `--dry-run`),
  `cmd_dispatch_complete` (validates `--verdict` presence/absence by which step is completing, then
  calls `apply_completion_transition`), `cmd_dispatch_verify` (loads every `tests/fixtures/dispatch/
  *.json`, feeds each to `decide()`, diffs against the fixture's `expected` block), `cmd_dispatch_audit`
  (reads the log via `read_log`/`audit_step10_calls`, prints every `loopr-step10` record, HALTs on
  any invalid one). `cmd_dispatch` also owns two post-approval fixes read directly in this pass:
  threading `_resolve_step10_artifact_overrides` through to `find_step10_execution_artifacts` (so an
  operator can disambiguate two legitimate phase-spec files with `--phase-1-spec-path`), and resolving
  `build_complete_present` against a `--build-complete-path` override rather than a hardcoded
  `BUILD_COMPLETE.md` at repo root (this repo hosts two independent completion markers,
  `BUILD_COMPLETE.md` for the base module and `CUSTOMIZATION_BUILD_COMPLETE.md` for this series).
- `tests/fixtures/dispatch/*.json` -- eleven fixture files, one per `DispatchStateId` member,
  confirmed present by directory listing this run: `s0_terminal.json`, `s1_pre_step10.json`,
  `s2_step10_in_flight.json`, `s3_step10_done.json`, `s4_step11_in_flight.json`,
  `s5_step11_done.json`, `s6_step12_in_flight.json`, `s7_step12_clean.json`, `s8_step12_minor.json`,
  `s9_step12_spec_violating.json`, `s10_rework_stalled.json`.
- Tests, all present and read (in part) this run: `tests/test_dispatch_controller.py`,
  `tests/test_dispatch_fixtures.py`, `tests/test_dispatch_transitions.py`, `tests/test_dispatch_log.py`,
  `tests/test_dispatch_boundary.py`, `tests/test_dispatch_cli.py`.

## 3. Decisions and tradeoffs

- **`DispatchState` nested under `InterrogationState.dispatch`, not flat**, as the confirmed boundary's
  literal wording ("new fields on `InterrogationState`") would have allowed. Tradeoff: a small
  indirection (`state.dispatch.build_round` instead of `state.build_round`) traded for making the one
  conflation the boundary explicitly warned about -- `state.round` (interrogation counter) vs. the new
  build-round counter -- a type error instead of a naming discipline.
- **Two states added beyond the user's six pre-written answers** (`S0_TERMINAL`, `S5_STEP11_DONE`),
  later joined by a third (`S10_REWORK_STALLED`, 2026-08-06). Tradeoff: the user's confirmed set was
  incomplete (no terminal state, no state that ever reaches step12) rather than wrong, so the
  architect added exactly the missing coverage rather than leaving `decide()` non-total; the cost is
  that a third party reading only the six pre-written answers must also read the fixture files'
  own "derived" labels to see the full state space.
- **`--remodernize` resets `build_round` and `last_step12_verdict` to zero/`None`** rather than
  preserving them. Tradeoff: history at the state level is discarded (though the append-only dispatch
  log still retains every prior round), in exchange for `decide()` never having to reason about a
  round counter that describes a phase-1 spec no longer on disk.
- **`build_round` increments on step11 completion, not on dispatch.** Read directly in
  `apply_completion_transition` (`controller.py` line ~312-313) and in the SS6.3 worked trace
  (`CUSTOMIZATION_PHASE_3_SPEC.md` SS6.3). Tradeoff: this is the only thing that makes
  `S3_STEP10_DONE` (`build_round == 0`) and `S5_STEP11_DONE` (`build_round >= 1`) distinguishable at
  all; the cost is that `build_round` cannot answer "how many times has step11 been dispatched",
  only "how many rounds have finished."
- **`consecutive_spec_violating` is a separate counter from `build_round`, added 2026-08-06.** The
  original premise recorded in `loopr-PRD.md` section 15 ("build_round is persisted, so the data to
  build a cap already exists") was read this run as corrected in-place
  (`loopr-PRD.md` lines 831-837, `[FIXED 2026-08-06]`): `build_round` counts *total* rounds including
  reworks of the same phase, so it cannot by itself distinguish "3 rounds, 3 different phases" from
  "3 rounds, the same phase failing repeatedly." The tradeoff explicitly accepted: the new counter
  cannot be reset "on a new phase" directly, because the controller still does not and cannot know the
  phase number (a deliberate non-goal, SS9) -- it only learns a phase changed via the same
  `clean`/`minor` verdict that already resets the counter to 0, confirmed by reading
  `apply_completion_transition`'s `streak = ... if verdict == SPEC_VIOLATING else 0` line directly.
- **The rework-stall threshold (3) is a fixed constant, not a CLI flag**, per
  `_REWORK_STALL_THRESHOLD = 3` in `controller.py` (line 35) and confirmed as "a proposal, not assumed
  settled" / "v1 of this policy is a fixed constant" in
  `.claude/loopr-rework-cap/baby_prd.md` (lines 48, 62). Tradeoff: simplicity and a zero-argument
  `decide()` signature (preserving guard G5) traded against not letting an operator tune the
  threshold per project without a code change.
- **`Step12Verdict` stays three-valued (`clean`/`minor`/`spec_violating`) even though rows 8-10 of the
  routing table all currently target `loopr-step11` for `clean`/`minor`, and `spec_violating` splits
  into two outcomes depending on the streak counter.** Read directly: this is not dead enumeration --
  it is a disclosed, deliberate reconciliation with step12's own binary approve/reject language
  (`loopr-PRD.md` lines 844-850), kept for logging/falsifiability, not routing necessity.

## 4. Domain mechanics

One genuine domain figure in this phase's code: `_REWORK_STALL_THRESHOLD = 3`
(`src/loopr/dispatch/controller.py`, line 35) -- the number of consecutive `spec_violating` step12
verdicts on the same phase that the controller treats as "stuck" rather than "still iterating."

Source: **not** an external literature figure -- explicitly an operator-confirmed policy proposal,
cited in-code to `.claude/loopr-rework-cap/baby_prd.md`, which this run read directly and confirms
states: "This build's proposed threshold is 3... a fixed constant, not assumed settled" (line 48).
Marking this **[CITED, not empirical]** rather than [UNVERIFIED]: it is not a claim about the world
that could be independently checked against a source, it is a recorded human decision, and the code's
own docstring and the baby PRD agree on where that decision came from.

No other domain figures were introduced by this phase's code. The two arXiv citations grounding the
dispatch controller's *design rationale* (`arXiv:2604.12262` cascade-routing escalation,
`arXiv:2605.18796` confidence miscalibration) live in `loopr-PRD.md` section 6 B6, not in the shipped
`src/loopr/dispatch/` code itself -- they justify why a deterministic, zero-confidence-score
controller was chosen as an approach, not a runtime figure the code computes or depends on, so they
are out of scope for this section's per-figure citation requirement.

## 5. Honesty audit

Compared the current code in `src/loopr/dispatch/controller.py`, `models/dispatch.py`, `models/
common.py`, `dispatch/log.py`, `dispatch/render.py`, and `cli.py`'s four dispatch handlers against
`CUSTOMIZATION_PHASE_3_SPEC.md` section by section (SS3 schemas, SS4 CLI surface, SS6 implementation
logic, SS7 guards, SS8 acceptance criteria).

One real, concrete divergence found, already disclosed by the spec itself rather than hidden, but
worth restating precisely because it changes what "the Phase 3 spec" means as a grounding document:
**the spec file `CUSTOMIZATION_PHASE_3_SPEC.md` is not a static artifact frozen at the `fa80008`
approval commit -- it has been edited in place twice since approval** (by `4703148`, `c65a0d2`, and
`4aa40c4`, all tagged LOOPR-CUSTOMIZATION but none carrying their own "Phase N review approved"
commit). Concretely: SS4.1's `--modernized-prd-path`/`--phase-1-spec-path`/`--build-complete-path`
flags and SS6.2 row 11 (`S10_REWORK_STALLED`) do not appear in the spec version that was actually
reviewed and approved at `fa80008` -- they were added afterward, as amendments woven into the same
file rather than a new numbered phase. The shipped code matches the *current* spec text exactly on
every mechanical point checked (eleven `DispatchStateId` members with a fixture per state; the two
CLI amendments present in both `cli.py` and the spec's own amendment notes; the rework-stall
threshold and counter present in both `controller.py`/`models/dispatch.py` and the spec's row-11
addition) -- so there is no gap between code and the spec *as it reads today*. The gap is structural,
not behavioral: a reader relying on "Phase 3 was reviewed and approved at `fa80008`, so the spec at
that commit is the ground truth" would be reading a stale, incomplete picture of what actually
shipped, because the spec file itself moved after that approval without a corresponding new approval
commit. This is exactly the kind of thing loopr-PRD.md's own "Disclosed process gap" section already
flags for Phase 2 (a retroactive-approval gap) -- the Phase 3 series has a related but distinct gap:
not a missing approval, but post-approval spec edits under the same approved phase number.

## 6. Open items

- **Operator-configurable rework-stall threshold.** `.claude/loopr-rework-cap/baby_prd.md` explicitly
  scopes this out of v1 ("Making the threshold operator-configurable (a CLI flag) -- v1 of this policy
  is a fixed constant", line 62) -- not resolved by this phase's code, carried forward as a real,
  named non-goal rather than an oversight.
- **Cross-build-marker robustness beyond the two markers this repo happens to have.** The
  `--build-complete-path` override fix (amendment in `CUSTOMIZATION_PHASE_3_SPEC.md` SS6.2, code in
  `cli.py::cmd_dispatch`) was discovered and fixed via exactly one dogfood run against exactly one
  repo carrying exactly two completion markers; the fix generalizes structurally (any explicit path
  works), but no second dogfood run against a differently-shaped repo has verified it beyond this one
  instance -- noted in `CUSTOMIZATION_BUILD_COMPLETE.md` itself as a single data point, not repeated
  here as new information but carried forward as still genuinely open.
- **Traycer / Phase B remain entirely unbuilt and parked**, per `loopr-PRD.md` section 14 item 4 and
  section 15 -- not something this phase's code touches or resolves, but a standing open item any
  comprehension of the dispatch controller's *scope* should carry: the controller is explicitly a
  signpost, not a harness, and that boundary has not moved.
- **"Who writes `last_step12_verdict`, and how severity is graded" stays a soft-open revisit
  condition**, not a resolved-closed item: `loopr-PRD.md` section 15 (lines 838-843) records the
  git-marker-derivation alternative as considered and declined for Phase 3, "worth revisiting only if
  recorded verdicts are observed drifting from reality in practice" -- no such drift has been recorded
  as of this run, so the item stays open-but-inactive rather than closed.

## Phase Log

- **Phase 3 -- 2026-08-11 (VERIFICATION RUN, not an official phase closure).** First (and, per this
  run's own scope, only) COMPREHENSION.md-shaped pass written for `CUSTOMIZATION_PHASE_3_SPEC.md`.
  Summarizes the dispatch controller (`src/loopr/dispatch/controller.py`, `log.py`, `render.py`,
  `src/loopr/models/dispatch.py`) as it stands after the post-approval rework-stall-cap amendment
  (`4aa40c4`, `S10_REWORK_STALLED`, `consecutive_spec_violating`) and the two step10-artifact/
  build-complete-path CLI amendments (`4703148`, `c65a0d2`). This is the first entry in this log
  because no prior COMPREHENSION.md (real or verification) existed to append to.
