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
ALLOWED_INPUTS_V2: Mapping[JudgeCallType, frozenset[str]] = {
    **ALLOWED_INPUTS_V1,
    JudgeCallType.C5_SOFT_CONTEXT: frozenset(
        {"context_note", "problem_statement", "acceptance_criteria", "scope_edges", "boundary"}
    ),
}

ALLOWED_INPUTS_BY_VERSION: Mapping[int, Mapping[JudgeCallType, frozenset[str]]] = {
    1: ALLOWED_INPUTS_V1,
    2: ALLOWED_INPUTS_V2,
}

CURRENT_ENVELOPE_VERSION = 2

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
            )
            if value is not None
        ]
        if len(populated) > 1:
            raise ValueError(
                f"exactly one of passed/verdict/selected_files may be set, got: {populated}"
            )
        return self


class JudgeExchange(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    request: JudgeRequest
    response: JudgeResponse
    request_sha256: str = Field(min_length=1)
    response_sha256: str = Field(min_length=1)
    answered_at_round: int = Field(ge=1)
