"""Baby PRD renderer, TL;DR-first. Implements PHASE_1_SPEC.md SS1.5.

Mitigation for the 'unread gate' failure mode (loopr-PRD.md section 10): the TL;DR leads, and
force-resolved assumptions are surfaced immediately after it, not buried.
"""

from __future__ import annotations

from loopr.models.interrogation import InterrogationState


def render_baby_prd(state: InterrogationState, tldr: str) -> str:
    lines = ["# Baby PRD", "", "## TL;DR", tldr, ""]

    if state.assumptions:
        lines.append("## Assumptions (force-resolved -- read these; they were not confirmed by you)")
        for assumption in state.assumptions:
            lines.append(f"- {assumption.text} _(round {assumption.created_round})_")
        lines.append("")

    lines.append("## Problem statement")
    lines.append(state.problem_statement or "(none)")
    lines.append("")

    lines.append("## Acceptance criteria")
    for criterion in state.acceptance_criteria:
        lines.append(f"- {criterion.text}")
    lines.append("")

    lines.append("## Scope edges")
    for edge in state.scope_edges:
        lines.append(f"- **{edge.kind.value}**: {edge.item} -- {edge.reason}")
    lines.append("")

    lines.append("## Boundary")
    if state.boundary is not None:
        if state.boundary.declined:
            lines.append("(no boundary -- explicitly declined; audit degrades to failure-mode-only)")
        else:
            lines.append(state.boundary.text)
    else:
        lines.append("(none)")

    return "\n".join(lines) + "\n"
