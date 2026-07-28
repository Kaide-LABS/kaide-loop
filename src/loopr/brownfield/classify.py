"""Classification request construction and verdict routing. Implements PHASE_1_SPEC.md SS6.7.3.

One BF_CLASSIFY call per bundle -- never batched. Routing per
docs/conformance-classification-spec.md section 5: CONFORM/DO_NOT_REPLICATE -> ledger, no gate;
CONFLICT -> Gate 3 (via the computed BrownfieldState.gate_3_required property); AMBIGUOUS -> a new
OpenQuestion feeding condition 6's existing ledger (loopr-MIGRATION.md section 1a) -- no seventh
condition, no parallel gate.
"""

from __future__ import annotations

from loopr.judge.envelope import make_call_id
from loopr.models.brownfield import EvidenceBundle, PatternClassification
from loopr.models.common import JudgeCallType, QuestionOrigin, QuestionStatus, Verdict
from loopr.models.interrogation import InterrogationState, OpenQuestion
from loopr.models.judge import JsonValue, JudgeRequest
from loopr.rubrics import RUBRICS


def build_classify_request(bundle: EvidenceBundle, state: InterrogationState) -> JudgeRequest:
    inputs: dict[str, JsonValue] = {
        "evidence_bundle": bundle.model_dump(mode="json"),
        "problem_statement": state.problem_statement,
        "acceptance_criteria": [c.text for c in state.acceptance_criteria],
        "scope_edges": [e.item for e in state.scope_edges],
        "boundary": state.boundary.text if state.boundary is not None else None,
    }
    rubric = RUBRICS[JudgeCallType.BF_CLASSIFY]
    call_id = make_call_id(JudgeCallType.BF_CLASSIFY.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.BF_CLASSIFY,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


def route_verdict(state: InterrogationState, classification: PatternClassification) -> InterrogationState:
    if state.brownfield is None:
        raise ValueError("route_verdict requires brownfield state")

    state.brownfield.classifications.append(classification)

    if classification.verdict == Verdict.AMBIGUOUS:
        question_id = f"pattern-ambiguity-{classification.pattern_id}"
        already_logged = any(q.id == question_id for q in state.open_questions)
        if not already_logged:
            state.open_questions.append(
                OpenQuestion(
                    id=question_id,
                    text=(
                        f"Pattern '{classification.pattern_id}' has conflicting evidence signals "
                        f"and no confident CONFORM/DO_NOT_REPLICATE/CONFLICT call is possible: "
                        f"{classification.reason}"
                    ),
                    origin=QuestionOrigin.PATTERN_AMBIGUITY,
                    status=QuestionStatus.OPEN,
                )
            )
    # CONFORM / DO_NOT_REPLICATE: routine, applied silently via the ledger renderer.
    # CONFLICT: gate_3_required recomputes from classifications -- nothing further to set here.
    return state
