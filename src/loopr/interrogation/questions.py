"""Targeted follow-up construction. Implements PHASE_1_SPEC.md SS6.5.1.

Never emits a generic "anything else?" (docs/stopping-test-spec.md Design approach) -- every
question names the specific failing condition.
"""

from __future__ import annotations

from loopr.models.common import ConditionId
from loopr.models.interrogation import InterrogationState

_ANTI_LOOP_THRESHOLD = 2


def build_followup(state: InterrogationState, target: ConditionId) -> str:
    if target == ConditionId.C1_OUTCOME:
        failures = state.consecutive_judge_failures.get(ConditionId.C1_OUTCOME, 0)
        if failures >= _ANTI_LOOP_THRESHOLD:
            reasons = [
                exchange.response.reason
                for exchange in state.judge_log[-_ANTI_LOOP_THRESHOLD:]
                if exchange.request.call_type.value == "c1_outcome"
            ]
            joined = "\n".join(f"- {r}" for r in reasons)
            return (
                "I've asked about the outcome twice and haven't landed it. Here's exactly what "
                f"was unclear both times:\n{joined}\n\nPlease restate, in one sentence, what "
                "becomes true when this is done and for whom."
            )
        return (
            "What is the real-world outcome you want -- what becomes true when this is done, and "
            "for whom? (Not the tool or approach -- the result.)"
        )

    if target == ConditionId.C2_ACCEPTANCE:
        return (
            "How would you, or a third party who didn't build this, concretely check that it "
            "worked -- something observable, not a feeling?"
        )

    if target == ConditionId.C3_SCOPE_EDGES:
        return (
            "What is explicitly OUT of scope for now, or deferred to later? Name something "
            "concrete (a feature, an integration, a scale threshold) rather than 'nothing fancy'."
        )

    if target == ConditionId.C4_BOUNDARY:
        return (
            "Here is the proposed boundary for what's in-scope-now versus later. Confirm it, tweak "
            "it, or explicitly decline to set one."
        )

    if target == ConditionId.C5_SOFT_CONTEXT:
        return (
            "Is there anything a boss said, a political constraint, or a watch-out that would "
            "make this judged a failure even if it's technically correct -- or is this a clean "
            "slate with no soft context to capture?"
        )

    if target == ConditionId.C6_NO_UNKNOWNS:
        open_texts = [q.text for q in state.open_questions if q.status.value == "open"]
        if open_texts:
            return f"Still open, and it may change the spec: {open_texts[0]}"
        return "Is there any open question whose answer would materially change the spec?"

    raise AssertionError(f"unhandled condition {target}")
