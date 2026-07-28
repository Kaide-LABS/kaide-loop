"""Two-stage touched-surface discovery. Implements PHASE_1_SPEC.md SS6.7.1.

Stage 1 is deterministic and free, cast deliberately wide (recall over precision) -- the primary
mitigation for touched-surface miss (loopr-PRD.md section 10). Stage 2 is one BF_RELEVANCE judge
call over file paths plus short summaries, never full file contents
(docs/conformance-classification-spec.md section 1).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from loopr.judge.envelope import make_call_id
from loopr.models.common import JudgeCallType
from loopr.models.interrogation import InterrogationState
from loopr.models.judge import JsonValue, JudgeRequest, JudgeResponse
from loopr.rubrics import RUBRICS

_IGNORED_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    ".loopr-state",
}

_BINARY_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".exe", ".dll", ".so"}


def _keywords(state: InterrogationState) -> list[str]:
    text_parts: list[str] = []
    if state.problem_statement:
        text_parts.append(state.problem_statement)
    text_parts.extend(c.text for c in state.acceptance_criteria)
    text_parts.extend(e.item for e in state.scope_edges)
    words: set[str] = set()
    for part in text_parts:
        for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", part):
            words.add(word.lower())
    return sorted(words)


def prefilter_candidates(repo_root: Path, state: InterrogationState) -> list[str]:
    """Cheap keyword search over the repo file tree. Casts a wide net on purpose (recall, not
    precision) -- docs/conformance-classification-spec.md section 1 stage 1."""
    keywords = _keywords(state)
    if not keywords:
        return []
    matches: list[str] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in _BINARY_SUFFIXES:
            continue
        if any(part in _IGNORED_DIR_NAMES for part in path.parts):
            continue
        relative = path.relative_to(repo_root).as_posix()
        haystack = relative.lower()
        try:
            haystack += "\n" + path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if any(keyword in haystack for keyword in keywords):
            matches.append(relative)
    return sorted(matches)


def build_relevance_request(candidates: list[str], state: InterrogationState) -> JudgeRequest:
    inputs: dict[str, JsonValue] = cast(
        "dict[str, JsonValue]",
        {
            "candidate_files": candidates,
            "problem_statement": state.problem_statement,
            "acceptance_criteria": [c.text for c in state.acceptance_criteria],
            "scope_edges": [e.item for e in state.scope_edges],
        },
    )
    rubric = RUBRICS[JudgeCallType.BF_RELEVANCE]
    call_id = make_call_id(JudgeCallType.BF_RELEVANCE.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.BF_RELEVANCE,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


def apply_relevance_response(state: InterrogationState, response: JudgeResponse) -> InterrogationState:
    if state.brownfield is None:
        raise ValueError("apply_relevance_response requires brownfield state")
    if response.selected_files is not None:
        state.brownfield.touched_surface = list(response.selected_files)
    return state
