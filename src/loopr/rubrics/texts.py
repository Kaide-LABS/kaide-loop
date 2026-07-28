"""Frozen rubric text. Implements PHASE_1_SPEC.md SS1.4.

Rubric text is data, not f-strings (guard G-4) -- variable content belongs in JudgeRequest.inputs,
never interpolated into rubric_text. Verbatim from docs/stopping-test-spec.md and
docs/conformance-classification-spec.md (as amended 2026-07-28).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from loopr.models.common import JudgeCallType


@dataclass(frozen=True)
class RubricSpec:
    rubric_id: str
    text: str


RUBRICS: Mapping[JudgeCallType, RubricSpec] = {
    JudgeCallType.C1_OUTCOME: RubricSpec(
        rubric_id="c1_outcome_v1",
        text=(
            "Does this statement describe a desired real-world outcome/result (what becomes true "
            "when this is done, for whom), or does it prescribe a specific solution/implementation "
            "as the primary subject? Pass only if a concrete outcome is named. A stated solution is "
            "acceptable ONLY if it is explicitly subordinate to a stated outcome (e.g. 'I want X to "
            "happen; my current guess at how is Y' passes -- 'Y' alone does not)."
        ),
    ),
    JudgeCallType.C2_ACCEPTANCE: RubricSpec(
        rubric_id="c2_acceptance_v1",
        text=(
            "For each acceptance criterion, could a third party who did not build the system check "
            "it by observation or a concrete test, without needing to ask the builder for a "
            "judgment call? Pass only if at least one criterion is independently checkable this "
            "way. Reject criteria that are purely subjective ('feels fast', 'is good') with no "
            "observable proxy."
        ),
    ),
    JudgeCallType.C3_SCOPE_EDGES: RubricSpec(
        rubric_id="c3_scope_edges_v1",
        text=(
            "Is each named edge specific enough that a builder reading it later would know "
            "unambiguously whether a new request falls inside or outside it? Reject vague edges "
            "('nothing fancy', 'basic stuff only') that don't name a concrete boundary object (a "
            "feature, an integration, a scale threshold, a user segment)."
        ),
    ),
    JudgeCallType.C5_SOFT_CONTEXT: RubricSpec(
        rubric_id="c5_soft_context_v1",
        text=(
            "Given the current acceptance criteria list, does this note change how the finished "
            "build would be JUDGED (accepted/rejected) without being expressible as a testable spec "
            "requirement? If it IS expressible as one of the existing or a new acceptance "
            "criterion, it belongs there, not here -- flag as misplaced rather than failing "
            "outright."
        ),
    ),
    JudgeCallType.C6_LOAD_BEARING: RubricSpec(
        rubric_id="c6_load_bearing_v1",
        text=(
            "Given the current acceptance criteria, scope edges, and boundary, would a plausible "
            "alternative answer to this question require a materially different value in any of "
            "those three? If yes, load-bearing."
        ),
    ),
    JudgeCallType.BF_RELEVANCE: RubricSpec(
        rubric_id="bf_relevance_v1",
        text=(
            "Given the confirmed problem statement, acceptance criteria, and scope edges, which of "
            "these candidate files are actually relevant to the work -- i.e. the new work will "
            "read, modify, or must interact with them? Select only genuinely relevant files; do not "
            "pad the selection for safety."
        ),
    ),
    JudgeCallType.BF_CLASSIFY: RubricSpec(
        rubric_id="bf_classify_v1",
        text=(
            "Given this pattern's evidence and the confirmed problem statement, acceptance "
            "criteria, scope edges, and boundary, classify:\n"
            "- CONFORM if the pattern is a real, current convention: recurring or structurally "
            "central, actively maintained (recent commits, more than one author, or expected "
            "staleness for genuinely stable code), no deprecation markers, and does not conflict "
            "with the stated intent.\n"
            "- DO_NOT_REPLICATE if it shows cruft signals -- isolated/peripheral, stale, "
            "single-author, deprecation-marked, or a one-off inconsistent with the surface's "
            "otherwise-different approach -- AND does not itself conflict with the stated intent.\n"
            "- CONFLICT if conforming to this pattern, or the new work simply having to coexist "
            "with it, would make the stated outcome, an acceptance criterion, or the boundary NOT "
            "hold.\n"
            "- AMBIGUOUS if the evidence signals genuinely conflict with each other and no "
            "confident call is possible.\n"
            "IMPORTANT CAVEATS on the evidence bundle's signals (read signal_qualifiers on the "
            "bundle for which apply here): staleness (git_last_touched_days_ago) alone is NOT "
            "sufficient for DO_NOT_REPLICATE -- stable, mature, correct code is also old. A "
            "deprecation marker may indicate 'on-hold' debt (correct code intentionally blocked on "
            "an external event), not cruft -- if the marker's text suggests this, prefer AMBIGUOUS "
            "over DO_NOT_REPLICATE. Do not treat any single signal as dispositive on its own."
        ),
    ),
}
