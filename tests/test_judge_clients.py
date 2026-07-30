"""AgentJudgeClient (emit-and-exit) and ScriptedJudgeClient's missing-fixture failure mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from loopr.judge.agent_client import AgentJudgeClient
from loopr.judge.envelope import read_request
from loopr.judge.scripted_client import MissingFixtureError, ScriptedJudgeClient
from loopr.models.common import JudgeCallType
from loopr.models.judge import JudgeRequest


def _request(call_id: str) -> JudgeRequest:
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.C1_OUTCOME,
        rubric_id="r1",
        rubric_text="text",
        inputs={"problem_statement": "x", "prefilter_flagged": False},
        created_round=1,
    )


def test_agent_judge_client_writes_envelope_and_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "pending_judge.json"
    client = AgentJudgeClient(path)
    request = _request("abc")

    result = client.ask(request)

    assert result is None
    assert path.exists()
    assert read_request(path) == request


def test_scripted_judge_client_raises_on_missing_fixture() -> None:
    client = ScriptedJudgeClient({})
    with pytest.raises(MissingFixtureError):
        client.ask(_request("no-such-fixture"))
