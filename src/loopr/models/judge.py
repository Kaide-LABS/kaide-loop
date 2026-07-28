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
ALLOWED_INPUTS: Mapping[JudgeCallType, frozenset[str]] = {
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


class JudgeScopeError(ValueError):
    """Raised when a JudgeRequest's inputs do not exactly match its call type's allowed scope."""


class JudgeRequest(LooprBase):
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
    envelope_version: int = 1

    @model_validator(mode="after")
    def check_scope(self) -> "JudgeRequest":
        allowed = ALLOWED_INPUTS[self.call_type]
        actual = set(self.inputs.keys())
        if actual != allowed:
            missing = allowed - actual
            extra = actual - allowed
            raise JudgeScopeError(
                f"{self.call_type} scope violation: missing={sorted(missing)} extra={sorted(extra)}"
            )
        return self


class JudgeResponse(LooprBase):
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


class JudgeExchange(LooprBase):
    request: JudgeRequest
    response: JudgeResponse
    request_sha256: str = Field(min_length=1)
    response_sha256: str = Field(min_length=1)
    answered_at_round: int = Field(ge=1)
