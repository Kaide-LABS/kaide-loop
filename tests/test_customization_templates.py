"""Template discovery, skeleton extraction, and placeholder inventory.

Implements CUSTOMIZATION_PHASE_1_SPEC.md SS4.2, SS4.3. Exercises the three traps directly against
the real files in prompts/Template_prompts/ where possible, and against synthetic fixtures for
cases the real templates don't happen to contain (e.g. a surviving <<CUSTOMIZE:>> marker).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from loopr.customization.templates import (
    _BRACKET_TOKEN_RE,
    NON_PLACEHOLDER_BRACKET_TOKENS,
    STEP10_PLACEHOLDER_ALLOWLIST,
    TemplateDiscoveryError,
    VacuousSkeletonError,
    discover_template,
    extract_skeleton,
    find_gap_candidates,
    inventory_placeholders,
    surviving_customize_markers,
)
from loopr.models.common import CustomizationStep

REAL_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "prompts" / "Template_prompts"


def test_step10_has_zero_markdown_headers() -> None:
    """The trap, verified against the real file: a markdown-header extractor finds nothing here."""
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    header_lines = [line for line in text.splitlines() if line.strip().startswith("#")]
    assert header_lines == []


def test_why_this_must_be_airtight_is_present_in_the_extracted_skeleton() -> None:
    """Regression for the confirmed defect: this section (line 52) was silently dropped because it
    ends in a lowercase parenthetical qualifier and the old character class required the ENTIRE
    line to be uppercase. Asserted directly against the real file, not against a stated count."""
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    skeleton = extract_skeleton(text, CustomizationStep.STEP_10)
    assert "WHY THIS MUST BE AIRTIGHT (loop context)" in skeleton.sections


def test_step10_skeleton_is_exactly_nine_sections_with_title_declared_excluded() -> None:
    """The corrected count (CUSTOMIZATION_PHASE_1_SPEC.md SS4.3, 2026-08-01): 9, not 8 -- and the
    document title (line 1) is excluded by a DECLARED rule (always skip line 1), not by an
    incidental regex gap. Cross-checked independently with gap analysis below, per SS4.3's
    verification rule: the file is the oracle, and a second, convention-independent mechanism must
    agree, rather than trusting this one extractor's count on its own."""
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    skeleton = extract_skeleton(text, CustomizationStep.STEP_10)
    assert skeleton.convention == "all_caps"
    assert skeleton.sections == [
        "ROLE",
        "DELIVERABLES (TWO -- BOTH REQUIRED, NEITHER OPTIONAL)",
        "WHY THIS MUST BE AIRTIGHT (loop context)",
        "1. CONTEXTUALIZE (REPO SCAN -- LOCAL TOOLS)",
        "2. RESEARCH & GROUNDING (EXTERNAL DEPENDENCY ADD-ON)",
        "3. UNIVERSAL INVARIANTS (bake into BOTH the modernised PRD and the Phase 1 spec)",
        "4. DELIVERABLE A -- MODERNISE & ENHANCE THE PRD",
        "5. DELIVERABLE B -- PHASE_1_SPEC.md (BUILT FROM THE MODERNISED PRD)",
        "6. HANDOFF",
    ]
    assert len(skeleton.sections) == 9

    # Independent cross-check (FIX 3): gap analysis, built without sharing _is_all_caps_section's
    # regex, must find nothing suspicious left over except the three ALREADY-REVIEWED, genuinely
    # benign colon-terminated sub-labels (not real sections in this convention) -- named explicitly
    # here so a NEW, unreviewed candidate appearing later fails this assertion loudly.
    reviewed_benign_sub_labels = {
        "DOCUMENTATION & CODEBASE -- /Nia:",
        "WEB SEARCH:",
        "HALT CONDITIONS:",
    }
    gap_candidates = set(find_gap_candidates(text, skeleton.sections))
    assert gap_candidates == reviewed_benign_sub_labels, (
        f"unexpected gap-analysis candidates: {gap_candidates - reviewed_benign_sub_labels} -- "
        "review whether any of these is a genuinely missed section before adding it to the "
        "reviewed-benign set"
    )


def test_gap_analysis_flags_a_crippled_extractors_miss() -> None:
    """Demonstrates the checker firing for real: take the real template, extract with the OLD,
    pre-fix 8-section list (simulating the crippled all-caps-only convention this defect shipped
    with), and confirm gap analysis reports exactly the section that extraction dropped."""
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    crippled_sections = [
        "ROLE",
        "DELIVERABLES (TWO -- BOTH REQUIRED, NEITHER OPTIONAL)",
        "1. CONTEXTUALIZE (REPO SCAN -- LOCAL TOOLS)",
        "2. RESEARCH & GROUNDING (EXTERNAL DEPENDENCY ADD-ON)",
        "3. UNIVERSAL INVARIANTS (bake into BOTH the modernised PRD and the Phase 1 spec)",
        "4. DELIVERABLE A -- MODERNISE & ENHANCE THE PRD",
        "5. DELIVERABLE B -- PHASE_1_SPEC.md (BUILT FROM THE MODERNISED PRD)",
        "6. HANDOFF",
    ]
    candidates = find_gap_candidates(text, crippled_sections)
    assert "WHY THIS MUST BE AIRTIGHT (loop context)" in candidates


@pytest.mark.parametrize(
    ("filename", "step", "expected_min_sections"),
    [
        ("STEP _11", CustomizationStep.STEP_11, 9),
        ("step_12", CustomizationStep.STEP_12, 11),
    ],
)
def test_markdown_convention_templates_extract_correctly(
    filename: str, step: CustomizationStep, expected_min_sections: int
) -> None:
    text = (REAL_TEMPLATES_DIR / filename).read_text(encoding="utf-8")
    skeleton = extract_skeleton(text, step)
    assert len(skeleton.sections) >= expected_min_sections
    assert all(s.startswith("#") for s in skeleton.sections)


def test_vacuous_extraction_halts_never_passes() -> None:
    """The guard, fired for real: near-empty input yields a skeleton too short to trust, and
    extraction refuses rather than silently succeeding by comparing two near-empty lists."""
    with pytest.raises(VacuousSkeletonError):
        extract_skeleton("ROLE\n\nsome body text with no other headers at all\n", CustomizationStep.STEP_10)


def test_empty_text_is_vacuous() -> None:
    with pytest.raises(VacuousSkeletonError):
        extract_skeleton("", CustomizationStep.STEP_10)


@pytest.mark.parametrize("decoy", ["[UNVERIFIED]", "[EXECUTOR]", "[RESEARCH FOCUS]", "[PHASE_COUNT]"])
def test_decoys_are_never_treated_as_placeholders(decoy: str) -> None:
    assert decoy not in STEP10_PLACEHOLDER_ALLOWLIST
    assert decoy in NON_PLACEHOLDER_BRACKET_TOKENS
    text = f"Some line with {decoy} embedded, and [PROJECT_NAME] as a real placeholder."
    found = inventory_placeholders(text, CustomizationStep.STEP_10)
    assert decoy not in found
    assert "[PROJECT_NAME]" in found


def test_step10_real_file_unverified_occurrences_are_not_placeholders() -> None:
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    assert text.count("[UNVERIFIED]") == 3
    found = inventory_placeholders(text, CustomizationStep.STEP_10)
    assert "[UNVERIFIED]" not in found


def test_step10_real_file_research_focus_occurrences_are_not_placeholders() -> None:
    """Regression: [RESEARCH FOCUS] (SS1, lines 84-86) reads like a placeholder but is bound to a
    value the STEP10-EXECUTING agent derives from its own repo scan, not one the customizer can
    supply -- confirmed against the real precedent in prompts/loopr/step10_prd_modernization.md,
    which leaves it untouched. It must never be treated as resolvable, like [UNVERIFIED]/[EXECUTOR]."""
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    assert text.count("[RESEARCH FOCUS]") == 3
    found = inventory_placeholders(text, CustomizationStep.STEP_10)
    assert "[RESEARCH FOCUS]" not in found
    assert "[RESEARCH FOCUS]" in NON_PLACEHOLDER_BRACKET_TOKENS


def test_step10_real_file_phase_count_occurrence_is_not_a_placeholder() -> None:
    """Regression: [PHASE_COUNT] (SS5 line 282, inside SS0's phase-plan-header instruction) reads
    like a placeholder but is bound to a value the STEP10-EXECUTING agent derives from its own Phase
    1 breakdown, not one the customizer can supply -- confirmed against the real precedent
    (prompts/loopr/step10_prd_modernization.md line 261: "PHASE_COUNT is not yet known; determine and
    state it here ... do not guess a number in advance"). Same defect class as [RESEARCH FOCUS], and
    STEP_10-SPECIFIC: [PHASE_COUNT] becomes genuinely customizer-resolvable for step11/step12 once
    step10 has executed (SS5's two-pass finding) -- do not carry this exclusion forward to Phase 2
    without re-deriving it for those steps."""
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    assert text.count("[PHASE_COUNT]") == 1
    found = inventory_placeholders(text, CustomizationStep.STEP_10)
    assert "[PHASE_COUNT]" not in found
    assert "[PHASE_COUNT]" in NON_PLACEHOLDER_BRACKET_TOKENS


def test_step10_bracket_token_classification_is_complete() -> None:
    """The load-bearing completeness check: every distinct bracket-shaped token actually present in
    the real STEP_10 file must be classified by EITHER STEP10_PLACEHOLDER_ALLOWLIST OR
    NON_PLACEHOLDER_BRACKET_TOKENS -- never neither. A token in neither set is not harmlessly
    ignored, it is UNCLASSIFIED, and inventory_placeholders would silently treat it as "not a
    placeholder" without anyone having actually decided that. This is what would have caught both
    [RESEARCH FOCUS] and [PHASE_COUNT] before they shipped as misclassified in the OTHER direction
    (wrongly allowlisted) -- this check catches the missing-classification shape of the same defect
    class, and the two sets being disjoint is asserted as a sanity companion."""
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    found = set(_BRACKET_TOKEN_RE.findall(text))
    classified = STEP10_PLACEHOLDER_ALLOWLIST | NON_PLACEHOLDER_BRACKET_TOKENS
    unclassified = found - classified
    assert unclassified == set(), (
        f"bracket token(s) found in the real STEP_10 file with no classification in either "
        f"STEP10_PLACEHOLDER_ALLOWLIST or NON_PLACEHOLDER_BRACKET_TOKENS: {sorted(unclassified)} -- "
        "classify each per the rule documented in templates.py before this can pass"
    )
    assert STEP10_PLACEHOLDER_ALLOWLIST & NON_PLACEHOLDER_BRACKET_TOKENS == set(), (
        "a token cannot be both customizer-resolvable and runtime-derived for the same step"
    )


def test_completeness_check_fails_when_a_real_token_is_unclassified() -> None:
    """Demonstrates the completeness check firing for real, not merely existing: reproduce the exact
    shape of the [RESEARCH FOCUS]/[PHASE_COUNT] miss by removing a real token from BOTH sets and
    confirming the same set-difference logic test_step10_bracket_token_classification_is_complete
    uses actually detects it, rather than silently passing on an incomplete classification."""
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    found = set(_BRACKET_TOKEN_RE.findall(text))
    crippled_classified = (STEP10_PLACEHOLDER_ALLOWLIST | NON_PLACEHOLDER_BRACKET_TOKENS) - {
        "[PHASE_COUNT]"
    }
    unclassified = found - crippled_classified
    assert unclassified == {"[PHASE_COUNT]"}


def test_surviving_customize_marker_detected() -> None:
    text = "some line\n<<CUSTOMIZE: fill this in>>\nmore text"
    assert surviving_customize_markers(text) == ["<<CUSTOMIZE: fill this in>>"]


def test_no_customize_markers_in_step10() -> None:
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    assert surviving_customize_markers(text) == []


@pytest.fixture
def templates_repo(tmp_path: Path) -> Path:
    templates_dir = tmp_path / "prompts" / "Template_prompts"
    templates_dir.mkdir(parents=True)
    (templates_dir / "STEP_10").write_text("ROLE\n\nBODY\n\n1. FIRST SECTION\n\n2. SECOND SECTION\n", encoding="utf-8")
    (templates_dir / "STEP _11").write_text("## ROLE\n\n## OTHER\n", encoding="utf-8")
    (templates_dir / "step_12").write_text("## ROLE\n\n### SUB\n\n## OTHER\n", encoding="utf-8")
    return tmp_path


def test_discover_template_handles_inconsistent_naming(templates_repo: Path) -> None:
    """The second trap: STEP_10, "STEP _11" (embedded space), step_12 -- a tidy glob would miss
    "STEP _11". Discovery must handle them as they are."""
    assert discover_template(templates_repo, CustomizationStep.STEP_10).name == "STEP_10"
    assert discover_template(templates_repo, CustomizationStep.STEP_11).name == "STEP _11"
    assert discover_template(templates_repo, CustomizationStep.STEP_12).name == "step_12"


def test_discover_template_raises_when_directory_missing(tmp_path: Path) -> None:
    with pytest.raises(TemplateDiscoveryError):
        discover_template(tmp_path, CustomizationStep.STEP_10)


def test_discover_template_raises_when_file_missing(templates_repo: Path) -> None:
    (templates_repo / "prompts" / "Template_prompts" / "STEP_10").unlink()
    with pytest.raises(TemplateDiscoveryError):
        discover_template(templates_repo, CustomizationStep.STEP_10)
