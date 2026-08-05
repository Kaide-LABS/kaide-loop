"""Unit tests for `dispatch/controller.py`'s `decide()` and `check_coherence()`. Implements
CUSTOMIZATION_PHASE_3_SPEC.md SS1, SS6, SS8 criteria 1, 4, 5.
"""

from __future__ import annotations

import pytest

from loopr.dispatch.controller import check_coherence, decide
from loopr.models.common import (
    CustomizationStep,
    DispatchStateId,
    DispatchTarget,
    Step10Warrant,
    Step12Verdict,
)
from loopr.models.dispatch import DispatchDecision, DispatchState


# --- models/dispatch.py SS3.2/SS3.3: the validators that make an unwarranted decision unconstructable ---


def test_dispatch_state_rejects_verdict_with_zero_build_round() -> None:
    with pytest.raises(ValueError, match="last_step12_verdict"):
        DispatchState(build_round=0, last_step12_verdict=Step12Verdict.CLEAN)


def test_dispatch_state_rejects_step10_active_with_nonzero_round() -> None:
    with pytest.raises(ValueError, match="active_step=step_10"):
        DispatchState(active_step=CustomizationStep.STEP_10, build_round=1)


def test_dispatch_state_rejects_step10_active_with_a_verdict() -> None:
    with pytest.raises(ValueError, match="active_step=step_10"):
        DispatchState(
            active_step=CustomizationStep.STEP_10, build_round=1, last_step12_verdict=Step12Verdict.CLEAN
        )


def test_dispatch_decision_rejects_target_none_with_nonterminal_state_id() -> None:
    with pytest.raises(ValueError, match="target is None iff"):
        DispatchDecision(
            state_id=DispatchStateId.S1_PRE_STEP10,
            target=None,
            reason="test",
            step10_declined_because="test",
            build_round=0,
        )


def test_dispatch_decision_rejects_target_present_with_terminal_state_id() -> None:
    with pytest.raises(ValueError, match="target is None iff"):
        DispatchDecision(
            state_id=DispatchStateId.S0_TERMINAL,
            target=DispatchTarget.STEP_11,
            reason="test",
            step10_declined_because="test",
            build_round=0,
        )


def test_dispatch_decision_rejects_a_warrant_on_a_non_step10_target() -> None:
    with pytest.raises(ValueError, match="step10_warrant is only valid"):
        DispatchDecision(
            state_id=DispatchStateId.S3_STEP10_DONE,
            target=DispatchTarget.STEP_11,
            reason="test",
            step10_warrant=Step10Warrant.GREENFIELD_NO_ARTIFACTS,
            step10_declined_because="test",
            build_round=0,
        )


def test_state_id_enum_has_exactly_ten_members() -> None:
    """SS8 criterion 1: the state set is enumerated explicitly and is complete."""
    assert len(DispatchStateId) == 10


def test_step10_warrant_enum_is_closed_at_two_members() -> None:
    """The hard boundary's primary structural guarantee (SS3.1, SS7 guard G1)."""
    assert len(Step10Warrant) == 2


# --- SS8 criterion 4: every one of the user's six pre-written answers holds unchanged ---


def test_before_step10_has_run_routes_to_step10() -> None:
    state = DispatchState()
    decision = decide(state, artifacts_present=False, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S1_PRE_STEP10
    assert decision.target == DispatchTarget.STEP_10
    assert decision.step10_warrant == Step10Warrant.GREENFIELD_NO_ARTIFACTS


def test_step10_done_clean_routes_to_step11() -> None:
    state = DispatchState(active_step=None, build_round=0, last_step12_verdict=None)
    decision = decide(state, artifacts_present=True, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S3_STEP10_DONE
    assert decision.target == DispatchTarget.STEP_11
    assert decision.step10_warrant is None


def test_step11_mid_round_routes_to_step11() -> None:
    state = DispatchState(active_step=CustomizationStep.STEP_11, build_round=0)
    decision = decide(state, artifacts_present=True, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S4_STEP11_IN_FLIGHT
    assert decision.target == DispatchTarget.STEP_11
    assert decision.step10_warrant is None


def test_step12_clean_routes_to_step11() -> None:
    state = DispatchState(active_step=None, build_round=1, last_step12_verdict=Step12Verdict.CLEAN)
    decision = decide(state, artifacts_present=True, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S7_STEP12_CLEAN
    assert decision.target == DispatchTarget.STEP_11
    assert decision.step10_warrant is None


def test_step12_minor_routes_to_step11() -> None:
    state = DispatchState(active_step=None, build_round=1, last_step12_verdict=Step12Verdict.MINOR)
    decision = decide(state, artifacts_present=True, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S8_STEP12_MINOR
    assert decision.target == DispatchTarget.STEP_11
    assert decision.step10_warrant is None


def test_step12_spec_violating_routes_to_step11_not_step10() -> None:
    """The single most load-bearing pre-written answer: spec-violating does NOT escalate to step10."""
    state = DispatchState(
        active_step=None, build_round=1, last_step12_verdict=Step12Verdict.SPEC_VIOLATING
    )
    decision = decide(state, artifacts_present=True, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S9_STEP12_SPEC_VIOLATING
    assert decision.target == DispatchTarget.STEP_11
    assert decision.target != DispatchTarget.STEP_10
    assert decision.step10_warrant is None


# --- the two architect-derived states ---


def test_build_complete_routes_to_terminal_with_no_target() -> None:
    state = DispatchState()
    decision = decide(state, artifacts_present=True, build_complete_present=True)
    assert decision.state_id == DispatchStateId.S0_TERMINAL
    assert decision.target is None
    assert decision.step10_declined_because == "build is complete"


def test_terminal_wins_even_over_an_in_flight_step10() -> None:
    """Row order: S0_TERMINAL (row 1) is checked before S2_STEP10_IN_FLIGHT (row 2)."""
    state = DispatchState(active_step=CustomizationStep.STEP_10)
    decision = decide(state, artifacts_present=False, build_complete_present=True)
    assert decision.state_id == DispatchStateId.S0_TERMINAL
    assert decision.target is None


def test_step11_done_no_review_yet_routes_to_step12() -> None:
    state = DispatchState(active_step=None, build_round=1, last_step12_verdict=None)
    decision = decide(state, artifacts_present=True, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S5_STEP11_DONE
    assert decision.target == DispatchTarget.STEP_12
    assert decision.step10_warrant is None


# --- the remaining two rows: S2 (both warrant branches) and S6 ---


def test_step10_in_flight_greenfield_warrant() -> None:
    state = DispatchState(active_step=CustomizationStep.STEP_10, build_round=0)
    decision = decide(state, artifacts_present=False, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S2_STEP10_IN_FLIGHT
    assert decision.target == DispatchTarget.STEP_10
    assert decision.step10_warrant == Step10Warrant.GREENFIELD_NO_ARTIFACTS


def test_step10_in_flight_remodernization_warrant() -> None:
    state = DispatchState(active_step=CustomizationStep.STEP_10, build_round=0)
    decision = decide(state, artifacts_present=True, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S2_STEP10_IN_FLIGHT
    assert decision.target == DispatchTarget.STEP_10
    assert decision.step10_warrant == Step10Warrant.EXPLICIT_REMODERNIZATION


def test_step12_in_flight_resumes_step12() -> None:
    state = DispatchState(active_step=CustomizationStep.STEP_12, build_round=1)
    decision = decide(state, artifacts_present=True, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S6_STEP12_IN_FLIGHT
    assert decision.target == DispatchTarget.STEP_12
    assert decision.step10_warrant is None


# --- SS3.3: every non-step10 decision states why step10 was declined ---


@pytest.mark.parametrize(
    ("state", "artifacts_present", "build_complete_present"),
    [
        (DispatchState(), True, True),
        (DispatchState(active_step=CustomizationStep.STEP_11), True, False),
        (DispatchState(active_step=CustomizationStep.STEP_12), True, False),
        (DispatchState(), True, False),
        (DispatchState(build_round=1), True, False),
        (DispatchState(build_round=1, last_step12_verdict=Step12Verdict.CLEAN), True, False),
        (DispatchState(build_round=1, last_step12_verdict=Step12Verdict.MINOR), True, False),
        (
            DispatchState(build_round=1, last_step12_verdict=Step12Verdict.SPEC_VIOLATING),
            True,
            False,
        ),
    ],
)
def test_every_non_step10_decision_declines_step10_with_a_reason(
    state: DispatchState, artifacts_present: bool, build_complete_present: bool
) -> None:
    decision = decide(state, artifacts_present, build_complete_present)
    assert decision.target != DispatchTarget.STEP_10
    assert decision.step10_declined_because


# --- SS6.1: check_coherence's three cross-disk-truth checks (C1, C2, C3) ---


def test_c1_artifacts_absent_and_build_round_nonzero_is_incoherent() -> None:
    state = DispatchState(active_step=None, build_round=1, last_step12_verdict=None)
    assert check_coherence(state, artifacts_present=False) is not None


def test_c2_artifacts_absent_and_verdict_present_is_incoherent() -> None:
    state = DispatchState(active_step=None, build_round=1, last_step12_verdict=Step12Verdict.CLEAN)
    assert check_coherence(state, artifacts_present=False) is not None


def test_c2_fires_on_its_own_terms_even_when_c1_would_not() -> None:
    """`DispatchState`'s own validator (models/dispatch.py) guarantees `build_round >= 1` whenever
    `last_step12_verdict` is not None, so in practice C1 always also fires whenever C2's condition
    does -- constructed here via `model_construct` (bypassing that validator) purely to prove C2's
    own check line is independently correct, not merely reachable as a side effect of C1."""
    state = DispatchState.model_construct(
        active_step=None, build_round=0, last_step12_verdict=Step12Verdict.CLEAN
    )
    message = check_coherence(state, artifacts_present=False)
    assert message is not None
    assert "last_step12_verdict" in message


def test_c3_artifacts_absent_and_active_step_is_step11_is_incoherent() -> None:
    state = DispatchState(active_step=CustomizationStep.STEP_11, build_round=0)
    assert check_coherence(state, artifacts_present=False) is not None


def test_c3_artifacts_absent_and_active_step_is_step12_is_incoherent() -> None:
    state = DispatchState(active_step=CustomizationStep.STEP_12, build_round=0)
    assert check_coherence(state, artifacts_present=False) is not None


def test_coherent_states_pass_check_coherence() -> None:
    assert check_coherence(DispatchState(), artifacts_present=False) is None
    assert check_coherence(DispatchState(), artifacts_present=True) is None
    assert (
        check_coherence(DispatchState(active_step=CustomizationStep.STEP_10), artifacts_present=False)
        is None
    )


def test_incoherent_state_never_names_step10_as_a_dispatch_target() -> None:
    """SS8 criterion 5: a HALT must never read as a step10 recommendation."""
    state = DispatchState(active_step=None, build_round=1, last_step12_verdict=None)
    message = check_coherence(state, artifacts_present=False)
    assert message is not None
    assert "loopr-step10" not in message
