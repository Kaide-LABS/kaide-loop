"""CLI integration: init -> step (looped) -> emit. Acceptance B-1: a full greenfield run to
COMPLETE, driven entirely through the CLI's file-based exit-code contract, answering every judge
call and gate exactly as an invoking agent would."""

from __future__ import annotations

import json
from pathlib import Path

from loopr import exit_codes
from loopr.cli import main
from loopr.models.common import Verdict
from loopr.models.judge import JudgeResponse
from loopr.state.store import StateStore


def _answer_pending_judge(state_dir: Path, answer_path: Path) -> None:
    request = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
    call_type = request["call_type"]

    if call_type == "bf_classify":
        response = JudgeResponse(
            call_id=request["call_id"], verdict=Verdict.CONFORM, reason="looks fine"
        )
    elif call_type == "bf_relevance":
        candidates = request["inputs"]["candidate_files"]
        response = JudgeResponse(call_id=request["call_id"], selected_files=candidates, reason="all relevant")
    else:
        response = JudgeResponse(call_id=request["call_id"], passed=True, reason="ok")

    answer_path.write_text(response.model_dump_json(), encoding="utf-8")


def test_full_greenfield_run_reaches_complete(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    state_path = tmp_path / "state.json"
    answer_path = tmp_path / "answer.json"
    judge_response_path = tmp_path / "judge_response.json"

    code = main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)])
    assert code == exit_codes.OK

    store = StateStore(state_path)
    state_dir = store.dir

    # Seed the answers for the six conditions, one per QUESTION_REQUIRED round.
    answers = iter(
        [
            "on-call stops losing an hour to manual failover",
            "the page returns a 200 within 5 seconds",
            "mobile app is deferred -- not funded this quarter",
            "no boss-said constraints -- clean slate",
        ]
    )

    code = main(["step", "--state", str(state_path)])
    max_iterations = 100
    for _ in range(max_iterations):
        if code == exit_codes.COMPLETE:
            break

        if code == exit_codes.JUDGE_REQUIRED:
            _answer_pending_judge(state_dir, judge_response_path)
            code = main(
                ["step", "--state", str(state_path), "--judge-response", str(judge_response_path)]
            )
            continue

        if code == exit_codes.QUESTION_REQUIRED:
            try:
                answer_text = next(answers)
            except StopIteration:
                answer_text = "no further open questions"
            answer_path.write_text(answer_text, encoding="utf-8")
            code = main(["step", "--state", str(state_path), "--answer", str(answer_path)])
            continue

        if code == exit_codes.GATE_REQUIRED:
            meta = json.loads((state_dir / "pending_gate.json").read_text(encoding="utf-8"))
            gate_response: dict[str, bool | str] = {"confirmed": True}
            if meta["gate"] == "gate_2_boundary":
                gate_response["boundary_text"] = "this phase covers failover automation only"
            response_path = tmp_path / "gate_response.json"
            response_path.write_text(json.dumps(gate_response), encoding="utf-8")
            code = main(["step", "--state", str(state_path), "--gate-response", str(response_path)])
            continue

        raise AssertionError(f"unexpected exit code {code}")
    else:
        raise AssertionError("did not reach COMPLETE within max_iterations")

    final_state = store.load()
    assert len(final_state.condition_results) == 6
    assert all(r.overall for r in final_state.condition_results)

    emit_code = main(["emit", "--state", str(state_path)])
    assert emit_code == exit_codes.COMPLETE
    assert (repo / ".claude" / "loopr" / "baby_prd.md").exists()
    assert (repo / ".claude" / "loopr" / "context.md").exists()


def test_init_refuses_to_overwrite_existing_state(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    code = main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)])
    assert code == exit_codes.USAGE
