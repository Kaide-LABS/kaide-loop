"""Re-exports StateStore. Implements PHASE_1_SPEC.md SS1.5."""

from loopr.state.store import StateStore, StateVersionError

__all__ = ["StateStore", "StateVersionError"]
