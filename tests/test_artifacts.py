"""Artifact renderers: TL;DR-first, layered context.md, and the ledger's novelty header."""

from __future__ import annotations

from loopr.artifacts.baby_prd import render_baby_prd
from loopr.artifacts.conformance_ledger import render_conformance_ledger
from loopr.artifacts.context_md import render_context_md
from loopr.models.brownfield import PatternClassification
from loopr.models.common import NoteSource, Verdict
from loopr.models.interrogation import AcceptanceCriterion, ContextNote, InterrogationState


def test_baby_prd_leads_with_tldr(greenfield_state: InterrogationState) -> None:
    greenfield_state.acceptance_criteria = [AcceptanceCriterion(text="the page returns a 200")]
    rendered = render_baby_prd(greenfield_state, tldr="THIS IS THE TLDR")
    tldr_index = rendered.index("THIS IS THE TLDR")
    criteria_index = rendered.index("the page returns a 200")
    assert tldr_index < criteria_index


def test_context_md_has_current_state_header(greenfield_state: InterrogationState) -> None:
    greenfield_state.context_notes = [ContextNote(text="boss cares about latency", source=NoteSource.STATED)]
    rendered = render_context_md(greenfield_state)
    assert "Current state" in rendered
    assert "boss cares about latency" in rendered


def test_conformance_ledger_states_novelty(brownfield_state: InterrogationState) -> None:
    assert brownfield_state.brownfield is not None
    brownfield_state.brownfield.classifications = [
        PatternClassification(pattern_id="p1", verdict=Verdict.CONFORM, reason="fine")
    ]
    rendered = render_conformance_ledger(brownfield_state)
    assert "novel" in rendered.lower()
    assert "p1" in rendered
