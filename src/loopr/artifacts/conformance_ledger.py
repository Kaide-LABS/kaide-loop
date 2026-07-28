"""conformance-ledger.md renderer (brownfield only). Implements PHASE_1_SPEC.md SS1.5, guard G-16.

The header states plainly that this classification mechanism is novel and unvalidated -- no prior
art, no labelled dataset, no published baseline exists for convention-vs-cruft discrimination
(loopr-PRD.md section 5 A3a) -- so the mechanism is not overclaimed as validated technique.
"""

from __future__ import annotations

from loopr.models.common import Verdict
from loopr.models.interrogation import InterrogationState


def render_conformance_ledger(state: InterrogationState) -> str:
    if state.brownfield is None:
        raise ValueError("render_conformance_ledger requires brownfield state")

    lines = [
        "# conformance-ledger.md",
        "",
        "> **Novelty flag:** this classification is a novel mechanism carried by its human-escalation "
        "path (CONFLICT -> Gate 3; AMBIGUOUS -> open question), not an application of validated "
        "technique. No prior art, labelled dataset, or published baseline exists for "
        "convention-vs-cruft discrimination (loopr-PRD.md section 5 A3a).",
        "",
    ]

    routine = [
        c
        for c in state.brownfield.classifications
        if c.verdict in (Verdict.CONFORM, Verdict.DO_NOT_REPLICATE)
    ]
    if routine:
        lines.append("## Routine calls (applied silently, no gate)")
        for classification in routine:
            lines.append(
                f"- **{classification.verdict.value}** `{classification.pattern_id}`: "
                f"{classification.reason}"
            )
        lines.append("")

    conflicts = [c for c in state.brownfield.classifications if c.verdict == Verdict.CONFLICT]
    if conflicts:
        lines.append("## CONFLICT calls (resolved at Gate 3)")
        for classification in conflicts:
            lines.append(f"- `{classification.pattern_id}`: {classification.reason}")
        lines.append("")

    ambiguous = [c for c in state.brownfield.classifications if c.verdict == Verdict.AMBIGUOUS]
    if ambiguous:
        lines.append("## AMBIGUOUS calls (routed to the open-questions ledger)")
        for classification in ambiguous:
            lines.append(f"- `{classification.pattern_id}`: {classification.reason}")
        lines.append("")

    return "\n".join(lines)
