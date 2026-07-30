"""State persistence: atomicity, forward-reference resolution, schema-version guard.

Acceptance A-5 (forward refs), B-5 (crash safety).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopr.errors import StateLoadError
from loopr.judge.envelope import digest
from loopr.models.common import JudgeCallType, Mode, NoteSource
from loopr.models.interrogation import ContextNote, InterrogationState
from loopr.models.judge import JudgeExchange, JudgeRequest, JudgeResponse
from loopr.state.store import StateStore, StateVersionError


def test_forward_references_resolved() -> None:
    assert InterrogationState.__pydantic_complete__ is True


def test_roundtrip_through_json(tmp_path: Path) -> None:
    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path))
    store = StateStore(tmp_path / "state.json")
    store.save(state)
    loaded = store.load()
    assert loaded == state


def test_save_is_atomic_no_leftover_tmp(tmp_path: Path) -> None:
    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path))
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.save(state)
    assert path.exists()
    assert not (tmp_path / "state.json.tmp").exists()


def test_save_output_is_sorted_and_diffable(tmp_path: Path) -> None:
    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path))
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    keys = list(payload.keys())
    assert keys == sorted(keys)


def test_unrecognised_schema_version_raises(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
    store = StateStore(path)
    with pytest.raises(StateVersionError):
        store.load()


def test_reload_after_mutation_resumes_identically(tmp_path: Path) -> None:
    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path))
    state.problem_statement = "on-call stops losing an hour to manual failover"
    state.round = 3
    store = StateStore(tmp_path / "state.json")
    store.save(state)
    reloaded = store.load()
    assert reloaded.problem_statement == state.problem_statement
    assert reloaded.round == 3


def test_old_envelope_version_record_still_loads_after_scope_amendment(tmp_path: Path) -> None:
    """Regression: check_scope must validate a historical JudgeRequest against the ALLOWED_INPUTS
    that was current AT ITS OWN envelope_version, not today's live (possibly widened) scope --
    otherwise a scope amendment permanently breaks loading/replaying any state file recorded before
    it, exactly what blocked the brownfield proof run's own replay/emit verification."""
    v1_request = JudgeRequest(
        call_id="deadbeefdeadbeef",
        call_type=JudgeCallType.C5_SOFT_CONTEXT,
        rubric_id="c5_soft_context_v1",
        rubric_text="old rubric",
        inputs={"context_note": "old-scope note", "acceptance_criteria": []},
        created_round=1,
        envelope_version=1,
    )
    v1_response = JudgeResponse(call_id=v1_request.call_id, passed=True, reason="genuine")
    exchange = JudgeExchange(
        request=v1_request,
        response=v1_response,
        request_sha256=digest(v1_request.model_dump_json()),
        response_sha256=digest(v1_response.model_dump_json()),
        answered_at_round=1,
    )

    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path))
    state.context_notes = [ContextNote(text="old-scope note", source=NoteSource.STATED)]
    state.judge_log = [exchange]

    store = StateStore(tmp_path / "state.json")
    store.save(state)
    reloaded = store.load()

    assert reloaded.judge_log[0].request.envelope_version == 1
    assert reloaded.judge_log[0].request.inputs == {
        "context_note": "old-scope note",
        "acceptance_criteria": [],
    }


def test_corrupt_state_file_raises_clean_loopr_error_not_raw_traceback(tmp_path: Path) -> None:
    """Regression: every other failure mode in this module maps to a clean LooprError/exit code --
    a malformed state file used to crash with an uncaught pydantic.ValidationError instead."""
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps({"schema_version": 1, "mode": "not-a-real-mode", "repo_root": str(tmp_path)}),
        encoding="utf-8",
    )
    store = StateStore(path)
    with pytest.raises(StateLoadError):
        store.load()


def test_not_valid_json_raises_clean_loopr_error(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json at all", encoding="utf-8")
    store = StateStore(path)
    with pytest.raises(StateLoadError):
        store.load()
