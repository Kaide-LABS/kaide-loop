"""Judge-request construction and response application for step10 customization.

Implements CUSTOMIZATION_PHASE_1_SPEC.md SS4.1, SS4.3 layer 2. Two judge calls: STEP10_CUSTOMIZATION
drafts the customized output (drafted_text); STEP10_FIDELITY_JUDGE judges whether that output is
genuinely project-specific (passed) -- run only after layer 1's structural check passes.
"""

from __future__ import annotations

from loopr.errors import LooprError
from loopr.judge.envelope import make_call_id
from loopr.models.common import JudgeCallType
from loopr.models.interrogation import InterrogationState
from loopr.models.judge import JsonValue, JudgeRequest, JudgeResponse
from loopr.rubrics import RUBRICS


class CustomizationError(LooprError):
    """Raised when a judge response for a customization call doesn't carry the field its shape
    requires -- a malformed response from the invoking agent, not a normal failure mode."""


def _conformance_summary(state: InterrogationState) -> JsonValue:
    """A derived, compact projection of the conformance ledger -- verdict, pattern id, one-line
    reason -- never the raw ledger. Brownfield only; None for greenfield."""
    if state.brownfield is None:
        return None
    return [
        {
            "pattern_id": classification.pattern_id,
            "verdict": classification.verdict.value,
            "reason": classification.reason,
        }
        for classification in state.brownfield.classifications
    ]


def build_customization_request(state: InterrogationState, template_text: str) -> JudgeRequest:
    inputs: dict[str, JsonValue] = {
        "template_text": template_text,
        "problem_statement": state.problem_statement,
        "acceptance_criteria": [c.text for c in state.acceptance_criteria],
        "scope_edges": [e.item for e in state.scope_edges],
        "boundary": state.boundary.text if state.boundary is not None else None,
        "context_notes": [n.text for n in state.context_notes],
        "conformance_summary": _conformance_summary(state),
    }
    rubric = RUBRICS[JudgeCallType.STEP10_CUSTOMIZATION]
    call_id = make_call_id(JudgeCallType.STEP10_CUSTOMIZATION.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.STEP10_CUSTOMIZATION,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


def apply_customization_response(response: JudgeResponse) -> str:
    if response.drafted_text is None:
        raise CustomizationError("STEP10_CUSTOMIZATION response must carry drafted_text")
    return response.drafted_text


def build_fidelity_judge_request(
    state: InterrogationState, template_text: str, customized_text: str
) -> JudgeRequest:
    inputs: dict[str, JsonValue] = {
        "template_text": template_text,
        "customized_text": customized_text,
        "problem_statement": state.problem_statement,
        "acceptance_criteria": [c.text for c in state.acceptance_criteria],
        "boundary": state.boundary.text if state.boundary is not None else None,
    }
    rubric = RUBRICS[JudgeCallType.STEP10_FIDELITY_JUDGE]
    call_id = make_call_id(JudgeCallType.STEP10_FIDELITY_JUDGE.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.STEP10_FIDELITY_JUDGE,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


def apply_fidelity_judge_response(response: JudgeResponse) -> tuple[bool, str]:
    if response.passed is None:
        raise CustomizationError("STEP10_FIDELITY_JUDGE response must carry passed")
    return response.passed, response.reason
