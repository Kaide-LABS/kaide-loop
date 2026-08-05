"""The dispatch controller's pure decision logic. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS6.

PROJECT HARD BOUNDARY (loopr-PRD.md section 6 B6): `loopr-step10` is the Opus-tier subagent, and
this module may name it in exactly two circumstances -- step10's execution artifacts are absent from
disk (a greenfield run), or the operator explicitly requested re-modernization. There is no third
circumstance, however plausible-sounding, under which a step this module cannot classify still earns
a step10 dispatch. A state this module cannot classify returns a HALT signal (`check_coherence`
returning non-None, checked by the caller BEFORE `decide()` is ever invoked) instead.

Both functions here are pure and total: no file reads, no subprocess calls, no judge or LLM calls of
any kind. `check_coherence` and `decide` take only the small set of facts CUSTOMIZATION_PHASE_3_SPEC.md
SS6 names -- three persisted state fields plus (for `decide`) two live disk facts already resolved to
booleans by the caller. This module imports nothing from `loopr.judge`, `loopr.gates`, or
`loopr.interrogation`, and never shells out -- see CUSTOMIZATION_PHASE_3_SPEC.md SS7 guard G5. Any new
input to `decide()` is a boundary change requiring a human, not a patch.
"""

from __future__ import annotations

import typing

from loopr.models.common import (
    CustomizationStep,
    DispatchStateId,
    DispatchTarget,
    Step10Warrant,
    Step12Verdict,
)
from loopr.models.dispatch import DispatchDecision, DispatchState

_DECLINED_ARTIFACTS_PRESENT = "step10 artifacts present on disk; no --remodernize given."
"""Shared declined-because text for every row that lands on step11 or step12 (CUSTOMIZATION_PHASE_3_
SPEC.md SS6.2, rows 4 through 10). Kept as one constant so the wording cannot drift row to row."""


def check_coherence(state: DispatchState, artifacts_present: bool) -> str | None:
    """The cross-disk-truth checks a Pydantic validator cannot see (CUSTOMIZATION_PHASE_3_SPEC.md
    SS6.1) -- `DispatchState`'s own validator (models/dispatch.py) already rejects everything that
    is wrong purely from the state's own fields; these three checks are the ones that additionally
    need the live `artifacts_present` disk fact. Returns a human-readable failure reason, or `None`
    if the state is coherent.

    The caller (`cli.py`'s `cmd_dispatch`) MUST call this before `decide()` and HALT on a non-None
    result, never calling `decide()` at all in that case -- an incoherent state is not a step10
    signal wearing a plausible disguise, it is a state a human needs to look at.
    """
    if not artifacts_present and state.build_round >= 1:
        return (
            "step10's execution artifacts are absent from disk, yet build_round="
            f"{state.build_round} -- a round was recorded as built against a specification that "
            "does not exist on disk (CUSTOMIZATION_PHASE_3_SPEC.md SS6.1 check C1)."
        )
    if not artifacts_present and state.last_step12_verdict is not None:
        return (
            "step10's execution artifacts are absent from disk, yet last_step12_verdict="
            f"{state.last_step12_verdict.value!r} -- a review was recorded against a specification "
            "that does not exist on disk (CUSTOMIZATION_PHASE_3_SPEC.md SS6.1 check C2)."
        )
    if not artifacts_present and state.active_step in (
        CustomizationStep.STEP_11,
        CustomizationStep.STEP_12,
    ):
        return (
            "step10's execution artifacts are absent from disk, yet active_step="
            f"{state.active_step.value!r} -- step11/step12 cannot legally run without step10's own "
            "output (CUSTOMIZATION_PHASE_3_SPEC.md SS6.1 check C3)."
        )
    return None


def decide(
    state: DispatchState, artifacts_present: bool, build_complete_present: bool
) -> DispatchDecision:
    """The deterministic routing table (CUSTOMIZATION_PHASE_3_SPEC.md SS6.2). Match order is
    significant and is the order below; the first matching row wins. Zero LLM calls, zero judge
    calls, zero heuristics, zero confidence scores.

    ASSUMES `check_coherence(state, artifacts_present)` already returned `None` -- this function does
    not re-check cross-disk-truth coherence itself (that check cannot be routed, it can only HALT;
    see `check_coherence`'s own docstring). Every branch below is a standalone guard clause with its
    own early `return`; none of them fall through to a shared closing branch, and none of them wrap
    a `try`/`except`. It is total over the validated state space by construction, matching every
    `DispatchStateId` member across the branches below, and the one open-ended sub-branch (over
    `Step12Verdict`) ends in `typing.assert_never` rather than constructing a decision -- adding a
    fourth verdict without a routing rule is then a mypy --strict error, not a runtime surprise that
    could silently reach step10.
    """
    if build_complete_present:
        return DispatchDecision(
            state_id=DispatchStateId.S0_TERMINAL,
            target=None,
            reason="BUILD_COMPLETE.md exists at the target repository root; the build is complete.",
            step10_warrant=None,
            step10_declined_because="build is complete",
            build_round=state.build_round,
        )

    if state.active_step == CustomizationStep.STEP_10 and not artifacts_present:
        return DispatchDecision(
            state_id=DispatchStateId.S2_STEP10_IN_FLIGHT,
            target=DispatchTarget.STEP_10,
            reason="step10's execution artifacts are absent from disk; step10 is already the active step.",
            step10_warrant=Step10Warrant.GREENFIELD_NO_ARTIFACTS,
            step10_declined_because=None,
            build_round=state.build_round,
        )

    if state.active_step == CustomizationStep.STEP_10:
        return DispatchDecision(
            state_id=DispatchStateId.S2_STEP10_IN_FLIGHT,
            target=DispatchTarget.STEP_10,
            reason="re-modernization was explicitly requested; step10 is already the active step.",
            step10_warrant=Step10Warrant.EXPLICIT_REMODERNIZATION,
            step10_declined_because=None,
            build_round=state.build_round,
        )

    if not artifacts_present:
        return DispatchDecision(
            state_id=DispatchStateId.S1_PRE_STEP10,
            target=DispatchTarget.STEP_10,
            reason="step10's execution artifacts are absent from disk; this is a greenfield run.",
            step10_warrant=Step10Warrant.GREENFIELD_NO_ARTIFACTS,
            step10_declined_because=None,
            build_round=state.build_round,
        )

    if state.active_step == CustomizationStep.STEP_11:
        return DispatchDecision(
            state_id=DispatchStateId.S4_STEP11_IN_FLIGHT,
            target=DispatchTarget.STEP_11,
            reason="step11 is already the active step; resuming it.",
            step10_warrant=None,
            step10_declined_because=_DECLINED_ARTIFACTS_PRESENT,
            build_round=state.build_round,
        )

    if state.active_step == CustomizationStep.STEP_12:
        return DispatchDecision(
            state_id=DispatchStateId.S6_STEP12_IN_FLIGHT,
            target=DispatchTarget.STEP_12,
            reason="step12 is already the active step; resuming it.",
            step10_warrant=None,
            step10_declined_because=_DECLINED_ARTIFACTS_PRESENT,
            build_round=state.build_round,
        )

    # `state.active_step` is now known to be None -- every other CustomizationStep member was
    # matched and returned above. The remaining classification (rows 6-10, CUSTOMIZATION_PHASE_3_
    # SPEC.md SS6.2) is exhaustive over `last_step12_verdict`.
    match state.last_step12_verdict:
        case None:
            if state.build_round == 0:
                return DispatchDecision(
                    state_id=DispatchStateId.S3_STEP10_DONE,
                    target=DispatchTarget.STEP_11,
                    reason=(
                        "step10 finished and no round has been built yet; the first round's build "
                        "runs next."
                    ),
                    step10_warrant=None,
                    step10_declined_because=_DECLINED_ARTIFACTS_PRESENT,
                    build_round=state.build_round,
                )
            return DispatchDecision(
                state_id=DispatchStateId.S5_STEP11_DONE,
                target=DispatchTarget.STEP_12,
                reason=(
                    f"step11 completed round {state.build_round} and no review has happened yet; "
                    "that round is owed a review."
                ),
                step10_warrant=None,
                step10_declined_because=_DECLINED_ARTIFACTS_PRESENT,
                build_round=state.build_round,
            )
        case Step12Verdict.CLEAN:
            return DispatchDecision(
                state_id=DispatchStateId.S7_STEP12_CLEAN,
                target=DispatchTarget.STEP_11,
                reason=(
                    "step12 approved the previous round clean; the next round's build is what runs "
                    "next."
                ),
                step10_warrant=None,
                step10_declined_because=_DECLINED_ARTIFACTS_PRESENT,
                build_round=state.build_round,
            )
        case Step12Verdict.MINOR:
            return DispatchDecision(
                state_id=DispatchStateId.S8_STEP12_MINOR,
                target=DispatchTarget.STEP_11,
                reason=(
                    "step12 approved the previous round after patching a minor issue itself; the "
                    "next round's build is what runs next."
                ),
                step10_warrant=None,
                step10_declined_because=_DECLINED_ARTIFACTS_PRESENT,
                build_round=state.build_round,
            )
        case Step12Verdict.SPEC_VIOLATING:
            return DispatchDecision(
                state_id=DispatchStateId.S9_STEP12_SPEC_VIOLATING,
                target=DispatchTarget.STEP_11,
                reason=(
                    "step12 found the previous round spec-violating; the same round's build must be "
                    "reworked."
                ),
                step10_warrant=None,
                step10_declined_because=_DECLINED_ARTIFACTS_PRESENT,
                build_round=state.build_round,
            )
        case unreachable:
            # Not a route to a decision: this is a static-typing proof only. mypy --strict
            # proves this branch is unreachable for the three real Step12Verdict members matched
            # above; a fourth member added without a routing rule turns this into a mypy error at
            # build time rather than a runtime path a careless change could route to step10.
            typing.assert_never(unreachable)


_TARGET_TO_STEP: dict[DispatchTarget, CustomizationStep] = {
    DispatchTarget.STEP_10: CustomizationStep.STEP_10,
    DispatchTarget.STEP_11: CustomizationStep.STEP_11,
    DispatchTarget.STEP_12: CustomizationStep.STEP_12,
}
"""The one place a `DispatchTarget` (a subagent name) is mapped to a `CustomizationStep` (the field
`DispatchState.active_step` reuses -- SS3.2's rationale against a parallel three-member enum)."""


def apply_dispatch_transition(state: DispatchState, target: DispatchTarget) -> DispatchState:
    """The sole writer of `active_step` / `last_step12_verdict` at DISPATCH time (CUSTOMIZATION_
    PHASE_3_SPEC.md SS6.3), paired with `apply_completion_transition` below for the completion half
    and with `cli.py`'s `dispatch-complete` handler, which calls that pairing function -- together
    the only two writers SS7 guard G4 permits. Pure: returns a new `DispatchState`, no I/O.

    Applies the load-bearing clearing rule on a step11 dispatch: `last_step12_verdict` resets to
    `None` the moment step11 is (re-)dispatched, so a stale verdict from a prior round can never
    survive into the state read at the START of the next round (SS6.3's own worked example: without
    this, `(None, 4, CLEAN)` would satisfy both S5 and S7 and the controller would loop on step11
    forever). step10's own build_round=0/verdict=None invariant when `active_step=step_10` is already
    enforced by `DispatchState`'s own validator (models/dispatch.py) for every path reaching this
    call, so no separate reset is written here for that target.
    """
    active_step = _TARGET_TO_STEP[target]
    if target == DispatchTarget.STEP_11:
        return state.model_copy(update={"active_step": active_step, "last_step12_verdict": None})
    return state.model_copy(update={"active_step": active_step})


def apply_remodernize_reset(state: DispatchState) -> DispatchState:
    """`--remodernize`'s state mutation (CUSTOMIZATION_PHASE_3_SPEC.md SS0.2 deviation 3), applied
    BEFORE `decide()` runs so the decision it produces necessarily lands on S2_STEP10_IN_FLIGHT with
    warrant EXPLICIT_REMODERNIZATION. Re-modernization rewrites the phase-1 specification, so the
    prior round counter and verdict describe a plan that no longer exists -- reset, not carried
    forward. History is not lost: the append-only dispatch log retains every prior round regardless.

    The caller (`cli.py`) is responsible for rejecting the operator act with `exit_codes.USAGE` when
    `state.active_step` is already non-`None` (cannot re-modernize on top of an in-flight step) --
    this function performs the reset unconditionally and does not repeat that check itself, matching
    every other transition helper here staying a small, pure, single-purpose function.
    """
    return state.model_copy(
        update={
            "active_step": CustomizationStep.STEP_10,
            "build_round": 0,
            "last_step12_verdict": None,
        }
    )


def apply_completion_transition(
    state: DispatchState, completed_step: CustomizationStep, verdict: Step12Verdict | None
) -> DispatchState:
    """The sole writer of `build_round` / `last_step12_verdict` at COMPLETION time (CUSTOMIZATION_
    PHASE_3_SPEC.md SS6.3), called only from `cli.py`'s `dispatch-complete` handler -- together with
    `apply_dispatch_transition` above, the only two writers SS7 guard G4 permits. Pure: returns a new
    `DispatchState`, no I/O. The caller already validated `verdict` is present iff `completed_step`
    is step12 (SS4.2's USAGE checks); this function trusts that and does not re-validate it.

    `build_round` increments on step11 COMPLETION, never on dispatch -- that timing is what makes
    S3_STEP10_DONE (`build_round == 0`, nothing built yet) and S5_STEP11_DONE (`build_round >= 1`, a
    round exists and is owed a review) distinguishable at all (SS6.2 point 1).
    """
    if completed_step == CustomizationStep.STEP_11:
        return state.model_copy(update={"active_step": None, "build_round": state.build_round + 1})
    if completed_step == CustomizationStep.STEP_12:
        return state.model_copy(update={"active_step": None, "last_step12_verdict": verdict})
    return state.model_copy(update={"active_step": None})
