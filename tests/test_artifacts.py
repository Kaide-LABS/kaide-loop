"""Artifact renderers: TL;DR-first, layered context.md, and the ledger's novelty header."""

from __future__ import annotations

from loopr.artifacts.baby_prd import render_baby_prd
from loopr.artifacts.conformance_ledger import render_conformance_ledger
from loopr.artifacts.context_md import render_context_md
from loopr.judge.envelope import digest
from loopr.models.brownfield import PatternClassification
from loopr.models.common import JudgeCallType, NoteSource, Verdict
from loopr.models.interrogation import AcceptanceCriterion, ContextNote, InterrogationState
from loopr.models.judge import JudgeExchange, JudgeRequest, JudgeResponse


def _c5_exchange(note_text: str, *, passed: bool, misplaced: bool = False) -> JudgeExchange:
    request = JudgeRequest(
        call_id="c5" + "0" * 14,
        call_type=JudgeCallType.C5_SOFT_CONTEXT,
        rubric_id="c5_soft_context_v2",
        rubric_text="rubric",
        inputs={
            "context_note": note_text,
            "problem_statement": None,
            "acceptance_criteria": [],
            "scope_edges": [],
            "boundary": None,
        },
        created_round=1,
    )
    response = JudgeResponse(
        call_id=request.call_id, passed=passed, misplaced=misplaced, reason="test verdict"
    )
    return JudgeExchange(
        request=request,
        response=response,
        request_sha256=digest(request.model_dump_json()),
        response_sha256=digest(response.model_dump_json()),
        answered_at_round=1,
    )


def test_baby_prd_leads_with_tldr(greenfield_state: InterrogationState) -> None:
    greenfield_state.acceptance_criteria = [AcceptanceCriterion(text="the page returns a 200")]
    rendered = render_baby_prd(greenfield_state, tldr="THIS IS THE TLDR")
    tldr_index = rendered.index("THIS IS THE TLDR")
    criteria_index = rendered.index("the page returns a 200")
    assert tldr_index < criteria_index


def test_context_md_has_current_state_header(greenfield_state: InterrogationState) -> None:
    greenfield_state.context_notes = [ContextNote(text="boss cares about latency", source=NoteSource.STATED)]
    greenfield_state.judge_log = [_c5_exchange("boss cares about latency", passed=True)]
    rendered = render_context_md(greenfield_state)
    assert "Current state" in rendered
    assert "boss cares about latency" in rendered


def test_context_md_never_renders_a_rejected_note(greenfield_state: InterrogationState) -> None:
    """Regression (FIX 4): a note the judge rejected outright (off-topic, per condition 5's amended
    relevance check) must never appear in context.md -- not relocated, not superseded, just dropped
    from output. It stays in judge_log for audit purposes, which this test also confirms."""
    greenfield_state.context_notes = [
        ContextNote(text="accepted watch-out", source=NoteSource.STATED),
        ContextNote(text="rejected off-topic note", source=NoteSource.STATED),
    ]
    greenfield_state.judge_log = [
        _c5_exchange("accepted watch-out", passed=True),
        _c5_exchange("rejected off-topic note", passed=False, misplaced=False),
    ]

    rendered = render_context_md(greenfield_state)

    assert "accepted watch-out" in rendered
    assert "rejected off-topic note" not in rendered
    # The rejected note must still be reconstructable from the audit trail.
    assert any(
        exchange.request.inputs.get("context_note") == "rejected off-topic note"
        for exchange in greenfield_state.judge_log
    )


def test_conformance_ledger_states_novelty(brownfield_state: InterrogationState) -> None:
    assert brownfield_state.brownfield is not None
    brownfield_state.brownfield.classifications = [
        PatternClassification(pattern_id="p1", verdict=Verdict.CONFORM, reason="fine")
    ]
    rendered = render_conformance_ledger(brownfield_state)
    assert "novel" in rendered.lower()
    assert "p1" in rendered
