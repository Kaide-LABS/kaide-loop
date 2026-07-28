"""Classification request/routing (docs/conformance-classification-spec.md SS4-5)."""

from __future__ import annotations

from loopr.brownfield.classify import build_classify_request, route_verdict
from loopr.models.brownfield import EvidenceBundle, PatternClassification
from loopr.models.common import Centrality, QuestionOrigin, Verdict
from loopr.models.interrogation import InterrogationState


def _bundle(pattern_id: str = "decorator:retry") -> EvidenceBundle:
    return EvidenceBundle(
        pattern_id=pattern_id,
        description="retry decorator",
        locations=["a.py:1", "b.py:1", "c.py:1"],
        occurrence_count=3,
        centrality=Centrality.CORE,
    )


def test_build_classify_request_scope(brownfield_state: InterrogationState) -> None:
    request = build_classify_request(_bundle(), brownfield_state)
    assert set(request.inputs.keys()) == {
        "evidence_bundle",
        "problem_statement",
        "acceptance_criteria",
        "scope_edges",
        "boundary",
    }


def test_conform_routes_to_ledger_no_gate(brownfield_state: InterrogationState) -> None:
    classification = PatternClassification(pattern_id="p1", verdict=Verdict.CONFORM, reason="fine")
    route_verdict(brownfield_state, classification)
    assert brownfield_state.brownfield is not None
    assert brownfield_state.brownfield.gate_3_required is False
    assert classification in brownfield_state.brownfield.classifications


def test_conflict_makes_gate_3_required(brownfield_state: InterrogationState) -> None:
    classification = PatternClassification(pattern_id="p1", verdict=Verdict.CONFLICT, reason="breaks it")
    route_verdict(brownfield_state, classification)
    assert brownfield_state.brownfield is not None
    assert brownfield_state.brownfield.gate_3_required is True


def test_ambiguous_creates_open_question(brownfield_state: InterrogationState) -> None:
    classification = PatternClassification(pattern_id="p1", verdict=Verdict.AMBIGUOUS, reason="mixed signals")
    route_verdict(brownfield_state, classification)
    questions = [q for q in brownfield_state.open_questions if q.origin == QuestionOrigin.PATTERN_AMBIGUITY]
    assert len(questions) == 1
    assert "p1" in questions[0].text
