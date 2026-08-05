# CUSTOMIZATION_PHASE_3_SPEC.md — Dispatch Controller (Phase 3 of 3)

Built FROM the **modernised** `loopr-PRD.md` (re-modernized 2026-08-04 — see its `## MODERNIZATION
CHANGELOG` Entry 3 and the new section 6 B6), and from the confirmed baby PRD produced by the live
`/loopr` brownfield run recorded in `.claude/loopr/` (`baby_prd.md`, `context.md`,
`conformance-ledger.md`; round 5, brownfield).

Third and final phase of the customization series (`CUSTOMIZATION_PHASE_1_SPEC.md` §0, as amended
2026-08-03). Namespaced per the marker decision in `SKILL_PHASE_1_SPEC.md`: `PHASE_1_SPEC.md`,
`BUILD_COMPLETE.md`, and `SKILL_PHASE_1_SPEC.md` stay untouched.

Written architect-side, same as Phases 1 and 2 — loopr's own Phase 1 module does not generate this
tier of granular blueprint.

---

## §0 Phase Plan Header

**Phase 3 of 3.** Deliverable: `loopr dispatch` and its three companion commands — a deterministic
controller that reads the current run's state and names which of the three already-generated
subagents (`loopr-step10`, `loopr-step11`, `loopr-step12`) runs next, plus the fixture suite and
log audit that prove it, both shipped *as part of this phase* rather than after it.

This closes the question `CUSTOMIZATION_PHASE_1_SPEC.md` §0 flagged forward on 2026-08-03
("once step10/11/12 dispatch as subagents, 'sequencing' plausibly means choosing *which subagent to
dispatch*") and that §7.2 restated. The answer this phase gives: **yes, and nothing more than that.**

### 0.1 Confirmed source of truth (verbatim from the run)

**Problem statement / TL;DR (verbatim):** "When Phase 3 is done, the loop deterministically knows
which subagent to dispatch at every point in the sequence -- executor, reviewer, or Step 10 -- with
no ambiguity and no unnecessary escalation to a more expensive subagent than the step requires.
That's true for me, running this loop, not a hypothetical future user."

**Confirmed boundary (verbatim, `.claude/loopr/baby_prd.md`):** "Phase 3 builds a controller that
reads the current state of a loopr customization run -- has Step 10 executed yet, is Step 11
mid-round, did Step 12 return clean or flag an issue and at what severity -- and deterministically
decides which of the three existing subagents (loopr-step10, loopr-step11, loopr-step12) to dispatch
next. The decision must be unambiguous for any given state, and must never dispatch a more expensive
subagent (Step 10, Opus-tier) than the current state actually warrants."

**Soft context (verbatim, `.claude/loopr/context.md`):** "A technically-correct dispatcher that's slow
to write is still a failure here, because this phase exists to remove a manual step I'm doing myself
right now. If Phase 3 ships correct dispatch logic but it takes me longer to read its output and
trust it than it would to just pick the next subagent myself, the phase has failed on its actual
purpose even though every fixture passes. … if I catch myself re-verifying the controller's choice by
hand more than once or twice while dogfooding it, that's the failure signal."

That last paragraph is **not** decoration. It is why §4.3 (output rendering) is a spec'd requirement
with a fixed shape, and why §8 criterion 9 exists. A green fixture suite cannot detect this failure.

### 0.2 Disclosed deviations from the confirmed boundary

Three, all additive-or-shape rather than scope changes, stated here rather than buried:

1. **The three new fields are nested under `InterrogationState.dispatch`, not flat on
   `InterrogationState`.** The boundary says "New in-scope state fields on `InterrogationState`". The
   field *set* is exactly the three it names — `active_step`, `build_round`, `last_step12_verdict`;
   nothing added, nothing dropped. Nesting follows the precedent every other subsystem already uses
   (`brownfield`, `customization`, `gates`, `judge_log`) and structurally prevents the one conflation
   the boundary explicitly warns about: `state.round` (the six-condition interrogation counter) versus
   `state.dispatch.build_round` (the step11/12 cycle count) can no longer be typed interchangeably.
2. **Two states are added to the enumerated set** (§6.2). The confirmed acceptance criteria list six
   states and require the set be "finite, listable — list it explicitly." The listed six contain no
   state that ever dispatches step12, and no terminal state, so the set as listed is incomplete rather
   than wrong. `S5_STEP11_DONE` (→ step12) and `S0_TERMINAL` (→ nothing) are added. **Every one of the
   user's six pre-written answers is preserved unchanged**; the two additions are flagged as
   architect-derived in §6.2's table and in the fixture files, so the pre-written answers stay
   distinguishable from the derived ones when a third party reads the results.
3. **`--remodernize` resets `build_round` to 0 and `last_step12_verdict` to `None`.** Re-modernization
   rewrites `PHASE_1_SPEC.md`, so the build restarts from phase 1 and the prior round counter and
   verdict describe a plan that no longer exists. History is not lost — the append-only dispatch log
   retains every prior round. Stated because it is a behavioural choice the boundary does not make.

---

## §1 Files added or modified

| File | Change |
|---|---|
| `src/loopr/models/common.py` | Add four enums (§3.1): `DispatchTarget`, `Step10Warrant`, `Step12Verdict`, `DispatchStateId`. Repo convention — **every** enum in this project lives in `common.py`; do not colocate them with the models. |
| `src/loopr/models/dispatch.py` | **New.** `DispatchState`, `DispatchDecision` (§3.2, §3.3). |
| `src/loopr/models/interrogation.py` | Add `dispatch: DispatchState = Field(default_factory=DispatchState)` — **non-optional, always present**, unlike `customization`/`brownfield` (§3.2 rationale). Bump `schema_version` default `1` → `2`. Import + `model_rebuild()` at the file foot, matching the existing deferred-import pattern. |
| `src/loopr/state/store.py` | `_CURRENT_SCHEMA_VERSION = 1` → `2`. **No migration path** (§5). |
| `src/loopr/dispatch/__init__.py` | **New.** |
| `src/loopr/dispatch/controller.py` | **New.** `check_coherence()` + `decide()` — the pure total function. **No imports of anything that performs I/O beyond `pathlib`, and no judge/LLM import of any kind** (§7 guard G5). |
| `src/loopr/dispatch/log.py` | **New.** Append-only JSONL dispatch log: `append_decision()`, `read_log()`, `audit_step10_calls()`. |
| `src/loopr/dispatch/render.py` | **New.** `render_human(decision)` / `render_json(decision)` — the legibility surface (§4.3). Separate module so the output shape is unit-testable without the CLI. |
| `src/loopr/cli.py` | Add four subcommands: `dispatch`, `dispatch-complete`, `dispatch-verify`, `dispatch-audit` (§4). Flat subcommands, matching `init`/`step`/`status`/`emit`/`replay`/`customize`. |
| `.claude/skills/loopr/SKILL.md` | Add the dispatch step to the orchestration loop; keep under the ~5000-word budget. |
| `tests/fixtures/dispatch/*.json` | **New.** One file per enumerated state (§8 criterion 2). Data, not code. |
| `tests/test_dispatch_controller.py` | **New.** Unit tests for `decide()` and `check_coherence()`. |
| `tests/test_dispatch_fixtures.py` | **New.** Parametrizes over `tests/fixtures/dispatch/`. |
| `tests/test_dispatch_transitions.py` | **New.** The full round-trip trace (§6.4) asserted step by step. |
| `tests/test_dispatch_log.py` | **New.** Log append/read/audit, including a planted unwarranted record that the audit must catch. |
| `tests/test_dispatch_boundary.py` | **New.** The executable form of §7's hard-boundary grep (guard G1). |
| `tests/test_dispatch_cli.py` | **New.** Exit codes, output shape, state mutation. |
| `tests/test_state_store.py` | **Modified.** Existing assertions pin `schema_version: 1`; update to 2 and add a test that a v1 file now raises `StateVersionError` (§5). |

**Conform to** (from `.claude/loopr/conformance-ledger.md`, all 17 CONFORM, zero DO_NOT_REPLICATE —
there is no cruft to avoid on this touched surface): `from __future__ import annotations` in every new
module (universal, 15/15 files — mandated, `loopr-MIGRATION.md` §8); `@model_validator` for invariants
on new Pydantic models (the ledger names this as "directly applicable, load-bearing" for exactly these
three fields); `@property` for read-only accessors; `@pytest.fixture` for shared test setup;
`ConfigDict(extra="forbid")` inherited from `LooprBase`.

---

## §2 Dependencies

**None new.** The controller is pure stdlib plus `pydantic` (already the sole runtime dependency) plus
`pathlib` for the two disk checks. Adding anything breaches the single-runtime-dependency invariant
that `tests/test_no_paid_dependency.py` mechanically enforces.

Pinned versions, as reconciled in Deliverable A (`loopr-PRD.md` §8a, re-verified 2026-08-04):

| Component | Pin | Latest | Installed |
|---|---|---|---|
| Python | `>=3.14` | 3.14.4 | 3.14.4 |
| Pydantic | `>=2.13,<3` | 2.13.4 | 2.13.3 (satisfies the floor) |
| mypy | `>=2.3,<3` | 2.3.0 | 2.3.0 |

**No model string appears anywhere in this phase's code.** The dispatcher names subagent *names*
(`loopr-step10`); the model and effort pins live where they already live — module-level constants in
`customization/customize.py`, using coarse tier keywords (`opus` / `sonnet`), which is what real
shipped agent definitions use. Do not "improve" this by writing a dated model ID.

---

## §3 Pydantic schemas

Every model inherits `LooprBase`, which sets `extra="forbid"`, `validate_assignment=True`,
`str_strip_whitespace=True` once for the whole project. Do not re-declare `model_config`.

### 3.1 Enums (all in `models/common.py`)

```python
class DispatchTarget(str, Enum):
    """The three subagents Phase 3 routes between. Values are the literal subagent NAMES, matching
    STEP10_SUBAGENT_NAME / STEP11_SUBAGENT_NAME / STEP12_SUBAGENT_NAME in customization/customize.py
    so a decision is directly usable as a dispatch argument with no translation layer.

    No fourth member. Adding one is adding a subagent type, which the confirmed scope edge
    (.claude/loopr/baby_prd.md, scope edge 4) puts out of scope for this phase -- including the
    auditor tier and anything from docs/loopr-v2-agent-archetypes.md."""

    STEP_10 = "loopr-step10"
    STEP_11 = "loopr-step11"
    STEP_12 = "loopr-step12"


class Step10Warrant(str, Enum):
    """The ONLY two circumstances under which the Opus-tier step10 subagent may be dispatched
    (loopr-PRD.md section 6 B6, PROJECT HARD BOUNDARY).

    This enum is CLOSED. A third member meaning uncertainty, defaulting, safety, or 'when in doubt'
    is the exact regression the confirmed acceptance criteria name as most load-bearing -- adding one
    would make an unwarranted escalation representable, and representable is the first step to
    reachable. If a future state cannot be classified into one of these two, the correct behaviour is
    HALT (exit_codes.HALT), never a step10 dispatch."""

    GREENFIELD_NO_ARTIFACTS = "greenfield_no_artifacts"
    """step10's execution artifacts do not exist on disk. Live disk truth, checked every time via
    templates.find_step10_execution_artifacts() -- never cached into a step10_done state field that
    could drift out of sync with the real artifact (confirmed boundary: 'one source of truth for that
    fact, not two')."""

    EXPLICIT_REMODERNIZATION = "explicit_remodernization"
    """The operator explicitly asked for re-modernization (`loopr dispatch --remodernize`). An
    operator act, never an inference."""


class Step12Verdict(str, Enum):
    """The severity distinction the confirmed acceptance criteria require. Three-valued by design.

    Note the disclosed tension with step_12's own template, which says approval is 'either clean or
    not' with 'no approve with minor follow-ups' -- these reconcile rather than conflict (loopr-PRD.md
    section 15): MINOR means step12 APPROVED the phase after patching the issue itself, which the
    template's own THE FIX section already describes. MINOR and CLEAN route identically; the
    distinction is a logging and falsifiability requirement, not a routing one. Do not 'simplify' it
    away -- the acceptance criteria require the two to be separately enumerable."""

    CLEAN = "clean"
    MINOR = "minor"
    SPEC_VIOLATING = "spec_violating"


class DispatchStateId(str, Enum):
    """The complete, finite set of states the controller can be in (CUSTOMIZATION_PHASE_3_SPEC.md
    section 6.2). Exhaustive by construction: decide() matches every member and the final branch is
    guarded by typing.assert_never, so adding a member without a routing rule is a mypy --strict
    error rather than a runtime surprise."""

    S0_TERMINAL = "s0_terminal"
    S1_PRE_STEP10 = "s1_pre_step10"
    S2_STEP10_IN_FLIGHT = "s2_step10_in_flight"
    S3_STEP10_DONE = "s3_step10_done"
    S4_STEP11_IN_FLIGHT = "s4_step11_in_flight"
    S5_STEP11_DONE = "s5_step11_done"
    S6_STEP12_IN_FLIGHT = "s6_step12_in_flight"
    S7_STEP12_CLEAN = "s7_step12_clean"
    S8_STEP12_MINOR = "s8_step12_minor"
    S9_STEP12_SPEC_VIOLATING = "s9_step12_spec_violating"
```

### 3.2 `DispatchState` (`models/dispatch.py`)

```python
class DispatchState(LooprBase):
    """The three new state fields named by the confirmed boundary, and only those three.

    Hung off InterrogationState as a NON-OPTIONAL field with default_factory, unlike
    `customization` / `brownfield` which are `| None`. Deliberate: an absent-vs-default distinction
    here would create a fourth implicit state ('dispatch never started') that means exactly the same
    thing as the default instance, and decide() must be TOTAL. One representation, not two."""

    active_step: CustomizationStep | None = None
    """Which of step10/11/12 is currently in progress, or None. Set when a dispatch is issued;
    cleared by `loopr dispatch-complete`. Reuses the existing CustomizationStep enum -- do NOT
    introduce a parallel three-member enum for the same three steps."""

    build_round: int = Field(default=0, ge=0)
    """The step11/step12 cycle count. DISTINCT from InterrogationState.round, the six-condition
    interrogation counter, and MUST NOT be conflated with it (confirmed boundary, stated explicitly).
    Nesting under `.dispatch` is what makes that confusion structurally hard rather than merely
    discouraged. Incremented when step11 COMPLETES (not when it is dispatched) -- see section 6.3;
    that timing is what makes S3 and S5 distinguishable."""

    last_step12_verdict: Step12Verdict | None = None
    """The most recent step12 outcome, or None if step12 has not returned since the last step11
    dispatch. CLEARED when step11 is dispatched (section 6.3) -- without that clearing rule a stale
    verdict survives into the next round and S5 becomes indistinguishable from S7/S8/S9."""

    @model_validator(mode="after")
    def check_field_coherence(self) -> "DispatchState":
        if self.last_step12_verdict is not None and self.build_round < 1:
            raise ValueError(
                "last_step12_verdict is only meaningful once step11 has completed at least one "
                f"round; got verdict={self.last_step12_verdict.value!r} with build_round=0"
            )
        if self.active_step == CustomizationStep.STEP_10:
            if self.build_round != 0 or self.last_step12_verdict is not None:
                raise ValueError(
                    "active_step=step_10 requires build_round=0 and last_step12_verdict=None -- "
                    "both entry paths reset them (greenfield: never set; re-modernization: reset "
                    "explicitly, section 0.2 deviation 3)"
                )
        return self
```

**Two invariants, not more.** Everything else that could be wrong involves disk state, which a
validator cannot see; those checks live in `check_coherence()` (§6.1) where they belong.

### 3.3 `DispatchDecision` (`models/dispatch.py`)

```python
class DispatchDecision(LooprBase):
    """One decision. Deliberately carries NO timestamp -- the log writer adds that (dispatch/log.py),
    so a DispatchDecision is byte-stable and can be compared directly against a fixture's expected
    value with no field exclusions. A fixture comparison that has to ignore fields is a fixture
    comparison a third party cannot fully trust."""

    state_id: DispatchStateId
    target: DispatchTarget | None
    """None ONLY in S0_TERMINAL. Enforced below."""
    reason: str = Field(min_length=1)
    """One sentence, present tense, naming the facts that decided it. Rendered verbatim to the human
    (section 4.3) -- write it for a person mid-loop, not for a log parser."""

    step10_warrant: Step10Warrant | None = None
    """Non-None iff target is STEP_10. Enforced below."""

    step10_declined_because: str | None = None
    """Present on EVERY decision that is not a step10 dispatch, including terminal. Absence of a
    step10 call must be positive evidence, not silence -- otherwise the acceptance criteria's
    log-grep is searching for something that may simply never have been written."""

    build_round: int = Field(ge=0)
    """Echoed from state for the log and the human line. Not an independent input."""

    @model_validator(mode="after")
    def check_decision_coherence(self) -> "DispatchDecision":
        terminal = self.state_id == DispatchStateId.S0_TERMINAL
        if terminal != (self.target is None):
            raise ValueError("target is None iff state_id is S0_TERMINAL")
        is_step10 = self.target == DispatchTarget.STEP_10
        if is_step10 and self.step10_warrant is None:
            raise ValueError(
                "a step10 dispatch MUST carry a Step10Warrant (loopr-PRD.md section 6 B6 hard "
                "boundary). An unwarranted step10 decision is not constructable by design."
            )
        if not is_step10 and self.step10_warrant is not None:
            raise ValueError("step10_warrant is only valid on a step10 dispatch")
        if not is_step10 and not self.step10_declined_because:
            raise ValueError(
                "every non-step10 decision must state why step10 was declined -- silence is not "
                "evidence (section 3.3)"
            )
        return self
```

**This validator is the hard boundary's primary enforcement.** It moves "the reviewer greps for it"
up to "the type system rejects it": there is no way to construct a `DispatchDecision` naming step10
without a warrant from the closed two-member enum, and no way to construct any other decision without
an explicit reason step10 was declined. §7's greps are the second line, not the first.

---

## §4 CLI surface (this project's equivalent of route signatures)

*Section retained in position per the step10 template's structure; loopr has no HTTP surface — the
CLI subcommand contract is the analogous artifact, exactly as `CUSTOMIZATION_PHASE_1_SPEC.md` §6.1
treated it.*

Exit codes reuse `src/loopr/exit_codes.py` **unchanged**. Do not invent new codes — the named-constant
discipline and the terminal-HALT rule are carried directly from the abandoned Docker harness's
failure (`loopr-MIGRATION.md` §7).

### 4.1 `loopr dispatch`

```
loopr dispatch --state <state.json> [--json] [--dry-run] [--remodernize]
                [--modernized-prd-path PATH] [--phase-1-spec-path PATH] [--build-complete-path PATH]
```

| Flag | Meaning |
|---|---|
| `--state` | required; same as every other subcommand |
| `--json` | emit `DispatchDecision.model_dump_json(indent=2)` instead of the human block |
| `--dry-run` | decide and print; **do not** mutate state, **do not** append to the log |
| `--remodernize` | the operator act that makes `EXPLICIT_REMODERNIZATION` reachable (§4.2) |
| `--modernized-prd-path` / `--phase-1-spec-path` | **added 2026-08-05**, amendment, see below |
| `--build-complete-path` | **added 2026-08-05**, second amendment from the same dogfood run, see §6.2 |

**Amendment (2026-08-05): step10-artifact override flags, threaded through from `customize`.** The
first real `loopr dispatch` run against this project's own state (`.loopr-state/state.json`) HALTed
immediately — `find_step10_execution_artifacts` correctly detected that this repo carries two genuine
phase-spec-shaped files (`PHASE_1_SPEC.md` and `CUSTOMIZATION_PHASE_3_SPEC.md`, both legitimately
built from the same modernised PRD, per G8's own "a mature repo can legitimately carry more than one
valid phase-spec artifact permanently" rule) and raised the ambiguity it's supposed to raise — but
`dispatch` had no flag for a human to resolve it with. `customize` had gained exactly this override
mechanism in a prior fix (bebdce3); `dispatch` called the same detector directly with no arguments at
all (cli.py, prior to this amendment). Fixed by reusing `_resolve_step10_artifact_overrides` and
threading its result into `dispatch`'s own `find_step10_execution_artifacts` call — no new resolver,
no new persisted state field (G7), no second artifact detector (G8). This is not a corrected oversight
in the original design so much as the first real dispatch run surfacing a wiring gap the design didn't
anticipate: the override was added where `customize` needed it and not yet threaded to every other
caller of the same gate.

| Outcome | Exit | Behaviour |
|---|---|---|
| A subagent is named | `OK` (0) | print decision; set `active_step`; apply the §6.3 clearing rule; append to the log; save state |
| `S0_TERMINAL` | `COMPLETE` (50) | print decision; append to the log; **no state mutation** |
| State is incoherent | `HALT` (40) | print the failing check and the full state to stderr; append **nothing** to the log; **no state mutation** |

**A HALT never dispatches anything, and specifically never dispatches step10.** This is the single
most important behaviour in the phase.

`--remodernize` is not a decision flag — it is a state-mutating operator act, applied *before*
`decide()` runs: sets `active_step = STEP_10`, `build_round = 0`, `last_step12_verdict = None`
(§0.2 deviation 3), then falls through to the normal decision path, which necessarily lands on
`S2_STEP10_IN_FLIGHT`. It is rejected with `USAGE` (2) if `active_step` is already non-`None` — you
cannot re-modernize on top of an in-flight step.

### 4.2 `loopr dispatch-complete`

```
loopr dispatch-complete --state <state.json> [--verdict {clean,minor,spec_violating}]
```

Records that the currently-active step finished, and applies §6.3's transition.

| Condition | Exit | Behaviour |
|---|---|---|
| `active_step` is `None` | `USAGE` (2) | nothing is in flight |
| `active_step` is step10 or step11, `--verdict` **given** | `USAGE` (2) | a verdict is meaningful only for step12 |
| `active_step` is step12, `--verdict` **omitted** | `USAGE` (2) | step12 must record a severity — this is the criteria's falsifiable distinction, so it is required, never defaulted |
| otherwise | `OK` (0) | apply the transition, save state, print the new state one-line |

`--verdict` has **no default.** A defaulted verdict is a silently-fabricated fact about a review that
happened outside this process.

### 4.3 Output rendering — a spec'd shape, because legibility is an acceptance criterion

`render_human()` emits exactly four lines plus a blank line and a run line. Fixed field order, fixed
labels, no colour, no box drawing (this runs in whatever terminal the operator has):

```
DISPATCH   loopr-step11
STATE      s7_step12_clean  (build round 4)
WHY        step12 approved the previous round clean; the next round's build is what runs next.
NOT-STEP10 step10 artifacts present on disk (loopr-PRD.md + PHASE_1_SPEC.md); no --remodernize given.

RUN        Task(subagent_type="loopr-step11")
```

Terminal renders `DISPATCH   -- nothing; build is complete` and omits `RUN`.
HALT renders to **stderr** with the same four-label shape, `DISPATCH   -- HALT`, and the offending
state dumped underneath.

Requirements, each testable:
- `NOT-STEP10` appears on **every** non-step10 decision. It is simultaneously the operator's
  two-second spot-check and the machine-greppable Opus-avoidance record.
- On a step10 dispatch the fourth line becomes `WARRANT    greenfield_no_artifacts` (or
  `explicit_remodernization`) — the label changes so a step10 call is visually unmistakable when
  scrolling.
- `WHY` is one sentence and names the facts, not the rule. "step12 approved the previous round clean"
  is checkable at a glance; "matched rule S7" is not.
- The block is ≤ 6 lines. The failure mode this phase must avoid is output the operator skims past or
  re-derives (`.claude/loopr/context.md`); a screenful of reasoning is that failure.

### 4.4 `loopr dispatch-verify` — the third-party fixture runner

```
loopr dispatch-verify --fixtures <dir>
```

Loads every `*.json` in the directory, feeds each fixture's state + disk facts to `decide()`, and
diffs the result against the fixture's `expected` block. Prints one line per fixture
(`OK <name>` / `MISMATCH <name>: expected <...> got <...>`) and a total. Exit `OK` (0) if every
fixture matches, `HALT` (40) otherwise.

Precedent: `cmd_replay` already establishes a verification subcommand that diffs actual against
recorded. This is the same shape pointed at dispatch. **The point of it existing as a command rather
than only as a pytest file** is acceptance criterion 3: a third party runs one command and reads
pass/fail, with no need to understand the project or to have a working pytest environment.

### 4.5 `loopr dispatch-audit` — the Opus-avoidance check

```
loopr dispatch-audit --log <path>
```

Reads the JSONL dispatch log and reports **every** record whose `target` is `loopr-step10`, printing
its warrant, round, and reason. Exit `HALT` (40) if any such record has a missing, null, or
unrecognised warrant; `OK` (0) otherwise, printing the count of step10 calls found and their warrants
so a zero is visibly a zero rather than an empty screen.

This is a **separate check from the fixture suite by explicit requirement** — the confirmed criteria
call for it "rather than relying on the fixture tests to catch it incidentally." The equivalent raw
command is documented in the help text so the operator can do it by hand:

```
grep '"target": "loopr-step10"' .loopr-state/dispatch-log.jsonl
```

---

## §5 Migration — schema_version 1 → 2, hard-fail, no migration path

Applicable, and it is the one genuinely destructive change in this phase.

`InterrogationState` gains a required field, so `schema_version` bumps `1` → `2` in **both** places
that carry it: the model default (`models/interrogation.py`) and `_CURRENT_SCHEMA_VERSION`
(`state/store.py`).

**Follow `store.py`'s existing convention exactly: hard-fail, never silently upgrade.** `load()`
already raises `StateVersionError` on any mismatch, with the docstring "Never silently upgraded." Do
**not** add a v1→v2 upgrade path, a `try: v1 except: v2` fallback, or a default-injection shim. The
confirmed boundary names this explicitly: "old state files become unloadable under the new version by
the same design already in place, not silently reinterpreted."

Consequences, stated so they are not discovered at runtime:
- Every existing `.loopr-state/state.json` in this repo and in `_archive/` becomes unloadable. That is
  intended. Re-run or archive; do not migrate.
- `tests/test_state_store.py:54` currently plants `{"schema_version": 999}` and expects
  `StateVersionError` — still passes. `tests/test_state_store.py:114` plants `schema_version: 1` and
  expects a *validation* error on a bad mode; that test now fails at the **version** gate first and
  must be updated to `2` or its assertion will be testing the wrong thing.
- Add a new test asserting a well-formed **v1** payload raises `StateVersionError` — the migration
  behaviour must be demonstrated firing, not assumed.

---

## §6 Implementation logic flow

### 6.1 `check_coherence(state, artifacts_present) -> str | None` — runs first, always

Returns a failure message, or `None`. The state-internal invariants are already unrepresentable
(§3.2's validator); these are the checks that cross disk truth, which a validator cannot see.

| Check | Condition | Why it cannot be routed |
|---|---|---|
| C1 | artifacts absent **and** `build_round >= 1` | rounds were built against a spec that does not exist |
| C2 | artifacts absent **and** `last_step12_verdict is not None` | a review happened against a spec that does not exist |
| C3 | artifacts absent **and** `active_step in {STEP_11, STEP_12}` | step11/12 cannot legally run without step10's output — the same gate `cli.py::_step10_execution_gate_message` already enforces at customization time (`CUSTOMIZATION_PHASE_2_SPEC.md` §1.1) |

Any hit → the caller returns `HALT`. **Not a step10 dispatch.** The tempting reading of C1/C2/C3 is
"step10 hasn't run, so run step10" — that is precisely escalation-by-default wearing a plausible
disguise, and it is forbidden. These states are not *pre-step10*; they are *incoherent*, and the
difference is that a human needs to look.

### 6.2 `decide(state, artifacts_present, build_complete_present) -> DispatchDecision` — the routing table

The deterministic anchor for this whole phase. **Zero LLM calls, zero judge calls, zero heuristics,
zero confidence scores.** Match order is significant and is the order below.

| # | State ID | Precondition | → Target | Warrant / declined-because |
|---|---|---|---|---|
| 1 | `S0_TERMINAL` | `build_complete_present` (CLI-resolved, see amendment below) | *(none)* — exit `COMPLETE` | declined: build is complete |

**Amendment (2026-08-05): the CLI-side resolution of `build_complete_present`, not `decide()` itself,
changed.** `decide()`'s signature is unchanged — it still takes a bare `build_complete_present: bool`
(G5's guard: no new input without a human decision, and this isn't one). What changed is how
`cli.py::cmd_dispatch` computes that bool: the second finding from this project's own first real
`loopr dispatch` run — from the *same* call as the artifact-override finding above — was that
`build_complete_present` was hardcoded to `(repo_root / "BUILD_COMPLETE.md").exists()`, unrelated to
the project the given `--state` file actually tracks. This repo hosts two loopr-managed builds
(`BUILD_COMPLETE.md` for the base module, `CUSTOMIZATION_BUILD_COMPLETE.md` for this series, per the
latter's own "Note on naming"), and the hardcoded check happened to read the *other* project's marker
and get the right answer by coincidence — not by verification. The dangerous direction (this series
mid-build while the unrelated `BUILD_COMPLETE.md` still sits at repo root) was never exercised because
both builds happened to be done simultaneously. Fixed with a `--build-complete-path` override flag,
same shape as `--modernized-prd-path`/`--phase-1-spec-path`, defaulting to the exact prior behaviour
when omitted. This was a **silent, coincidentally-correct pass**, not a HALT — more concerning in kind
than the first finding, which at least refused loudly.
| 2 | `S2_STEP10_IN_FLIGHT` | `active_step == STEP_10` | `loopr-step10` | `GREENFIELD_NO_ARTIFACTS` if artifacts absent, else `EXPLICIT_REMODERNIZATION` |
| 3 | `S1_PRE_STEP10` | artifacts absent (⇒ `active_step is None`, by C3) | `loopr-step10` | `GREENFIELD_NO_ARTIFACTS` |
| 4 | `S4_STEP11_IN_FLIGHT` | `active_step == STEP_11` | `loopr-step11` | declined: artifacts present, no `--remodernize` |
| 5 | `S6_STEP12_IN_FLIGHT` | `active_step == STEP_12` | `loopr-step12` | declined: artifacts present, no `--remodernize` |
| 6 | `S3_STEP10_DONE` | `active_step is None`, verdict `None`, `build_round == 0` | `loopr-step11` | declined: artifacts present, no `--remodernize` |
| 7 | `S5_STEP11_DONE` **[architect-derived]** | `active_step is None`, verdict `None`, `build_round >= 1` | `loopr-step12` | declined: artifacts present, no `--remodernize` |
| 8 | `S7_STEP12_CLEAN` | `active_step is None`, verdict `CLEAN` | `loopr-step11` | declined: artifacts present, no `--remodernize` |
| 9 | `S8_STEP12_MINOR` | `active_step is None`, verdict `MINOR` | `loopr-step11` | declined: artifacts present, no `--remodernize` |
| 10 | `S9_STEP12_SPEC_VIOLATING` | `active_step is None`, verdict `SPEC_VIOLATING` | `loopr-step11` | declined: artifacts present, no `--remodernize` |

Rows 1–6 and 8–10 correspond to the six states the user enumerated plus the terminal state; row 7 and
row 1 are the two architect-derived additions (§0.2 deviation 2). Row 1 is also marked derived in the
fixture files.

**Four things about this table that a literal-minded implementer will otherwise get wrong:**

1. **`build_round` is the S3/S5 discriminator, and it is the only one.** Both present as
   `active_step is None` with no verdict. `== 0` means step10 finished and nothing has been built;
   `>= 1` means step11 finished a round and review is owed. This is why §6.3 increments on
   *completion* rather than on dispatch.
2. **Rows 8, 9, 10 all target `loopr-step11`, and that is correct, not a missing case.** `CLEAN` and
   `MINOR` advance to the next phase's build; `SPEC_VIOLATING` reworks the same phase. The controller
   does not and must not distinguish them by target, because **it does not know the phase number** —
   phase discovery stays inside the step11/step12 prompts themselves (git commit markers,
   `CUSTOMIZATION_PHASE_1_SPEC.md` §7.2). They are three separate states because the acceptance
   criteria require three separately-falsifiable answers and three distinct log records, and because
   collapsing them would erase the distinction the operator uses to sanity-check the loop.
3. **The final branch over `Step12Verdict` ends in `typing.assert_never(verdict)`.** With
   `mypy --strict`, adding a fourth verdict without a routing rule is then a *compile-time* error, not
   a runtime fall-through. Use `assert_never`, not `raise NotImplementedError` — the latter would
   produce a runtime path that a careless refactor could route to step10.
4. **There is no `else`, no `default`, and no `except` anywhere in `decide()`.** The function is total
   over the validated state space; anything outside it was already caught by §6.1 or by §3.2's
   validator. See §7 guard G1.

### 6.3 Transitions — who writes what, and when

```
dispatch(STEP_10)   -> active_step = STEP_10                             (build_round/verdict already 0/None)
dispatch(STEP_11)   -> active_step = STEP_11 ; last_step12_verdict = None   <-- THE CLEARING RULE
dispatch(STEP_12)   -> active_step = STEP_12
complete(step10)    -> active_step = None
complete(step11)    -> active_step = None ; build_round += 1               <-- INCREMENT ON COMPLETION
complete(step12, V) -> active_step = None ; last_step12_verdict = V
--remodernize       -> active_step = STEP_10 ; build_round = 0 ; last_step12_verdict = None
```

**The clearing rule and the completion-timed increment are the two load-bearing lines here.** Drop
either and the state machine stops being deterministic:

- Without clearing on step11 dispatch, a `CLEAN` verdict from round 3 survives into round 4, and once
  step11 completes the state reads `(None, 4, CLEAN)` — which matches both S5 and S7. The controller
  would then dispatch step11 forever and the phase would never be reviewed.
- Increment on *dispatch* instead of completion makes `(STEP_11, 1, None)` and `(None, 1, None)`
  describe a round that has and has not been built respectively — recoverable, but it puts S3 at
  `build_round == 1` for a build that never happened, which breaks the "step10 done, nothing built"
  reading the log depends on.

### 6.4 The full round-trip trace (assert this exactly, `tests/test_dispatch_transitions.py`)

```
(None, 0, None)   + artifacts   -> S3  -> step11 ; state becomes (STEP_11, 0, None)
(STEP_11, 0, None)              -> S4  -> step11 (resume)
complete(step11)                        state becomes (None, 1, None)
(None, 1, None)                 -> S5  -> step12 ; state becomes (STEP_12, 1, None)
(STEP_12, 1, None)              -> S6  -> step12 (resume)
complete(step12, CLEAN)                 state becomes (None, 1, CLEAN)
(None, 1, CLEAN)                -> S7  -> step11 ; state becomes (STEP_11, 1, None)
complete(step11)                        state becomes (None, 2, None)
(None, 2, None)                 -> S5  -> step12 ; state becomes (STEP_12, 2, None)
complete(step12, SPEC_VIOLATING)        state becomes (None, 2, SPEC_VIOLATING)
(None, 2, SPEC_VIOLATING)       -> S9  -> step11 (rework) ; state becomes (STEP_11, 2, None)
complete(step11)                        state becomes (None, 3, None)
(None, 3, None)                 -> S5  -> step12
```

Zero step10 dispatches across the entire trace. That is the point, and §8 criterion 7 asserts it.

### 6.5 The dispatch log

Append-only JSONL at `<state_dir>/dispatch-log.jsonl` (i.e. alongside `state.json`, same directory
`StateStore.dir` already exposes). One JSON object per line, written with `sort_keys=True` for a
diffable file, matching `store.py`'s existing canonical-serialisation choice:

```json
{"active_step": null, "build_round": 4, "last_step12_verdict": "clean",
 "reason": "step12 approved the previous round clean; the next round's build is what runs next.",
 "state_id": "s7_step12_clean",
 "step10_declined_because": "step10 artifacts present on disk (loopr-PRD.md + PHASE_1_SPEC.md); no --remodernize given.",
 "step10_warrant": null, "target": "loopr-step11", "ts": "2026-08-04T16:12:03Z"}
```

Rules:
- **Append-only.** Never rewrite, never truncate, never rotate. The audit trail is the deliverable.
- `ts` is added by `log.py`, never by `decide()` — §3.3's rationale.
- A HALT appends **nothing**. The log is a record of dispatches; a HALT is the absence of one, and
  writing a non-dispatch into it would corrupt the grep the acceptance criteria depend on.
- `--dry-run` appends nothing.
- Written *after* the decision is validated, so a malformed decision can never reach the log.

---

## §7 Failure-mode guards

Each maps to a `loopr-PRD.md` §10 entry (four added 2026-08-04) and names exactly what the review
agent checks. G1–G3 are executable as `tests/test_dispatch_boundary.py`.

### G1 — Escalation-by-default *(the hard boundary; auto-reject on breach)*

**What would violate it, concretely — grep for these in `src/loopr/dispatch/controller.py`:**
- any `return`/construction of a decision with `target=DispatchTarget.STEP_10` outside the two
  branches at rows 2 and 3 of §6.2's table;
- an `else:` or `default` branch anywhere in `decide()` (there must be none at all);
- any `try:`/`except` inside `decide()` (a swallowed exception is a silent fall-through);
- any new `Step10Warrant` member — the enum member count must be exactly 2;
- any identifier or comment in the module matching `/uncertain|fallback|safe(r|ty)?[_ ]?default|when in doubt|just in case|to be safe/i` on a path that can reach a step10 decision;
- `DispatchTarget.STEP_10` appearing in `cli.py` outside the `--remodernize` handling and the
  rendering label switch;
- any code that maps an unrecognised or incoherent state to a *dispatch* rather than to
  `exit_codes.HALT`.

**Review agent action on a hit: HALT.** A modernization or refactor that touches this boundary is
auto-rejected, not applied — the boundary outranks any newer or tidier method.

**Positive checks (must all hold):** `len(Step10Warrant) == 2`; every `DispatchDecision` with
`target == STEP_10` has a non-`None` warrant (already unconstructable otherwise, §3.3); the trace in
§6.4 produces zero step10 dispatches.

### G2 — Non-total routing

**Guard:** `decide()` matches every `DispatchStateId` member; the verdict branch terminates in
`typing.assert_never`. **Check:** `mypy --strict` passes, and a test that removes a routing arm fails
to type-check (documented in the test's docstring rather than run, since it is a negative
compile-time assertion).

### G3 — Silence read as evidence

**Guard:** `DispatchDecision` cannot be constructed for a non-step10 target without
`step10_declined_because`. **Check:** every record in a produced log has either a non-null
`step10_warrant` or a non-empty `step10_declined_because`; `dispatch-audit` exits `HALT` on a planted
record that has neither.

### G4 — Silent state drift between the recorded verdict and reality

**Guard:** `dispatch-complete` is the sole writer of `last_step12_verdict`; `--verdict` is required
for step12 and rejected for step10/step11; the verdict is cleared on step11 dispatch; §6.1's C1/C2/C3
reject verdict/round combinations that no legal transition could produce. **Check:** the review agent
greps for any other assignment to `last_step12_verdict` or `build_round` outside
`dispatch/controller.py`'s transition helper and `cli.py`'s `dispatch-complete` handler.

### G5 — Scope leak into Phase B

**Guard:** `dispatch/controller.py` imports nothing from `loopr.judge`, `loopr.gates`,
`loopr.interrogation`, or `subprocess`; the module contains no `git` string; `decide()`'s parameters
are exactly `(state, artifacts_present, build_complete_present)`. **Check:** the review agent asserts
the import list against that whitelist. Any new input to `decide()` is a boundary change requiring a
human, not a patch.

### G6 — Illegible output *(the failure a green suite cannot see)*

**Guard:** `render_human()` emits ≤ 6 lines, in the fixed label order of §4.3, with `NOT-STEP10` on
every non-step10 decision and `WARRANT` on every step10 one. **Check:** a golden-output test per
state, plus §8 criterion 9's behavioural check, which is the only one that actually settles it.

### G7 — Redundant source of truth for "has step10 run"

**Guard:** the artifact check calls
`loopr.customization.templates.find_step10_execution_artifacts(repo_root)` on every invocation; there
is **no** `step10_done` / `step10_executed` / `artifacts_present` field on `DispatchState` or
`InterrogationState`. **Check:** grep the diff for any new persisted boolean about step10's
existence. The confirmed boundary is explicit: "one source of truth for that fact, not two."

### G8 — Reimplementing the step10 artifact check

**Guard:** do not write a second artifact detector. `find_step10_execution_artifacts` already encodes
the non-obvious part — `PHASE_1_SPEC.md` is a fixed filename but the modernised PRD is **not** (this
project's own is `loopr-PRD.md`, not the template's `ULTIMATE_PRD.md` default), so it is detected by
content (`## MODERNIZATION CHANGELOG`). A reimplementation that guesses a filename will silently
report "step10 never ran" on this very repo and dispatch Opus. **Check:** exactly one call site
pattern; no new `glob("*.md")` in `dispatch/`.

---

## §8 Phase 3 acceptance criteria

Concrete and testable. 1–8 are mechanical; 9 is behavioural and is not optional.

1. **The state set is enumerated explicitly and is complete.** `DispatchStateId` has ten members;
   `decide()` has a routing rule for each; the two architect-derived states are labelled as such in
   §6.2 and in the fixture files.
2. **One fixture file per state**, in `tests/fixtures/dispatch/`, each carrying the input state, the
   two disk facts, and a pre-written `expected` block (`state_id`, `target`, `step10_warrant`).
   Fixtures are **data files**, not live project runs.
3. **`loopr dispatch-verify --fixtures tests/fixtures/dispatch` exits 0**, and a third party can run
   exactly that command and read pass/fail without understanding the project. Demonstrated by
   deliberately corrupting one fixture's `expected.target` and confirming a `MISMATCH` line and exit
   `HALT` — the runner must be shown failing, not merely present.
4. **Every one of the user's six pre-written answers holds unchanged:** before step10 has run →
   `loopr-step10`; step10 done/clean → `loopr-step11`; step11 mid-round → `loopr-step11`; step12 clean
   → `loopr-step11`; step12 minor → `loopr-step11`; step12 spec-violating → `loopr-step11`
   (**not** `loopr-step10`).
5. **Incoherent states HALT and dispatch nothing.** Demonstrated firing for each of C1, C2, C3 in
   §6.1: exit `HALT` (40), nothing written to state, nothing appended to the log, and — asserted
   explicitly — the word `loopr-step10` absent from stdout.
6. **The transition trace in §6.4 reproduces exactly**, step for step, including the clearing rule and
   the completion-timed increment.
7. **Zero unwarranted step10 calls in the log.** After running the §6.4 trace,
   `loopr dispatch-audit --log <path>` reports zero step10 dispatches and exits 0; separately, a
   planted record with `target: "loopr-step10"` and `step10_warrant: null` makes it exit `HALT`. Both
   directions must be demonstrated — a check that has never failed has not been tested.
8. **`schema_version` migration behaves as designed:** a well-formed **v1** state file raises
   `StateVersionError`; no upgrade path exists in `store.py`; `tests/test_state_store.py`'s v1
   fixtures are updated to 2.
9. **Dogfood legibility check (behavioural, and the one a green suite cannot catch).** Run the
   controller through at least one real build round in this repo. Pass condition: the operator
   re-verifies the controller's choice by hand **no more than twice** across that run. More than twice
   is a **fail** even with every other criterion green, and the remedy is `render_human()`'s shape
   (§4.3) — not a code fix elsewhere. Stated as a criterion because `.claude/loopr/context.md` names
   it as the failure mode most likely to be missed.

   **Amendment (2026-08-05): first real data point.** The first genuine `loopr dispatch` run against
   this repo's own state was not a legibility failure, but a functional one: `dispatch` HALTed outright
   on the `PHASE_1_SPEC.md` / `CUSTOMIZATION_PHASE_3_SPEC.md` ambiguity `find_step10_execution_artifacts`
   correctly detects (per §4.1's amendment note above), with no override flag to resolve it — the run
   never reached the point where legibility could even be assessed. This criterion's status moves from
   "unverified, no signal yet" to "one real run recorded, and it surfaced a genuine gap in `dispatch`'s
   CLI surface, not a rendering concern." Re-run after the override-flag fix landed:
   `loopr dispatch --state .loopr-state/state.json --dry-run --phase-1-spec-path
   CUSTOMIZATION_PHASE_3_SPEC.md` produces a normal `DISPATCH`/`STATE`/`WHY`/`NOT-STEP10` block,
   re-verified by hand in one look — the legibility check itself still passes once the run can proceed
   at all.
10. **`mypy --strict` clean; full suite green;** `test_no_paid_dependency` and
    `test_no_hardcoded_domain` still passing; `tests/test_dispatch_boundary.py` (G1–G3, G5, G7, G8)
    passing.

---

## §9 Explicit NON-GOALS

Not built in Phase 3. The first four are verbatim scope edges from the confirmed run.

- **Cost or token budgeting, spend caps, running cost trackers.** The controller decides *which*
  subagent based on state, never *whether the run can afford it*. It prevents **unwarranted** step10
  calls (the state did not justify one), not **too many warranted** ones. Budget enforcement is a
  separate, deferred feature — and it is already listed in `loopr-PRD.md` §12 as deferred to the
  loop-hardening slice.
- **Concurrent or interleaved phases.** One round in flight at a time — step10 or step11 or step12,
  sequentially. `active_step` is a single value by design, not a set. If simultaneous rounds ever
  become real, that is a different and harder controller.
- **Retry or backoff for a subagent that errors, crashes, or times out.** That is error handling, not
  dispatch logic. If a dispatched subagent dies, `active_step` simply stays set and the next
  `loopr dispatch` resumes it (S2/S4/S6) — which is a *consequence* of the design, not a retry policy,
  and no attempt/failure counting exists.
- **Any new subagent type.** Phase 3 routes between the three that already exist. No auditor tier,
  nothing from `docs/loopr-v2-agent-archetypes.md`. That forward spec stays parked.
- **A rework ping-pong cap.** Bounding S9→step11→S5→step12→S9 cycles requires remembering prior
  rounds, which the confirmed boundary's own threshold clause puts out of scope: such a case "should
  surface as an open question, not get silently built in." Surfaced in `loopr-PRD.md` §15.
- **Git-marker phase discovery.** The controller never shells out to git and never reads commit
  markers. Which phase N is being built stays inside the step11/step12 prompts
  (`CUSTOMIZATION_PHASE_1_SPEC.md` §7.2). Deriving `last_step12_verdict` from markers was considered
  and declined for this phase (`loopr-PRD.md` §15).
- **Gates as ground truth, the audit tier, the build→review→audit loop, Traycer.** Phase B's three
  invariants remain unbuilt and parked (`loopr-PRD.md` §6, §14 step 4). A dispatcher that names the
  next subagent is a signpost, not a harness.
- **Any LLM or judge call.** No new `JudgeCallType`, no rubric text, no `ALLOWED_INPUTS` bump, no
  envelope version bump. The controller is pure code end to end — that is the design, not a
  simplification of it (`loopr-PRD.md` §6 B6).
- **Auto-dispatch.** `loopr dispatch` *names* the next subagent and prints a copy-pasteable line; it
  does not invoke one. Actually spawning the subagent is the invoking agent's job, exactly as
  answering a judge call is today. This preserves the module's standing property of making no
  outbound call and needing no API key.
- **Touching Phase 1 or Phase 2.** No changes to step10/11/12 customization, the fidelity checks, the
  template registries, or the subagent renderers beyond reading the three `*_SUBAGENT_NAME` constants.
