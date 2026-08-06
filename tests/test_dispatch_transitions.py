"""The full round-trip trace, asserted step by step. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS6.4,
SS8 criterion 6. Drives `decide()` plus the transition helpers exactly the way `cli.py`'s `dispatch`
and `dispatch-complete` commands do, without going through argparse -- the CLI-level equivalent lives
in `test_dispatch_cli.py`.
"""

from __future__ import annotations

from loopr.dispatch.controller import apply_completion_transition, apply_dispatch_transition, decide
from loopr.models.common import CustomizationStep, DispatchStateId, DispatchTarget, Step12Verdict
from loopr.models.dispatch import DispatchState


def test_full_round_trip_trace_reproduces_exactly() -> None:
    """CUSTOMIZATION_PHASE_3_SPEC.md SS6.4's worked example, reproduced exactly, including the
    clearing rule (step11 dispatch always resets last_step12_verdict to None) and the
    completion-timed increment (build_round increments on step11 COMPLETION, not dispatch)."""
    artifacts_present = True
    build_complete_present = False
    step10_dispatch_count = 0

    def note_target(target: DispatchTarget | None) -> None:
        nonlocal step10_dispatch_count
        if target == DispatchTarget.STEP_10:
            step10_dispatch_count += 1

    # (None, 0, None) + artifacts -> S3 -> step11 ; state becomes (STEP_11, 0, None)
    state = DispatchState()
    decision = decide(state, artifacts_present, build_complete_present)
    note_target(decision.target)
    assert decision.state_id == DispatchStateId.S3_STEP10_DONE
    assert decision.target == DispatchTarget.STEP_11
    state = apply_dispatch_transition(state, decision.target)
    assert state == DispatchState(active_step=CustomizationStep.STEP_11, build_round=0)

    # (STEP_11, 0, None) -> S4 -> step11 (resume)
    decision = decide(state, artifacts_present, build_complete_present)
    note_target(decision.target)
    assert decision.state_id == DispatchStateId.S4_STEP11_IN_FLIGHT
    assert decision.target == DispatchTarget.STEP_11

    # complete(step11) -> state becomes (None, 1, None)
    state = apply_completion_transition(state, CustomizationStep.STEP_11, None)
    assert state == DispatchState(active_step=None, build_round=1, last_step12_verdict=None)

    # (None, 1, None) -> S5 -> step12 ; state becomes (STEP_12, 1, None)
    decision = decide(state, artifacts_present, build_complete_present)
    note_target(decision.target)
    assert decision.state_id == DispatchStateId.S5_STEP11_DONE
    assert decision.target == DispatchTarget.STEP_12
    state = apply_dispatch_transition(state, decision.target)
    assert state == DispatchState(active_step=CustomizationStep.STEP_12, build_round=1)

    # (STEP_12, 1, None) -> S6 -> step12 (resume)
    decision = decide(state, artifacts_present, build_complete_present)
    note_target(decision.target)
    assert decision.state_id == DispatchStateId.S6_STEP12_IN_FLIGHT
    assert decision.target == DispatchTarget.STEP_12

    # complete(step12, CLEAN) -> state becomes (None, 1, CLEAN)
    state = apply_completion_transition(state, CustomizationStep.STEP_12, Step12Verdict.CLEAN)
    assert state == DispatchState(
        active_step=None, build_round=1, last_step12_verdict=Step12Verdict.CLEAN
    )

    # (None, 1, CLEAN) -> S7 -> step11 ; state becomes (STEP_11, 1, None)
    decision = decide(state, artifacts_present, build_complete_present)
    note_target(decision.target)
    assert decision.state_id == DispatchStateId.S7_STEP12_CLEAN
    assert decision.target == DispatchTarget.STEP_11
    state = apply_dispatch_transition(state, decision.target)
    assert state == DispatchState(active_step=CustomizationStep.STEP_11, build_round=1)

    # complete(step11) -> state becomes (None, 2, None)
    state = apply_completion_transition(state, CustomizationStep.STEP_11, None)
    assert state == DispatchState(active_step=None, build_round=2, last_step12_verdict=None)

    # (None, 2, None) -> S5 -> step12 ; state becomes (STEP_12, 2, None)
    decision = decide(state, artifacts_present, build_complete_present)
    note_target(decision.target)
    assert decision.state_id == DispatchStateId.S5_STEP11_DONE
    assert decision.target == DispatchTarget.STEP_12
    state = apply_dispatch_transition(state, decision.target)
    assert state == DispatchState(active_step=CustomizationStep.STEP_12, build_round=2)

    # complete(step12, SPEC_VIOLATING) -> state becomes (None, 2, SPEC_VIOLATING); the new
    # consecutive_spec_violating counter (added 2026-08-06) also ticks to 1 here.
    state = apply_completion_transition(
        state, CustomizationStep.STEP_12, Step12Verdict.SPEC_VIOLATING
    )
    assert state == DispatchState(
        active_step=None,
        build_round=2,
        last_step12_verdict=Step12Verdict.SPEC_VIOLATING,
        consecutive_spec_violating=1,
    )

    # (None, 2, SPEC_VIOLATING) -> S9 -> step11 (rework) ; state becomes (STEP_11, 2, None)
    decision = decide(state, artifacts_present, build_complete_present)
    note_target(decision.target)
    assert decision.state_id == DispatchStateId.S9_STEP12_SPEC_VIOLATING
    assert decision.target == DispatchTarget.STEP_11
    state = apply_dispatch_transition(state, decision.target)
    # the clearing rule resets last_step12_verdict, but NOT consecutive_spec_violating -- the streak
    # must survive the rework dispatch, or a stall spanning 3 rounds could never be counted.
    assert state == DispatchState(
        active_step=CustomizationStep.STEP_11, build_round=2, consecutive_spec_violating=1
    )

    # complete(step11) -> state becomes (None, 3, None); the streak (1) is untouched by a step11
    # completion -- only a step12 verdict writes it.
    state = apply_completion_transition(state, CustomizationStep.STEP_11, None)
    assert state == DispatchState(
        active_step=None, build_round=3, last_step12_verdict=None, consecutive_spec_violating=1
    )

    # (None, 3, None) -> S5 -> step12
    decision = decide(state, artifacts_present, build_complete_present)
    note_target(decision.target)
    assert decision.state_id == DispatchStateId.S5_STEP11_DONE
    assert decision.target == DispatchTarget.STEP_12

    # SS8 criterion 6 + SS6.4's own closing line: zero step10 dispatches across the entire trace.
    assert step10_dispatch_count == 0


def test_clearing_rule_prevents_stale_verdict_from_surviving_a_dispatch() -> None:
    """Without the clearing rule, a CLEAN verdict from an earlier round would survive step11's
    dispatch and make the post-completion state ambiguous between S5 and S7 (SS6.3's own worked
    counter-example)."""
    state = DispatchState(active_step=None, build_round=1, last_step12_verdict=Step12Verdict.CLEAN)
    dispatched = apply_dispatch_transition(state, DispatchTarget.STEP_11)
    assert dispatched.last_step12_verdict is None

    completed = apply_completion_transition(dispatched, CustomizationStep.STEP_11, None)
    assert completed.last_step12_verdict is None
    decision = decide(completed, artifacts_present=True, build_complete_present=False)
    assert decision.state_id == DispatchStateId.S5_STEP11_DONE


def test_complete_step10_clears_active_step_only() -> None:
    """SS6.3: `complete(step10) -> active_step = None` -- neither `build_round` nor
    `last_step12_verdict` moves, since step10 completing doesn't build or review a round."""
    state = DispatchState(active_step=CustomizationStep.STEP_10)
    completed = apply_completion_transition(state, CustomizationStep.STEP_10, None)
    assert completed == DispatchState(active_step=None, build_round=0, last_step12_verdict=None)


def test_build_round_increments_on_completion_not_dispatch() -> None:
    """SS6.3: incrementing on dispatch instead of completion would make S3 read build_round==1 for a
    round that was never actually built."""
    state = DispatchState()
    dispatched = apply_dispatch_transition(state, DispatchTarget.STEP_11)
    assert dispatched.build_round == 0

    completed = apply_completion_transition(dispatched, CustomizationStep.STEP_11, None)
    assert completed.build_round == 1


# --- Added 2026-08-06 (.claude/loopr-rework-cap/baby_prd.md): the rework-stall cap ---


def test_mixed_verdict_sequence_does_not_false_trigger_the_stall_threshold() -> None:
    """Acceptance criterion 2: a sequence that interleaves clean/minor with spec_violating verdicts is
    healthy iteration (rework converging, then a fresh phase starting), not a stall -- the counter must
    not silently carry a partial streak across a clean/minor verdict. Drives the full dispatch/complete
    cycle exactly like `cli.py` does, the same style as `test_full_round_trip_trace_reproduces_exactly`.
    Only a genuine run of `_REWORK_STALL_THRESHOLD` consecutive spec_violating verdicts stalls."""
    artifacts_present = True
    build_complete_present = False

    def build_and_review(state: DispatchState, verdict: Step12Verdict) -> DispatchState:
        decision = decide(state, artifacts_present, build_complete_present)
        assert decision.target == DispatchTarget.STEP_11
        state = apply_dispatch_transition(state, decision.target)
        state = apply_completion_transition(state, CustomizationStep.STEP_11, None)

        decision = decide(state, artifacts_present, build_complete_present)
        assert decision.target == DispatchTarget.STEP_12
        state = apply_dispatch_transition(state, decision.target)
        return apply_completion_transition(state, CustomizationStep.STEP_12, verdict)

    state = DispatchState()

    # two spec_violating verdicts in a row on the same phase: ordinary rework, below the threshold.
    state = build_and_review(state, Step12Verdict.SPEC_VIOLATING)
    assert state.consecutive_spec_violating == 1
    state = build_and_review(state, Step12Verdict.SPEC_VIOLATING)
    assert state.consecutive_spec_violating == 2
    assert (
        decide(state, artifacts_present, build_complete_present).state_id
        == DispatchStateId.S9_STEP12_SPEC_VIOLATING
    )

    # a clean verdict resets the streak -- the phase converged, it did not stall.
    state = build_and_review(state, Step12Verdict.CLEAN)
    assert state.consecutive_spec_violating == 0
    assert (
        decide(state, artifacts_present, build_complete_present).state_id
        == DispatchStateId.S7_STEP12_CLEAN
    )

    # a fresh run of consecutive spec_violating verdicts on the next phase genuinely stalls at 3.
    for _ in range(2):
        state = build_and_review(state, Step12Verdict.SPEC_VIOLATING)
    assert state.consecutive_spec_violating == 2
    assert (
        decide(state, artifacts_present, build_complete_present).state_id
        == DispatchStateId.S9_STEP12_SPEC_VIOLATING
    )

    state = build_and_review(state, Step12Verdict.SPEC_VIOLATING)
    assert state.consecutive_spec_violating == 3
    decision = decide(state, artifacts_present, build_complete_present)
    assert decision.state_id == DispatchStateId.S10_REWORK_STALLED
    assert decision.target is None
