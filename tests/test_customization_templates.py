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
    STEP10_FILL_IN_BLOCK_MARKERS,
    STEP10_PLACEHOLDER_ALLOWLIST,
    STEP11_NON_PLACEHOLDER_BRACKET_TOKENS,
    STEP11_PLACEHOLDER_ALLOWLIST,
    STEP11_SECTION_DELETIONS,
    STEP12_NON_PLACEHOLDER_BRACKET_TOKENS,
    STEP12_PLACEHOLDER_ALLOWLIST,
    STEP12_SECTION_DELETIONS,
    TemplateDiscoveryError,
    VacuousSkeletonError,
    discover_template,
    expected_output_sections,
    extract_skeleton,
    find_conditional_blocks,
    find_fill_in_blocks,
    find_gap_candidates,
    find_step10_execution_artifacts,
    find_unclassified_bracket_spans,
    inventory_placeholders,
    surviving_customize_markers,
    unresolved_conditional_blocks,
    unresolved_fill_in_blocks,
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
    """The load-bearing completeness check, INDEPENDENT-ORACLE version (CUSTOMIZATION_PHASE_1_SPEC.md
    SS4.3, decided 2026-08-03). The prior version of this test checked _BRACKET_TOKEN_RE's own output
    against itself -- a self-referential check that certifies itself and is structurally blind to
    anything that regex's narrow character class cannot see. It cannot detect a token unclassified
    for want of the *narrow regex never matching it in the first place*, which is exactly what
    happened with STEP_10's multi-line `[PROJECT HARD BOUNDARY ...]` block (SS3): invisible to
    _BRACKET_TOKEN_RE (no DOTALL, character class excludes `-`, `:`, `/`, `(`), so it never appeared
    in `found` for the old test to even consider.

    `find_unclassified_bracket_spans` is the fix: it scans with the WIDE, permissive oracle
    (`_WIDE_BRACKET_SPAN_RE`, DOTALL, tolerant of any character except `[`/`]`) and returns whatever
    that oracle finds that is NEITHER a classified short token NOR a recognized fill-in block
    (STEP10_FILL_IN_BLOCK_MARKERS). A genuinely complete classification returns nothing -- if
    anything survives, it is UNCLASSIFIED, never silently absorbed either way, and needs a human to
    add it to the appropriate registry in templates.py."""
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    unclassified = find_unclassified_bracket_spans(text, CustomizationStep.STEP_10)
    assert unclassified == [], (
        f"bracket span(s) found in the real STEP_10 file by the wide oracle with no classification: "
        f"{unclassified} -- classify each per the rule documented in templates.py before this can "
        "pass (a short token, or a recognized fill-in block via STEP10_FILL_IN_BLOCK_MARKERS)"
    )
    assert STEP10_PLACEHOLDER_ALLOWLIST & NON_PLACEHOLDER_BRACKET_TOKENS == set(), (
        "a token cannot be both customizer-resolvable and runtime-derived for the same step"
    )


def test_hard_boundary_block_is_the_one_span_the_narrow_regex_cannot_see() -> None:
    """Confirms the defect's exact shape against the real file: comparing the WIDE oracle's raw
    output directly against the NARROW token regex's raw output (not the final, marker-aware
    classification -- that's test_step10_bracket_token_classification_is_complete's job) shows
    exactly one span the narrow regex cannot see at all, and it is the hard-boundary block."""
    from loopr.customization.templates import _BRACKET_TOKEN_RE, _WIDE_BRACKET_SPAN_RE

    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    wide = set(_WIDE_BRACKET_SPAN_RE.findall(text))
    narrow = set(_BRACKET_TOKEN_RE.findall(text))
    invisible_to_narrow = wide - narrow
    assert len(invisible_to_narrow) == 1
    [span] = invisible_to_narrow
    assert span.startswith("[PROJECT HARD BOUNDARY")
    assert len(span) == 303

    # And confirm it's now recognized, not merely detected as a gap.
    assert find_fill_in_blocks(text, CustomizationStep.STEP_10) == [span]
    assert find_unclassified_bracket_spans(text, CustomizationStep.STEP_10) == []


def test_hard_boundary_reappears_as_unclassified_if_marker_registry_is_emptied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Carried forward from Phase 1's review close (CUSTOMIZATION_PHASE_2_SPEC.md SS2): the
    fill-in-block marker registry itself was never regression-tested -- every existing test only
    confirms the CURRENT registry correctly recognizes the hard-boundary block, never that removing
    it from the registry makes the block reappear as genuinely unclassified. Demonstrated here before
    STEP10_FILL_IN_BLOCK_MARKERS's exact pattern is extended to two more steps (STEP11_/STEP12_ own
    marker registries), so all three inherit a fully tested mechanism instead of the same untested
    edge three times over."""
    import loopr.customization.templates as templates_module

    monkeypatch.setattr(templates_module, "STEP10_FILL_IN_BLOCK_MARKERS", ())

    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    assert templates_module.find_fill_in_blocks(text, CustomizationStep.STEP_10) == []
    unclassified = templates_module.find_unclassified_bracket_spans(text, CustomizationStep.STEP_10)
    assert len(unclassified) == 1
    assert unclassified[0].startswith("[PROJECT HARD BOUNDARY")

    # Sanity: the module's real, un-patched registry still has the marker -- confirms the
    # reappearance above is caused specifically by emptying the registry, not some other effect.
    assert STEP10_FILL_IN_BLOCK_MARKERS == ("[PROJECT HARD BOUNDARY",)


def test_completeness_check_fails_when_a_real_token_is_unclassified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Demonstrates the completeness check firing for real, not merely existing: reproduce the exact
    shape of the [RESEARCH FOCUS]/[PHASE_COUNT] miss by removing a real token from
    NON_PLACEHOLDER_BRACKET_TOKENS (via monkeypatch, so find_unclassified_bracket_spans's own module
    globals see the crippled set) and confirming it is reported as unclassified -- the hard-boundary
    block, correctly classified via the marker registry, must NOT also show up as noise."""
    import loopr.customization.templates as templates_module

    crippled = templates_module.NON_PLACEHOLDER_BRACKET_TOKENS - {"[PHASE_COUNT]"}
    monkeypatch.setattr(templates_module, "NON_PLACEHOLDER_BRACKET_TOKENS", crippled)

    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    unclassified = templates_module.find_unclassified_bracket_spans(text, CustomizationStep.STEP_10)
    assert unclassified == ["[PHASE_COUNT]"]


def test_unresolved_fill_in_blocks_detects_untouched_hard_boundary() -> None:
    """FIX 1's detection primitive, unit-tested directly against the real file: a block still
    byte-identical to the template is unresolved; a genuinely replaced block is not. "Resolved"
    cannot mean "token absent" for a multi-line prose block the way it does for [PROJECT_NAME] -- the
    template's own original text is the sentinel instead."""
    template_text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")

    untouched_output = template_text  # no customization applied at all
    unresolved = unresolved_fill_in_blocks(template_text, untouched_output, CustomizationStep.STEP_10)
    assert len(unresolved) == 1
    assert unresolved[0].startswith("[PROJECT HARD BOUNDARY")

    [block] = find_fill_in_blocks(template_text, CustomizationStep.STEP_10)
    filled_output = template_text.replace(block, "Never replicate the client's proprietary model.")
    assert unresolved_fill_in_blocks(template_text, filled_output, CustomizationStep.STEP_10) == []


def test_surviving_customize_marker_detected() -> None:
    text = "some line\n<<CUSTOMIZE: fill this in>>\nmore text"
    assert surviving_customize_markers(text) == ["<<CUSTOMIZE: fill this in>>"]


def test_no_customize_markers_in_step10() -> None:
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    assert surviving_customize_markers(text) == []


@pytest.mark.parametrize(
    ("filename", "hard_boundary_needle"),
    [("STEP _11", "name the specific thing"), ("step_12", "exhaustively list the forbidden")],
)
def test_surviving_customize_markers_finds_the_hard_boundary_block(
    filename: str, hard_boundary_needle: str
) -> None:
    """Regression: found while building CONDITIONAL_BLOCK_MARKERS (CUSTOMIZATION_PHASE_2_SPEC.md
    SS3.4) -- the HARD BOUNDARY `<<CUSTOMIZE: ...>>` block in both real templates contains "->"
    arrow notation ("client demo -> ..."), which the previous `[^>]*`-excluding pattern could not
    cross, silently finding ZERO markers for this block in either template. A customization shipping
    this section completely unfilled -- the single highest-stakes field these templates define --
    would have passed layer 1 undetected. Demonstrated against the real files, not a synthetic
    fixture engineered to avoid the exact shape that broke it."""
    text = (REAL_TEMPLATES_DIR / filename).read_text(encoding="utf-8")
    markers = surviving_customize_markers(text)
    assert any(hard_boundary_needle in m for m in markers), (
        f"the HARD BOUNDARY <<CUSTOMIZE: ...>> block was not found among {len(markers)} marker(s) "
        f"in {filename} -- the '->' truncation regression may have resurfaced"
    )


def test_surviving_customize_markers_handles_arrow_notation_in_a_minimal_case() -> None:
    """Unit-level isolation of the regression above, independent of the real files' full length."""
    text = "<<CUSTOMIZE: a -> b, c -> d>>"
    assert surviving_customize_markers(text) == [text]


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


# ============================================================================
# CUSTOMIZATION_PHASE_2_SPEC.md -- step11/step12 registries, section deletion, conditional blocks.
# ============================================================================

_STEP11_TEXT = (REAL_TEMPLATES_DIR / "STEP _11").read_text(encoding="utf-8")
_STEP12_TEXT = (REAL_TEMPLATES_DIR / "step_12").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("step", "text", "expected_tokens"),
    [
        (
            CustomizationStep.STEP_11,
            _STEP11_TEXT,
            {
                "[ ]",
                "[EXECUTOR]",
                "[PHASE_COUNT]",
                "[PROJECT]",
                "[PROJECT_NAME]",
                "[PROJECT_REPO_NAME]",
                "[PROJECT_TAG]",
                "[implemented instead]",
                "[reason]",
                "[specified]",
                "[wanted to do]",
                "[why the invariant prevents it]",
            },
        ),
        (
            CustomizationStep.STEP_12,
            _STEP12_TEXT,
            {
                "[ ]",
                "[EXECUTOR]",
                "[EXECUTOR_AGENT_FICTION]",
                "[PHASE_COUNT]",
                "[PROJECT]",
                "[PROJECT_NAME]",
                "[PROJECT_REPO_NAME]",
                "[PROJECT_TAG]",
            },
        ),
    ],
)
def test_narrow_token_inventory_matches_real_file_exactly(
    step: CustomizationStep, text: str, expected_tokens: set[str]
) -> None:
    """CUSTOMIZATION_PHASE_2_SPEC.md SS1.2's table, verified independently against the real files
    (not transcribed) -- every distinct narrow-regex-shaped bracket token actually present, and
    nothing else."""
    from loopr.customization.templates import _BRACKET_TOKEN_RE

    assert set(_BRACKET_TOKEN_RE.findall(text)) == expected_tokens


@pytest.mark.parametrize(
    ("step", "text"),
    [(CustomizationStep.STEP_11, _STEP11_TEXT), (CustomizationStep.STEP_12, _STEP12_TEXT)],
)
def test_step11_step12_bracket_token_classification_is_complete(
    step: CustomizationStep, text: str
) -> None:
    """The independent-oracle completeness check (same discipline as step10's), run against both real
    templates as an early step per CUSTOMIZATION_PHASE_2_SPEC.md SS3.2 -- resolves the [PROJECT_*]
    finding flagged at Phase 1's close (SS7.2): it must be classified, not merely rediscovered."""
    unclassified = find_unclassified_bracket_spans(text, step)
    assert unclassified == [], (
        f"bracket span(s) found in the real {step.value} file with no classification: {unclassified}"
    )


@pytest.mark.parametrize("step", [CustomizationStep.STEP_11, CustomizationStep.STEP_12])
def test_project_star_is_documentation_not_a_placeholder(step: CustomizationStep) -> None:
    """SS7.2's finding, resolved: [PROJECT_*] is descriptive prose (documentation about the
    template's own conventions), classified in its own registry -- same CATEGORY as [EXECUTOR] (no
    resolution enforced) for a DIFFERENT reason (not agent-emitted runtime output)."""
    text = _STEP11_TEXT if step == CustomizationStep.STEP_11 else _STEP12_TEXT
    assert "[PROJECT_*]" in text
    assert find_unclassified_bracket_spans(text, step) == []
    allowlist = STEP11_PLACEHOLDER_ALLOWLIST if step == CustomizationStep.STEP_11 else STEP12_PLACEHOLDER_ALLOWLIST
    non_placeholder = (
        STEP11_NON_PLACEHOLDER_BRACKET_TOKENS
        if step == CustomizationStep.STEP_11
        else STEP12_NON_PLACEHOLDER_BRACKET_TOKENS
    )
    assert "[PROJECT_*]" not in allowlist
    assert "[PROJECT_*]" not in non_placeholder  # wide-only; never narrow-matched, so never here


def test_phase_count_is_customizer_resolvable_for_step11_step12_not_step10() -> None:
    """The concrete flip CUSTOMIZATION_PHASE_2_SPEC.md SS1.2 names as the trap most likely to
    recur: [PHASE_COUNT] is non-placeholder (unknowable) for step10, but customizer-resolvable for
    step11/step12 -- step-scoped registries, not a single shared set, because there is no correct
    single answer."""
    assert "[PHASE_COUNT]" in NON_PLACEHOLDER_BRACKET_TOKENS  # step10
    assert "[PHASE_COUNT]" in STEP11_PLACEHOLDER_ALLOWLIST
    assert "[PHASE_COUNT]" in STEP12_PLACEHOLDER_ALLOWLIST


def test_step11_autonomous_critique_tokens_are_not_carried_to_step12() -> None:
    """SS1.2's table: step_12 has no AUTONOMOUS-CRITIQUE-style worked-example tokens -- verified
    directly, not assumed by symmetry with step11."""
    autonomous_critique_tokens = {
        "[specified]",
        "[implemented instead]",
        "[reason]",
        "[wanted to do]",
        "[why the invariant prevents it]",
    }
    assert autonomous_critique_tokens <= STEP11_NON_PLACEHOLDER_BRACKET_TOKENS
    assert autonomous_critique_tokens.isdisjoint(STEP12_NON_PLACEHOLDER_BRACKET_TOKENS)
    assert autonomous_critique_tokens.isdisjoint(STEP12_PLACEHOLDER_ALLOWLIST)


@pytest.mark.parametrize(
    ("step", "decoy"),
    [
        (CustomizationStep.STEP_11, "[EXECUTOR]"),
        (CustomizationStep.STEP_11, "[ ]"),
        (CustomizationStep.STEP_11, "[specified]"),
        (CustomizationStep.STEP_12, "[EXECUTOR]"),
        (CustomizationStep.STEP_12, "[ ]"),
    ],
)
def test_step11_step12_decoys_survive_customization(step: CustomizationStep, decoy: str) -> None:
    """[EXECUTOR_AGENT_FICTION] is deliberately excluded from this parametrize list -- it is a real,
    customizer-resolvable placeholder for step12 (STEP12_PLACEHOLDER_ALLOWLIST), not a decoy; it
    belongs in the fill-and-resolve category, not the survive-untouched one."""
    text = f"Some line with {decoy} embedded, and [PROJECT_NAME] as a real placeholder."
    found = inventory_placeholders(text, step)
    assert decoy not in found
    assert "[PROJECT_NAME]" in found


def test_executor_agent_fiction_is_customizer_resolvable_for_step12() -> None:
    assert "[EXECUTOR_AGENT_FICTION]" in STEP12_PLACEHOLDER_ALLOWLIST
    text = "Written by [EXECUTOR_AGENT_FICTION], and [PROJECT_NAME] too."
    found = inventory_placeholders(text, CustomizationStep.STEP_12)
    assert "[EXECUTOR_AGENT_FICTION]" in found


# --- Section deletion (SS3.3) ---


@pytest.mark.parametrize(
    ("step", "filename"),
    [(CustomizationStep.STEP_11, "STEP _11"), (CustomizationStep.STEP_12, "step_12")],
)
def test_expected_output_sections_drops_only_the_checklist(
    step: CustomizationStep, filename: str
) -> None:
    """SS3.3: the checklist header is the ONLY section subtracted -- every other section is still
    required (verify the delta, don't just loosen the equality)."""
    text = (REAL_TEMPLATES_DIR / filename).read_text(encoding="utf-8")
    skeleton = extract_skeleton(text, step)
    expected = expected_output_sections(skeleton.sections, step)
    assert len(expected) == len(skeleton.sections) - 1
    assert all("TEMPLATE CUSTOMIZATION CHECKLIST" not in s for s in expected)
    # Everything else survives, in the same order.
    assert expected == [s for s in skeleton.sections if "TEMPLATE CUSTOMIZATION CHECKLIST" not in s]


def test_expected_output_sections_is_a_noop_for_step10() -> None:
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    skeleton = extract_skeleton(text, CustomizationStep.STEP_10)
    assert expected_output_sections(skeleton.sections, CustomizationStep.STEP_10) == skeleton.sections


def test_step11_step12_section_deletion_markers_are_substrings_not_full_lines() -> None:
    """Verified directly: the two templates' checklist headers differ in wording (STEP_11 adds "for
    the project web chat -- ") without changing what section it is -- the registry marker must be a
    SUBSTRING match, not the full exact line, or one of the two templates would never match."""
    assert STEP11_SECTION_DELETIONS == ("TEMPLATE CUSTOMIZATION CHECKLIST",)
    assert STEP12_SECTION_DELETIONS == ("TEMPLATE CUSTOMIZATION CHECKLIST",)
    step11_header = "## TEMPLATE CUSTOMIZATION CHECKLIST (for the project web chat -- remove before pasting to Claude Code)"
    step12_header = "## TEMPLATE CUSTOMIZATION CHECKLIST (remove before pasting to Claude Code)"
    assert step11_header != step12_header
    assert all(marker in step11_header for marker in STEP11_SECTION_DELETIONS)
    assert all(marker in step12_header for marker in STEP12_SECTION_DELETIONS)


# --- Conditional include-or-replace blocks (SS3.4) ---


def test_step11_conditional_block_is_the_ingestion_marker() -> None:
    blocks = find_conditional_blocks(_STEP11_TEXT, CustomizationStep.STEP_11)
    assert len(blocks) == 2  # the full instructional block + the bare form inside the checklist
    assert any(b.startswith("<<CITATION_GATE_INGESTION_BLOCK: include only if") for b in blocks)
    assert "<<CITATION_GATE_INGESTION_BLOCK>>" in blocks


def test_step12_conditional_block_is_the_citation_gate_marker() -> None:
    """Regression: the full instructional block contains literal `>` characters as "->" arrow
    notation (e.g. "PASS -> add a SS0.5..."), which a naive `[^<>]`-excluding wide-angle regex cannot
    cross -- it would silently find only the bare form inside the checklist and miss the real block
    entirely (confirmed as a real, not hypothetical, bug: templates.py's _WIDE_ANGLE_SPAN_RE)."""
    blocks = find_conditional_blocks(_STEP12_TEXT, CustomizationStep.STEP_12)
    assert len(blocks) == 2  # the full instructional block + the bare form inside the checklist
    assert any(b.startswith("<<CITATION_GATE_BLOCK: include only if") for b in blocks)
    assert "<<CITATION_GATE_BLOCK>>" in blocks


def test_step10_has_no_conditional_blocks() -> None:
    text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    assert find_conditional_blocks(text, CustomizationStep.STEP_10) == []


def test_unresolved_conditional_blocks_against_real_precedent_files() -> None:
    """Validates the sentinel mechanism against REAL, human-produced customizations (not synthetic):
    prompts/loopr/step11_build.md and step12_review.md both resolve their citation-gate block, and
    neither uses the template's byte-exact fallback text -- confirming layer 1 must only verify the
    raw marker is gone, never mandate specific replacement wording (see the registry's own comment
    in templates.py for why: the two templates aren't even symmetric with each other here)."""
    real_step11_dir = REAL_TEMPLATES_DIR.parents[1] / "prompts" / "loopr"
    step11_output = (real_step11_dir / "step11_build.md").read_text(encoding="utf-8")
    step12_output = (real_step11_dir / "step12_review.md").read_text(encoding="utf-8")

    assert unresolved_conditional_blocks(_STEP11_TEXT, step11_output, CustomizationStep.STEP_11) == []
    assert unresolved_conditional_blocks(_STEP12_TEXT, step12_output, CustomizationStep.STEP_12) == []


def test_unresolved_conditional_blocks_detects_untouched_template() -> None:
    """An output identical to the template never resolved anything -- both occurrences of each
    step's marker prefix (the full instructional block and the bare checklist form) survive
    untouched."""
    unresolved11 = unresolved_conditional_blocks(_STEP11_TEXT, _STEP11_TEXT, CustomizationStep.STEP_11)
    assert len(unresolved11) == 2
    unresolved12 = unresolved_conditional_blocks(_STEP12_TEXT, _STEP12_TEXT, CustomizationStep.STEP_12)
    assert len(unresolved12) == 2


def test_conditional_block_markers_are_not_symmetric_across_templates() -> None:
    """Guards against silently assuming step11 and step12 behave the same way here -- they don't
    (verified against the raw files: step_12's block states an exact replacement line, STEP_11's
    says only to remove the block, with none specified)."""
    assert "replace with:" in _STEP12_TEXT
    step11_block = [
        b for b in find_conditional_blocks(_STEP11_TEXT, CustomizationStep.STEP_11) if len(b) > 100
    ][0]
    assert "replace with:" not in step11_block
    assert "remove this block" in step11_block.lower()


# --- Angle-bracket independent-oracle completeness (informal, SS3.2's discipline extended) ---


@pytest.mark.parametrize(
    ("step", "text"),
    [(CustomizationStep.STEP_11, _STEP11_TEXT), (CustomizationStep.STEP_12, _STEP12_TEXT)],
)
def test_angle_bracket_wide_scan_is_fully_accounted_for(step: CustomizationStep, text: str) -> None:
    """Every `<<...>>` span in both real templates is either a `<<CUSTOMIZE:...>>` marker (handled
    by surviving_customize_markers), a recognized conditional block (handled by
    find_conditional_blocks), or lives entirely inside the deleted TEMPLATE CUSTOMIZATION CHECKLIST
    section (handled by expected_output_sections) -- verified exhaustively, not assumed, per this
    phase's own "run the independent-oracle wide scan... as an early step, not an afterthought"."""
    import re

    # Lazy-to-first->>, not a `[^<>]` exclusion -- matches the corrected _WIDE_ANGLE_SPAN_RE (a
    # `[^<>]`-style exclusion here would repeat the exact regression templates.py's own comment
    # documents: step_12's real CITATION_GATE_BLOCK contains literal `>` from "->" arrow notation,
    # which such an exclusion cannot cross, silently making this "completeness" check blind to the
    # one span most worth catching.
    all_angle_spans = set(re.findall(r"<<.{1,8000}?>>", text, re.DOTALL))
    customize_markers = set(surviving_customize_markers(text))
    conditional_blocks = set(find_conditional_blocks(text, step))

    skeleton = extract_skeleton(text, step)
    checklist_headers = [s for s in skeleton.sections if "TEMPLATE CUSTOMIZATION CHECKLIST" not in s]
    checklist_start = text.index(
        next(s for s in skeleton.sections if "TEMPLATE CUSTOMIZATION CHECKLIST" in s)
    )

    unaccounted = []
    for span in all_angle_spans:
        if span in customize_markers or span in conditional_blocks:
            continue
        if text.index(span) >= checklist_start:
            continue  # lives inside the deleted checklist section
        unaccounted.append(span)
    assert unaccounted == [], f"unaccounted-for <<...>> span(s) in {step.value}: {unaccounted}"
    assert checklist_headers  # sanity: the fixture logic above actually found real sections


# --- SS1.1 gating condition: find_step10_execution_artifacts ---


def test_find_step10_execution_artifacts_none_when_phase_1_spec_missing(tmp_path: Path) -> None:
    (tmp_path / "SOME_PRD.md").write_text("## MODERNIZATION CHANGELOG\n", encoding="utf-8")
    assert find_step10_execution_artifacts(tmp_path) is None


def test_find_step10_execution_artifacts_none_when_no_prd_has_changelog(tmp_path: Path) -> None:
    (tmp_path / "PHASE_1_SPEC.md").write_text("Phase 1 of 1.\n", encoding="utf-8")
    (tmp_path / "SOME_PRD.md").write_text("just a PRD, no changelog section\n", encoding="utf-8")
    assert find_step10_execution_artifacts(tmp_path) is None


def test_find_step10_execution_artifacts_found_by_content_not_default_filename(tmp_path: Path) -> None:
    """STEP_10's own default PRD filename is "ULTIMATE_PRD.md", but real usage overrides it
    (verified: this project's own real customization uses "loopr-PRD.md") -- detection must be
    content-based, not a filename guess. Uses a NON-default name deliberately."""
    (tmp_path / "PHASE_1_SPEC.md").write_text("**Phase 1 of 1.**\n", encoding="utf-8")
    (tmp_path / "totally-custom-prd-name.md").write_text(
        "some intro\n## MODERNIZATION CHANGELOG\n- change 1\n", encoding="utf-8"
    )
    result = find_step10_execution_artifacts(tmp_path)
    assert result is not None
    prd_path, phase_1_spec_path = result
    assert prd_path.name == "totally-custom-prd-name.md"
    assert phase_1_spec_path.name == "PHASE_1_SPEC.md"


def test_find_step10_execution_artifacts_against_this_repos_own_real_state() -> None:
    """Demonstrated against THIS project's own real, already-executed step10 output -- not a
    synthetic fixture standing in for one (CUSTOMIZATION_PHASE_2_SPEC.md SS5.2's discipline, applied
    here too)."""
    repo_root = Path(__file__).resolve().parents[1]
    result = find_step10_execution_artifacts(repo_root)
    assert result is not None
    prd_path, phase_1_spec_path = result
    assert prd_path.name == "loopr-PRD.md"  # NOT the default "ULTIMATE_PRD.md"
    assert phase_1_spec_path.name == "PHASE_1_SPEC.md"
