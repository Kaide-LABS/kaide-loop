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
_ALL_CAPS_HEADER_RE = re.compile(r"^[A-Z0-9][A-Z0-9 &/\-(),']*[A-Z0-9)]$")
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


def _is_all_caps_section(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _NUMBERED_HEADER_RE.match(stripped):
        return True
    if stripped.endswith(":"):
        return False
    return bool(_ALL_CAPS_HEADER_RE.match(stripped))


def extract_skeleton(text: str, step: CustomizationStep) -> TemplateSkeleton:
    """Extracts the ordered section-header list under whichever convention applies to this step,
    declared explicitly per template (SS4.3) -- never one generic regex. STEP_10 has zero markdown
    headers at all (a markdown-header extractor finds literally nothing in it); STEP_11 uses `##`;
    STEP_12 uses `##` and `###`. Raises VacuousSkeletonError if the result is implausibly short."""
    lines = text.splitlines()

    if step == CustomizationStep.STEP_10:
        convention = "all_caps"
        sections = [line.strip() for line in lines if _is_all_caps_section(line)]
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


# Allowlist of true placeholder tokens per step -- bracket-shaped tokens NOT on this list are left
# verbatim and reported, never guessed at (SS4.2: "an explicit allowlist, never a regex sweep").
# [UNVERIFIED] and [EXECUTOR] deliberately do NOT appear here: the first is a tag the executing
# model is instructed to emit in its own output, the second is reject-pattern shorthand -- both
# match the bracket shape but are not placeholders, and a naive fill-every-bracket implementation
# would corrupt both.
STEP10_PLACEHOLDER_ALLOWLIST: frozenset[str] = frozenset(
    {
        "[PROJECT_NAME]",
        "[PROJECT_REPO_NAME]",
        "[PRD_FILENAME]",
        "[PHASE_COUNT]",
        "[RESEARCH FOCUS]",
    }
)

NON_PLACEHOLDER_BRACKET_TOKENS: frozenset[str] = frozenset({"[UNVERIFIED]", "[EXECUTOR]"})

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
