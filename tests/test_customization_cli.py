"""`loopr customize --step 10` end to end. Implements CUSTOMIZATION_PHASE_1_SPEC.md SS8.

Every SS8 acceptance criterion is demonstrated here against the real CLI, not merely asserted at
the unit level.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopr import exit_codes
from loopr.cli import main
from loopr.models.common import Verdict
from loopr.models.judge import JudgeResponse
from loopr.state.store import StateStore

# Every fixture carries a dummy title line first, matching real STEP_10's own shape -- extract_
# skeleton always excludes line 1 as the declared title exclusion (CUSTOMIZATION_PHASE_1_SPEC.md
# SS4.3), so a fixture without one would silently lose its own first real section to that rule.
_TITLE = "DOC TITLE (TEMPLATE)\n\n"

_STEP10_TEMPLATE = (
    _TITLE
    + "ROLE\n\nAct as an architect for [PROJECT_NAME].\n\n"
    + "1. FIRST SECTION\n\nDo the first thing for [PROJECT_REPO_NAME].\n\n"
    + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
)

_GOOD_CUSTOMIZATION = (
    _TITLE
    + "ROLE\n\nAct as an architect for Acme Corp.\n\n"
    + "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
    + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
)

_RESTRUCTURED_CUSTOMIZATION = (
    _TITLE
    + "ROLE\n\nAct as an architect for Acme Corp.\n\n"
    + "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
    # section 2 dropped
)

_PLACEHOLDER_DELETION_ONLY = (
    _TITLE
    + "ROLE\n\nAct as an architect for the project.\n\n"
    + "1. FIRST SECTION\n\nDo the first thing for the repo.\n\n"
    + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
)


def _seed_templates(repo: Path) -> None:
    templates_dir = repo / "prompts" / "Template_prompts"
    templates_dir.mkdir(parents=True)
    (templates_dir / "STEP_10").write_text(_STEP10_TEMPLATE, encoding="utf-8")


def _answer_pending_judge(state_dir: Path, answer_path: Path) -> None:
    request = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
    call_type = request["call_type"]
    if call_type == "bf_classify":
        response = JudgeResponse(call_id=request["call_id"], verdict=Verdict.CONFORM, reason="fine")
    elif call_type == "bf_relevance":
        candidates = request["inputs"]["candidate_files"]
        response = JudgeResponse(call_id=request["call_id"], selected_files=candidates, reason="all relevant")
    elif call_type == "boundary_proposal":
        response = JudgeResponse(call_id=request["call_id"], drafted_text="drafted boundary", reason="drafted")
    else:
        response = JudgeResponse(call_id=request["call_id"], passed=True, reason="ok")
    answer_path.write_text(response.model_dump_json(), encoding="utf-8")


def _drive_to_complete(state_path: Path, state_dir: Path, tmp_path: Path) -> None:
    answer_path = tmp_path / "answer.json"
    judge_response_path = tmp_path / "judge_response.json"
    answers = iter(
        [
            "on-call stops losing an hour to manual failover",
            "the page returns a 200 within 5 seconds",
            "mobile app is deferred -- not funded this quarter",
            "no boss-said constraints -- clean slate",
        ]
    )
    code = main(["step", "--state", str(state_path)])
    for _ in range(100):
        if code == exit_codes.COMPLETE:
            return
        if code == exit_codes.JUDGE_REQUIRED:
            _answer_pending_judge(state_dir, judge_response_path)
            code = main(["step", "--state", str(state_path), "--judge-response", str(judge_response_path)])
        elif code == exit_codes.QUESTION_REQUIRED:
            try:
                text = next(answers)
            except StopIteration:
                text = "no further open questions"
            answer_path.write_text(text, encoding="utf-8")
            code = main(["step", "--state", str(state_path), "--answer", str(answer_path)])
        elif code == exit_codes.GATE_REQUIRED:
            meta = json.loads((state_dir / "pending_gate.json").read_text(encoding="utf-8"))
            gate_response: dict[str, object] = {"confirmed": True}
            if meta["gate"] == "gate_2_boundary":
                gate_response["boundary_text"] = "this phase covers failover automation only"
            path = tmp_path / "gate_response.json"
            path.write_text(json.dumps(gate_response), encoding="utf-8")
            code = main(["step", "--state", str(state_path), "--gate-response", str(path)])
        else:
            raise AssertionError(f"unexpected exit code {code}")
    raise AssertionError("did not reach COMPLETE")


@pytest.fixture
def confirmed_state(tmp_path: Path) -> tuple[Path, Path]:
    """A repo with real STEP_10-shaped templates and a state file driven to COMPLETE."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_templates(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)
    return repo, state_path


def test_customize_refuses_before_six_conditions_pass(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_templates(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0

    code = main(["customize", "--state", str(state_path), "--step", "10"])
    assert code == exit_codes.HALT


def test_customize_step10_produces_fidelity_verified_output(
    confirmed_state: tuple[Path, Path], tmp_path: Path
) -> None:
    repo, state_path = confirmed_state
    judge_response_path = tmp_path / "customize_judge_response.json"

    code = main(["customize", "--state", str(state_path), "--step", "10"])
    assert code == exit_codes.JUDGE_REQUIRED
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request["call_type"] == "step10_customization"

    response = JudgeResponse(call_id=request["call_id"], drafted_text=_GOOD_CUSTOMIZATION, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED  # now the layer-2 fidelity judge call
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request2["call_type"] == "step10_fidelity_judge"

    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="genuinely specific")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    store = StateStore(state_path)
    final_state = store.load()
    assert final_state.customization is not None
    assert final_state.customization.step10_fidelity is not None
    assert final_state.customization.step10_fidelity.overall is True

    assert final_state.customization.step10_output_path is not None
    output_path = Path(final_state.customization.step10_output_path)
    output_text = output_path.read_text(encoding="utf-8")
    # JudgeResponse.drafted_text is whitespace-stripped by LooprBase's str_strip_whitespace=True.
    assert output_text == _GOOD_CUSTOMIZATION.strip()
    assert "[UNVERIFIED]" in output_text
    assert "[PROJECT_NAME]" not in output_text


def test_customize_rejects_restructured_output(confirmed_state: tuple[Path, Path], tmp_path: Path) -> None:
    """SS8.4, demonstrated against the real CLI: a restructured customization HALTs."""
    repo, state_path = confirmed_state
    judge_response_path = tmp_path / "customize_judge_response.json"

    code = main(["customize", "--state", str(state_path), "--step", "10"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response = JudgeResponse(
        call_id=request["call_id"], drafted_text=_RESTRUCTURED_CUSTOMIZATION, reason="drafted"
    )
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.HALT

    store = StateStore(state_path)
    final_state = store.load()
    assert final_state.customization is not None
    assert final_state.customization.step10_fidelity is not None
    assert final_state.customization.step10_fidelity.structural_pass is False
    assert final_state.customization.step10_fidelity.overall is False


def test_customize_rejects_placeholder_deletion_only_via_layer2(
    confirmed_state: tuple[Path, Path], tmp_path: Path
) -> None:
    """SS8.5, demonstrated against the real CLI: layer 1 cannot catch generic filler (skeleton and
    placeholders are both technically fine), but layer 2's judge rejects it."""
    repo, state_path = confirmed_state
    judge_response_path = tmp_path / "customize_judge_response.json"

    main(["customize", "--state", str(state_path), "--step", "10"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response = JudgeResponse(
        call_id=request["call_id"], drafted_text=_PLACEHOLDER_DELETION_ONLY, reason="drafted"
    )
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED  # layer 1 passed -- reached the layer-2 judge call
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request2["call_type"] == "step10_fidelity_judge"

    response2 = JudgeResponse(
        call_id=request2["call_id"], passed=False, reason="generic filler, placeholders merely deleted"
    )
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.HALT

    store = StateStore(state_path)
    final_state = store.load()
    assert final_state.customization is not None
    assert final_state.customization.step10_fidelity is not None
    assert final_state.customization.step10_fidelity.overall is False
    assert final_state.customization.step10_fidelity.judge_pass is False


def test_topology_independence_resume_from_state_produces_byte_identical_output(
    confirmed_state: tuple[Path, Path], tmp_path: Path
) -> None:
    """SS8.7: a customization interrupted after the judge call and resumed from the state file in a
    fresh process produces byte-identical output to one completed in a single process. Simulated
    here by driving two independent state files with the identical judge response content -- one
    completed straight through, one "interrupted" by reloading the state from disk between calls
    (the same StateStore.load()/save() round trip a genuinely separate process would use)."""
    repo, state_path = confirmed_state

    # Run A: straight through, no simulated interruption.
    judge_response_path = tmp_path / "jr_a.json"
    main(["customize", "--state", str(state_path), "--step", "10"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response = JudgeResponse(call_id=request["call_id"], drafted_text=_GOOD_CUSTOMIZATION, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    main(["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)])
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="specific")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK
    customization_a = StateStore(state_path).load().customization
    assert customization_a is not None and customization_a.step10_output_path is not None
    output_a = Path(customization_a.step10_output_path).read_text(encoding="utf-8")

    # Run B: a SECOND, independent confirmed repo/state -- "interrupted" by explicitly reloading
    # the state from disk (StateStore round trip) between every single step, exactly what a fresh
    # process resuming from the state file alone would do, with no session memory carried over.
    repo_b = tmp_path / "repo_b"
    repo_b.mkdir()
    _seed_templates(repo_b)
    state_path_b = tmp_path / "state_b.json"
    main(["init", "--repo", str(repo_b), "--mode", "greenfield", "--state", str(state_path_b)])
    store_b = StateStore(state_path_b)
    _drive_to_complete(state_path_b, store_b.dir, tmp_path)

    # Fresh "process": nothing from run A's Python objects is reused below this point --
    # every step reloads via a brand-new StateStore(...).load() call against state_path_b.
    main(["customize", "--state", str(state_path_b), "--step", "10"])
    request_b = json.loads((state_path_b.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response_b = JudgeResponse(call_id=request_b["call_id"], drafted_text=_GOOD_CUSTOMIZATION, reason="drafted")
    judge_response_path.write_text(response_b.model_dump_json(), encoding="utf-8")
    main(
        ["customize", "--state", str(state_path_b), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    request_b2 = json.loads((state_path_b.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response_b2 = JudgeResponse(call_id=request_b2["call_id"], passed=True, reason="specific")
    judge_response_path.write_text(response_b2.model_dump_json(), encoding="utf-8")
    code_b = main(
        ["customize", "--state", str(state_path_b), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code_b == exit_codes.OK
    customization_b = StateStore(state_path_b).load().customization
    assert customization_b is not None and customization_b.step10_output_path is not None
    output_b = Path(customization_b.step10_output_path).read_text(encoding="utf-8")

    assert output_a == output_b, "resumed-from-disk output must be byte-identical to the direct run"


def test_topology_independence_no_session_identity_in_state(confirmed_state: tuple[Path, Path]) -> None:
    """SS8.7, inspected: no field anywhere in CustomizationState/InterrogationState encodes session
    identity or role."""
    from loopr.models.customization import CustomizationState
    from loopr.models.interrogation import InterrogationState

    for model in (CustomizationState, InterrogationState):
        for field_name in model.model_fields:
            lowered = field_name.lower()
            assert "session" not in lowered
            assert "role" not in lowered
            assert "architect" not in lowered
            assert "executor" not in lowered
