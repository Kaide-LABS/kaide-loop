"""context.md renderer, layered per loopr-PRD.md section 7. Implements PHASE_1_SPEC.md SS1.5.

Layered, never a blind append: a current-state header, a sectioned body, and (in later iterations)
a supersession pointer for a changed constraint rather than deletion. Mitigates 'context.md rot'
(loopr-PRD.md section 10).
"""

from __future__ import annotations

from loopr.models.common import JudgeCallType
from loopr.models.interrogation import InterrogationState


def _note_is_accepted(state: InterrogationState, note_text: str) -> bool:
    """True iff the judge's latest verdict for this exact note text was a genuine, non-misplaced
    pass. A note the judge rejected outright (docs/stopping-test-spec.md Condition 5's relevance
    check) has no home anywhere and must never render here -- not relocated, not superseded, simply
    dropped from output. It stays in judge_log for audit purposes regardless."""
    for exchange in reversed(state.judge_log):
        if (
            exchange.request.call_type == JudgeCallType.C5_SOFT_CONTEXT
            and exchange.request.inputs.get("context_note") == note_text
        ):
            return exchange.response.passed is True and not exchange.response.misplaced
    return False


def render_context_md(state: InterrogationState) -> str:
    lines = [
        "# context.md",
        "",
        "## Current state (single source of 'what's true now')",
        f"- Mode: {state.mode.value}",
        f"- Round reached: {state.round}",
        "",
        "## Soft context (boss-said / watch-out / judged-a-failure-if)",
    ]
    for note in state.context_notes:
        if _note_is_accepted(state, note.text):
            lines.append(f"- _{note.source.value}_: {note.text}")
    return "\n".join(lines) + "\n"
