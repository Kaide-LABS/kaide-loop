"""Fixture-replay judge client for tests and `loopr replay`. Implements PHASE_1_SPEC.md SS6.2.3."""

from __future__ import annotations

from collections.abc import Mapping

from loopr.models.judge import JudgeRequest, JudgeResponse


class MissingFixtureError(KeyError):
    """Raised when a scripted client has no fixture for a given call_id."""


class ScriptedJudgeClient:
    """Never falls back to a live call -- a missing fixture is a test failure, not a network call."""

    def __init__(self, fixtures: Mapping[str, JudgeResponse]) -> None:
        self._fixtures = dict(fixtures)

    def ask(self, request: JudgeRequest) -> JudgeResponse | None:
        try:
            return self._fixtures[request.call_id]
        except KeyError as exc:
            raise MissingFixtureError(
                f"no fixture for call_id={request.call_id!r} (call_type={request.call_type})"
            ) from exc
