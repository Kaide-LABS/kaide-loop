"""State persistence: atomicity, forward-reference resolution, schema-version guard.

Acceptance A-5 (forward refs), B-5 (crash safety).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopr.models.common import Mode
from loopr.models.interrogation import InterrogationState
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
