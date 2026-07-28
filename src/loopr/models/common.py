"""Shared base model and enums. Implements PHASE_1_SPEC.md SS3.1."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class LooprBase(BaseModel):
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
    """Deliberately does NOT include C4 -- condition 4 is a pure state-machine check, no rubric."""

    C1_OUTCOME = "c1_outcome"
    C2_ACCEPTANCE = "c2_acceptance"
    C3_SCOPE_EDGES = "c3_scope_edges"
    C5_SOFT_CONTEXT = "c5_soft_context"
    C6_LOAD_BEARING = "c6_load_bearing"
    BF_RELEVANCE = "bf_relevance"
    BF_CLASSIFY = "bf_classify"


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
