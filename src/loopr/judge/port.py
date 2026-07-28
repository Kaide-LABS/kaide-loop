"""The JudgeClient port. Implements PHASE_1_SPEC.md SS6.2.3."""

from __future__ import annotations

from typing import Protocol

from loopr.models.judge import JudgeRequest, JudgeResponse


class JudgeClient(Protocol):
    """Returning None means 'cannot answer in-process -- caller must suspend.'"""

    def ask(self, request: JudgeRequest) -> JudgeResponse | None: ...
