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


_MODERNIZATION_CHANGELOG_HEADING = "## MODERNIZATION CHANGELOG"

# STEP_10's own template text (SS5, "§0 Phase Plan Header") names this section literally, with an
# optional "##" markdown prefix and a "§0" / "SS0" section marker depending on how the executing
# agent (or this environment's own § transcription -- verified inconsistent even within this
# project's own real files and test fixtures: "§0" in CUSTOMIZATION_PHASE_3_SPEC.md, "SS0" is this
# project's own established ASCII stand-in elsewhere) renders it. Matched as a heading-shaped LINE
# (stripped, own-line, allowing that prefix), not a substring search anywhere in the file -- same
# discipline as _has_modernization_changelog_heading below, for the same reason: a prose sentence
# that happens to mention "Phase Plan Header" must never count.
_PHASE_PLAN_HEADER_LINE_RE = re.compile(
    r"^[#\s]*(?:§|SS)?\s*\d*\.?\s*Phase Plan Header\b", re.IGNORECASE
)


class Step10ArtifactAmbiguityError(LooprError):
    """Raised by find_step10_execution_artifacts when a modernised PRD is confirmed present (so
    step10 has clearly executed) but which *.md file is its Phase-N-spec companion cannot be
    uniquely determined from real, on-disk evidence -- zero or multiple candidates carry BOTH the
    required structural marker (a "Phase Plan Header" heading line) AND provenance naming the
    detected PRD's own filename. A genuine ambiguity for a human to resolve, never a silent guess
    (e.g. "most recently modified") -- that failure mode is exactly what this function replaced."""


def _has_modernization_changelog_heading(text: str) -> bool:
    """True only if "## MODERNIZATION CHANGELOG" appears as its OWN LINE (after stripping
    whitespace) -- not merely as a substring anywhere in the file. A raw `in` check previously let a
    file that only *mentions* the heading in prose (e.g. documenting this very detection mechanism,
    or quoting it inside a blockquote) satisfy this by accident; confirmed live against this repo's
    own CUSTOMIZATION_PHASE_3_SPEC.md, which does exactly that."""
    return any(line.strip() == _MODERNIZATION_CHANGELOG_HEADING for line in text.splitlines())


def _has_phase_plan_header_line(text: str) -> bool:
    """The structural half of Phase-N-spec detection (FIX 2a): a real "Phase Plan Header" heading
    line, not a loose substring match anywhere in the file -- same own-line discipline as
    _has_modernization_changelog_heading above."""
    return any(_PHASE_PLAN_HEADER_LINE_RE.match(line.strip()) for line in text.splitlines())


def _names_prd_as_provenance(text: str, prd_filename: str) -> bool:
    """The provenance half of Phase-N-spec detection (FIX 2b): the candidate must explicitly claim to
    be BUILT FROM the detected PRD, not merely mention its filename somewhere incidentally (a real
    file -- SKILL_PHASE_1_SPEC.md in this project's own repo -- names an unrelated PRD as its actual
    provenance claim and only mentions the real modernised PRD's filename much later, in an unrelated
    cross-reference; a bare substring check would have wrongly counted it). Requires the word "built"
    within a short distance before the filename, tolerant of markdown emphasis/backticks and the
    "from" that STEP_10's template instructs the agent to write in between."""
    pattern = re.compile(r"built\b.{0,120}?" + re.escape(prd_filename), re.IGNORECASE | re.DOTALL)
    return bool(pattern.search(text))


def find_step10_execution_artifacts(repo_root: Path) -> tuple[Path, Path] | None:
    """The SS1.1 gating condition, checked directly against real files: `loopr customize --step 11`
    and `--step 12` must refuse to run unless step10 has actually EXECUTED in the target project, not
    merely been customized (a fidelity-passing step10 PROMPT is not the same as step10 having been
    RUN against the project). Returns (modernised_prd_path, phase_1_spec_path) if both of step10's
    real deliverables exist, None if neither does (step10 genuinely has not executed) -- never
    inferred from CustomizationState.step10_fidelity, which only proves the prompt was well-formed.
    Raises Step10ArtifactAmbiguityError if the PRD is found but its Phase-N-spec companion is not
    uniquely determinable -- a real ambiguity, not something to guess past.

    The modernised PRD (Deliverable A) is NOT a fixed filename -- STEP_10's own default is
    "ULTIMATE_PRD.md", but that default is commonly overridden (verified: this project's own real
    customization uses "loopr-PRD.md" instead). Detected by CONTENT instead: STEP_10's own template
    mandates every modernised PRD carry a "## MODERNIZATION CHANGELOG" section -- the first *.md file
    at repo_root carrying that heading AS ITS OWN LINE (_has_modernization_changelog_heading, not a
    raw substring check) is treated as the modernised PRD.

    The Phase-N-spec (Deliverable B) is likewise NOT a fixed filename in practice: this project's own
    dogfooding run proves it -- STEP_10's literal default, "PHASE_1_SPEC.md", was already occupied by
    an unrelated file from loopr's own earlier core-module build, so the real Phase 3 deliverable was
    correctly written to CUSTOMIZATION_PHASE_3_SPEC.md instead rather than clobbering it. A fixed
    filename lookup here (the original implementation) silently paired the modernised PRD with that
    stale, unrelated file -- no error, no HALT, just a wrong answer. Detected instead by TWO
    independent signals combined, neither alone (a single weak signal is exactly what misfired
    before, whether that signal is a fixed filename or a loose substring check):
      (a) structural -- a real "Phase Plan Header" heading line (_has_phase_plan_header_line), the
          section STEP_10's own template mandates every Phase-N spec carry.
      (b) provenance -- the candidate's own text explicitly claims to be BUILT FROM that specific
          PRD (_names_prd_as_provenance: "built" near the PRD's filename, not merely a bare mention
          of the filename anywhere in the file -- exactly what STEP_10's template instructs the agent
          to state, and what this project's own CUSTOMIZATION_PHASE_3_SPEC.md does in its opening
          line: "Built FROM the modernised `loopr-PRD.md`...").
    Exactly one *.md file (other than the PRD itself) passing both: that is the Phase-N spec. Zero or
    more than one: Step10ArtifactAmbiguityError, never a recency guess or any other tiebreak."""
    md_files = [path for path in sorted(repo_root.glob("*.md")) if path.is_file()]

    prd_path: Path | None = None
    for candidate in md_files:
        if _has_modernization_changelog_heading(candidate.read_text(encoding="utf-8")):
            prd_path = candidate
            break
    if prd_path is None:
        return None

    structural_candidates = [
        candidate
        for candidate in md_files
        if candidate != prd_path and _has_phase_plan_header_line(candidate.read_text(encoding="utf-8"))
    ]
    provenance_matches = [
        candidate
        for candidate in structural_candidates
        if _names_prd_as_provenance(candidate.read_text(encoding="utf-8"), prd_path.name)
    ]

    if len(provenance_matches) == 1:
        return prd_path, provenance_matches[0]

    if not provenance_matches:
        raise Step10ArtifactAmbiguityError(
            f"modernised PRD found ({prd_path.name}), but no *.md file at {repo_root} both carries a "
            f"'Phase Plan Header' heading and names {prd_path.name} as its source -- structural "
            f"candidates checked: {sorted(c.name for c in structural_candidates)}. step10 may not "
            "have produced its Phase-N-spec deliverable yet, or it was written without provenance "
            "back to the PRD; resolve manually, do not guess."
        )

    raise Step10ArtifactAmbiguityError(
        f"modernised PRD found ({prd_path.name}), but more than one *.md file at {repo_root} both "
        f"carries a 'Phase Plan Header' heading and names {prd_path.name} as its source -- colliding "
        f"candidates: {sorted(c.name for c in provenance_matches)}. Resolve manually, do not guess."
    )


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

# STEP_11 / step_12 (CUSTOMIZATION_PHASE_2_SPEC.md SS1.2): every distinct bracket-shaped token
# actually present in the real files, verified directly (not transcribed from the spec's own table --
# it has already been wrong once in this build's history, for a different token). [PHASE_COUNT]'s
# flip to customizer-resolvable HERE, versus non-placeholder for step10, is the concrete case the
# per-step-registry discipline above exists for -- SS1.1's gating condition is what makes this side of
# the flip true: these steps refuse to customize until step10 has genuinely executed and
# PHASE_1_SPEC.md SS0 states the real count (see customize.py's find_step10_execution_artifacts).
STEP11_PLACEHOLDER_ALLOWLIST: frozenset[str] = frozenset(
    {
        "[PROJECT_NAME]",
        "[PROJECT_REPO_NAME]",
        "[PROJECT]",
        "[PROJECT_TAG]",
        "[PHASE_COUNT]",
    }
)

# [EXECUTOR]: same rule as step10 -- reject-pattern shorthand ("[EXECUTOR] may have written X --
# reject"), never a placeholder.
# [ ] (a single space): markdown checkbox markup, `[ ] item` bullets inside the "## TEMPLATE
# CUSTOMIZATION CHECKLIST" section (SS3.3) -- matches the narrow token regex as a one-character token,
# but it is list syntax, not a placeholder. Classified here independently of that section being
# deleted wholesale (STEP11_SECTION_DELETIONS below), so find_unclassified_bracket_spans never depends
# on section-deletion timing to stay complete.
# [specified], [implemented instead], [reason], [wanted to do], [why the invariant prevents it]: A
# DIFFERENT reason than [ ] or [EXECUTOR] above, despite sharing this set (SS1.2's table names the
# distinction explicitly, worth stating rather than collapsing) -- these are output-FORMAT
# placeholders inside the AUTONOMOUS CRITIQUE section's worked example ("1. [specified] ->
# [implemented instead] -- [reason]"), filled by the STEP11-EXECUTING agent at runtime when it reports
# its own critique, not by the customizer -- same underlying rule as step10's [RESEARCH FOCUS]
# (runtime-derived, not customizer-knowable now), confirmed surviving byte-identical in the real
# precedent (prompts/loopr/step11_build.md lines 105-109).
STEP11_NON_PLACEHOLDER_BRACKET_TOKENS: frozenset[str] = frozenset(
    {
        "[EXECUTOR]",
        "[ ]",
        "[specified]",
        "[implemented instead]",
        "[reason]",
        "[wanted to do]",
        "[why the invariant prevents it]",
    }
)

# [PROJECT_*] (SS7.2, the finding flagged at Phase 1's close): descriptive prose in the template's own
# opening "TEMPLATE STATUS" paragraph ("Customization surfaces are marked [PROJECT_*] and
# <<CUSTOMIZE: ...>>"), referencing a token PATTERN by example, not a literal token to resolve. Same
# CATEGORY as [EXECUTOR] -- no resolution enforced, safe either surviving or edited away as part of
# ordinary prose adaptation (confirmed: the real precedent, prompts/loopr/step11_build.md lines 3-5,
# rewrites this whole paragraph and the reference doesn't survive, but nothing requires that) -- for a
# DIFFERENT underlying reason (documentation about the template's own conventions, not agent-emitted
# runtime output), worth naming per SS7.2 rather than conflating the two reasons. Lives in its own
# registry, not *_NON_PLACEHOLDER_BRACKET_TOKENS, because it is WIDE-only: `*` falls outside
# _BRACKET_TOKEN_RE's character class, so the narrow regex never finds it and it could never be
# intersected against a frozenset of narrow-shaped tokens the way [EXECUTOR] is -- see
# find_unclassified_bracket_spans, which checks this registry by prefix against the WIDE oracle
# instead.
STEP11_DOCUMENTATION_MARKERS: tuple[str, ...] = ("[PROJECT_*]",)

STEP12_PLACEHOLDER_ALLOWLIST: frozenset[str] = frozenset(
    {
        "[PROJECT_NAME]",
        "[PROJECT_REPO_NAME]",
        "[PROJECT]",
        "[PROJECT_TAG]",
        "[PHASE_COUNT]",
        "[EXECUTOR_AGENT_FICTION]",
    }
)

# [EXECUTOR], [ ]: same reasons as STEP_11's entries above. step_12 has no AUTONOMOUS-CRITIQUE-style
# worked-example tokens -- verified directly (its "## THE FIX" section has no bracket-token example
# block); do not carry STEP_11's five-token sub-category over here, it would be unclassified noise.
STEP12_NON_PLACEHOLDER_BRACKET_TOKENS: frozenset[str] = frozenset({"[EXECUTOR]", "[ ]"})

STEP12_DOCUMENTATION_MARKERS: tuple[str, ...] = ("[PROJECT_*]",)

# These are FUNCTIONS, not module-level dict constants, and deliberately so: they are rebuilt from
# the live STEP<N>_* globals on every call, not snapshotted once at import time. A frozen dict built
# at import time would silently break monkeypatch-based regression testing of the individual
# registries (e.g. the carried-forward STEP10_FILL_IN_BLOCK_MARKERS regression test,
# CUSTOMIZATION_PHASE_2_SPEC.md SS2) -- patching a STEP10_*/STEP11_*/STEP12_* constant would have no
# effect on a dict entry that already copied its value before the patch ran. Rebuilding per call keeps
# each registry independently, genuinely monkeypatchable, which is the whole point of testing them
# that way.
def _placeholder_allowlist_by_step() -> dict[CustomizationStep, frozenset[str]]:
    return {
        CustomizationStep.STEP_10: STEP10_PLACEHOLDER_ALLOWLIST,
        CustomizationStep.STEP_11: STEP11_PLACEHOLDER_ALLOWLIST,
        CustomizationStep.STEP_12: STEP12_PLACEHOLDER_ALLOWLIST,
    }


def _non_placeholder_bracket_tokens_by_step() -> dict[CustomizationStep, frozenset[str]]:
    return {
        CustomizationStep.STEP_10: NON_PLACEHOLDER_BRACKET_TOKENS,
        CustomizationStep.STEP_11: STEP11_NON_PLACEHOLDER_BRACKET_TOKENS,
        CustomizationStep.STEP_12: STEP12_NON_PLACEHOLDER_BRACKET_TOKENS,
    }


def _documentation_markers_by_step() -> dict[CustomizationStep, tuple[str, ...]]:
    return {
        CustomizationStep.STEP_10: (),
        CustomizationStep.STEP_11: STEP11_DOCUMENTATION_MARKERS,
        CustomizationStep.STEP_12: STEP12_DOCUMENTATION_MARKERS,
    }


def _fill_in_block_markers_by_step() -> dict[CustomizationStep, tuple[str, ...]]:
    return {
        CustomizationStep.STEP_10: STEP10_FILL_IN_BLOCK_MARKERS,
        # STEP_11 / step_12 have no square-bracket fill-in block of their own -- verified: neither
        # template contains a `[...]`-delimited multi-line instruction block the way STEP_10's hard
        # boundary does. Their equivalent conditional content (the citation-gate blocks) uses
        # `<<...>>` delimiters instead -- see CONDITIONAL_BLOCK_MARKERS below, a separate mechanism.
        CustomizationStep.STEP_11: (),
        CustomizationStep.STEP_12: (),
    }


def find_fill_in_blocks(text: str, step: CustomizationStep) -> list[str]:
    """Returns the recognized multi-line fill-in blocks actually present in `text`, for this step,
    found via the wide-scan oracle since _BRACKET_TOKEN_RE cannot see them. Empty for steps with no
    registered marker (STEP11_FILL_IN_BLOCK_MARKERS/STEP12_FILL_IN_BLOCK_MARKERS are both empty)."""
    markers = _fill_in_block_markers_by_step()[step]
    spans = set(_WIDE_BRACKET_SPAN_RE.findall(text))
    return sorted(span for span in spans if span.startswith(markers))


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
    (allowlist | non-placeholder set) NOR a recognized fill-in block NOR a recognized documentation
    marker -- i.e. genuinely unaccounted for by any classification mechanism this module has. For
    every real template this returns an empty list once its registries are complete. Anything this
    DOES return needs a human to classify it (add to the appropriate registry above), never silently
    absorbed as "probably fine" either way -- that silent-absorption is exactly how STEP_10's
    hard-boundary block went undetected for four commits (b020ade through 1ccc8dd)."""
    classified_short = _placeholder_allowlist_by_step()[step] | _non_placeholder_bracket_tokens_by_step()[
        step
    ]
    fill_in_markers = _fill_in_block_markers_by_step()[step]
    documentation_markers = _documentation_markers_by_step()[step]
    spans = set(_WIDE_BRACKET_SPAN_RE.findall(text))
    return sorted(
        span
        for span in spans
        if span not in classified_short
        and not span.startswith(fill_in_markers)
        and not span.startswith(documentation_markers)
    )


def inventory_placeholders(text: str, step: CustomizationStep) -> list[str]:
    """Returns the allowlisted placeholder tokens actually present in `text`, for this step. Tokens
    matching the bracket shape but not on the allowlist (e.g. [UNVERIFIED], [EXECUTOR]) are never
    returned here -- they are not placeholders and must never be treated as one."""
    found = set(_BRACKET_TOKEN_RE.findall(text))
    return sorted(found & _placeholder_allowlist_by_step()[step])


def unresolved_placeholders(text: str, step: CustomizationStep) -> list[str]:
    """The allowlisted tokens from `inventory_placeholders` that are STILL present in `text` --
    i.e. never got filled. Same function works for the template (everything is "unresolved" there)
    and the customized output (should be empty there)."""
    return inventory_placeholders(text, step)


def surviving_customize_markers(text: str) -> list[str]:
    """`<<CUSTOMIZE: ...>>` markers are instructions TO the customizer; they must never reach the
    executing agent. Returns every such marker still present in `text`. Step-agnostic -- the
    `<<CUSTOMIZE...>>` convention is used identically in STEP_11 and step_12 (STEP_10 has none).

    REGRESSION, found and fixed while building CONDITIONAL_BLOCK_MARKERS (CUSTOMIZATION_PHASE_2_SPEC
    .md SS3.4) -- confirmed as a real, pre-existing defect, not hypothetical: the previous pattern
    (`[^>]*`, a `>`-excluding class, same shape as _WIDE_ANGLE_SPAN_RE's original bug) could not cross
    the literal `>` characters in STEP_11/step_12's HARD BOUNDARY block's own "->" arrow notation
    ("client demo -> the customer's core IP...") -- it silently found ZERO markers for that block in
    either template, meaning a customization that shipped the HARD BOUNDARY section completely
    unfilled (the template's own generic per-project-kind examples verbatim) would have
    passed layer 1 undetected. This was never exercised in Phase 1, which only ever tested this
    function against STEP_10 (zero CUSTOMIZE markers) and short synthetic fixtures with no "->"
    content. Fixed the same way as _WIDE_ANGLE_SPAN_RE: lazy match to the first literal `>>`, not a
    `[^<>]`-style exclusion."""
    return re.findall(r"<<CUSTOMIZE.{0,8000}?>>", text, re.DOTALL)


# Section deletion (CUSTOMIZATION_PHASE_2_SPEC.md SS3.3) -- new in Phase 2: both STEP_11 and step_12
# end in a "## TEMPLATE CUSTOMIZATION CHECKLIST" section whose own text instructs "remove before
# pasting to Claude Code." This is scaffolding for the human who customizes by hand, not a fill
# target -- the customized OUTPUT must not contain it at all, and the skeleton-equality check Phase 1
# used is now wrong as written (it would reject every genuinely correct step11/step12 customization
# for "missing" a section that is SUPPOSED to be gone). Matched by SUBSTRING against the extracted
# skeleton's section strings, not the full exact line -- verified directly against both real files:
# the parenthetical wording differs ("for the project web chat -- remove before..." in STEP_11 vs.
# "remove before..." in step_12) without changing what section it is.
STEP11_SECTION_DELETIONS: tuple[str, ...] = ("TEMPLATE CUSTOMIZATION CHECKLIST",)
STEP12_SECTION_DELETIONS: tuple[str, ...] = ("TEMPLATE CUSTOMIZATION CHECKLIST",)

def _section_deletions_by_step() -> dict[CustomizationStep, tuple[str, ...]]:
    return {
        CustomizationStep.STEP_10: (),
        CustomizationStep.STEP_11: STEP11_SECTION_DELETIONS,
        CustomizationStep.STEP_12: STEP12_SECTION_DELETIONS,
    }


def expected_output_sections(template_sections: list[str], step: CustomizationStep) -> list[str]:
    """The section list a genuinely fidelity-passing output must match: the template's own skeleton
    MINUS every section matching a declared SECTION_DELETIONS marker for this step (SS3.3). Returns
    the template's sections unchanged for steps with nothing declared (step10 -- no deletions there).
    A section is deleted if any registered marker is a SUBSTRING of it, not an exact-line match (see
    the registry comment above for why). This subtraction must stay exact, not loose: any section NOT
    matching a declared marker is still required, so a customization dropping a real section is still
    rejected -- verify the delta, don't just relax the equality (SS3.3's own warning)."""
    markers = _section_deletions_by_step()[step]
    if not markers:
        return template_sections
    return [section for section in template_sections if not any(marker in section for marker in markers)]


# Conditional include-or-replace (CUSTOMIZATION_PHASE_2_SPEC.md SS3.4) -- new in Phase 2:
# <<CITATION_GATE_INGESTION_BLOCK: ...>> (STEP_11) and <<CITATION_GATE_BLOCK: ...>> (step_12) are
# neither fill targets nor unconditional deletions -- include verbatim if the project has
# load-bearing arXiv citations, otherwise resolve per EACH TEMPLATE'S OWN stated fallback. Verified
# directly against both real files, and the two are NOT symmetric -- do not assume they are:
#   - step_12's block states an exact single-line replacement ("If not applicable, replace with:
#     'No citation re-verification gate required for this project.'"). Even so, the real,
#     human-produced precedent (prompts/loopr/step12_review.md line 151) does not use that line
#     byte-for-byte -- it opens with it, then adds genuine project-specific reasoning after it.
#   - STEP_11's block says only "Otherwise remove this block" -- no replacement text is specified at
#     all (there is no "replace with: ..." clause in STEP_11's version, unlike step_12's). The real
#     precedent (prompts/loopr/step11_build.md lines 46-48) replaces it with a bespoke
#     project-specific statement, not any fixed line, because none exists to copy.
# CONSEQUENCE: layer 1 can only reliably verify the raw marker doesn't survive verbatim (same
# sentinel mechanism as fill-in blocks, different delimiter) -- it cannot mandate byte-exact
# replacement text for EITHER step without rejecting the real, legitimate precedent for both. Whether
# the replacement content is genuinely appropriate (real citation content when included; real
# reasoning, not generic filler, when not) is a layer-2 judgment, exactly as SS3.4 says: "this is a
# judgment call, not a structural one."
STEP11_CONDITIONAL_BLOCK_MARKERS: tuple[str, ...] = ("<<CITATION_GATE_INGESTION_BLOCK",)
STEP12_CONDITIONAL_BLOCK_MARKERS: tuple[str, ...] = ("<<CITATION_GATE_BLOCK",)

def _conditional_block_markers_by_step() -> dict[CustomizationStep, tuple[str, ...]]:
    return {
        CustomizationStep.STEP_10: (),
        CustomizationStep.STEP_11: STEP11_CONDITIONAL_BLOCK_MARKERS,
        CustomizationStep.STEP_12: STEP12_CONDITIONAL_BLOCK_MARKERS,
    }


# The angle-bracket analogue of _WIDE_BRACKET_SPAN_RE -- same independent-oracle discipline and
# DOTALL/bounded shape, different delimiter, and NOT a non-nested character-class exclusion the way
# the square-bracket version is. Verified directly against step_12's real CITATION_GATE_BLOCK
# (confirmed a real bug, not a hypothetical): its own body text contains single `>` characters as
# "->" arrow notation ("PASS -> add a SS0.5 ...", twice), which a `[^<>]`-style exclusion cannot
# cross -- it would truncate the match at the first "->" and never reach the block's real closing
# `>>`, silently returning zero blocks found for step_12's FULL instructional form (the bare
# `<<CITATION_GATE_BLOCK>>` inside the checklist, which has no internal `>`, matched fine and masked
# the miss until tested against the real file with a real judge-drafted "include" resolution). A
# LAZY match to the FIRST literal `>>` is correct here instead: STEP_11/step_12 have exactly one
# genuine `>>` closing per block (verified), so the first one found is always the real one.
_WIDE_ANGLE_SPAN_RE = re.compile(r"<<.{1,8000}?>>", re.DOTALL)


def find_conditional_blocks(text: str, step: CustomizationStep) -> list[str]:
    """Returns the recognized conditional include-or-replace blocks (SS3.4) actually present in
    `text` for this step. Mirrors find_fill_in_blocks exactly (same sentinel-based design) but scans
    `<<...>>` spans instead of `[...]` spans, since these markers use angle brackets."""
    markers = _conditional_block_markers_by_step()[step]
    spans = set(_WIDE_ANGLE_SPAN_RE.findall(text))
    return sorted(span for span in spans if span.startswith(markers))


def unresolved_conditional_blocks(
    template_text: str, output_text: str, step: CustomizationStep
) -> list[str]:
    """Mirrors unresolved_fill_in_blocks exactly, for conditional blocks: the template's own
    original block text is the sentinel -- still present byte-identical in the output means the
    customizer never resolved the include-or-replace decision at all, regardless of which way it
    should have gone."""
    blocks = find_conditional_blocks(template_text, step)
    return [block for block in blocks if block in output_text]
