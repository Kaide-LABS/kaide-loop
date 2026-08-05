"""Log append/read/audit. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS6.5, SS7 guard G3, SS8
criterion 7 (both directions: a clean trace audits clean, and a planted bad record is caught).
"""

from __future__ import annotations

import json
from pathlib import Path

from loopr.dispatch.controller import decide
from loopr.dispatch.log import append_decision, audit_step10_calls, read_log
from loopr.models.common import DispatchTarget, Step10Warrant
from loopr.models.dispatch import DispatchState


def test_read_log_on_missing_file_returns_empty_list(tmp_path: Path) -> None:
    """A zero is visibly a zero, not an error."""
    assert read_log(tmp_path / "does-not-exist.jsonl") == []


def test_append_then_read_round_trips(tmp_path: Path) -> None:
    log_path = tmp_path / "dispatch-log.jsonl"
    state = DispatchState()
    decision = decide(state, artifacts_present=False, build_complete_present=False)
    append_decision(log_path, decision)

    records = read_log(log_path)
    assert len(records) == 1
    assert records[0]["target"] == DispatchTarget.STEP_10.value
    assert records[0]["step10_warrant"] == Step10Warrant.GREENFIELD_NO_ARTIFACTS.value
    assert "ts" in records[0]


def test_read_log_skips_blank_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "dispatch-log.jsonl"
    log_path.write_text('{"a": 1}\n\n{"a": 2}\n\n', encoding="utf-8")
    records = read_log(log_path)
    assert records == [{"a": 1}, {"a": 2}]


def test_log_is_append_only_and_diffable(tmp_path: Path) -> None:
    log_path = tmp_path / "dispatch-log.jsonl"
    state = DispatchState()
    decision_a = decide(state, artifacts_present=False, build_complete_present=False)
    append_decision(log_path, decision_a)
    decision_b = decide(state, artifacts_present=True, build_complete_present=False)
    append_decision(log_path, decision_b)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        payload = json.loads(line)
        assert list(payload.keys()) == sorted(payload.keys())


def test_decision_never_carries_a_timestamp_only_the_log_writer_adds_one() -> None:
    """models/dispatch.py SS3.3's rationale: DispatchDecision stays byte-stable / fixture-comparable
    with no field exclusions, because `ts` is not one of its fields at all."""
    state = DispatchState()
    decision = decide(state, artifacts_present=False, build_complete_present=False)
    assert "ts" not in decision.model_dump()


def test_audit_of_the_full_trace_finds_zero_step10_dispatches(tmp_path: Path) -> None:
    """SS8 criterion 7, direction one: after a normal build trace with real artifacts, the audit
    finds zero step10 calls and every one it does find (there are none) is trivially valid."""
    log_path = tmp_path / "dispatch-log.jsonl"
    state = DispatchState()
    for _ in range(3):
        decision = decide(state, artifacts_present=True, build_complete_present=False)
        append_decision(log_path, decision)

    records = read_log(log_path)
    entries = audit_step10_calls(records)
    assert entries == []


def test_audit_catches_a_planted_record_with_a_null_warrant(tmp_path: Path) -> None:
    """SS8 criterion 7, direction two: a planted record with target=loopr-step10 and
    step10_warrant=null must make the audit fail -- a check that has never failed has not been
    tested."""
    log_path = tmp_path / "dispatch-log.jsonl"
    planted = {
        "state_id": "s1_pre_step10",
        "target": "loopr-step10",
        "reason": "planted",
        "step10_warrant": None,
        "step10_declined_because": None,
        "build_round": 0,
        "ts": "2026-08-05T00:00:00Z",
    }
    log_path.write_text(json.dumps(planted, sort_keys=True) + "\n", encoding="utf-8")

    records = read_log(log_path)
    entries = audit_step10_calls(records)
    assert len(entries) == 1
    assert entries[0].valid is False
    assert entries[0].warrant is None


def test_audit_catches_a_planted_record_with_an_unrecognised_warrant(tmp_path: Path) -> None:
    log_path = tmp_path / "dispatch-log.jsonl"
    planted = {
        "state_id": "s1_pre_step10",
        "target": "loopr-step10",
        "reason": "planted",
        "step10_warrant": "uncertain_but_safe_default",
        "step10_declined_because": None,
        "build_round": 0,
        "ts": "2026-08-05T00:00:00Z",
    }
    log_path.write_text(json.dumps(planted, sort_keys=True) + "\n", encoding="utf-8")

    entries = audit_step10_calls(read_log(log_path))
    assert len(entries) == 1
    assert entries[0].valid is False


def test_audit_accepts_a_real_warranted_step10_record(tmp_path: Path) -> None:
    log_path = tmp_path / "dispatch-log.jsonl"
    state = DispatchState()
    decision = decide(state, artifacts_present=False, build_complete_present=False)
    append_decision(log_path, decision)

    entries = audit_step10_calls(read_log(log_path))
    assert len(entries) == 1
    assert entries[0].valid is True
    assert entries[0].warrant == Step10Warrant.GREENFIELD_NO_ARTIFACTS.value
