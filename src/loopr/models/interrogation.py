"""Interrogation state models. Implements PHASE_1_SPEC.md SS3.2."""

from __future__ import annotations

from pydantic import Field, model_validator

from loopr.models.common import (
    ConditionId,
    GateId,
    LooprBase,
    Mode,
    NoteSource,
    QuestionOrigin,
    QuestionStatus,
    ScopeEdgeKind,
)
from loopr.models.gates import GateRecord


class AcceptanceCriterion(LooprBase):
    text: str = Field(min_length=1)
    judge_confirmed_testable: bool = False


class ScopeEdge(LooprBase):
    item: str = Field(min_length=1)
    kind: ScopeEdgeKind
    reason: str = Field(min_length=1)


class Boundary(LooprBase):
    text: str = Field(min_length=1)
    confirmed: bool = False
    confirmed_hash: str | None = None
    declined: bool = False

    @model_validator(mode="after")
    def check_confirmation_coherent(self) -> "Boundary":
        if self.confirmed and self.confirmed_hash is None:
            raise ValueError("confirmed boundary must carry confirmed_hash")
        if self.confirmed and self.declined:
            raise ValueError("boundary cannot be both confirmed and declined")
        return self


class ContextNote(LooprBase):
    text: str = Field(min_length=1)
    source: NoteSource


class OpenQuestion(LooprBase):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    origin: QuestionOrigin
    status: QuestionStatus = QuestionStatus.OPEN
    load_bearing: bool | None = None
    resolution: str | None = None
    force_resolved: bool = False

    @model_validator(mode="after")
    def check_resolution_coherent(self) -> "OpenQuestion":
        if self.status == QuestionStatus.RESOLVED and self.resolution is None:
            raise ValueError("resolved question must carry a resolution")
        if self.force_resolved and self.status != QuestionStatus.DEFERRED_NON_LOAD_BEARING:
            raise ValueError("force_resolved implies status=deferred_non_load_bearing")
        return self


class Assumption(LooprBase):
    text: str = Field(min_length=1)
    source_question_id: str = Field(min_length=1)
    created_round: int = Field(ge=1)


class ConditionResult(LooprBase):
    condition: ConditionId
    structural_pass: bool
    judge_pass: bool | None
    overall: bool
    detail: str

    @model_validator(mode="after")
    def check_two_layer_invariant(self) -> "ConditionResult":
        if self.overall:
            if not self.structural_pass:
                raise ValueError("overall cannot be True when structural_pass is False")
            judge_ok = self.judge_pass is True or self.condition == ConditionId.C4_BOUNDARY
            if not judge_ok:
                raise ValueError(
                    "overall cannot be True unless judge_pass is True (or condition is C4, "
                    "which has no judge)"
                )
        return self


class InterrogationState(LooprBase):
    schema_version: int = 1
    mode: Mode
    repo_root: str
    problem_statement: str | None = None
    problem_statement_prefilter_flagged: bool = False
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    scope_edges: list[ScopeEdge] = Field(default_factory=list)
    boundary: Boundary | None = None
    context_notes: list[ContextNote] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    condition_results: list[ConditionResult] = Field(default_factory=list)
    consecutive_judge_failures: dict[ConditionId, int] = Field(default_factory=dict)
    round: int = Field(default=1, ge=1)
    max_rounds: int = Field(default=8, ge=1, le=50)
    gates: dict[GateId, GateRecord] = Field(default_factory=dict)
    brownfield: "BrownfieldState | None" = None
    judge_log: list["JudgeExchange"] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_mode_coherent(self) -> "InterrogationState":
        has_brownfield = self.brownfield is not None
        if (self.mode == Mode.BROWNFIELD) != has_brownfield:
            raise ValueError("mode=BROWNFIELD iff brownfield state is present")
        return self


from loopr.models.brownfield import BrownfieldState  # noqa: E402
from loopr.models.judge import JudgeExchange  # noqa: E402

InterrogationState.model_rebuild()
