"""Parametrizes over `tests/fixtures/dispatch/*.json`, the one-fixture-per-state data files.
Implements CUSTOMIZATION_PHASE_3_SPEC.md SS8 criterion 2. The CLI-level demonstration that
`loopr dispatch-verify` itself catches a deliberately corrupted fixture lives in
`test_dispatch_cli.py` (SS8 criterion 3).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopr.dispatch.controller import decide
from loopr.dispatch.render import render_human
from loopr.models.common import DispatchStateId, DispatchTarget
from loopr.models.dispatch import DispatchState

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "dispatch"
FIXTURE_PATHS = sorted(FIXTURES_DIR.glob("*.json"))


def test_exactly_one_fixture_per_state() -> None:
    """SS8 criterion 2: one fixture file per state -- ten states, ten fixtures."""
    assert len(FIXTURE_PATHS) == len(DispatchStateId)
    fixture_state_ids = set()
    for path in FIXTURE_PATHS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fixture_state_ids.add(payload["expected"]["state_id"])
    assert fixture_state_ids == {member.value for member in DispatchStateId}


def test_exactly_two_fixtures_are_marked_derived() -> None:
    """SS6.2: row 1 (S0_TERMINAL) and row 7 (S5_STEP11_DONE) are the two architect-derived additions;
    every other fixture is one of the user's six pre-written answers."""
    derived_ids = set()
    for path in FIXTURE_PATHS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["derived"]:
            derived_ids.add(payload["expected"]["state_id"])
    assert derived_ids == {
        DispatchStateId.S0_TERMINAL.value,
        DispatchStateId.S5_STEP11_DONE.value,
    }


@pytest.mark.parametrize("fixture_path", FIXTURE_PATHS, ids=lambda p: p.stem)
def test_fixture_matches_decide(fixture_path: Path) -> None:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    state = DispatchState.model_validate(payload["state"])
    decision = decide(
        state,
        artifacts_present=bool(payload["artifacts_present"]),
        build_complete_present=bool(payload["build_complete_present"]),
    )
    expected = payload["expected"]
    assert decision.state_id.value == expected["state_id"]
    assert (decision.target.value if decision.target is not None else None) == expected["target"]
    assert (
        decision.step10_warrant.value if decision.step10_warrant is not None else None
    ) == expected["step10_warrant"]


@pytest.mark.parametrize("fixture_path", FIXTURE_PATHS, ids=lambda p: p.stem)
def test_render_human_golden_shape(fixture_path: Path) -> None:
    """SS7 guard G6: a golden-output test per state. render_human() must stay <= 6 lines, in the
    fixed label order, with NOT-STEP10 on every non-step10 decision and WARRANT on every step10 one.
    """
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    state = DispatchState.model_validate(payload["state"])
    decision = decide(
        state,
        artifacts_present=bool(payload["artifacts_present"]),
        build_complete_present=bool(payload["build_complete_present"]),
    )
    rendered = render_human(decision)
    lines = rendered.splitlines()

    assert len(lines) <= 6
    assert lines[0].startswith("DISPATCH")
    assert lines[1].startswith("STATE")
    assert lines[2].startswith("WHY")

    if decision.target == DispatchTarget.STEP_10:
        assert lines[3].startswith("WARRANT")
        assert not any(line.startswith("NOT-STEP10") for line in lines)
    elif decision.state_id != DispatchStateId.S0_TERMINAL:
        assert lines[3].startswith("NOT-STEP10")
        assert lines[4] == ""
        assert lines[5].startswith("RUN")
    else:
        assert lines[3].startswith("NOT-STEP10")
