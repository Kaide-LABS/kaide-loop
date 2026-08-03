"""The structural (layer-1) fidelity check. Implements CUSTOMIZATION_PHASE_1_SPEC.md SS4.3.

The same two-layer discipline loopr applies to its own six-condition test, applied here to
customization output: layer 1 (this module) is deterministic, pure code, no model call. Layer 2
(the STEP10_FIDELITY_JUDGE call, wired in customize.py) runs only if layer 1 passes.
"""

from __future__ import annotations

from loopr.customization.templates import (
    surviving_customize_markers,
    unresolved_fill_in_blocks,
    unresolved_placeholders,
)
from loopr.models.common import CustomizationStep
from loopr.models.customization import FidelityResult, TemplateSkeleton


def check_structural_fidelity(
    template_skeleton: TemplateSkeleton,
    output_skeleton: TemplateSkeleton,
    template_text: str,
    output_text: str,
    step: CustomizationStep,
) -> FidelityResult:
    """Layer 1. Fails structurally if: a section header from the template is missing; headers
    appear in a different order; any allowlisted placeholder token remains unresolved; a multi-line
    fill-in instruction block (found via the independent wide-scan oracle, SS4.3 decided 2026-08-03 --
    e.g. STEP_10's `[PROJECT HARD BOUNDARY ...]`) survives byte-identical from the template; or a
    `<<CUSTOMIZE: ...>>` marker survives into the output. Never sets overall=True on its own -- that
    requires layer 2 (STEP10_FIDELITY_JUDGE) to also pass."""
    if template_skeleton.sections != output_skeleton.sections:
        missing = [s for s in template_skeleton.sections if s not in output_skeleton.sections]
        extra = [s for s in output_skeleton.sections if s not in template_skeleton.sections]
        detail = (
            f"section skeleton mismatch -- template has {template_skeleton.sections}, output has "
            f"{output_skeleton.sections} (missing={missing}, unexpected={extra}); every section "
            "must be preserved, in the same order -- fill and adapt, never restructure"
        )
        return FidelityResult(structural_pass=False, judge_pass=None, overall=False, detail=detail)

    unresolved = unresolved_placeholders(output_text, step)
    if unresolved:
        return FidelityResult(
            structural_pass=False,
            judge_pass=None,
            overall=False,
            detail=f"unresolved placeholder(s) remain in output: {unresolved}",
        )

    unfilled_blocks = unresolved_fill_in_blocks(template_text, output_text, step)
    if unfilled_blocks:
        return FidelityResult(
            structural_pass=False,
            judge_pass=None,
            overall=False,
            detail=(
                "multi-line fill-in instruction block(s) survived byte-identical from the template: "
                f"{unfilled_blocks!r} -- these are project-specific instructions (e.g. the hard "
                "boundary) that must be replaced with real content, not left as the template's own "
                "placeholder text"
            ),
        )

    surviving = surviving_customize_markers(output_text)
    if surviving:
        return FidelityResult(
            structural_pass=False,
            judge_pass=None,
            overall=False,
            detail=(
                f"<<CUSTOMIZE: ...>> marker(s) survived into the output: {surviving} -- these are "
                "instructions TO the customizer and must never reach the executing agent"
            ),
        )

    return FidelityResult(
        structural_pass=True,
        judge_pass=None,
        overall=False,
        detail="structural layer passed; awaiting layer-2 genuineness judgment",
    )


def apply_judge_layer(structural_result: FidelityResult, judge_passed: bool, judge_reason: str) -> FidelityResult:
    """Combines layer 1's result with layer 2's judge verdict. Only called when layer 1 passed --
    layer 2 never runs otherwise (CUSTOMIZATION_PHASE_1_SPEC.md SS4.3: "runs only if layer 1
    passes")."""
    if not structural_result.structural_pass:
        raise ValueError("apply_judge_layer requires a structurally-passing result")
    return FidelityResult(
        structural_pass=True,
        judge_pass=judge_passed,
        overall=judge_passed,
        detail=judge_reason,
    )


def check_fidelity(
    template_skeleton: TemplateSkeleton,
    output_skeleton: TemplateSkeleton,
    template_text: str,
    output_text: str,
    step: CustomizationStep,
) -> FidelityResult:
    """Layer 1 only -- convenience entry point for callers that just want the structural verdict.
    Layer 2 requires an actual judge call, orchestrated in customize.py, not here."""
    return check_structural_fidelity(template_skeleton, output_skeleton, template_text, output_text, step)
