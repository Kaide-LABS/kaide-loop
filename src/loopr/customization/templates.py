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


# Allowlist of true placeholder tokens per step -- bracket-shaped tokens NOT on this list are left
# verbatim and reported, never guessed at (SS4.2: "an explicit allowlist, never a regex sweep").
# [UNVERIFIED], [EXECUTOR], and [RESEARCH FOCUS] deliberately do NOT appear here -- see
# NON_PLACEHOLDER_BRACKET_TOKENS below for why each is excluded.
STEP10_PLACEHOLDER_ALLOWLIST: frozenset[str] = frozenset(
    {
        "[PROJECT_NAME]",
        "[PROJECT_REPO_NAME]",
        "[PRD_FILENAME]",
        "[PHASE_COUNT]",
    }
)

# [UNVERIFIED]: a tag the executing model is instructed to emit in its own output.
# [EXECUTOR]: reject-pattern shorthand ("[EXECUTOR] may have written X -- reject").
# [RESEARCH FOCUS]: a THIRD instance of the same trap, confirmed against real usage rather than
# assumed -- it reads as a placeholder but is not one. The template (STEP_10 SS1, lines 84-86) binds
# it to a value the STEP10-EXECUTING agent derives from ITS OWN repo scan at execution time ("From
# this scan, extract the project's CORE METHODS ... you will feed these into the literature arm of
# SS2 as the [RESEARCH FOCUS]"; SS2 itself calls it back as "the core methods extracted in SS1") --
# not a value the customizer can legitimately supply ahead of time. The project's own real precedent
# (prompts/loopr/step10_prd_modernization.md line 88, a human-produced customization) leaves the
# token in place verbatim and adds elaboration AFTER it, rather than replacing it -- confirming this
# reading. Previously misclassified as allowlisted (b020ade); every real customization following
# established practice would have failed structural fidelity for correctly leaving it untouched, or
# been forced to fabricate a guessed research focus to pass -- exactly the corruption this allowlist
# exists to prevent. All three match the bracket shape but are not placeholders, and a naive
# fill-every-bracket implementation would corrupt all three.
NON_PLACEHOLDER_BRACKET_TOKENS: frozenset[str] = frozenset(
    {"[UNVERIFIED]", "[EXECUTOR]", "[RESEARCH FOCUS]"}
)

_BRACKET_TOKEN_RE = re.compile(r"\[[A-Za-z0-9 _]+\]")


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
