"""Envelope (de)serialisation and deterministic call_id derivation (SS6.2.3)."""

from __future__ import annotations

from pathlib import Path

from loopr.judge.envelope import digest, make_call_id, read_request, write_request
from loopr.models.common import JudgeCallType
from loopr.models.judge import JudgeRequest


def test_call_id_is_deterministic() -> None:
    inputs = {"problem_statement": "x", "prefilter_flagged": False}
    id1 = make_call_id("c1_outcome", 1, inputs)
    id2 = make_call_id("c1_outcome", 1, inputs)
    assert id1 == id2


def test_call_id_changes_with_round() -> None:
    inputs = {"problem_statement": "x", "prefilter_flagged": False}
    assert make_call_id("c1_outcome", 1, inputs) != make_call_id("c1_outcome", 2, inputs)


def test_call_id_changes_with_inputs() -> None:
    a = make_call_id("c1_outcome", 1, {"problem_statement": "x", "prefilter_flagged": False})
    b = make_call_id("c1_outcome", 1, {"problem_statement": "y", "prefilter_flagged": False})
    assert a != b


def test_digest_is_sha256_hex() -> None:
    value = digest("hello")
    assert len(value) == 64
    assert all(c in "0123456789abcdef" for c in value)


def test_write_and_read_request_roundtrip(tmp_path: Path) -> None:
    request = JudgeRequest(
        call_id="abc",
        call_type=JudgeCallType.C1_OUTCOME,
        rubric_id="r1",
        rubric_text="text",
        inputs={"problem_statement": "x", "prefilter_flagged": False},
        created_round=1,
    )
    path = tmp_path / "pending_judge.json"
    write_request(path, request)
    loaded = read_request(path)
    assert loaded == request
