"""Template discovery, skeleton extraction, and placeholder inventory.

Implements CUSTOMIZATION_PHASE_1_SPEC.md SS4.2, SS4.3. Exercises the three traps directly against
the real files in prompts/Template_prompts/ where possible, and against synthetic fixtures for
cases the real templates don't happen to contain (e.g. a surviving <<CUSTOMIZE:>> marker).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from loopr.customization.templates import (
    NON_PLACEHOLDER_BRACKET_TOKENS,
    STEP10_PLACEHOLDER_ALLOWLIST,
    TemplateDiscoveryError,
    VacuousSkeletonError,
    discover_template,
    extract_skeleton,
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


def test_step10_skeleton_extraction_finds_all_caps_sections() -> None:
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    skeleton = extract_skeleton(text, CustomizationStep.STEP_10)
    assert skeleton.convention == "all_caps"
    assert skeleton.sections == [
        "ROLE",
        "DELIVERABLES (TWO -- BOTH REQUIRED, NEITHER OPTIONAL)",
        "1. CONTEXTUALIZE (REPO SCAN -- LOCAL TOOLS)",
        "2. RESEARCH & GROUNDING (EXTERNAL DEPENDENCY ADD-ON)",
        "3. UNIVERSAL INVARIANTS (bake into BOTH the modernised PRD and the Phase 1 spec)",
        "4. DELIVERABLE A -- MODERNISE & ENHANCE THE PRD",
        "5. DELIVERABLE B -- PHASE_1_SPEC.md (BUILT FROM THE MODERNISED PRD)",
        "6. HANDOFF",
    ]


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


@pytest.mark.parametrize("decoy", ["[UNVERIFIED]", "[EXECUTOR]"])
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
