"""Re-exports every public loopr model. Implements PHASE_1_SPEC.md SS3."""

from loopr.models.brownfield import BrownfieldState, EvidenceBundle, PatternClassification
from loopr.models.common import (
    Centrality,
    ConditionId,
    CustomizationStep,
    GateId,
    JudgeCallType,
    LooprBase,
    Mode,
    NoteSource,
    QuestionOrigin,
    QuestionStatus,
    ScopeEdgeKind,
    Verdict,
)
from loopr.models.customization import (
    CustomizationState,
    CustomizedPrompt,
    FidelityResult,
    PlaceholderBinding,
    TemplateSkeleton,
)
from loopr.models.gates import GatePayload, GateRecord
from loopr.models.interrogation import (
    AcceptanceCriterion,
    Assumption,
    Boundary,
    ConditionResult,
    ContextNote,
    InterrogationState,
    OpenQuestion,
    ScopeEdge,
)
from loopr.models.judge import (
    ALLOWED_INPUTS,
    JsonValue,
    JudgeExchange,
    JudgeRequest,
    JudgeResponse,
    JudgeScopeError,
)

# Resolve forward references now that every module is imported (loopr-MIGRATION.md SS8:
# no unresolved forward references).
InterrogationState.model_rebuild()
JudgeRequest.model_rebuild()

__all__ = [
    "ALLOWED_INPUTS",
    "AcceptanceCriterion",
    "Assumption",
    "Boundary",
    "BrownfieldState",
    "Centrality",
    "ConditionId",
    "ConditionResult",
    "ContextNote",
    "CustomizationState",
    "CustomizationStep",
    "CustomizedPrompt",
    "EvidenceBundle",
    "FidelityResult",
    "GateId",
    "GatePayload",
    "GateRecord",
    "InterrogationState",
    "JsonValue",
    "JudgeCallType",
    "JudgeExchange",
    "JudgeRequest",
    "JudgeResponse",
    "JudgeScopeError",
    "LooprBase",
    "Mode",
    "NoteSource",
    "OpenQuestion",
    "PatternClassification",
    "PlaceholderBinding",
    "QuestionOrigin",
    "QuestionStatus",
    "ScopeEdge",
    "ScopeEdgeKind",
    "TemplateSkeleton",
    "Verdict",
]
