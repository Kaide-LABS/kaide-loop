"""Gate confirmation binding and chronology (docs/conformance-classification-spec.md SS6)."""

from __future__ import annotations

from loopr.gates.gates import (
    GateResponse,
    apply_gate_response,
    build_gate_payload,
    gate_is_satisfied,
    render_gate_2_body,
    request_gate,
)
from loopr.models.common import GateId
from loopr.models.interrogation import InterrogationState


def test_gate_unsatisfied_before_confirmation(greenfield_state: InterrogationState) -> None:
    payload = build_gate_payload(GateId.GATE_1_BABY_PRD, "t", "body")
    request_gate(greenfield_state, payload)
    assert gate_is_satisfied(greenfield_state, GateId.GATE_1_BABY_PRD, payload.digest) is False


def test_gate_satisfied_after_confirmation(greenfield_state: InterrogationState) -> None:
    payload = build_gate_payload(GateId.GATE_1_BABY_PRD, "t", "body")
    request_gate(greenfield_state, payload)
    response = GateResponse(gate=GateId.GATE_1_BABY_PRD, confirmed=True, payload_digest=payload.digest)
    apply_gate_response(greenfield_state, response)
    assert gate_is_satisfied(greenfield_state, GateId.GATE_1_BABY_PRD, payload.digest) is True


def test_gate_2_boundary_tweak_reinvalidates_confirmation(greenfield_state: InterrogationState) -> None:
    payload = build_gate_payload(GateId.GATE_2_BOUNDARY, "t", render_gate_2_body(greenfield_state))
    request_gate(greenfield_state, payload)

    confirm_response = GateResponse(
        gate=GateId.GATE_2_BOUNDARY,
        confirmed=True,
        payload_digest=payload.digest,
        boundary_text="v1 boundary",
    )
    apply_gate_response(greenfield_state, confirm_response)
    confirmed_boundary = greenfield_state.boundary
    assert confirmed_boundary is not None
    assert confirmed_boundary.confirmed is True

    tweak_response = GateResponse(
        gate=GateId.GATE_2_BOUNDARY,
        confirmed=False,
        payload_digest="stale-digest",
        boundary_text="v2 boundary -- materially different",
    )
    apply_gate_response(greenfield_state, tweak_response)
    tweaked_boundary = greenfield_state.boundary
    assert tweaked_boundary is not None
    assert tweaked_boundary.confirmed is False
    assert tweaked_boundary.text == "v2 boundary -- materially different"


def test_gate_2_decline_sets_escape_hatch(greenfield_state: InterrogationState) -> None:
    payload = build_gate_payload(GateId.GATE_2_BOUNDARY, "t", render_gate_2_body(greenfield_state))
    request_gate(greenfield_state, payload)
    response = GateResponse(
        gate=GateId.GATE_2_BOUNDARY, confirmed=False, payload_digest=payload.digest, declined=True
    )
    apply_gate_response(greenfield_state, response)
    assert greenfield_state.boundary is not None
    assert greenfield_state.boundary.declined is True


def test_gate_3_only_conflicts_in_payload(brownfield_state: InterrogationState) -> None:
    from loopr.gates.gates import render_gate_3_body
    from loopr.models.brownfield import PatternClassification
    from loopr.models.common import Verdict

    assert brownfield_state.brownfield is not None
    brownfield_state.brownfield.classifications = [
        PatternClassification(pattern_id="p1", verdict=Verdict.CONFORM, reason="fine"),
        PatternClassification(pattern_id="p2", verdict=Verdict.CONFLICT, reason="breaks boundary"),
    ]
    body = render_gate_3_body(brownfield_state)
    assert "p2" in body
    assert "p1" not in body
