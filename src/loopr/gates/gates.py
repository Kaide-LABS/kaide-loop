"""Gate payload construction, confirmation binding, and chronology. Implements PHASE_1_SPEC.md SS6.6.

Chronological firing order is Gate 2 -> Gate 3 -> Gate 1 (loopr-PRD.md section 4;
docs/conformance-classification-spec.md section 6), even though they are numbered and written up
1, 2, 3. Condition 4 requires a confirmed boundary before interrogation can stop, so Gate 2
necessarily fires during interrogation; Gate 3 (brownfield CONFLICTs) follows it; Gate 1 (baby PRD
TL;DR) is the final confirm on an already-settled spec.
"""

from __future__ import annotations

from pydantic import Field

from loopr.judge.envelope import digest
from loopr.models.common import GateId, LooprBase, Verdict
from loopr.models.gates import GatePayload, GateRecord
from loopr.models.interrogation import Boundary, InterrogationState


class GateResponse(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    gate: GateId
    confirmed: bool
    payload_digest: str = Field(min_length=1)
    amendment: str | None = None
    boundary_text: str | None = None
    declined: bool = False
    touched_surface: list[str] | None = None


def build_gate_payload(gate: GateId, title: str, body_markdown: str) -> GatePayload:
    return GatePayload(gate=gate, title=title, body_markdown=body_markdown, digest=digest(body_markdown))


def request_gate(state: InterrogationState, payload: GatePayload) -> InterrogationState:
    state.gates[payload.gate] = GateRecord(
        gate=payload.gate,
        requested_round=state.round,
        payload_digest=payload.digest,
    )
    return state


def gate_is_satisfied(state: InterrogationState, gate: GateId, current_payload_digest: str) -> bool:
    """True only if a confirmed record exists AND its confirmed digest matches the CURRENT payload.

    Any edit to the underlying content re-fires the gate automatically -- no separate dirty flag.
    """
    record = state.gates.get(gate)
    if record is None or not record.confirmed:
        return False
    return record.confirmed_payload_digest == current_payload_digest


def apply_gate_response(state: InterrogationState, response: GateResponse) -> InterrogationState:
    record = state.gates.get(response.gate)
    if record is None:
        raise ValueError(f"no gate request pending for {response.gate}")

    if response.gate == GateId.GATE_2_BOUNDARY:
        _apply_gate_2(state, response)
        # A boundary text change invalidates confirmation via the C4 hash check; recompute the
        # digest against the (possibly new) payload rather than trusting the caller's claim.
        new_body = render_gate_2_body(state)
        new_digest = digest(new_body)
        record.payload_digest = new_digest
        if response.confirmed:
            record.confirmed = True
            record.confirmed_payload_digest = new_digest
            record.user_amendment = response.amendment
        return state

    if response.confirmed and response.payload_digest == record.payload_digest:
        record.confirmed = True
        record.confirmed_payload_digest = response.payload_digest
        record.user_amendment = response.amendment
    return state


def _apply_gate_2(state: InterrogationState, response: GateResponse) -> None:
    if response.declined:
        if state.boundary is None:
            state.boundary = Boundary(text="(no boundary)", declined=True)
        else:
            state.boundary.declined = True
            state.boundary.confirmed = False
        return

    if response.boundary_text is not None:
        if state.boundary is None:
            state.boundary = Boundary(text=response.boundary_text)
        else:
            state.boundary.text = response.boundary_text
            state.boundary.confirmed = False
            state.boundary.confirmed_hash = None

    if response.confirmed and state.boundary is not None:
        # Order matters under validate_assignment=True: check_confirmation_coherent runs on every
        # single-field assignment, so confirmed_hash must land before confirmed flips to True.
        state.boundary.confirmed_hash = digest(state.boundary.text)
        state.boundary.confirmed = True

    if response.touched_surface is not None and state.brownfield is not None:
        state.brownfield.touched_surface = list(response.touched_surface)
        state.brownfield.touched_surface_confirmed_hash = digest(
            "\n".join(sorted(response.touched_surface))
        )


def render_gate_1_body(state: InterrogationState, tldr: str) -> str:
    lines = ["# Gate 1 -- Confirm the baby PRD (TL;DR first)", "", "## TL;DR", tldr, ""]
    if state.assumptions:
        lines.append("## Assumptions (force-resolved; kick any of these back into a question)")
        for assumption in state.assumptions:
            lines.append(f"- {assumption.text} (round {assumption.created_round})")
        lines.append("")
    lines.append("## Acceptance criteria")
    for criterion in state.acceptance_criteria:
        lines.append(f"- {criterion.text}")
    lines.append("")
    lines.append("## Scope edges")
    for edge in state.scope_edges:
        lines.append(f"- [{edge.kind.value}] {edge.item} -- {edge.reason}")
    return "\n".join(lines)


def render_gate_2_body(state: InterrogationState) -> str:
    lines = ["# Gate 2 -- Confirm the boundary"]
    if state.boundary is not None:
        lines += ["", "## Proposed boundary", state.boundary.text]
    if state.brownfield is not None:
        lines += ["", "## Proposed touched surface (brownfield)"]
        lines += [f"- {path}" for path in state.brownfield.touched_surface]
    return "\n".join(lines)


def render_gate_3_body(state: InterrogationState) -> str:
    lines = ["# Gate 3 -- Confirm pattern CONFLICTs (batched; routine calls never reach this gate)"]
    if state.brownfield is not None:
        for classification in state.brownfield.classifications:
            if classification.verdict == Verdict.CONFLICT:
                lines.append(f"- {classification.pattern_id}: {classification.reason}")
    return "\n".join(lines)
