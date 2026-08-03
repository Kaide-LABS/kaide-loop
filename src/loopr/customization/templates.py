"""Template discovery, skeleton extraction, and placeholder inventory.

Implements CUSTOMIZATION_PHASE_1_SPEC.md SS4.2, SS4.3. Plain-text line scanning only -- no
templating engine, no parser library (SS3); a new dependency here would breach the
single-runtime-dependency invariant `tests/test_no_paid_dependency.py` enforces.
"""

from __future__ import annotations

import re
from pathlib import Path

from loopr.errors import LooprError
from loopr.models.common import CustomizationStep
from loopr.models.customization import TemplateSkeleton

TEMPLATES_DIR_NAME = "prompts/Template_prompts"

# File discovery is name-normalized, never a glob -- the files on disk are inconsistently named
# (STEP_10, "STEP _11" with an embedded space, step_12), the second trap SS4.2 names explicitly.
# Matched by normalized (whitespace/underscore-stripped, uppercased) step identifier, not literal
# name, so a tidy glob pattern can never silently miss "STEP _11".
_STEP_ALIASES: dict[CustomizationStep, str] = {
    CustomizationStep.STEP_10: "STEP10",
    CustomizationStep.STEP_11: "STEP11",
    CustomizationStep.STEP_12: "STEP12",
}


class TemplateDiscoveryError(LooprError):
    """Raised when a step's template file cannot be found, or more than one candidate matches."""


class VacuousSkeletonError(LooprError):
    """Raised when skeleton extraction yields an implausibly short (or empty) result.

    Guard against the vacuous pass, CUSTOMIZATION_PHASE_1_SPEC.md SS4.3: comparing two empty
    section lists "succeeds" while verifying nothing. This fires at extraction time -- both when
    the ORIGINAL template is snapshotted (a convention mismatch would be caught immediately, before
    any customization is even attempted) and when the customized output is later extracted for
    comparison -- so a fidelity check can never silently report green having checked nothing.
    """


_MIN_PLAUSIBLE_SECTIONS = 2

_NUMBERED_HEADER_RE = re.compile(r"^\d+\.\s+[A-Z]{2,}\b")
_TRAILING_PAREN_RE = re.compile(r"^(.*?)\s*(\([^)]*\))$")
_ALL_CAPS_CORE_RE = re.compile(r"^[A-Z0-9][A-Z0-9 &/,'-]*[A-Z0-9]$")
_MARKDOWN_H2_RE = re.compile(r"^##\s+\S")
_MARKDOWN_H2_H3_RE = re.compile(r"^#{2,3}\s+\S")


def _normalize(name: str) -> str:
    return re.sub(r"[\s_]+", "", name).upper()


def discover_template(repo_root: Path, step: CustomizationStep) -> Path:
    """Finds the on-disk template file for a step, regardless of its actual casing/spacing/
    extension. An exact normalized-name match, never a glob -- a similarly-named stray file is
    never silently picked up, and ambiguity is reported rather than guessed at."""
    templates_dir = repo_root / TEMPLATES_DIR_NAME
    if not templates_dir.is_dir():
        raise TemplateDiscoveryError(f"no {TEMPLATES_DIR_NAME}/ directory under {repo_root}")

    wanted = _STEP_ALIASES[step]
    matches = [
        path
        for path in templates_dir.iterdir()
        if path.is_file() and _normalize(path.name).startswith(wanted)
    ]
    if len(matches) == 0:
        raise TemplateDiscoveryError(f"no template file found for {step.value} under {templates_dir}")
    if len(matches) > 1:
        names = sorted(m.name for m in matches)
        raise TemplateDiscoveryError(f"multiple candidate files found for {step.value}: {names}")
    return matches[0]


def _all_caps_core(stripped: str) -> str:
    """Strips one trailing parenthetical, if present, and returns what remains. A genuine STEP_10
    section header may carry a lowercase-content parenthetical qualifier (e.g. "WHY THIS MUST BE
    AIRTIGHT (loop context)") -- the earlier implementation required the ENTIRE line to be
    uppercase, which silently dropped that section (CUSTOMIZATION_PHASE_1_SPEC.md SS4.3, corrected
    2026-08-01). Only the part OUTSIDE the parenthetical must be all-caps; the qualifier itself may
    be anything.

    This permissiveness is a DECIDED tradeoff (CUSTOMIZATION_PHASE_1_SPEC.md SS4.3, decided
    2026-08-02), not an oversight: it can false-positive on customizer-drafted output (e.g. a filled
    HARD BOUNDARY line), causing a spurious structural HALT. Do not tighten this to chase that case --
    it risks reintroducing THIS defect (a missed real section = a silent false PASS), which is
    strictly worse than an occasional false HALT a human can retry. See the spec for the full
    reasoning before changing this regex."""
    match = _TRAILING_PAREN_RE.match(stripped)
    return match.group(1).strip() if match else stripped


def _is_all_caps_section(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _NUMBERED_HEADER_RE.match(stripped):
        return True
    if stripped.endswith(":"):
        return False
    core = _all_caps_core(stripped)
    if not core:
        return False
    return bool(_ALL_CAPS_CORE_RE.match(core))


def extract_skeleton(text: str, step: CustomizationStep) -> TemplateSkeleton:
    """Extracts the ordered section-header list under whichever convention applies to this step,
    declared explicitly per template (SS4.3) -- never one generic regex. STEP_10 has zero markdown
    headers at all (a markdown-header extractor finds literally nothing in it); STEP_11 uses `##`;
    STEP_12 uses `##` and `###`. Raises VacuousSkeletonError if the result is implausibly short.

    Doc-title handling is a DECLARED decision (SS4.3), not incidental regex behavior: the document
    title is excluded from the skeleton in all three conventions. For STEP_11/STEP_12 this falls out
    of the convention itself (the title is a markdown H1, `#`, and only `##`/`###` are matched --
    nothing special needed). STEP_10 has no markdown at all, so its title line is plain text in the
    same visual register as a real section -- it is excluded explicitly, by always skipping line 1,
    regardless of whether it happens to match the section pattern.
    """
    lines = text.splitlines()

    if step == CustomizationStep.STEP_10:
        convention = "all_caps"
        sections = [
            line.strip() for index, line in enumerate(lines) if index > 0 and _is_all_caps_section(line)
        ]
    elif step == CustomizationStep.STEP_11:
        convention = "markdown_h2"
        sections = [line.strip() for line in lines if _MARKDOWN_H2_RE.match(line.strip())]
    else:
        convention = "markdown_h2_h3"
        sections = [line.strip() for line in lines if _MARKDOWN_H2_H3_RE.match(line.strip())]

    if len(sections) < _MIN_PLAUSIBLE_SECTIONS:
        raise VacuousSkeletonError(
            f"extraction under convention {convention!r} for {step.value} yielded only "
            f"{len(sections)} section(s) -- implausibly short; refusing to treat this as a "
            "verified skeleton rather than silently comparing near-empty lists"
        )

    return TemplateSkeleton(convention=convention, sections=sections)


def _looks_heading_shaped(line: str) -> bool:
    """A GENERIC, convention-independent heuristic -- deliberately not sharing any code or regex
    with `_is_all_caps_section`/the markdown patterns above, per SS4.3's requirement that the gap
    checker "does not inherit the blind spot of whichever regex it is checking." Unindented, short,
    not sentence-ending punctuation, and majority-uppercase (allowing a lowercase parenthetical
    qualifier, unlike ordinary prose which is majority lowercase)."""
    stripped = line.strip()
    if not stripped or stripped != line:
        return False
    if len(stripped) > 100:
        return False
    if stripped[-1] in ".,;":
        return False
    letters = [c for c in stripped if c.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(c.isupper() for c in letters) / len(letters)
    return upper_ratio >= 0.6


def find_gap_candidates(text: str, detected_sections: list[str]) -> list[str]:
    """Structural cross-check, required by SS4.3: scans every line NOT already claimed by
    `detected_sections` for something that structurally looks like a missed header -- isolated by
    blank lines on both sides, and heading-shaped per `_looks_heading_shaped`. A minimum-count floor
    (VacuousSkeletonError) only catches TOTAL extraction failure; this catches PARTIAL failure, the
    exact case that let 8-of-9 sections in STEP_10 pass unnoticed. Line 1 (the document title) is
    excluded here too, consistent with the same declared title-exclusion decision `extract_skeleton`
    applies -- otherwise the title would be reported as a permanent, meaningless false positive on
    every scan. Returns every suspected-missed candidate; the caller decides how to act on it."""
    lines = text.splitlines()

    located: set[int] = set()
    search_start = 0
    for section in detected_sections:
        for index in range(search_start, len(lines)):
            if lines[index].strip() == section:
                located.add(index)
                search_start = index + 1
                break

    candidates = []
    for index, line in enumerate(lines):
        if index == 0 or index in located:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        prev_blank = index == 0 or lines[index - 1].strip() == ""
        next_blank = index == len(lines) - 1 or lines[index + 1].strip() == ""
        if prev_blank and next_blank and _looks_heading_shaped(line):
            candidates.append(stripped)
    return candidates


# CLASSIFICATION RULE for these two sets (state this explicitly -- do not make the next person
# re-derive it from the instances): for a given STEP, is a bracket token's value knowable AT THE
# MOMENT THAT STEP's template is customized, or is it derived by the agent EXECUTING that customized
# prompt (from its own future repo scan, its own future output, or emitted as its own in-output tag)?
# Customizer-knowable now -> STEP<N>_PLACEHOLDER_ALLOWLIST. Runtime-derived or agent-emitted ->
# NON_PLACEHOLDER_BRACKET_TOKENS. A token's classification is PER-STEP, not global: the same literal
# token can be customizer-knowable in one step's template and runtime-derived in another's, because
# "when it becomes knowable" depends on what that step's own execution produces (SS5's two-pass
# finding). [PHASE_COUNT] is the concrete case -- see its entry below. Two bracket-shape tokens that
# LOOK like placeholders but never belong on any allowlist, in any step, live in
# NON_PLACEHOLDER_BRACKET_TOKENS regardless: [UNVERIFIED] (a tag the executing model emits in its own
# output) and [EXECUTOR] (reject-pattern shorthand, "[EXECUTOR] may have written X -- reject").
#
# Bracket-shaped tokens NOT on the relevant allowlist are left verbatim and reported, never guessed
# at (SS4.2: "an explicit allowlist, never a regex sweep").

# STEP_10: every distinct bracket-shaped token actually present in the real file, verified directly
# against it (test_step10_bracket_token_classification_is_complete), not assumed from any table.
STEP10_PLACEHOLDER_ALLOWLIST: frozenset[str] = frozenset(
    {
        "[PROJECT_NAME]",
        "[PROJECT_REPO_NAME]",
        "[PRD_FILENAME]",
    }
)

# [UNVERIFIED]: see the shared rule above.
#
# [RESEARCH FOCUS] (STEP_10 only): the template (SS1, lines 84-86) binds it to a value the
# STEP10-EXECUTING agent derives from ITS OWN repo scan at execution time ("From this scan, extract
# the project's CORE METHODS ... you will feed these into the literature arm of SS2 as the [RESEARCH
# FOCUS]"; SS2 itself calls it back as "the core methods extracted in SS1") -- not a value the
# customizer can legitimately supply ahead of time. Real precedent
# (prompts/loopr/step10_prd_modernization.md line 88, a human-produced customization) leaves the
# token in place verbatim and adds elaboration AFTER it, rather than replacing it. Previously
# misclassified as allowlisted (b020ade).
#
# [PHASE_COUNT] (STEP_10 only -- STEP-DEPENDENT, do not generalize this exclusion to step11/step12):
# appears once, STEP_10 SS5 line 282, inside SS0's phase-plan-header instruction to the
# STEP10-EXECUTING agent for what it writes INTO PHASE_1_SPEC.md ("Phase 1 of [PHASE_COUNT]") -- the
# phase count is a product of that agent's own Phase 1 breakdown, unknowable before step10 runs.
# Real precedent (prompts/loopr/step10_prd_modernization.md line 261) states this explicitly:
# "PHASE_COUNT is not yet known; determine and state it here based on how you actually break down
# the build, do not guess a number in advance." Previously misclassified as allowlisted (b020ade),
# same defect class as [RESEARCH FOCUS]. THIS FLIPS FOR STEP_11/STEP_12 (SS5's two-pass finding, Phase
# 2 work): by the time those templates are customized, step10 has already executed and
# PHASE_1_SPEC.md SS0 states the real count, so [PHASE_COUNT] becomes genuinely customizer-knowable
# there and belongs on THEIR allowlist, not in a step11/12 non-placeholder set. When Phase 2 builds
# STEP11_PLACEHOLDER_ALLOWLIST / STEP12_PLACEHOLDER_ALLOWLIST, re-derive [PHASE_COUNT]'s
# classification for each from the rule above -- do not copy this exclusion forward by reflex.
#
# All of these match the bracket shape but are not customizer-resolvable placeholders for THIS step,
# and a naive fill-every-bracket implementation would corrupt all of them.
NON_PLACEHOLDER_BRACKET_TOKENS: frozenset[str] = frozenset(
    {"[UNVERIFIED]", "[EXECUTOR]", "[RESEARCH FOCUS]", "[PHASE_COUNT]"}
)

_BRACKET_TOKEN_RE = re.compile(r"\[[A-Za-z0-9 _]+\]")

# INDEPENDENT-ORACLE RULE (CUSTOMIZATION_PHASE_1_SPEC.md SS4.3, decided 2026-08-03): any
# completeness check must use a mechanism INDEPENDENT of the one it verifies, never check a regex's
# output against itself -- a self-referential check (asserting "every token _BRACKET_TOKEN_RE finds
# is classified", using the very regex that defines what counts as a token) certifies itself and is
# structurally blind to anything that regex's own character class cannot see. This is the same
# lesson as `find_gap_candidates` above (built deliberately not sharing code with the section-header
# regexes it cross-checks), applied to the token side rather than the section side.
#
# Confirmed concretely: _BRACKET_TOKEN_RE (`[A-Za-z0-9 _]` only, no DOTALL) cannot match STEP_10's
# `[PROJECT HARD BOUNDARY -- fill per project: ...]` block (SS3) -- a 303-character, 5-line,
# punctuation- and newline-bearing bracket construct. It was invisible to the token inventory
# entirely: not in the allowlist, not in the non-placeholder set, not reported as unclassified,
# because the completeness check that would have caught it was checking the narrow regex's output
# against itself. Layer 1 would pass a customization that left this -- the single highest-stakes
# field STEP_10 defines ("Specify ... exactly what code would VIOLATE this boundary, so the review
# agent can grep for it and HALT") -- completely unfilled, the template's own generic per-project-kind
# examples and all, left untouched. Previously undetected (b020ade through 1ccc8dd).
#
# _WIDE_BRACKET_SPAN_RE is the independent oracle: any non-nested `[...]` span, DOTALL (so it spans
# lines), tolerant of any character except `[`/`]` themselves, bounded only to guard against a
# runaway match. The narrow `_BRACKET_TOKEN_RE`-based classification is checked AGAINST this oracle's
# output, never the reverse.
_WIDE_BRACKET_SPAN_RE = re.compile(r"\[[^\[\]]{1,2000}\]", re.DOTALL)

# Multi-line, punctuation-bearing fill-in instruction blocks ARE customizer-resolvable (STEP_10 SS3
# says so of the hard boundary explicitly: "fill per project") -- but their exact wording lives in
# the template file, not a fixed short string, so they cannot be enumerated as frozenset members the
# way [PROJECT_NAME] is. They are identified instead by a stable marker prefix, an explicit, auditable
# registry exactly like the two token sets above -- NOT by "anything the wide oracle finds beyond a
# short token is automatically a fill-in block", which would silently treat a genuinely new,
# unclassified bracket construct as just another block to text-match, defeating the point of a
# completeness check. Add to this registry only after reviewing the construct, same discipline as the
# two token sets.
STEP10_FILL_IN_BLOCK_MARKERS: tuple[str, ...] = ("[PROJECT HARD BOUNDARY",)


def find_fill_in_blocks(text: str, step: CustomizationStep) -> list[str]:
    """Returns the recognized multi-line fill-in blocks (STEP10_FILL_IN_BLOCK_MARKERS) actually
    present in `text`, found via the wide-scan oracle since _BRACKET_TOKEN_RE cannot see them."""
    if step != CustomizationStep.STEP_10:
        raise NotImplementedError(
            f"fill-in block inventory for {step.value} is Phase 2 work -- only step 10 is in scope"
        )
    spans = set(_WIDE_BRACKET_SPAN_RE.findall(text))
    return sorted(span for span in spans if span.startswith(STEP10_FILL_IN_BLOCK_MARKERS))


def unresolved_fill_in_blocks(template_text: str, output_text: str, step: CustomizationStep) -> list[str]:
    """Fill-in blocks found in the TEMPLATE via `find_fill_in_blocks` are not short tokens --
    "resolved" cannot mean "token absent" the way `unresolved_placeholders` checks it, because a
    genuine resolution replaces the block with several sentences of project-specific prose, not a
    short value that either is or isn't present. The template's own original block text is the
    sentinel instead: a block still present byte-identical in the output was never touched by the
    customizer, filled or otherwise. Returns every such surviving block, found in the template and
    still verbatim in the output."""
    blocks = find_fill_in_blocks(template_text, step)
    return [block for block in blocks if block in output_text]


def find_unclassified_bracket_spans(text: str, step: CustomizationStep) -> list[str]:
    """The independent-oracle completeness check itself. Scans `text` with the WIDE, permissive
    regex and returns every span that is NEITHER one of this step's classified short tokens
    (STEP10_PLACEHOLDER_ALLOWLIST | NON_PLACEHOLDER_BRACKET_TOKENS) NOR a recognized fill-in block
    (STEP10_FILL_IN_BLOCK_MARKERS) -- i.e. genuinely unaccounted for by any classification mechanism
    this module has. For the real STEP_10 file this returns an empty list: the hard-boundary block is
    accounted for via the marker registry, and every short token is classified. Anything this DOES
    return needs a human to classify it (add to the appropriate registry above), never silently
    absorbed as "probably fine" either way -- that silent-absorption is exactly how the hard-boundary
    block went undetected for four commits (b020ade through 1ccc8dd)."""
    if step != CustomizationStep.STEP_10:
        raise NotImplementedError(
            f"bracket-span completeness check for {step.value} is Phase 2 work -- only step 10 is "
            "in scope"
        )
    classified_short = STEP10_PLACEHOLDER_ALLOWLIST | NON_PLACEHOLDER_BRACKET_TOKENS
    spans = set(_WIDE_BRACKET_SPAN_RE.findall(text))
    return sorted(
        span
        for span in spans
        if span not in classified_short and not span.startswith(STEP10_FILL_IN_BLOCK_MARKERS)
    )


def inventory_placeholders(text: str, step: CustomizationStep) -> list[str]:
    """Returns the allowlisted placeholder tokens actually present in `text`, for this step. Tokens
    matching the bracket shape but not on the allowlist (including [UNVERIFIED] and [EXECUTOR]) are
    never returned here -- they are not placeholders and must never be treated as one."""
    if step != CustomizationStep.STEP_10:
        raise NotImplementedError(
            f"placeholder inventory for {step.value} is Phase 2 work -- only step 10 is in scope"
        )
    found = set(_BRACKET_TOKEN_RE.findall(text))
    return sorted(found & STEP10_PLACEHOLDER_ALLOWLIST)


def unresolved_placeholders(text: str, step: CustomizationStep) -> list[str]:
    """The allowlisted tokens from `inventory_placeholders` that are STILL present in `text` --
    i.e. never got filled. Same function works for the template (everything is "unresolved" there)
    and the customized output (should be empty there)."""
    return inventory_placeholders(text, step)


def surviving_customize_markers(text: str) -> list[str]:
    """`<<CUSTOMIZE: ...>>` markers are instructions TO the customizer; they must never reach the
    executing agent. Returns every such marker still present in `text`."""
    return re.findall(r"<<CUSTOMIZE[^>]*>>", text)
