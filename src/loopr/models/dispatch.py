"""Dispatch-controller state and decision models. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS3.

DispatchState is the three new persisted fields the confirmed boundary named
(`.claude/loopr/baby_prd.md`), nested under `InterrogationState.dispatch` rather than flat (SS0.2
deviation 1) so `state.round` (the six-condition interrogation counter) and
`state.dispatch.build_round` (the step11/step12 cycle count) can never be typed interchangeably.

DispatchDecision is the hard boundary's primary enforcement mechanism (SS3.3): a step10 dispatch is
unconstructable without a `Step10Warrant` drawn from the closed two-member enum, and a non-step10
decision is unconstructable without a stated reason step10 was declined. This moves "the reviewer
greps for it" up to "the type system rejects it".
"""

from __future__ import annotations

from pydantic import Field, model_validator

from loopr.models.common import (
    CustomizationStep,
    DispatchStateId,
    DispatchTarget,
    LooprBase,
    Step10Warrant,
    Step12Verdict,
)


class DispatchState(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
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
    discouraged. Incremented when step11 COMPLETES (not when it is dispatched) -- see SS6.3; that
    timing is what makes S3 and S5 distinguishable."""

    last_step12_verdict: Step12Verdict | None = None
    """The most recent step12 outcome, or None if step12 has not returned since the last step11
    dispatch. CLEARED when step11 is dispatched (SS6.3) -- without that clearing rule a stale verdict
    survives into the next round and S5 becomes indistinguishable from S7/S8/S9."""

    consecutive_spec_violating: int = Field(default=0, ge=0)
    """Added 2026-08-06 (.claude/loopr-rework-cap/baby_prd.md): how many `spec_violating` step12
    verdicts have been recorded IN A ROW for the phase currently being reworked. Incremented by
    `apply_completion_transition` when it records a `spec_violating` verdict, reset to 0 when it
    records `clean` or `minor`. DELIBERATELY NOT keyed on `build_round` -- `build_round` increments on
    every step11 completion, including a rework of the same phase (SS6.3), so it counts total rounds,
    not consecutive failures on one phase; it cannot answer 'is this phase stuck' by itself. A phase
    boundary (moving on to a new phase) only ever happens after step11 the round following a `clean`/
    `minor` verdict (SS6.2 point 2: the controller never learns the phase number, so `S7`/`S8` are the
    only routes that advance past a phase) -- that same verdict already resets this counter to 0, so
    no separate phase-boundary reset is needed."""

    @model_validator(mode="after")
    def check_field_coherence(self) -> "DispatchState":
        if self.last_step12_verdict is not None and self.build_round < 1:
            raise ValueError(
                "last_step12_verdict is only meaningful once step11 has completed at least one "
                f"round; got verdict={self.last_step12_verdict.value!r} with build_round=0"
            )
        if self.consecutive_spec_violating > 0 and self.build_round < 1:
            raise ValueError(
                "consecutive_spec_violating is only meaningful once step11 has completed at least "
                f"one round; got consecutive_spec_violating={self.consecutive_spec_violating} with "
                "build_round=0"
            )
        if self.active_step == CustomizationStep.STEP_10:
            if (
                self.build_round != 0
                or self.last_step12_verdict is not None
                or self.consecutive_spec_violating != 0
            ):
                raise ValueError(
                    "active_step=step_10 requires build_round=0, last_step12_verdict=None, and "
                    "consecutive_spec_violating=0 -- both entry paths reset them (greenfield: never "
                    "set; re-modernization: reset explicitly, SS0.2 deviation 3)"
                )
        return self


_NO_TARGET_STATE_IDS = frozenset({DispatchStateId.S0_TERMINAL, DispatchStateId.S10_REWORK_STALLED})
"""The only two `DispatchStateId` members that carry `target=None` -- build complete (nothing left to
run) and rework stalled (added 2026-08-06: a human decision is owed, not another subagent dispatch)."""


class DispatchDecision(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    """One decision. Deliberately carries NO timestamp -- the log writer adds that (dispatch/log.py),
    so a DispatchDecision is byte-stable and can be compared directly against a fixture's expected
    value with no field exclusions. A fixture comparison that has to ignore fields is a fixture
    comparison a third party cannot fully trust."""

    state_id: DispatchStateId
    target: DispatchTarget | None
    """None in S0_TERMINAL and (added 2026-08-06) S10_REWORK_STALLED -- the two state IDs that do not
    name a subagent to run. Enforced below."""
    reason: str = Field(min_length=1)
    """One sentence, present tense, naming the facts that decided it. Rendered verbatim to the human
    (SS4.3) -- write it for a person mid-loop, not for a log parser."""

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
        no_target = self.state_id in _NO_TARGET_STATE_IDS
        if no_target != (self.target is None):
            raise ValueError(
                "target is None iff state_id is S0_TERMINAL or S10_REWORK_STALLED -- the only two "
                "outcomes that do not name a subagent to run"
            )
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
                "evidence (SS3.3)"
            )
        return self
