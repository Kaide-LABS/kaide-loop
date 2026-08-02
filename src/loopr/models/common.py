"""Shared base model and enums. Implements PHASE_1_SPEC.md SS3.1."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class LooprBase(BaseModel):  # type: ignore[explicit-any]  # pydantic's own ConfigDict TypedDict carries Any-typed fields (e.g. json_encoders); no real Any in loopr code
    """Base for every loopr model. extra='forbid' is set once here and inherited everywhere."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        frozen=False,
    )


class Mode(str, Enum):
    GREENFIELD = "greenfield"
    BROWNFIELD = "brownfield"


class ConditionId(str, Enum):
    C1_OUTCOME = "c1_outcome"
    C2_ACCEPTANCE = "c2_acceptance"
    C3_SCOPE_EDGES = "c3_scope_edges"
    C4_BOUNDARY = "c4_boundary"
    C5_SOFT_CONTEXT = "c5_soft_context"
    C6_NO_UNKNOWNS = "c6_no_unknowns"


class JudgeCallType(str, Enum):
    """Deliberately does NOT include C4 -- condition 4 itself is a pure state-machine check, no
    rubric. BOUNDARY_PROPOSAL is a distinct thing: a one-off drafting call that runs UPSTREAM of
    condition 4, to give Gate 2 real content to show, before condition 4's own confirm-only check
    ever runs. Added 2026-08-01 -- see docs/stopping-test-spec.md Condition 4's boundary-drafting
    amendment."""

    C1_OUTCOME = "c1_outcome"
    C2_ACCEPTANCE = "c2_acceptance"
    C3_SCOPE_EDGES = "c3_scope_edges"
    C5_SOFT_CONTEXT = "c5_soft_context"
    C6_LOAD_BEARING = "c6_load_bearing"
    BF_RELEVANCE = "bf_relevance"
    BF_CLASSIFY = "bf_classify"
    BOUNDARY_PROPOSAL = "boundary_proposal"
    STEP10_CUSTOMIZATION = "step10_customization"
    STEP10_FIDELITY_JUDGE = "step10_fidelity_judge"
    """Layer 2 of the customization fidelity check (CUSTOMIZATION_PHASE_1_SPEC.md SS4.3) -- a
    distinct call type from STEP10_CUSTOMIZATION, not mentioned by name in that spec's SS2 file
    list (which said to add "the new call type", singular). Required because JudgeResponse's
    exactly-one-of-four shape means a single response can carry drafted_text (the customization) OR
    passed (the genuineness judgment), never both -- two structurally different response shapes
    cannot share one call type under the existing schema. Disclosed deviation, not silent."""


class QuestionStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DEFERRED_NON_LOAD_BEARING = "deferred_non_load_bearing"


class QuestionOrigin(str, Enum):
    MODULE = "module"
    USER = "user"
    PATTERN_AMBIGUITY = "pattern_ambiguity"


class ScopeEdgeKind(str, Enum):
    OUT = "out"
    DEFERRED = "deferred"


class NoteSource(str, Enum):
    STATED = "stated"
    INFERRED = "inferred"


class Verdict(str, Enum):
    CONFORM = "conform"
    DO_NOT_REPLICATE = "do_not_replicate"
    CONFLICT = "conflict"
    AMBIGUOUS = "ambiguous"


class Centrality(str, Enum):
    CORE = "core"
    PERIPHERAL = "peripheral"


class GateId(str, Enum):
    GATE_1_BABY_PRD = "gate_1_baby_prd"
    GATE_2_BOUNDARY = "gate_2_boundary"
    GATE_3_CONFLICTS = "gate_3_conflicts"


class CustomizationStep(str, Enum):
    """Identifies which template a discovery/skeleton-extraction result belongs to. All three exist
    as a type since template discovery must handle all three on-disk files' inconsistent naming
    (CUSTOMIZATION_PHASE_1_SPEC.md SS4.2) -- only STEP_10 is wired to the `loopr customize` CLI in
    Phase 1; STEP_11/STEP_12 customization itself is Phase 2, not built here."""

    STEP_10 = "step_10"
    STEP_11 = "step_11"
    STEP_12 = "step_12"
