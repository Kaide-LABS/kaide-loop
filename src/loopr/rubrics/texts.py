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
        rubric_id="c5_soft_context_v2",
        text=(
            "First, relevance: does this note actually relate to the CONFIRMED problem_statement, "
            "acceptance_criteria, scope_edges, or boundary for THIS build? If it is well-formed, "
            "confidently phrased, or even stated as settled fact, but has no bearing on any of "
            "those four fields, REJECT it outright as off-topic -- do not route it anywhere. "
            "Confident phrasing is not evidence of relevance. Second, only for notes that pass the "
            "relevance check: does this note change how the finished build would be JUDGED "
            "(accepted/rejected) without being expressible as a testable spec requirement? If it IS "
            "expressible as one of the existing or a new acceptance criterion, it belongs there, "
            "not here -- flag as misplaced rather than failing outright."
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
    JudgeCallType.BOUNDARY_PROPOSAL: RubricSpec(
        rubric_id="boundary_proposal_v1",
        text=(
            "Given the confirmed problem statement, acceptance criteria, scope edges, and soft "
            "context notes so far, draft a plain-language boundary proposal: a short statement of "
            "what this build covers and what it explicitly does not, grounded only in what has "
            "actually been said in those fields -- never invent scope, never import an example from "
            "another project, never generalize beyond what the confirmed fields actually support. "
            "This is a DRAFT for the human to confirm or tweak at Gate 2, not a final decision -- "
            "state it as a proposal, not settled fact. Return the drafted text only; do not set "
            "confirmed status, that is the human's action alone."
        ),
    ),
    JudgeCallType.STEP10_CUSTOMIZATION: RubricSpec(
        rubric_id="step10_customization_v2",
        text=(
            "Customize this template for THIS project, using only the confirmed problem statement, "
            "acceptance criteria, scope edges, boundary, soft context notes, conformance summary, and "
            "repo_root (the project's real filesystem path) given -- never invent detail, never "
            "import an example from another project. This is a synthesis task, not a pass/fail "
            "judgment: fill and adapt every placeholder you can resolve from the given fields; where "
            "a placeholder's value is not yet knowable (e.g. it depends on this template's own future "
            "output), leave it exactly as it appears in the template -- do not guess, do not delete "
            "it, do not fabricate a plausible-looking value. Resolve [PROJECT_NAME] and "
            "[PROJECT_REPO_NAME] from repo_root (the repo's real directory name and a readable "
            "project name derived from it plus the confirmed problem statement) -- these ARE "
            "genuinely resolvable now, do not leave them as placeholders for lack of a dedicated "
            "project-name field. Resolve [PRD_FILENAME] the same way, using your own judgment from "
            "repo_root and the confirmed fields; if genuinely unsure, the template's own stated "
            "default ('ULTIMATE_PRD.md') is an honest fallback, not a guess. "
            "PRESERVE EVERY SECTION, IN THE SAME ORDER, WITH THE SAME HEADERS -- fill and adapt, "
            "never restructure, condense, reorder, or rewrite the template's own shape. Tags and "
            "reject-pattern shorthand that merely LOOK like placeholders (e.g. a bracketed tag the "
            "executing model is instructed to emit, or bracketed shorthand inside a rejection rule) "
            "are not placeholders -- leave them completely untouched, byte-for-byte. Return the "
            "customized text only."
        ),
    ),
    JudgeCallType.STEP10_FIDELITY_JUDGE: RubricSpec(
        rubric_id="step10_fidelity_judge_v1",
        text=(
            "Given the original template and the customized output, is the injected content "
            "genuinely specific to THIS project -- naming its actual files, invariants, boundary, "
            "and stack -- or is it generic filler that would read identically for any project? "
            "Verbatim template text with placeholders merely deleted (not replaced with real, "
            "project-specific content) is a FAIL, not a pass. Reject outright if any resolved value "
            "could describe an arbitrary, unrelated project rather than the one actually described "
            "by the given problem statement, acceptance criteria, and boundary."
        ),
    ),
    JudgeCallType.STEP11_CUSTOMIZATION: RubricSpec(
        rubric_id="step11_customization_v2",
        text=(
            "Customize this template for THIS project, using only the confirmed problem statement, "
            "acceptance criteria, scope edges, boundary, soft context notes, conformance summary, "
            "repo_root (the project's real filesystem path), and the project's own PHASE_1_SPEC.md "
            "(produced by step10 having actually run) given -- never invent detail, never import an "
            "example from another project. This is a synthesis task, not a pass/fail judgment: fill "
            "and adapt every placeholder you can resolve from the given fields; where a placeholder's "
            "value is not yet knowable even now, leave it exactly as it appears in the template -- do "
            "not guess, do not delete it, do not fabricate a plausible-looking value. Resolve "
            "[PROJECT_NAME], [PROJECT_REPO_NAME], [PROJECT], and [PROJECT_TAG] from repo_root (the "
            "repo's real directory name, and a readable project name/short tag derived from it plus "
            "the confirmed problem statement) -- these ARE genuinely resolvable now, do not leave "
            "them as placeholders for lack of a dedicated project-name field. Resolve [PHASE_COUNT] "
            "by reading it directly from PHASE_1_SPEC.md's own SS0 phase-plan header ('Phase 1 of "
            "N') -- it is now genuinely knowable, unlike in step10's own template, precisely because "
            "step10 has already run. "
            "PRESERVE EVERY SECTION, IN THE SAME ORDER, WITH THE SAME HEADERS, EXCEPT: the "
            "'TEMPLATE CUSTOMIZATION CHECKLIST' section must be removed entirely from your output -- "
            "its own text says to remove it before use, it is scaffolding for a human customizing by "
            "hand, never content for the executing agent. Elsewhere, fill and adapt, never "
            "restructure, condense, reorder, or rewrite the template's own shape. The "
            "'<<CITATION_GATE_INGESTION_BLOCK: ...>>' block is a judgment call, not a fill target: "
            "if the confirmed spec content establishes load-bearing arXiv citations anchoring this "
            "project's architecture, resolve it into real, project-specific instructions per what "
            "the block itself describes; otherwise remove it entirely, per its own stated fallback "
            "('Otherwise remove this block') -- it specifies no replacement line, so do not invent "
            "one. State which way you decided, and why, in your reason. Tags and reject-pattern "
            "shorthand that merely LOOK like placeholders (e.g. '[EXECUTOR]', the checkbox markup "
            "'[ ]', or the output-format examples inside the AUTONOMOUS CRITIQUE section such as "
            "'[specified]'/'[implemented instead]'/'[reason]') are not placeholders -- leave them "
            "completely untouched, byte-for-byte; they are emitted by the agent that executes this "
            "prompt, not by you. Return the customized text only."
        ),
    ),
    JudgeCallType.STEP11_FIDELITY_JUDGE: RubricSpec(
        rubric_id="step11_fidelity_judge_v1",
        text=(
            "Given the original template and the customized output, is the injected content "
            "genuinely specific to THIS project -- naming its actual files, invariants, boundary, "
            "phase count, and stack -- or is it generic filler that would read identically for any "
            "project? Verbatim template text with placeholders merely deleted (not replaced with "
            "real, project-specific content) is a FAIL, not a pass. If a citation-gate decision was "
            "made, is the resolution genuinely reasoned (real citation content if included; real, "
            "specific reasoning if not -- not a bare restatement with nothing behind it) rather than "
            "a placeholder-shaped non-answer? Reject outright if any resolved value could describe "
            "an arbitrary, unrelated project rather than the one actually described by the given "
            "problem statement, acceptance criteria, and boundary."
        ),
    ),
    JudgeCallType.STEP12_CUSTOMIZATION: RubricSpec(
        rubric_id="step12_customization_v2",
        text=(
            "Customize this template for THIS project, using only the confirmed problem statement, "
            "acceptance criteria, scope edges, boundary, soft context notes, conformance summary, "
            "repo_root (the project's real filesystem path), and the project's own PHASE_1_SPEC.md "
            "(produced by step10 having actually run) given -- never invent detail, never import an "
            "example from another project. This is a synthesis task, not a pass/fail judgment: fill "
            "and adapt every placeholder you can resolve from the given fields; where a placeholder's "
            "value is not yet knowable even now, leave it exactly as it appears in the template -- do "
            "not guess, do not delete it, do not fabricate a plausible-looking value. Resolve "
            "[PROJECT_NAME], [PROJECT_REPO_NAME], [PROJECT], and [PROJECT_TAG] from repo_root (the "
            "repo's real directory name, and a readable project name/short tag derived from it plus "
            "the confirmed problem statement) -- these ARE genuinely resolvable now, do not leave "
            "them as placeholders for lack of a dedicated project-name field. Resolve [PHASE_COUNT] "
            "by reading it directly from PHASE_1_SPEC.md's own SS0 phase-plan header ('Phase 1 of "
            "N') -- it is now genuinely knowable, unlike in step10's own template, precisely because "
            "step10 has already run. "
            "[EXECUTOR_AGENT_FICTION] names the entity that supposedly wrote the code under review: "
            "draft a value grounded only in the confirmed spec content available to you -- if that "
            "content doesn't establish genuine build/review separateness, a generic fictional name "
            "is the honest default; never infer or encode anything about session topology, which you "
            "are not told and must not guess at. PRESERVE EVERY SECTION, IN THE SAME ORDER, WITH THE "
            "SAME HEADERS, EXCEPT: the 'TEMPLATE CUSTOMIZATION CHECKLIST' section must be removed "
            "entirely from your output -- its own text says to remove it before use, it is "
            "scaffolding for a human customizing by hand, never content for the executing agent. "
            "Elsewhere, fill and adapt, never restructure, condense, reorder, or rewrite the "
            "template's own shape. The '<<CITATION_GATE_BLOCK: ...>>' block is a judgment call, not "
            "a fill target: if the confirmed spec content establishes load-bearing arXiv citations "
            "anchoring this project's architecture, resolve it into real, project-specific "
            "instructions per what the block itself describes; otherwise replace it with genuine, "
            "project-specific reasoning for why no citation gate applies -- its own stated fallback "
            "line ('No citation re-verification gate required for this project.') is a starting "
            "point, not a substitute for actually explaining why, in this project's own terms. State "
            "which way you decided, and why, in your reason. Tags and reject-pattern shorthand that "
            "merely LOOK like placeholders (e.g. '[EXECUTOR]' or the checkbox markup '[ ]') are not "
            "placeholders -- leave them completely untouched, byte-for-byte; they are emitted by the "
            "agent that executes this prompt, not by you. Return the customized text only."
        ),
    ),
    JudgeCallType.STEP12_FIDELITY_JUDGE: RubricSpec(
        rubric_id="step12_fidelity_judge_v1",
        text=(
            "Given the original template and the customized output, is the injected content "
            "genuinely specific to THIS project -- naming its actual files, invariants, boundary, "
            "phase count, and stack -- or is it generic filler that would read identically for any "
            "project? Verbatim template text with placeholders merely deleted (not replaced with "
            "real, project-specific content) is a FAIL, not a pass. If a citation-gate decision was "
            "made, is the resolution genuinely reasoned (real citation content if included; real, "
            "specific reasoning if not -- not a bare restatement of the template's own fallback line "
            "with nothing added) rather than a placeholder-shaped non-answer? Reject outright if any "
            "resolved value could describe an arbitrary, unrelated project rather than the one "
            "actually described by the given problem statement, acceptance criteria, and boundary."
        ),
    ),
}
