"""Regression: boundary-proposal drafting (FIX 1) and touched-surface timing (FIX 2).

Traced live: loopr-PRD.md SS A3 says loopr "analyzes and proposes a boundary" before asking for
confirmation, but no code ever drafted one -- Gate 2 rendered empty unless the user supplied
boundary_text themselves. Separately, touched-surface discovery was gated on the boundary being
already confirmed/declined, so it only populated on a LATER step, changing Gate 2's payload digest
and forcing it to re-fire a second time. Both fixed together: boundary drafting and touched-surface
discovery both run upstream of Gate 2's first render.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from loopr import exit_codes
from loopr.cli import main
from loopr.models.common import Verdict
from loopr.models.judge import JudgeResponse
from loopr.state.store import StateStore


def _commit(repo_root: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo_root, check=True)


def _drive_to_first_gate(state_path: Path, state_dir: Path, tmp_path: Path) -> dict[str, object]:
    """Drives a fresh brownfield run through C1-C3 and returns the FIRST Gate 2 payload metadata
    seen -- along with the rendered body, read by the caller."""
    answer_path = tmp_path / "answer.json"
    judge_response_path = tmp_path / "judge_response.json"
    answers = iter(
        [
            "existing code gets a consistent retry pattern applied everywhere it's needed",
            "a request retried under this pattern returns 200 within 3 attempts",
            "changing the retry backoff curve is deferred -- not this phase",
        ]
    )

    code = main(["step", "--state", str(state_path)])
    for _ in range(50):
        if code == exit_codes.GATE_REQUIRED:
            meta: dict[str, object] = json.loads(
                (state_dir / "pending_gate.json").read_text(encoding="utf-8")
            )
            return meta
        if code == exit_codes.QUESTION_REQUIRED:
            answer_path.write_text(next(answers), encoding="utf-8")
            code = main(["step", "--state", str(state_path), "--answer", str(answer_path)])
        elif code == exit_codes.JUDGE_REQUIRED:
            request = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
            call_type = request["call_type"]
            if call_type == "boundary_proposal":
                response = JudgeResponse(
                    call_id=request["call_id"],
                    drafted_text="loopr-drafted: this phase covers the retry-pattern scope only",
                    reason="drafted from confirmed fields",
                )
            elif call_type == "bf_relevance":
                candidates = request["inputs"]["candidate_files"]
                response = JudgeResponse(
                    call_id=request["call_id"], selected_files=candidates, reason="all relevant"
                )
            elif call_type == "bf_classify":
                response = JudgeResponse(
                    call_id=request["call_id"], verdict=Verdict.CONFORM, reason="looks fine"
                )
            else:
                response = JudgeResponse(call_id=request["call_id"], passed=True, reason="ok")
            judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
            code = main(
                ["step", "--state", str(state_path), "--judge-response", str(judge_response_path)]
            )
        else:
            raise AssertionError(f"unexpected exit code {code} before Gate 2")
    raise AssertionError("did not reach Gate 2")


def _brownfield_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in ("a", "b", "c"):
        (repo / f"{name}.py").write_text("@shared_pattern\ndef call():\n    pass\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    _commit(repo, "initial")
    return repo


def test_first_gate_2_shows_drafted_boundary_and_touched_surface_together(tmp_path: Path) -> None:
    repo = _brownfield_repo(tmp_path)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "brownfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    state_dir = store.dir

    meta = _drive_to_first_gate(state_path, state_dir, tmp_path)
    assert meta["gate"] == "gate_2_boundary"

    body = (state_dir / "pending_gate.md").read_text(encoding="utf-8")
    assert "loopr-drafted: this phase covers the retry-pattern scope only" in body, (
        "Gate 2's first render must show real, loopr-drafted boundary content, not an empty section "
        "the user has to author themselves"
    )
    assert "## Proposed touched surface (brownfield)" in body
    assert "a.py" in body or "b.py" in body or "c.py" in body, (
        "the touched-surface list must already be populated on Gate 2's FIRST render, not appear "
        "only after a separate confirm step"
    )


def test_gate_2_fires_exactly_once_in_a_typical_brownfield_run(tmp_path: Path) -> None:
    repo = _brownfield_repo(tmp_path)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "brownfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    state_dir = store.dir

    _drive_to_first_gate(state_path, state_dir, tmp_path)

    gate_2_fire_count = 0
    answer_path = tmp_path / "answer.json"
    judge_response_path = tmp_path / "judge_response.json"
    gate_response_path = tmp_path / "gate_response.json"
    answers = iter(["no further open questions"] * 5)

    code = exit_codes.GATE_REQUIRED
    for _ in range(100):
        if code == exit_codes.GATE_REQUIRED:
            meta = json.loads((state_dir / "pending_gate.json").read_text(encoding="utf-8"))
            if meta["gate"] == "gate_2_boundary":
                gate_2_fire_count += 1
            gate_response_path.write_text(json.dumps({"confirmed": True}), encoding="utf-8")
            code = main(
                ["step", "--state", str(state_path), "--gate-response", str(gate_response_path)]
            )
        elif code == exit_codes.JUDGE_REQUIRED:
            request = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
            call_type = request["call_type"]
            if call_type == "bf_classify":
                response = JudgeResponse(
                    call_id=request["call_id"], verdict=Verdict.CONFORM, reason="looks fine"
                )
            elif call_type == "bf_relevance":
                candidates = request["inputs"]["candidate_files"]
                response = JudgeResponse(
                    call_id=request["call_id"], selected_files=candidates, reason="all relevant"
                )
            else:
                response = JudgeResponse(call_id=request["call_id"], passed=True, reason="ok")
            judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
            code = main(
                ["step", "--state", str(state_path), "--judge-response", str(judge_response_path)]
            )
        elif code == exit_codes.QUESTION_REQUIRED:
            answer_path.write_text(next(answers), encoding="utf-8")
            code = main(["step", "--state", str(state_path), "--answer", str(answer_path)])
        elif code == exit_codes.COMPLETE:
            break
        else:
            raise AssertionError(f"unexpected exit code {code}")
    else:
        raise AssertionError("did not reach COMPLETE")

    assert gate_2_fire_count == 1, f"Gate 2 fired {gate_2_fire_count} times, expected exactly once"


def test_judge_response_shape_rejects_drafted_text_with_another_field() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        JudgeResponse(call_id="x", passed=True, drafted_text="also drafted", reason="bad")


def test_judge_response_shape_allows_drafted_text_alone() -> None:
    response = JudgeResponse(call_id="x", drafted_text="a boundary draft", reason="ok")
    assert response.drafted_text == "a boundary draft"
