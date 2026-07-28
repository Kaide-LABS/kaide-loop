"""The two-layer condition evaluator. Implements PHASE_1_SPEC.md SS6.4 step 3, SS6.5.

Conditions are checked every round, not gated in strict order -- a later answer can
opportunistically close an earlier gap (docs/stopping-test-spec.md Cross-condition sequencing).
Structural checks always run first and are pure. Exactly one judge call is issued per evaluation
pass, for the lowest-numbered condition lacking a fresh judge verdict.
"""

from __future__ import annotations

from dataclasses import dataclass

from loopr.checks.structural import (
    check_c1_outcome,
    check_c2_acceptance,
    check_c3_scope_edges,
    check_c4_boundary,
    check_c5_soft_context,
    check_c6_no_unknowns,
)
from loopr.judge.envelope import make_call_id
from loopr.models.common import ConditionId, JudgeCallType, QuestionStatus
from loopr.models.interrogation import ConditionResult, InterrogationState, OpenQuestion
from loopr.models.judge import JsonValue, JudgeRequest, JudgeResponse
from loopr.rubrics import RUBRICS

_CONDITION_ORDER: tuple[ConditionId, ...] = (
    ConditionId.C1_OUTCOME,
    ConditionId.C2_ACCEPTANCE,
    ConditionId.C3_SCOPE_EDGES,
    ConditionId.C4_BOUNDARY,
    ConditionId.C5_SOFT_CONTEXT,
    ConditionId.C6_NO_UNKNOWNS,
)

_CALL_TYPE_FOR: dict[ConditionId, JudgeCallType] = {
    ConditionId.C1_OUTCOME: JudgeCallType.C1_OUTCOME,
    ConditionId.C2_ACCEPTANCE: JudgeCallType.C2_ACCEPTANCE,
    ConditionId.C3_SCOPE_EDGES: JudgeCallType.C3_SCOPE_EDGES,
    ConditionId.C5_SOFT_CONTEXT: JudgeCallType.C5_SOFT_CONTEXT,
    ConditionId.C6_NO_UNKNOWNS: JudgeCallType.C6_LOAD_BEARING,
}


@dataclass(frozen=True)
class EvaluationOutcome:
    results: list[ConditionResult]
    pending_request: JudgeRequest | None


def _scoped_inputs(condition: ConditionId, state: InterrogationState) -> dict[str, JsonValue] | None:
    """Build the exact Shape 1 / Shape 2 scoped-input dict for a condition's judge call.

    Returns None if there is currently nothing to judge (e.g. C5 with no unresolved note, C6 with
    no unjudged question).
    """
    if condition == ConditionId.C1_OUTCOME:
        return {
            "problem_statement": state.problem_statement,
            "prefilter_flagged": check_c1_outcome(state).advisory_flags != [],
        }
    if condition == ConditionId.C2_ACCEPTANCE:
        return {"acceptance_criteria": [c.text for c in state.acceptance_criteria]}
    if condition == ConditionId.C3_SCOPE_EDGES:
        return {
            "scope_edges": [
                {"item": e.item, "kind": e.kind.value, "reason": e.reason} for e in state.scope_edges
            ]
        }
    if condition == ConditionId.C5_SOFT_CONTEXT:
        unresolved = _first_unjudged_note_index(state)
        if unresolved is None:
            return None
        note = state.context_notes[unresolved]
        return {
            "context_note": note.text,
            "acceptance_criteria": [c.text for c in state.acceptance_criteria],
        }
    if condition == ConditionId.C6_NO_UNKNOWNS:
        question = _first_unjudged_question(state)
        if question is None:
            return None
        boundary_text = state.boundary.text if state.boundary is not None else None
        return {
            "question_text": question.text,
            "acceptance_criteria": [c.text for c in state.acceptance_criteria],
            "scope_edges": [e.item for e in state.scope_edges],
            "boundary": boundary_text,
        }
    raise AssertionError(f"condition {condition} has no judge call")


def _first_unjudged_note_index(state: InterrogationState) -> int | None:
    for index, note in enumerate(state.context_notes):
        if not _has_fresh_verdict(state, JudgeCallType.C5_SOFT_CONTEXT, {"context_note": note.text}):
            return index
    return None


def _any_note_confirmed_genuine(state: InterrogationState) -> bool:
    """True if at least one context note has a judged, non-misplaced, passing verdict."""
    for note in state.context_notes:
        for exchange in reversed(state.judge_log):
            if (
                exchange.request.call_type == JudgeCallType.C5_SOFT_CONTEXT
                and exchange.request.inputs.get("context_note") == note.text
            ):
                if exchange.response.passed is True and not exchange.response.misplaced:
                    return True
                break
    return False


def _first_unjudged_question(state: InterrogationState) -> OpenQuestion | None:
    for question in state.open_questions:
        if question.status != QuestionStatus.OPEN or question.load_bearing is not None:
            continue
        return question
    return None


def _has_fresh_verdict(
    state: InterrogationState, call_type: JudgeCallType, partial_inputs: dict[str, JsonValue]
) -> bool:
    """A verdict is fresh if the most recent exchange of this call type carried exactly the same
    partial-match inputs. We compare on the subset of keys provided, since C5/C6 vary the
    identifying key (context_note / question_text) while the cross-referenced fields may drift."""
    for exchange in reversed(state.judge_log):
        if exchange.request.call_type != call_type:
            continue
        if all(exchange.request.inputs.get(k) == v for k, v in partial_inputs.items()):
            return True
    return False


def _latest_response_for(
    state: InterrogationState, call_type: JudgeCallType, inputs: dict[str, JsonValue]
) -> JudgeResponse | None:
    for exchange in reversed(state.judge_log):
        if exchange.request.call_type == call_type and exchange.request.inputs == inputs:
            return exchange.response
    return None


def build_request(condition: ConditionId, state: InterrogationState) -> JudgeRequest:
    call_type = _CALL_TYPE_FOR[condition]
    inputs = _scoped_inputs(condition, state)
    if inputs is None:
        raise AssertionError(f"no pending judge input for condition {condition}")
    rubric = RUBRICS[call_type]
    call_id = make_call_id(call_type.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=call_type,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


_STRUCTURAL = {
    ConditionId.C1_OUTCOME: check_c1_outcome,
    ConditionId.C2_ACCEPTANCE: check_c2_acceptance,
    ConditionId.C3_SCOPE_EDGES: check_c3_scope_edges,
    ConditionId.C4_BOUNDARY: check_c4_boundary,
    ConditionId.C5_SOFT_CONTEXT: check_c5_soft_context,
    ConditionId.C6_NO_UNKNOWNS: check_c6_no_unknowns,
}


def evaluate_all(state: InterrogationState) -> EvaluationOutcome:
    results: list[ConditionResult] = []
    pending: JudgeRequest | None = None

    for condition in _CONDITION_ORDER:
        structural = _STRUCTURAL[condition](state)

        if not structural.passed:
            results.append(
                ConditionResult(
                    condition=condition,
                    structural_pass=False,
                    judge_pass=None,
                    overall=False,
                    detail=structural.detail,
                )
            )
            continue

        if condition == ConditionId.C4_BOUNDARY:
            results.append(
                ConditionResult(
                    condition=condition,
                    structural_pass=True,
                    judge_pass=None,
                    overall=True,
                    detail=structural.detail,
                )
            )
            continue

        call_type = _CALL_TYPE_FOR[condition]
        inputs = _scoped_inputs(condition, state)

        if inputs is None:
            # Nothing left to judge (every note/question already has a fresh verdict).
            if condition == ConditionId.C5_SOFT_CONTEXT:
                genuine = _any_note_confirmed_genuine(state)
                results.append(
                    ConditionResult(
                        condition=condition,
                        structural_pass=True,
                        judge_pass=genuine,
                        overall=genuine,
                        detail=(
                            "at least one note judge-confirmed as genuine soft context"
                            if genuine
                            else "all notes judged, none confirmed as genuine (misplaced or rejected)"
                        ),
                    )
                )
            else:
                results.append(
                    ConditionResult(
                        condition=condition,
                        structural_pass=True,
                        judge_pass=True,
                        overall=True,
                        detail="structural pass and all items already judge-confirmed",
                    )
                )
            continue

        cached = _latest_response_for(state, call_type, inputs)
        if cached is not None:
            passed = cached.passed is True
            results.append(
                ConditionResult(
                    condition=condition,
                    structural_pass=True,
                    judge_pass=passed,
                    overall=passed,
                    detail=f"judge verdict reused: {cached.reason}",
                )
            )
            continue

        results.append(
            ConditionResult(
                condition=condition,
                structural_pass=True,
                judge_pass=None,
                overall=False,
                detail="awaiting judge verdict",
            )
        )
        if pending is None:
            pending = build_request(condition, state)

    return EvaluationOutcome(results=results, pending_request=pending)


def lowest_false_condition(results: list[ConditionResult]) -> ConditionId | None:
    for result in results:
        if not result.overall:
            return result.condition
    return None
