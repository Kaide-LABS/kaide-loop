"""Judge request/response envelope and the scope-enforcement mechanism.

Implements PHASE_1_SPEC.md SS3.4 -- this is where "the judge sees exactly its documented scope"
stops being a review convention and becomes a runtime error via check_scope below.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import ConfigDict, Field, model_validator

from loopr.models.common import JudgeCallType, LooprBase, Verdict

# PEP 695 named recursive type alias -- required for pydantic to build a non-recursing schema
# (a plain `Union[..., list["JsonValue"], ...]` alias causes unbounded schema-generation recursion).
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]

# The machine-readable transcription of the Shape 1 / Shape 2 discipline. Must match
# docs/stopping-test-spec.md Design approach and docs/conformance-classification-spec.md SS1/SS4
# exactly. C1/C2/C3 are Shape 1 (single field, C1 plus its advisory flag); C5/C6/BF_* are Shape 2.
#
# Version-gated (docs/stopping-test-spec.md Condition 5, amended 2026-07-30 -- brownfield proof
# Finding: check_scope used to validate every record, historical or new, against whichever scope is
# live today. That breaks `loopr replay`/`emit` against any state file recorded before a rubric's
# scope was ever tuned. Each JudgeRequest already carries envelope_version (PHASE_1_SPEC.md SS6.3.3's
# "future version bump" guard, applied here per-record rather than per-file): check_scope looks up
# the ALLOWED_INPUTS that was current AT THAT VERSION, not today's, so a historical record stays
# valid forever. A scope amendment MUST bump CURRENT_ENVELOPE_VERSION and add a new entry to
# ALLOWED_INPUTS_BY_VERSION -- never edit an existing version's entry in place.
ALLOWED_INPUTS_V1: Mapping[JudgeCallType, frozenset[str]] = {
    JudgeCallType.C1_OUTCOME: frozenset({"problem_statement", "prefilter_flagged"}),
    JudgeCallType.C2_ACCEPTANCE: frozenset({"acceptance_criteria"}),
    JudgeCallType.C3_SCOPE_EDGES: frozenset({"scope_edges"}),
    JudgeCallType.C5_SOFT_CONTEXT: frozenset({"context_note", "acceptance_criteria"}),
    JudgeCallType.C6_LOAD_BEARING: frozenset(
        {"question_text", "acceptance_criteria", "scope_edges", "boundary"}
    ),
    JudgeCallType.BF_RELEVANCE: frozenset(
        {"candidate_files", "problem_statement", "acceptance_criteria", "scope_edges"}
    ),
    JudgeCallType.BF_CLASSIFY: frozenset(
        {"evidence_bundle", "problem_statement", "acceptance_criteria", "scope_edges", "boundary"}
    ),
}

# v2 (2026-07-30): condition 5's relevance check widened its scope to problem_statement/scope_edges/
# boundary, per the brownfield proof run's smuggling finding. Everything else is unchanged from v1.
#
# Also carries BOUNDARY_PROPOSAL (added 2026-08-01): a wholly new call type, not a scope change to an
# existing one, so no historical record can ever reference it -- safe to add directly to the current
# version's map rather than needing its own version bump. See docs/stopping-test-spec.md Condition 4.
ALLOWED_INPUTS_V2: Mapping[JudgeCallType, frozenset[str]] = {
    **ALLOWED_INPUTS_V1,
    JudgeCallType.C5_SOFT_CONTEXT: frozenset(
        {"context_note", "problem_statement", "acceptance_criteria", "scope_edges", "boundary"}
    ),
    JudgeCallType.BOUNDARY_PROPOSAL: frozenset(
        {"problem_statement", "acceptance_criteria", "scope_edges", "context_notes"}
    ),
}

# v3 (2026-08-02): adds the two customization call types (CUSTOMIZATION_PHASE_1_SPEC.md SS4.1).
# STEP10_CUSTOMIZATION's input set is deliberately wider than any prior call -- disclosed, not
# smuggled in: customization is a synthesis, not a judgment (see the rubric text), so it legitimately
# needs more of the confirmed record than a pass/fail check does. The discipline that still applies:
# the set is explicit and version-gated, never "the whole transcript" or "whatever is in state."
# STEP10_FIDELITY_JUDGE is layer 2 of the fidelity check -- a distinct call type from
# STEP10_CUSTOMIZATION, required by JudgeResponse's exactly-one-of-four response shape (a single
# response cannot carry both drafted_text and passed).
ALLOWED_INPUTS_V3: Mapping[JudgeCallType, frozenset[str]] = {
    **ALLOWED_INPUTS_V2,
    JudgeCallType.STEP10_CUSTOMIZATION: frozenset(
        {
            "template_text",
            "problem_statement",
            "acceptance_criteria",
            "scope_edges",
            "boundary",
            "context_notes",
            "conformance_summary",
        }
    ),
    JudgeCallType.STEP10_FIDELITY_JUDGE: frozenset(
        {
            "template_text",
            "customized_text",
            "problem_statement",
            "acceptance_criteria",
            "boundary",
        }
    ),
}

# v4 (2026-08-03): adds step11/step12's customization + fidelity pairs (CUSTOMIZATION_PHASE_2_SPEC.md
# SS2). STEP11_CUSTOMIZATION/STEP12_CUSTOMIZATION's input set is STEP10_CUSTOMIZATION's set plus one
# new field, `phase_1_spec_text` -- step10's own §1.1 gating condition guarantees this file exists and
# is real by the time these calls are ever made, and the judge needs its content to resolve
# [PHASE_COUNT] (SS1.2: "PHASE_1_SPEC.md SS0's phase plan header states it once step10 has run") and
# the PRD-section-reference <<CUSTOMIZE: ...>> marker. Disclosed scope decision: the modernised PRD's
# own full text is deliberately NOT included here -- no acceptance criterion in
# CUSTOMIZATION_PHASE_2_SPEC.md SS5 requires it, and its filename is genuinely variable (loopr's own
# real customization uses "loopr-PRD.md", not the template's stated default "ULTIMATE_PRD.md" --
# verified against prompts/loopr/step10_prd_modernization.md), unlike PHASE_1_SPEC.md's fixed name.
# The judge resolves the PRD-section-reference marker from the confirmed spec fields available to it
# without the PRD's literal text, same as it already resolves everything else it cannot see directly.
# STEP11_FIDELITY_JUDGE/STEP12_FIDELITY_JUDGE mirror STEP10_FIDELITY_JUDGE's set exactly -- layer 2
# judges genuineness of what was already drafted, it does not need phase_1_spec_text to do that.
ALLOWED_INPUTS_V4: Mapping[JudgeCallType, frozenset[str]] = {
    **ALLOWED_INPUTS_V3,
    JudgeCallType.STEP11_CUSTOMIZATION: frozenset(
        {
            "template_text",
            "phase_1_spec_text",
            "problem_statement",
            "acceptance_criteria",
            "scope_edges",
            "boundary",
            "context_notes",
            "conformance_summary",
        }
    ),
    JudgeCallType.STEP11_FIDELITY_JUDGE: frozenset(
        {
            "template_text",
            "customized_text",
            "problem_statement",
            "acceptance_criteria",
            "boundary",
        }
    ),
    JudgeCallType.STEP12_CUSTOMIZATION: frozenset(
        {
            "template_text",
            "phase_1_spec_text",
            "problem_statement",
            "acceptance_criteria",
            "scope_edges",
            "boundary",
            "context_notes",
            "conformance_summary",
        }
    ),
    JudgeCallType.STEP12_FIDELITY_JUDGE: frozenset(
        {
            "template_text",
            "customized_text",
            "problem_statement",
            "acceptance_criteria",
            "boundary",
        }
    ),
}

ALLOWED_INPUTS_BY_VERSION: Mapping[int, Mapping[JudgeCallType, frozenset[str]]] = {
    1: ALLOWED_INPUTS_V1,
    2: ALLOWED_INPUTS_V2,
    3: ALLOWED_INPUTS_V3,
    4: ALLOWED_INPUTS_V4,
}

CURRENT_ENVELOPE_VERSION = 4

# The live scope, for callers building NEW requests (checks/conditions.py, tests). Always the
# highest entry in ALLOWED_INPUTS_BY_VERSION -- kept as a top-level name for backward compatibility.
ALLOWED_INPUTS: Mapping[JudgeCallType, frozenset[str]] = ALLOWED_INPUTS_BY_VERSION[
    CURRENT_ENVELOPE_VERSION
]


class JudgeScopeError(ValueError):
    """Raised when a JudgeRequest's inputs do not exactly match its call type's allowed scope, as of
    that request's own envelope_version -- or when envelope_version itself is unrecognised."""


class JudgeRequest(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        frozen=True,
    )

    call_id: str = Field(min_length=1)
    call_type: JudgeCallType
    rubric_id: str = Field(min_length=1)
    rubric_text: str = Field(min_length=1)
    inputs: dict[str, JsonValue]
    created_round: int = Field(ge=1)
    envelope_version: int = CURRENT_ENVELOPE_VERSION

    @model_validator(mode="after")
    def check_scope(self) -> "JudgeRequest":
        allowed_map = ALLOWED_INPUTS_BY_VERSION.get(self.envelope_version)
        if allowed_map is None:
            raise JudgeScopeError(
                f"unrecognised envelope_version={self.envelope_version!r}; known versions are "
                f"{sorted(ALLOWED_INPUTS_BY_VERSION)}"
            )
        allowed = allowed_map[self.call_type]
        actual = set(self.inputs.keys())
        if actual != allowed:
            missing = allowed - actual
            extra = actual - allowed
            raise JudgeScopeError(
                f"{self.call_type} scope violation (envelope_version={self.envelope_version}): "
                f"missing={sorted(missing)} extra={sorted(extra)}"
            )
        return self


class JudgeResponse(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    call_id: str = Field(min_length=1)
    passed: bool | None = None
    verdict: Verdict | None = None
    selected_files: list[str] | None = None
    drafted_text: str | None = None
    """Free-text drafted content -- currently only BOUNDARY_PROPOSAL's response shape. Added
    2026-08-01: none of the other three shapes (a pass/fail, a four-way verdict, a file selection)
    can carry drafted prose, and the judge genuinely needs to draft one here (see
    docs/stopping-test-spec.md Condition 4)."""
    reason: str = Field(min_length=1)
    missing: str | None = None
    misplaced: bool = False

    @model_validator(mode="after")
    def check_response_shape(self) -> "JudgeResponse":
        populated = [
            name
            for name, value in (
                ("passed", self.passed),
                ("verdict", self.verdict),
                ("selected_files", self.selected_files),
                ("drafted_text", self.drafted_text),
            )
            if value is not None
        ]
        if len(populated) > 1:
            raise ValueError(
                f"exactly one of passed/verdict/selected_files/drafted_text may be set, got: "
                f"{populated}"
            )
        return self


class JudgeExchange(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    request: JudgeRequest
    response: JudgeResponse
    request_sha256: str = Field(min_length=1)
    response_sha256: str = Field(min_length=1)
    answered_at_round: int = Field(ge=1)
