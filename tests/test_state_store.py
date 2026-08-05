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
    a malformed state file used to crash with an uncaught pydantic.ValidationError instead.

    CUSTOMIZATION_PHASE_3_SPEC.md SS5: schema_version bumped 1 -> 2 for the new `dispatch` field, so
    this payload must now carry schema_version=2 -- otherwise it would raise StateVersionError at the
    version gate before ever reaching the bad-`mode` validation this test actually means to exercise
    (StateVersionError is itself a StateLoadError, so the old payload would still "pass" here, just
    for the wrong reason -- see test_well_formed_v1_payload_raises_state_version_error below for the
    version-gate case, tested directly)."""
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps({"schema_version": 2, "mode": "not-a-real-mode", "repo_root": str(tmp_path)}),
        encoding="utf-8",
    )
    store = StateStore(path)
    with pytest.raises(StateLoadError):
        store.load()


def test_well_formed_v1_payload_raises_state_version_error(tmp_path: Path) -> None:
    """CUSTOMIZATION_PHASE_3_SPEC.md SS5: no migration path exists -- a well-formed v1 state file
    (valid in every way except its schema_version) must hard-fail, never be silently upgraded or
    reinterpreted. Demonstrated firing with a payload that is otherwise completely valid, so the
    failure is provably about the version gate and nothing else."""
    v1_state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path))
    payload = json.loads(v1_state.model_dump_json())
    payload["schema_version"] = 1
    del payload["dispatch"]  # a real v1 payload predates this field entirely
    path = tmp_path / "state.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    store = StateStore(path)
    with pytest.raises(StateVersionError):
        store.load()


def test_not_valid_json_raises_clean_loopr_error(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{not json at all", encoding="utf-8")
    store = StateStore(path)
    with pytest.raises(StateLoadError):
        store.load()


def test_customization_state_round_trips(tmp_path: Path) -> None:
    """CUSTOMIZATION_PHASE_1_SPEC.md SS2: "verify the new state field round-trips" -- checked
    directly rather than assumed."""
    from loopr.models.customization import CustomizationState, FidelityResult, TemplateSkeleton

    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path))
    state.customization = CustomizationState(
        step10_template_path=str(tmp_path / "STEP_10"),
        step10_skeleton=TemplateSkeleton(convention="all_caps", sections=["ROLE", "1. FIRST"]),
        step10_output_path=str(tmp_path / "out.md"),
        step10_fidelity=FidelityResult(
            structural_pass=True, judge_pass=True, overall=True, detail="ok"
        ),
    )
    store = StateStore(tmp_path / "state.json")
    store.save(state)
    reloaded = store.load()

    assert reloaded.customization is not None
    assert reloaded.customization.step10_skeleton is not None
    assert reloaded.customization.step10_skeleton.sections == ["ROLE", "1. FIRST"]
    assert reloaded.customization.step10_fidelity is not None
    assert reloaded.customization.step10_fidelity.overall is True


def test_step11_step12_customization_state_round_trips(tmp_path: Path) -> None:
    """CUSTOMIZATION_PHASE_2_SPEC.md SS2: step11_*/step12_* mirror step10_* exactly -- checked
    directly, same discipline as Phase 1's own round-trip test."""
    from loopr.models.customization import CustomizationState, FidelityResult, TemplateSkeleton

    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path))
    state.customization = CustomizationState(
        step10_template_path=str(tmp_path / "STEP_10"),
        step10_skeleton=TemplateSkeleton(convention="all_caps", sections=["ROLE", "1. FIRST"]),
        step10_output_path=str(tmp_path / "step10-out.md"),
        step10_fidelity=FidelityResult(structural_pass=True, judge_pass=True, overall=True, detail="ok"),
        step11_template_path=str(tmp_path / "STEP _11"),
        step11_skeleton=TemplateSkeleton(convention="markdown_h2", sections=["## ROLE"]),
        step11_output_path=str(tmp_path / "step11-out.md"),
        step11_fidelity=FidelityResult(structural_pass=True, judge_pass=True, overall=True, detail="ok11"),
        step12_template_path=str(tmp_path / "step_12"),
        step12_skeleton=TemplateSkeleton(convention="markdown_h2_h3", sections=["## ROLE", "### SUB"]),
        step12_output_path=str(tmp_path / "step12-out.md"),
        step12_fidelity=FidelityResult(structural_pass=True, judge_pass=True, overall=True, detail="ok12"),
    )
    store = StateStore(tmp_path / "state.json")
    store.save(state)
    reloaded = store.load()

    assert reloaded.customization is not None
    c = reloaded.customization
    assert c.step11_skeleton is not None and c.step11_skeleton.sections == ["## ROLE"]
    assert c.step11_fidelity is not None and c.step11_fidelity.detail == "ok11"
    assert c.step12_skeleton is not None and c.step12_skeleton.sections == ["## ROLE", "### SUB"]
    assert c.step12_fidelity is not None and c.step12_fidelity.detail == "ok12"


def test_dispatch_state_round_trips(tmp_path: Path) -> None:
    """CUSTOMIZATION_PHASE_3_SPEC.md SS1: `dispatch` is always present (non-optional, unlike
    `customization`/`brownfield`) and round-trips through save/load like every other field."""
    from loopr.models.common import CustomizationStep

    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path))
    assert state.dispatch is not None
    assert state.dispatch.active_step is None
    assert state.dispatch.build_round == 0
    assert state.dispatch.last_step12_verdict is None

    state.dispatch.active_step = CustomizationStep.STEP_11
    state.dispatch.build_round = 3
    store = StateStore(tmp_path / "state.json")
    store.save(state)
    reloaded = store.load()

    assert reloaded.dispatch.active_step == CustomizationStep.STEP_11
    assert reloaded.dispatch.build_round == 3
    assert reloaded.dispatch.last_step12_verdict is None
    assert reloaded == state
    assert reloaded.schema_version == 2


def test_customization_state_supports_step11_without_step10_populated(tmp_path: Path) -> None:
    """CUSTOMIZATION_PHASE_1_SPEC.md SS4.4's hard topology-independence constraint, concretely: a
    state customizing step11 need not have customized step10 in the SAME state at all (step10 may
    have been customized and executed via a wholly separate session/state file) -- step10_template_path
    /step10_skeleton must be constructible as absent, not required, or this legitimate case couldn't
    be represented. Regression for the model fix made while building CUSTOMIZATION_PHASE_2_SPEC.md."""
    from loopr.models.customization import CustomizationState, FidelityResult, TemplateSkeleton

    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path))
    state.customization = CustomizationState(
        step11_template_path=str(tmp_path / "STEP _11"),
        step11_skeleton=TemplateSkeleton(convention="markdown_h2", sections=["## ROLE"]),
        step11_output_path=str(tmp_path / "step11-out.md"),
        step11_fidelity=FidelityResult(structural_pass=True, judge_pass=True, overall=True, detail="ok"),
    )
    assert state.customization.step10_template_path is None
    assert state.customization.step10_skeleton is None

    store = StateStore(tmp_path / "state.json")
    store.save(state)
    reloaded = store.load()

    assert reloaded.customization is not None
    assert reloaded.customization.step10_template_path is None
    assert reloaded.customization.step10_skeleton is None
    assert reloaded.customization.step11_skeleton is not None
    assert reloaded.customization.step11_skeleton.sections == ["## ROLE"]
    assert reloaded == state
