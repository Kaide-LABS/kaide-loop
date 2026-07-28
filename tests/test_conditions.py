"""Two-layer evaluator and the ConditionResult invariant (docs/stopping-test-spec.md)."""

from __future__ import annotations

import pytest

from loopr.checks.conditions import evaluate_all, lowest_false_condition
from loopr.judge.scripted_client import ScriptedJudgeClient
from loopr.models.common import ConditionId
from loopr.models.interrogation import AcceptanceCriterion, ConditionResult, InterrogationState
from loopr.models.judge import JudgeResponse


def test_condition_result_rejects_overall_true_without_structural_pass() -> None:
    with pytest.raises(ValueError):
        ConditionResult(
            condition=ConditionId.C2_ACCEPTANCE,
            structural_pass=False,
            judge_pass=True,
            overall=True,
            detail="bad",
        )


def test_condition_result_rejects_overall_true_without_judge_pass() -> None:
    with pytest.raises(ValueError):
        ConditionResult(
            condition=ConditionId.C2_ACCEPTANCE,
            structural_pass=True,
            judge_pass=None,
            overall=True,
            detail="bad",
        )


def test_condition_result_allows_c4_overall_true_without_judge() -> None:
    result = ConditionResult(
        condition=ConditionId.C4_BOUNDARY,
        structural_pass=True,
        judge_pass=None,
        overall=True,
        detail="ok",
    )
    assert result.overall is True


def test_evaluate_all_pending_request_is_lowest_numbered_gap(
    greenfield_state: InterrogationState,
) -> None:
    greenfield_state.problem_statement = "on-call stops losing an hour to manual failover"
    outcome = evaluate_all(greenfield_state)
    assert outcome.pending_request is not None
    assert outcome.pending_request.call_type.value == "c1_outcome"


def test_evaluate_all_never_batches_judge_calls(greenfield_state: InterrogationState) -> None:
    greenfield_state.problem_statement = "on-call stops losing an hour to manual failover"
    greenfield_state.acceptance_criteria = [AcceptanceCriterion(text="the page returns a 200")]
    outcome = evaluate_all(greenfield_state)
    pending_count = sum(1 for _ in [outcome.pending_request] if outcome.pending_request is not None)
    assert pending_count <= 1


def test_lowest_false_condition_empty_when_all_pass() -> None:
    results = [
        ConditionResult(
            condition=condition, structural_pass=True, judge_pass=True, overall=True, detail=""
        )
        for condition in ConditionId
    ]
    assert lowest_false_condition(results) is None


def test_judge_verdict_is_reused_once_answered(greenfield_state: InterrogationState) -> None:
    greenfield_state.problem_statement = "on-call stops losing an hour to manual failover"
    outcome = evaluate_all(greenfield_state)
    request = outcome.pending_request
    assert request is not None

    client = ScriptedJudgeClient(
        {request.call_id: JudgeResponse(call_id=request.call_id, passed=True, reason="clear outcome")}
    )
    response = client.ask(request)
    assert response is not None

    from loopr.judge.envelope import digest
    from loopr.models.judge import JudgeExchange

    greenfield_state.judge_log.append(
        JudgeExchange(
            request=request,
            response=response,
            request_sha256=digest(request.model_dump_json()),
            response_sha256=digest(response.model_dump_json()),
            answered_at_round=greenfield_state.round,
        )
    )

    outcome2 = evaluate_all(greenfield_state)
    c1_result = next(r for r in outcome2.results if r.condition == ConditionId.C1_OUTCOME)
    assert c1_result.overall is True
