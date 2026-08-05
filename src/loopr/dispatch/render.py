"""The dispatch output's legibility surface. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS4.3.

Legibility is a spec'd acceptance criterion here, not polish (SS0.1's soft context, SS8 criterion
9): a green fixture suite cannot detect an operator who re-derives the controller's choice by hand
instead of trusting the printed line. Kept in its own module, separate from `cli.py`, so the exact
output shape is unit-testable (golden-output tests, SS7 guard G6) without an argparse harness.
"""

from __future__ import annotations

from loopr.models.common import DispatchStateId, DispatchTarget
from loopr.models.dispatch import DispatchDecision, DispatchState

_LABEL_WIDTH = 11
"""Every label (`DISPATCH`, `STATE`, `WHY`, `NOT-STEP10`, `WARRANT`, `RUN`) is left-justified to this
width before the value -- `NOT-STEP10` is 10 characters, the widest label, plus one space."""


def _line(label: str, value: str) -> str:
    return f"{label:<{_LABEL_WIDTH}}{value}"


def render_human(decision: DispatchDecision) -> str:
    """The fixed four-(or-five-)line block CUSTOMIZATION_PHASE_3_SPEC.md SS4.3 specifies, plus a
    blank line and a copy-pasteable `RUN` line -- omitted on `S0_TERMINAL`, which has nothing to run.
    Fixed field order, fixed labels, no colour, no box drawing: this runs in whatever terminal the
    operator has. On every non-step10 decision the fourth line is `NOT-STEP10` -- simultaneously the
    operator's two-second spot-check and the machine-greppable Opus-avoidance record; on a step10
    dispatch it becomes `WARRANT` so a step10 call is visually unmistakable when scrolling.
    """
    if decision.state_id == DispatchStateId.S0_TERMINAL:
        lines = [
            _line("DISPATCH", "-- nothing; build is complete"),
            _line("STATE", f"{decision.state_id.value}  (build round {decision.build_round})"),
            _line("WHY", decision.reason),
            _line("NOT-STEP10", decision.step10_declined_because or ""),
        ]
        return "\n".join(lines)

    assert decision.target is not None  # unconstructable otherwise, models/dispatch.py SS3.3
    lines = [
        _line("DISPATCH", decision.target.value),
        _line("STATE", f"{decision.state_id.value}  (build round {decision.build_round})"),
        _line("WHY", decision.reason),
    ]
    if decision.target == DispatchTarget.STEP_10:
        assert decision.step10_warrant is not None  # unconstructable otherwise
        lines.append(_line("WARRANT", decision.step10_warrant.value))
    else:
        lines.append(_line("NOT-STEP10", decision.step10_declined_because or ""))
    lines.append("")
    lines.append(_line("RUN", f'Task(subagent_type="{decision.target.value}")'))
    return "\n".join(lines)


def render_json(decision: DispatchDecision) -> str:
    """`--json` output: `DispatchDecision.model_dump_json(indent=2)` verbatim, for machine consumers
    (CUSTOMIZATION_PHASE_3_SPEC.md SS4.1). No wrapping, no additional fields -- the model IS the
    contract."""
    return decision.model_dump_json(indent=2)


def render_halt(reason: str, state: DispatchState) -> str:
    """The HALT rendering (CUSTOMIZATION_PHASE_3_SPEC.md SS4.3): same fixed-label shape, printed to
    stderr by the caller, with the offending state dumped underneath so a human can see exactly what
    made the state incoherent. Not one of the two functions SS1's file table names by name, but the
    same module the table puts render_human/render_json in for the same reason -- SS4.3 specifies
    HALT's shape too, and it is equally unit-testable only if kept out of `cli.py`."""
    lines = [
        _line("DISPATCH", "-- HALT"),
        _line("STATE", "incoherent -- see below"),
        _line("WHY", reason),
        _line("NOT-STEP10", "state is incoherent; no target was chosen at all"),
        "",
        state.model_dump_json(indent=2),
    ]
    return "\n".join(lines)
