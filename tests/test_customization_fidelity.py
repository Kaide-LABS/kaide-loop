"""The two-layer fidelity check. Implements CUSTOMIZATION_PHASE_1_SPEC.md SS4.3.

Demonstrates SS8.4 (a deliberately restructured customization is rejected) and SS8.5 (a
placeholder-deletion-only "customization" is rejected) firing for real, not merely existing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from loopr.customization.fidelity import apply_judge_layer, check_fidelity
from loopr.customization.templates import extract_skeleton
from loopr.models.common import CustomizationStep
from loopr.models.customization import FidelityResult, TemplateSkeleton

REAL_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "prompts" / "Template_prompts"

# Every synthetic fixture below carries a dummy title line first, matching the real STEP_10's own
# shape (a plain-text title on line 1) -- extract_skeleton always excludes line 1 as the declared
# title exclusion (CUSTOMIZATION_PHASE_1_SPEC.md SS4.3), so a fixture without one would silently
# lose its own first real section to that rule.
_TITLE = "DOC TITLE (TEMPLATE)\n\n"

TEMPLATE_TEXT = (
    _TITLE
    + "ROLE\n\nAct as an architect for [PROJECT_NAME].\n\n"
    + "1. FIRST SECTION\n\nDo the first thing for [PROJECT_REPO_NAME].\n\n"
    + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
)


def _template_skeleton() -> TemplateSkeleton:
    return extract_skeleton(TEMPLATE_TEXT, CustomizationStep.STEP_10)


def test_dropping_only_why_this_must_be_airtight_is_now_rejected() -> None:
    """The exact scenario that previously passed green: a customization that preserves every
    section EXCEPT "WHY THIS MUST BE AIRTIGHT (loop context)". Demonstrates both sides of the fix:
    the crippled (pre-fix) 8-section extraction sees no difference at all (a false pass); the real,
    fixed extractor correctly rejects it."""
    real_template_text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    lines = real_template_text.splitlines()
    dropped_index = next(
        i for i, line in enumerate(lines) if line.strip() == "WHY THIS MUST BE AIRTIGHT (loop context)"
    )
    # Remove the section header line and its one-blank-line spacer, keep everything else untouched.
    output_lines = lines[:dropped_index] + lines[dropped_index + 1 :]
    output_text = "\n".join(output_lines)
    # Resolve every allowlisted placeholder, matching a plausible real customization, so the ONLY
    # structural difference from the template is the dropped section -- not also leftover
    # placeholders, which would fail for an unrelated reason and defeat the point of this test.
    # [RESEARCH FOCUS] is deliberately NOT resolved here -- it is not on the allowlist (it must
    # survive byte-identical, like [UNVERIFIED]/[EXECUTOR]; see templates.py's
    # NON_PLACEHOLDER_BRACKET_TOKENS), so leaving it untouched is what a genuine customization does.
    for token, value in {
        "[PROJECT_NAME]": "Acme Corp",
        "[PROJECT_REPO_NAME]": "acme-repo",
        "[PRD_FILENAME]": "ULTIMATE_PRD.md",
        "[PHASE_COUNT]": "4",
    }.items():
        output_text = output_text.replace(token, value)

    # BEFORE (simulated): the crippled 8-section extractor never saw this section to begin with, so
    # comparing its (identical, still-8-item) view of template vs. output finds no mismatch -- the
    # exact false-green this defect produced.
    crippled_sections = [
        s
        for s in extract_skeleton(real_template_text, CustomizationStep.STEP_10).sections
        if s != "WHY THIS MUST BE AIRTIGHT (loop context)"
    ]
    crippled_template_skeleton = TemplateSkeleton(convention="all_caps", sections=crippled_sections)
    crippled_output_skeleton = TemplateSkeleton(convention="all_caps", sections=crippled_sections)
    before_fix_result = check_fidelity(
        crippled_template_skeleton, crippled_output_skeleton, output_text, CustomizationStep.STEP_10
    )
    assert before_fix_result.structural_pass is True, (
        "sanity check on the OLD behavior: the crippled extractor's 8-item view really did see no "
        "difference -- confirming this defect really did produce a false green"
    )

    # AFTER (the actual fix): the real extractor sees all 9 sections in the template and correctly
    # notices the output is missing one of them.
    template_skeleton = extract_skeleton(real_template_text, CustomizationStep.STEP_10)
    output_skeleton = extract_skeleton(output_text, CustomizationStep.STEP_10)
    after_fix_result = check_fidelity(
        template_skeleton, output_skeleton, output_text, CustomizationStep.STEP_10
    )
    assert after_fix_result.structural_pass is False
    assert "WHY THIS MUST BE AIRTIGHT (loop context)" in after_fix_result.detail


def test_genuinely_customized_output_passes_structural_layer() -> None:
    output = (
        _TITLE
        + "ROLE\n\nAct as an architect for Acme Corp.\n\n"
        + "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
    )
    output_skeleton = extract_skeleton(output, CustomizationStep.STEP_10)
    result = check_fidelity(_template_skeleton(), output_skeleton, output, CustomizationStep.STEP_10)
    assert result.structural_pass is True
    assert result.overall is False  # awaiting layer 2 -- never true from layer 1 alone


def test_unverified_and_project_name_both_handled_correctly() -> None:
    """[UNVERIFIED] must survive (not flagged as unresolved); [PROJECT_NAME] must be resolved."""
    output = (
        _TITLE
        + "ROLE\n\nAct as an architect for Acme Corp.\n\n"
        + "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
    )
    output_skeleton = extract_skeleton(output, CustomizationStep.STEP_10)
    result = check_fidelity(_template_skeleton(), output_skeleton, output, CustomizationStep.STEP_10)
    assert result.structural_pass is True
    assert "[UNVERIFIED]" in output  # survived byte-identical
    assert "[PROJECT_NAME]" not in output  # genuinely resolved


def test_deliberately_restructured_customization_is_rejected() -> None:
    """SS8.4, demonstrated firing: a section dropped changes the skeleton and must fail."""
    restructured = (
        _TITLE
        + "ROLE\n\nAct as an architect for Acme Corp.\n\n"
        + "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        # section 2 dropped entirely -- still >= the vacuous-guard's floor, so this exercises the
        # real comparison path, not the vacuous guard
    )
    output_skeleton = extract_skeleton(restructured, CustomizationStep.STEP_10)
    result = check_fidelity(
        _template_skeleton(), output_skeleton, restructured, CustomizationStep.STEP_10
    )
    assert result.structural_pass is False
    assert "2. SECOND SECTION" in result.detail


def test_reordered_sections_are_rejected() -> None:
    """SS8.4's other shape: same sections present, wrong order -- must still fail."""
    reordered = (
        _TITLE
        + "ROLE\n\n2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as "
        + "[UNVERIFIED].\n\n1. FIRST SECTION\n\nDo the first thing for acme-repo.\n"
    )
    output_skeleton = extract_skeleton(reordered, CustomizationStep.STEP_10)
    result = check_fidelity(_template_skeleton(), output_skeleton, reordered, CustomizationStep.STEP_10)
    assert result.structural_pass is False
    assert "mismatch" in result.detail


def test_unresolved_placeholder_is_rejected() -> None:
    output = (
        _TITLE
        + "ROLE\n\nAct as an architect for [PROJECT_NAME].\n\n"  # never filled
        + "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
    )
    output_skeleton = extract_skeleton(output, CustomizationStep.STEP_10)
    result = check_fidelity(_template_skeleton(), output_skeleton, output, CustomizationStep.STEP_10)
    assert result.structural_pass is False
    assert "PROJECT_NAME" in result.detail


def test_surviving_customize_marker_is_rejected() -> None:
    template_with_marker = TEMPLATE_TEXT + "\n<<CUSTOMIZE: adjust per project>>\n"
    template_skeleton = extract_skeleton(template_with_marker, CustomizationStep.STEP_10)
    output = (
        _TITLE
        + "ROLE\n\nAct as an architect for Acme Corp.\n\n"
        + "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
        + "\n<<CUSTOMIZE: adjust per project>>\n"  # marker survived -- must never reach the agent
    )
    output_skeleton = extract_skeleton(output, CustomizationStep.STEP_10)
    result = check_fidelity(template_skeleton, output_skeleton, output, CustomizationStep.STEP_10)
    assert result.structural_pass is False
    assert "CUSTOMIZE" in result.detail


def test_placeholder_deletion_only_customization_is_rejected_by_layer_2() -> None:
    """SS8.5, demonstrated firing: tokens stripped but nothing project-specific injected passes
    layer 1 (structurally identical skeleton, no bracket tokens left) but must be rejected by the
    layer-2 judge -- this test simulates that judge call returning passed=False."""
    generic_output = (
        _TITLE
        + "ROLE\n\nAct as an architect for the project.\n\n"  # placeholder deleted, not replaced
        + "1. FIRST SECTION\n\nDo the first thing for the repo.\n\n"
        + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
    )
    output_skeleton = extract_skeleton(generic_output, CustomizationStep.STEP_10)
    structural = check_fidelity(
        _template_skeleton(), output_skeleton, generic_output, CustomizationStep.STEP_10
    )
    assert structural.structural_pass is True  # layer 1 alone cannot catch generic filler

    # Layer 2: the judge correctly recognizes generic filler and rejects it.
    final = apply_judge_layer(
        structural,
        judge_passed=False,
        judge_reason="verbatim template text with placeholders deleted, not replaced -- generic filler",
    )
    assert final.overall is False
    assert final.judge_pass is False


def test_genuinely_specific_output_passes_layer_2() -> None:
    output = (
        _TITLE
        + "ROLE\n\nAct as an architect for Acme Corp.\n\n"
        + "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
    )
    output_skeleton = extract_skeleton(output, CustomizationStep.STEP_10)
    structural = check_fidelity(_template_skeleton(), output_skeleton, output, CustomizationStep.STEP_10)
    assert structural.structural_pass is True

    final = apply_judge_layer(structural, judge_passed=True, judge_reason="names real project details")
    assert final.overall is True


def test_apply_judge_layer_requires_structural_pass_first() -> None:
    failing = FidelityResult(structural_pass=False, judge_pass=None, overall=False, detail="x")
    with pytest.raises(ValueError, match="structurally-passing"):
        apply_judge_layer(failing, judge_passed=True, judge_reason="irrelevant")


def test_fidelity_result_two_layer_invariant_rejects_overall_true_without_judge_pass() -> None:
    with pytest.raises(ValueError):
        FidelityResult(structural_pass=True, judge_pass=None, overall=True, detail="bad")
