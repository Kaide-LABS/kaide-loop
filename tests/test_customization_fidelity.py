"""The two-layer fidelity check. Implements CUSTOMIZATION_PHASE_1_SPEC.md SS4.3.

Demonstrates SS8.4 (a deliberately restructured customization is rejected) and SS8.5 (a
placeholder-deletion-only "customization" is rejected) firing for real, not merely existing.
"""

from __future__ import annotations

import pytest

from loopr.customization.fidelity import apply_judge_layer, check_fidelity
from loopr.customization.templates import extract_skeleton
from loopr.models.common import CustomizationStep
from loopr.models.customization import FidelityResult, TemplateSkeleton

TEMPLATE_TEXT = (
    "ROLE\n\nAct as an architect for [PROJECT_NAME].\n\n"
    "1. FIRST SECTION\n\nDo the first thing for [PROJECT_REPO_NAME].\n\n"
    "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
)


def _template_skeleton() -> TemplateSkeleton:
    return extract_skeleton(TEMPLATE_TEXT, CustomizationStep.STEP_10)


def test_genuinely_customized_output_passes_structural_layer() -> None:
    output = (
        "ROLE\n\nAct as an architect for Acme Corp.\n\n"
        "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
    )
    output_skeleton = extract_skeleton(output, CustomizationStep.STEP_10)
    result = check_fidelity(_template_skeleton(), output_skeleton, output, CustomizationStep.STEP_10)
    assert result.structural_pass is True
    assert result.overall is False  # awaiting layer 2 -- never true from layer 1 alone


def test_unverified_and_project_name_both_handled_correctly() -> None:
    """[UNVERIFIED] must survive (not flagged as unresolved); [PROJECT_NAME] must be resolved."""
    output = (
        "ROLE\n\nAct as an architect for Acme Corp.\n\n"
        "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
    )
    output_skeleton = extract_skeleton(output, CustomizationStep.STEP_10)
    result = check_fidelity(_template_skeleton(), output_skeleton, output, CustomizationStep.STEP_10)
    assert result.structural_pass is True
    assert "[UNVERIFIED]" in output  # survived byte-identical
    assert "[PROJECT_NAME]" not in output  # genuinely resolved


def test_deliberately_restructured_customization_is_rejected() -> None:
    """SS8.4, demonstrated firing: a section dropped changes the skeleton and must fail."""
    restructured = (
        "ROLE\n\nAct as an architect for Acme Corp.\n\n"
        "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
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
        "ROLE\n\n2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as "
        "[UNVERIFIED].\n\n1. FIRST SECTION\n\nDo the first thing for acme-repo.\n"
    )
    output_skeleton = extract_skeleton(reordered, CustomizationStep.STEP_10)
    result = check_fidelity(_template_skeleton(), output_skeleton, reordered, CustomizationStep.STEP_10)
    assert result.structural_pass is False
    assert "mismatch" in result.detail


def test_unresolved_placeholder_is_rejected() -> None:
    output = (
        "ROLE\n\nAct as an architect for [PROJECT_NAME].\n\n"  # never filled
        "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
    )
    output_skeleton = extract_skeleton(output, CustomizationStep.STEP_10)
    result = check_fidelity(_template_skeleton(), output_skeleton, output, CustomizationStep.STEP_10)
    assert result.structural_pass is False
    assert "PROJECT_NAME" in result.detail


def test_surviving_customize_marker_is_rejected() -> None:
    template_with_marker = TEMPLATE_TEXT + "\n<<CUSTOMIZE: adjust per project>>\n"
    template_skeleton = extract_skeleton(template_with_marker, CustomizationStep.STEP_10)
    output = (
        "ROLE\n\nAct as an architect for Acme Corp.\n\n"
        "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
        "\n<<CUSTOMIZE: adjust per project>>\n"  # marker survived -- must never reach the agent
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
        "ROLE\n\nAct as an architect for the project.\n\n"  # placeholder deleted, not replaced
        "1. FIRST SECTION\n\nDo the first thing for the repo.\n\n"
        "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
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
        "ROLE\n\nAct as an architect for Acme Corp.\n\n"
        "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
        "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
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
