"""Structural pre-check tests (docs/stopping-test-spec.md conditions 1-6)."""

from __future__ import annotations

from loopr.checks.structural import (
    check_c1_outcome,
    check_c2_acceptance,
    check_c3_scope_edges,
    check_c4_boundary,
    check_c5_soft_context,
    check_c6_no_unknowns,
)
from loopr.models.common import NoteSource, QuestionOrigin, QuestionStatus, ScopeEdgeKind
from loopr.models.interrogation import (
    AcceptanceCriterion,
    Boundary,
    ContextNote,
    InterrogationState,
    OpenQuestion,
    ScopeEdge,
)


def test_c1_empty_fails(greenfield_state: InterrogationState) -> None:
    assert check_c1_outcome(greenfield_state).passed is False


def test_c1_non_empty_passes(greenfield_state: InterrogationState) -> None:
    greenfield_state.problem_statement = "On-call stops losing an hour to manual failover"
    assert check_c1_outcome(greenfield_state).passed is True


def test_c1_prefilter_flags_but_does_not_block(greenfield_state: InterrogationState) -> None:
    greenfield_state.problem_statement = "Build a tool to automate deploys"
    result = check_c1_outcome(greenfield_state)
    assert result.passed is True  # non-empty is the only hard gate
    assert result.advisory_flags != []


def test_c2_empty_fails(greenfield_state: InterrogationState) -> None:
    assert check_c2_acceptance(greenfield_state).passed is False


def test_c2_subjective_only_fails(greenfield_state: InterrogationState) -> None:
    greenfield_state.acceptance_criteria = [AcceptanceCriterion(text="it feels fast and good")]
    assert check_c2_acceptance(greenfield_state).passed is False


def test_c2_observable_predicate_passes(greenfield_state: InterrogationState) -> None:
    greenfield_state.acceptance_criteria = [AcceptanceCriterion(text="the page returns a 200")]
    assert check_c2_acceptance(greenfield_state).passed is True


def test_c3_empty_fails(greenfield_state: InterrogationState) -> None:
    assert check_c3_scope_edges(greenfield_state).passed is False


def test_c3_empty_reason_is_unconstructible() -> None:
    """An edge without a stated reason isn't load-bearing, it's a guess -- the model itself
    refuses to even construct one (str_strip_whitespace + min_length=1), a stronger guarantee
    than the structural check alone (docs/stopping-test-spec.md Condition 3)."""
    import pytest

    with pytest.raises(Exception):
        ScopeEdge(item="mobile app", kind=ScopeEdgeKind.OUT, reason=" ")


def test_c3_well_formed_edge_passes(greenfield_state: InterrogationState) -> None:
    greenfield_state.scope_edges = [
        ScopeEdge(item="mobile app", kind=ScopeEdgeKind.DEFERRED, reason="not funded this quarter")
    ]
    assert check_c3_scope_edges(greenfield_state).passed is True


def test_c4_no_boundary_fails(greenfield_state: InterrogationState) -> None:
    assert check_c4_boundary(greenfield_state).passed is False


def test_c4_confirmed_boundary_passes(greenfield_state: InterrogationState) -> None:
    from loopr.judge.envelope import digest

    text = "this phase adds refunds; it does not touch charge-retry logic"
    greenfield_state.boundary = Boundary(text=text, confirmed=True, confirmed_hash=digest(text))
    assert check_c4_boundary(greenfield_state).passed is True


def test_c4_stale_confirmation_fails(greenfield_state: InterrogationState) -> None:
    from loopr.judge.envelope import digest

    greenfield_state.boundary = Boundary(
        text="original text", confirmed=True, confirmed_hash=digest("original text")
    )
    greenfield_state.boundary.text = "edited text"
    assert check_c4_boundary(greenfield_state).passed is False


def test_c4_declined_passes(greenfield_state: InterrogationState) -> None:
    greenfield_state.boundary = Boundary(text="(none)", declined=True)
    assert check_c4_boundary(greenfield_state).passed is True


def test_c5_empty_fails(greenfield_state: InterrogationState) -> None:
    assert check_c5_soft_context(greenfield_state).passed is False


def test_c5_explicit_none_passes(greenfield_state: InterrogationState) -> None:
    greenfield_state.context_notes = [
        ContextNote(text="user confirmed no soft context", source=NoteSource.STATED)
    ]
    assert check_c5_soft_context(greenfield_state).passed is True


def test_c6_open_load_bearing_fails(greenfield_state: InterrogationState) -> None:
    greenfield_state.open_questions = [
        OpenQuestion(
            id="q1",
            text="what auth provider?",
            origin=QuestionOrigin.MODULE,
            status=QuestionStatus.OPEN,
            load_bearing=True,
        )
    ]
    assert check_c6_no_unknowns(greenfield_state).passed is False


def test_c6_resolved_question_passes(greenfield_state: InterrogationState) -> None:
    greenfield_state.open_questions = [
        OpenQuestion(
            id="q1",
            text="what auth provider?",
            origin=QuestionOrigin.MODULE,
            status=QuestionStatus.RESOLVED,
            load_bearing=True,
            resolution="Okta",
        )
    ]
    assert check_c6_no_unknowns(greenfield_state).passed is True


def test_c6_no_questions_passes(greenfield_state: InterrogationState) -> None:
    assert check_c6_no_unknowns(greenfield_state).passed is True
