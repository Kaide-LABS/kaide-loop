"""Round-cap force-resolution: guard G-6, acceptance B-4.

A permanently load-bearing open question must never block forever; at round `max_rounds` it is
force-resolved into a visible Assumption, and assumption-count parity must hold against the
rendered baby PRD.
"""

from __future__ import annotations

from loopr.interrogation.loop import step
from loopr.models.common import JudgeCallType, QuestionOrigin, QuestionStatus
from loopr.models.interrogation import (
    AcceptanceCriterion,
    Boundary,
    ContextNote,
    InterrogationState,
    OpenQuestion,
    ScopeEdge,
)
from loopr.models.common import NoteSource, ScopeEdgeKind
from loopr.models.judge import JudgeRequest, JudgeResponse


class AlwaysLoadBearingJudgeClient:
    """Answers every condition True except C6, which always reports load_bearing=True -- an
    unresolvable open question that must be swept up by the round cap, never looped on forever."""

    def ask(self, request: JudgeRequest) -> JudgeResponse | None:
        if request.call_type == JudgeCallType.C6_LOAD_BEARING:
            return JudgeResponse(call_id=request.call_id, passed=True, reason="always load-bearing")
        if request.call_type == JudgeCallType.C5_SOFT_CONTEXT:
            return JudgeResponse(call_id=request.call_id, passed=True, reason="genuine soft context")
        return JudgeResponse(call_id=request.call_id, passed=True, reason="ok")


def test_round_cap_force_resolves_unresolvable_question(greenfield_state: InterrogationState) -> None:
    greenfield_state.problem_statement = "on-call stops losing an hour to manual failover"
    greenfield_state.acceptance_criteria = [AcceptanceCriterion(text="the page returns a 200")]
    greenfield_state.scope_edges = [
        ScopeEdge(item="mobile app", kind=ScopeEdgeKind.DEFERRED, reason="not funded")
    ]
    from loopr.judge.envelope import digest

    boundary_text = "this phase covers the failover path only"
    greenfield_state.boundary = Boundary(
        text=boundary_text, confirmed=True, confirmed_hash=digest(boundary_text)
    )
    greenfield_state.context_notes = [ContextNote(text="clean slate", source=NoteSource.STATED)]
    greenfield_state.open_questions = [
        OpenQuestion(
            id="unresolvable-1",
            text="which cloud provider, forever undecided",
            origin=QuestionOrigin.USER,
            status=QuestionStatus.OPEN,
        )
    ]
    greenfield_state.max_rounds = 3

    client = AlwaysLoadBearingJudgeClient()
    state = greenfield_state
    for _ in range(10):
        outcome = step(state, client)
        state = outcome.state
        if outcome.exit_code != 30:  # QUESTION_REQUIRED
            break

    forced = [a for a in state.assumptions if a.source_question_id == "unresolvable-1"]
    assert forced, "the unresolvable question should have been force-resolved into an assumption"

    question = next(q for q in state.open_questions if q.id == "unresolvable-1")
    assert question.force_resolved is True
    assert question.status == QuestionStatus.DEFERRED_NON_LOAD_BEARING

    # Assumption-count parity (G-6): every force-resolution is rendered, none silent.
    from loopr.artifacts.baby_prd import render_baby_prd

    rendered = render_baby_prd(state, tldr="test")
    for assumption in state.assumptions:
        assert assumption.text in rendered
