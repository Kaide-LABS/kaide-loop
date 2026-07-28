"""Re-exports the interrogation loop. Implements PHASE_1_SPEC.md SS1.5."""

from loopr.interrogation.loop import InboundKind, InboundPayload, StepOutcome, step
from loopr.interrogation.questions import build_followup

__all__ = ["InboundKind", "InboundPayload", "StepOutcome", "build_followup", "step"]
