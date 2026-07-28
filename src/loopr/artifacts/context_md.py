"""context.md renderer, layered per loopr-PRD.md section 7. Implements PHASE_1_SPEC.md SS1.5.

Layered, never a blind append: a current-state header, a sectioned body, and (in later iterations)
a supersession pointer for a changed constraint rather than deletion. Mitigates 'context.md rot'
(loopr-PRD.md section 10).
"""

from __future__ import annotations

from loopr.models.interrogation import InterrogationState


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
        lines.append(f"- _{note.source.value}_: {note.text}")
    return "\n".join(lines) + "\n"
