"""Pure, deterministic structural pre-checks. Implements PHASE_1_SPEC.md SS6.5.

Every function here is pure: no I/O, no model call, no randomness, deterministic on its inputs.
This module is the anchor the whole design rests on -- arXiv:2603.05399 measured 37.50% stochastic
stability on identical repeated judge input, so the judge cannot be the only thing standing between
a fuzzy answer and a stop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loopr.judge.envelope import digest
from loopr.models.common import NoteSource, QuestionStatus
from loopr.models.interrogation import InterrogationState

_SOLUTION_SHAPED_RE = re.compile(
    r"^\s*(build|use|create|write|implement|deploy)\b.*\b(tool|framework|library|system|app|"
    r"service|api|script|bot|pipeline)\b",
    re.IGNORECASE,
)

_OBSERVABLE_PREDICATE_RE = re.compile(
    r"\b(returns?|shows?|completes?|equals?|passes?|fails?|is visible|renders?|displays?|"
    r"responds?|matches?|contains?)\b",
    re.IGNORECASE,
)

_VAGUE_SCOPE_RE = re.compile(
    r"^\s*(nothing fancy|basic stuff only|keep it simple|nothing special)\s*\.?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class StructuralResult:
    passed: bool
    detail: str
    advisory_flags: list[str] = field(default_factory=list)


def check_c1_outcome(state: InterrogationState) -> StructuralResult:
    """Pre-filter can only downgrade, never hard-block (docs/stopping-test-spec.md Condition 1)."""
    statement = state.problem_statement
    if not statement or not statement.strip():
        return StructuralResult(passed=False, detail="problem_statement is empty")
    flags: list[str] = []
    if _SOLUTION_SHAPED_RE.match(statement):
        flags.append("structural pre-filter flagged this as possibly solution-shaped")
    return StructuralResult(passed=True, detail="problem_statement is non-empty", advisory_flags=flags)


def check_c2_acceptance(state: InterrogationState) -> StructuralResult:
    if not state.acceptance_criteria:
        return StructuralResult(passed=False, detail="no acceptance criteria present")
    for criterion in state.acceptance_criteria:
        if not criterion.text.strip():
            continue
        if _OBSERVABLE_PREDICATE_RE.search(criterion.text):
            return StructuralResult(
                passed=True, detail=f"at least one criterion has an observable predicate: {criterion.text!r}"
            )
    return StructuralResult(
        passed=False, detail="no criterion contains an observable predicate (comparator/observable verb)"
    )


def check_c3_scope_edges(state: InterrogationState) -> StructuralResult:
    if not state.scope_edges:
        return StructuralResult(passed=False, detail="no scope edges present")
    for edge in state.scope_edges:
        if not edge.item.strip() or not edge.reason.strip():
            continue
        if _VAGUE_SCOPE_RE.match(edge.item):
            continue
        return StructuralResult(passed=True, detail=f"at least one well-formed scope edge: {edge.item!r}")
    return StructuralResult(
        passed=False,
        detail="no scope edge has both a non-empty item and reason, or all are structurally vague",
    )


def check_c4_boundary(state: InterrogationState) -> StructuralResult:
    """Pure state machine, no judge. Hash comparison auto-invalidates a post-confirm tweak."""
    boundary = state.boundary
    if boundary is None:
        return StructuralResult(passed=False, detail="no boundary proposed")
    if boundary.declined:
        return StructuralResult(passed=True, detail="boundary explicitly declined (escape hatch)")
    if not boundary.confirmed or boundary.confirmed_hash is None:
        return StructuralResult(passed=False, detail="boundary not confirmed")
    current_hash = digest(boundary.text)
    if boundary.confirmed_hash != current_hash:
        return StructuralResult(
            passed=False, detail="boundary text changed since confirmation; confirmation is stale"
        )
    return StructuralResult(passed=True, detail="boundary confirmed and hash matches current text")


def check_c5_soft_context(state: InterrogationState) -> StructuralResult:
    if not state.context_notes:
        return StructuralResult(passed=False, detail="no context notes present")
    for note in state.context_notes:
        if note.text.strip() and note.source in (NoteSource.STATED, NoteSource.INFERRED):
            return StructuralResult(passed=True, detail="at least one well-formed context note")
    return StructuralResult(passed=False, detail="no well-formed context note")


def check_c6_no_unknowns(state: InterrogationState) -> StructuralResult:
    open_load_bearing = [
        q for q in state.open_questions if q.status == QuestionStatus.OPEN and q.load_bearing is True
    ]
    if open_load_bearing:
        return StructuralResult(
            passed=False,
            detail=f"{len(open_load_bearing)} open load-bearing question(s) remain",
        )
    return StructuralResult(passed=True, detail="no open load-bearing question remains")
