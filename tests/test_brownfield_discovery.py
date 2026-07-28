"""Two-stage touched-surface discovery (docs/conformance-classification-spec.md SS1)."""

from __future__ import annotations

from pathlib import Path

from loopr.brownfield.discovery import apply_relevance_response, build_relevance_request, prefilter_candidates
from loopr.models.interrogation import InterrogationState
from loopr.models.judge import JudgeResponse


def test_prefilter_casts_wide_net_on_keyword_match(repo_root: Path, brownfield_state: InterrogationState) -> None:
    (repo_root / "payments.py").write_text("def refund(amount): pass\n", encoding="utf-8")
    (repo_root / "unrelated.py").write_text("def noop(): pass\n", encoding="utf-8")
    brownfield_state.problem_statement = "add refund support to payments"
    candidates = prefilter_candidates(repo_root, brownfield_state)
    assert "payments.py" in candidates
    assert "unrelated.py" not in candidates


def test_prefilter_empty_keywords_returns_empty(repo_root: Path, brownfield_state: InterrogationState) -> None:
    candidates = prefilter_candidates(repo_root, brownfield_state)
    assert candidates == []


def test_apply_relevance_response_sets_touched_surface(brownfield_state: InterrogationState) -> None:
    request = build_relevance_request(["a.py", "b.py"], brownfield_state)
    response = JudgeResponse(call_id=request.call_id, selected_files=["a.py"], reason="only a.py matters")
    apply_relevance_response(brownfield_state, response)
    assert brownfield_state.brownfield is not None
    assert brownfield_state.brownfield.touched_surface == ["a.py"]
