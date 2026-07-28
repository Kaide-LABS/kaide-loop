"""The default emit-and-exit judge binding. Implements PHASE_1_SPEC.md SS6.2.

loopr never calls an LLM API. This client writes the request envelope and returns None; the CLI
translates that into exit code 10 (JUDGE_REQUIRED) and the invoking agent -- Claude Code by default,
using that session's own model -- answers on the next invocation. No API key, no network call.
"""

from __future__ import annotations

from pathlib import Path

from loopr.judge.envelope import write_request
from loopr.models.judge import JudgeRequest, JudgeResponse


class AgentJudgeClient:
    def __init__(self, pending_path: Path) -> None:
        self._pending_path = pending_path

    def ask(self, request: JudgeRequest) -> JudgeResponse | None:
        write_request(self._pending_path, request)
        return None
