"""The single state advance. Implements PHASE_1_SPEC.md SS6.4.

step() is pure with respect to the filesystem -- it does not read or write files; the CLI does.
Ordered algorithm; the order is load-bearing, do not reorder (see PHASE_1_SPEC.md SS6.4 for the
six-step rationale). Exactly one judge call, one question, or one gate is surfaced per invocation
that requires suspension; a client able to answer in-process (ScriptedJudgeClient) lets the loop
continue synchronously within the same call.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from loopr import exit_codes
from loopr.brownfield.classify import build_classify_request, route_verdict
from loopr.brownfield.discovery import (
    apply_relevance_response,
    build_relevance_request,
    prefilter_candidates,
)
from loopr.brownfield.evidence import discover_patterns
from loopr.checks.conditions import build_request, evaluate_all, lowest_false_condition
from loopr.errors import LooprError
from loopr.gates.gates import (
    GateResponse,
    apply_gate_response,
    build_gate_payload,
    gate_is_satisfied,
    render_gate_1_body,
    render_gate_3_body,
    request_gate,
)
from loopr.interrogation.questions import build_followup
from loopr.judge.envelope import digest
from loopr.judge.port import JudgeClient
from loopr.models.brownfield import PatternClassification
from loopr.models.common import ConditionId, GateId, JudgeCallType, Mode
from loopr.models.gates import GatePayload
from loopr.models.interrogation import Assumption, InterrogationState, OpenQuestion
from loopr.models.judge import JudgeExchange, JudgeRequest, JudgeResponse

_MAX_INTERNAL_ITERATIONS = 200


class InboundKind(str, Enum):
    """Judge responses are NOT delivered via InboundPayload -- they are paired to their pending
    request by the judge client itself (see cli.ResumingAgentJudgeClient), because step() always
    calls judge.ask() fresh and a client may answer in-process or from a preloaded file."""

    GATE = "gate"
    ANSWER = "answer"


@dataclass(frozen=True)
class InboundPayload:
    kind: InboundKind
    gate_response: GateResponse | None = None
    answer_target: ConditionId | None = None
    answer_text: str | None = None


@dataclass
class StepOutcome:
    state: InterrogationState
    exit_code: int
    pending_judge_request: JudgeRequest | None = None
    pending_gate_payload: GatePayload | None = None
    pending_question_text: str | None = None
    pending_question_target: ConditionId | None = None


class StateInvariantError(LooprError):
    """Raised when applying inbound data would violate a loopr invariant (mismatched call_id etc.)."""


def _apply_judge_exchange(
    state: InterrogationState, request: JudgeRequest, response: JudgeResponse
) -> InterrogationState:
    if response.call_id != request.call_id:
        raise StateInvariantError(
            f"judge response call_id={response.call_id!r} does not match request "
            f"call_id={request.call_id!r}"
        )
    exchange = JudgeExchange(
        request=request,
        response=response,
        request_sha256=digest(request.model_dump_json()),
        response_sha256=digest(response.model_dump_json()),
        answered_at_round=state.round,
    )
    state.judge_log.append(exchange)

    if request.call_type == JudgeCallType.C1_OUTCOME:
        if response.passed:
            state.consecutive_judge_failures[ConditionId.C1_OUTCOME] = 0
        else:
            state.consecutive_judge_failures[ConditionId.C1_OUTCOME] = (
                state.consecutive_judge_failures.get(ConditionId.C1_OUTCOME, 0) + 1
            )
    elif request.call_type == JudgeCallType.C2_ACCEPTANCE and response.passed:
        for criterion in state.acceptance_criteria:
            criterion.judge_confirmed_testable = True
    elif request.call_type == JudgeCallType.C5_SOFT_CONTEXT and response.misplaced:
        note_text = request.inputs.get("context_note")
        if isinstance(note_text, str):
            from loopr.models.interrogation import AcceptanceCriterion

            state.acceptance_criteria.append(AcceptanceCriterion(text=note_text))
    elif request.call_type == JudgeCallType.C6_LOAD_BEARING:
        question_text = request.inputs.get("question_text")
        for question in state.open_questions:
            if question.text == question_text and question.load_bearing is None:
                question.load_bearing = response.passed is True
                break

    return state


def _force_resolve_round_cap(state: InterrogationState) -> InterrogationState:
    """Guard G-6: every force-resolution writes a visible Assumption. Never silent."""
    from loopr.models.common import QuestionStatus

    for question in state.open_questions:
        if question.status != QuestionStatus.OPEN:
            continue
        guess = f"(assumed, round cap reached) {question.text} -> proceeding with no changes needed"
        question.resolution = guess
        question.status = QuestionStatus.DEFERRED_NON_LOAD_BEARING
        question.force_resolved = True
        state.assumptions.append(
            Assumption(text=guess, source_question_id=question.id, created_round=state.round)
        )
    return state


def _build_tldr(state: InterrogationState) -> str:
    outcome = state.problem_statement or "(no outcome stated)"
    criteria_count = len(state.acceptance_criteria)
    edges_count = len(state.scope_edges)
    return (
        f"{outcome} -- {criteria_count} acceptance criterion(ia), {edges_count} scope edge(s) "
        "named."
    )


def step(
    state: InterrogationState,
    judge: JudgeClient,
    inbound: InboundPayload | None = None,
) -> StepOutcome:
    if inbound is not None:
        state = _apply_inbound(state, inbound)

    if state.mode == Mode.BROWNFIELD and state.brownfield is not None:
        boundary_settled = state.boundary is not None and (
            state.boundary.confirmed or state.boundary.declined
        )
        brownfield = state.brownfield

        if boundary_settled and not brownfield.touched_surface:
            candidates = prefilter_candidates(Path(state.repo_root), state)
            request = build_relevance_request(candidates, state)
            response = judge.ask(request)
            if response is None:
                return StepOutcome(
                    state=state, exit_code=exit_codes.JUDGE_REQUIRED, pending_judge_request=request
                )
            state = _apply_judge_exchange(state, request, response)
            state = apply_relevance_response(state, response)

        if brownfield.touched_surface and not brownfield.pattern_candidates:
            brownfield.pattern_candidates = discover_patterns(
                Path(state.repo_root), brownfield.touched_surface
            )

        classified_ids = {c.pattern_id for c in brownfield.classifications}
        for bundle in brownfield.pattern_candidates:
            if bundle.pattern_id in classified_ids:
                continue
            request = build_classify_request(bundle, state)
            response = judge.ask(request)
            if response is None:
                return StepOutcome(
                    state=state, exit_code=exit_codes.JUDGE_REQUIRED, pending_judge_request=request
                )
            state = _apply_judge_exchange(state, request, response)
            if response.verdict is None:
                raise StateInvariantError("BF_CLASSIFY response must carry a verdict")
            classification = PatternClassification(
                pattern_id=bundle.pattern_id, verdict=response.verdict, reason=response.reason
            )
            state = route_verdict(state, classification)
            break  # one classification per invocation -- never batched (SS6.7.3)

    for _ in range(_MAX_INTERNAL_ITERATIONS):
        if state.round >= state.max_rounds:
            state = _force_resolve_round_cap(state)

        outcome = evaluate_all(state)
        state.condition_results = outcome.results

        if outcome.pending_request is not None:
            response = judge.ask(outcome.pending_request)
            if response is None:
                return StepOutcome(
                    state=state,
                    exit_code=exit_codes.JUDGE_REQUIRED,
                    pending_judge_request=outcome.pending_request,
                )
            state = _apply_judge_exchange(state, outcome.pending_request, response)
            continue

        all_pass = all(result.overall for result in outcome.results)
        if not all_pass:
            target = lowest_false_condition(outcome.results)
            assert target is not None

            if target == ConditionId.C4_BOUNDARY:
                # Condition 4 is a pure state-machine check (no judge, no free-text question) --
                # it is resolved through Gate 2, which fires during interrogation, before Gate 1
                # (loopr-PRD.md section 4; docs/conformance-classification-spec.md section 6).
                from loopr.gates.gates import render_gate_2_body

                body = render_gate_2_body(state)
                payload = build_gate_payload(GateId.GATE_2_BOUNDARY, "Gate 2 -- Boundary", body)
                if gate_is_satisfied(state, GateId.GATE_2_BOUNDARY, payload.digest):
                    # Payload confirmed but the underlying boundary field is still unset/stale --
                    # a defect elsewhere, not a state a well-behaved gate should reach silently.
                    raise StateInvariantError(
                        "Gate 2 reports satisfied but condition 4 still fails; state is inconsistent"
                    )
                state = request_gate(state, payload)
                return StepOutcome(
                    state=state, exit_code=exit_codes.GATE_REQUIRED, pending_gate_payload=payload
                )

            question_text = build_followup(state, target)
            state.round += 1
            return StepOutcome(
                state=state,
                exit_code=exit_codes.QUESTION_REQUIRED,
                pending_question_text=question_text,
                pending_question_target=target,
            )

        if (
            state.brownfield is not None
            and state.brownfield.gate_3_required
            and not state.brownfield.gate_3_confirmed
        ):
            body = render_gate_3_body(state)
            payload = build_gate_payload(GateId.GATE_3_CONFLICTS, "Gate 3 -- CONFLICTs", body)
            if gate_is_satisfied(state, GateId.GATE_3_CONFLICTS, payload.digest):
                state.brownfield.gate_3_confirmed = True
            else:
                state = request_gate(state, payload)
                return StepOutcome(
                    state=state, exit_code=exit_codes.GATE_REQUIRED, pending_gate_payload=payload
                )

        tldr = _build_tldr(state)
        gate1_body = render_gate_1_body(state, tldr)
        gate1_payload = build_gate_payload(GateId.GATE_1_BABY_PRD, "Gate 1 -- Baby PRD", gate1_body)
        if not gate_is_satisfied(state, GateId.GATE_1_BABY_PRD, gate1_payload.digest):
            state = request_gate(state, gate1_payload)
            return StepOutcome(
                state=state, exit_code=exit_codes.GATE_REQUIRED, pending_gate_payload=gate1_payload
            )

        return StepOutcome(state=state, exit_code=exit_codes.COMPLETE)

    raise StateInvariantError("step() did not converge within the internal iteration cap")


def _apply_inbound(state: InterrogationState, inbound: InboundPayload) -> InterrogationState:
    if inbound.kind == InboundKind.GATE:
        if inbound.gate_response is None:
            raise StateInvariantError("gate inbound requires gate_response")
        return apply_gate_response(state, inbound.gate_response)

    if inbound.kind == InboundKind.ANSWER:
        if inbound.answer_text is None or inbound.answer_target is None:
            raise StateInvariantError("answer inbound requires answer_target and answer_text")
        return _apply_answer(state, inbound.answer_target, inbound.answer_text)

    raise StateInvariantError(f"unhandled inbound kind {inbound.kind}")


def _apply_answer(
    state: InterrogationState, target: ConditionId, answer_text: str
) -> InterrogationState:
    from loopr.models.common import NoteSource, ScopeEdgeKind
    from loopr.models.interrogation import AcceptanceCriterion, ContextNote, ScopeEdge

    if target == ConditionId.C1_OUTCOME:
        state.problem_statement = answer_text
    elif target == ConditionId.C2_ACCEPTANCE:
        state.acceptance_criteria.append(AcceptanceCriterion(text=answer_text))
    elif target == ConditionId.C3_SCOPE_EDGES:
        state.scope_edges.append(
            ScopeEdge(item=answer_text, kind=ScopeEdgeKind.OUT, reason="user-stated")
        )
    elif target == ConditionId.C5_SOFT_CONTEXT:
        state.context_notes.append(ContextNote(text=answer_text, source=NoteSource.STATED))
    elif target == ConditionId.C6_NO_UNKNOWNS:
        next_id = f"user-question-{len(state.open_questions) + 1}"
        from loopr.models.common import QuestionOrigin, QuestionStatus

        state.open_questions.append(
            OpenQuestion(
                id=next_id,
                text=answer_text,
                origin=QuestionOrigin.USER,
                status=QuestionStatus.OPEN,
            )
        )
    return state
