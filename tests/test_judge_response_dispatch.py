"""Regression: FIX 3 -- a preloaded judge response must never be silently discarded.

step()'s brownfield precondition block (relevance discovery, pattern classification) runs
unconditionally at the top of every invocation, ahead of the condition-evaluation section a
condition-level judge call (e.g. C5) lives in. ResumingJudgeClient only consumes its one preloaded
response if it matches the FIRST judge.ask() call made inside that invocation -- if a brownfield
classification call is still pending and gets asked first, a response meant for a different, already
-issued pending request used to be thrown away silently: never applied, never logged, no error. This
reproduces that exact interleaving against the real CLI and confirms it is now a hard, logged error.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from loopr import exit_codes
from loopr.cli import main
from loopr.models.common import Verdict
from loopr.models.judge import JudgeResponse
from loopr.state.store import StateStore


def _commit(repo_root: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo_root, check=True)


def _answer_condition_questions(state_path: Path, tmp_path: Path) -> int:
    answer_path = tmp_path / "answer.json"
    answers = iter(
        [
            "existing code gets a consistent retry pattern applied everywhere it's needed",
            "a request retried under this pattern returns 200 within 3 attempts",
            "changing the retry backoff curve is deferred -- not this phase",
        ]
    )
    code = main(["step", "--state", str(state_path)])
    while code == exit_codes.QUESTION_REQUIRED:
        answer_path.write_text(next(answers), encoding="utf-8")
        code = main(["step", "--state", str(state_path), "--answer", str(answer_path)])
        if code == exit_codes.JUDGE_REQUIRED:
            break
    return code


def test_mismatched_judge_response_is_a_hard_error_not_a_silent_drop(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in ("a", "b", "c"):
        (repo / f"{name}.py").write_text(
            "@shared_pattern\ndef call():\n    pass\n", encoding="utf-8"
        )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    _commit(repo, "initial")

    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "brownfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    state_dir = store.dir

    # Drive C1-C3 answers until a judge call is required (C1's outcome judge).
    judge_response_path = tmp_path / "judge_response.json"

    def answer_pending_judge() -> int:
        request = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
        call_type = request["call_type"]
        if call_type == "bf_relevance":
            candidates = request["inputs"]["candidate_files"]
            response = JudgeResponse(
                call_id=request["call_id"], selected_files=candidates, reason="all relevant"
            )
        elif call_type == "bf_classify":
            response = JudgeResponse(
                call_id=request["call_id"], verdict=Verdict.CONFORM, reason="looks fine"
            )
        elif call_type == "boundary_proposal":
            response = JudgeResponse(
                call_id=request["call_id"], drafted_text="drafted boundary text", reason="drafted"
            )
        else:
            response = JudgeResponse(call_id=request["call_id"], passed=True, reason="ok")
        judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
        return main(["step", "--state", str(state_path), "--judge-response", str(judge_response_path)])

    answer_path = tmp_path / "answer.json"
    gate_response_path = tmp_path / "gate_response.json"
    answers = iter(
        [
            "existing code gets a consistent retry pattern applied everywhere it's needed",
            "a request retried under this pattern returns 200 within 3 attempts",
            "changing the retry backoff curve is deferred -- not this phase",
        ]
    )
    code = main(["step", "--state", str(state_path)])
    for _ in range(50):
        if code == exit_codes.JUDGE_REQUIRED:
            request = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
            if request["call_type"] == "bf_classify":
                break
            code = answer_pending_judge()
        elif code == exit_codes.QUESTION_REQUIRED:
            answer_path.write_text(next(answers), encoding="utf-8")
            code = main(["step", "--state", str(state_path), "--answer", str(answer_path)])
        elif code == exit_codes.GATE_REQUIRED:
            gate_response_path.write_text(json.dumps({"confirmed": True}), encoding="utf-8")
            code = main(
                ["step", "--state", str(state_path), "--gate-response", str(gate_response_path)]
            )
        else:
            raise AssertionError(f"unexpected exit code {code} before the classify stage")
    else:
        raise AssertionError("did not reach a pending bf_classify judge call")

    pending = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
    assert pending["call_type"] == "bf_classify"

    # This is the reproduction: supply a response for a call_id that is NOT the currently pending
    # bf_classify request (as if the caller thought a different, e.g. condition-level, call was
    # still open). The old behavior silently wrote a fresh pending request and discarded this
    # response with no error. It must now be a hard, logged LooprError.
    state_before = store.load()
    judge_log_len_before = len(state_before.judge_log)

    bogus_response = JudgeResponse(call_id="0" * 16, passed=True, reason="answering the wrong call")
    judge_response_path.write_text(bogus_response.model_dump_json(), encoding="utf-8")
    code = main(["step", "--state", str(state_path), "--judge-response", str(judge_response_path)])

    assert code == exit_codes.HALT
    state_after = store.load()
    assert len(state_after.judge_log) == judge_log_len_before, (
        "the mismatched response must not be silently applied to any request"
    )
    # The real pending classify request must still be intact and answerable normally.
    still_pending = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
    assert still_pending["call_type"] == "bf_classify"
