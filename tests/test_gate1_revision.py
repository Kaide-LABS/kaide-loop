"""Regression: Gate 1's "confirm or correct" -- correct used to be a complete no-op.

Traced precisely: apply_gate_response's only logic for any gate other than GATE_2_BOUNDARY was
"if confirmed and digest matches: mark confirmed" -- a decline/correction (confirmed=False) did
nothing at all, not even storing the amendment note. loopr-PRD.md promises Gate 1 lets the user
"confirm or correct"; this is one of the three headline acceptance signals (the TL;DR moment).

Design: a Gate 1 revision resets the relevant field(s) and routes back through the SAME
structural-then-judge evaluation any fresh answer to C1/C2/C3 gets -- verified against
checks/conditions.py's dedup-by-exact-value matching, not assumed. Boundary (condition 4) stays the
deliberate exception: "judged once, at proposal time... not re-litigated" per
docs/stopping-test-spec.md.
"""

from __future__ import annotations

import json
from pathlib import Path

from loopr import exit_codes
from loopr.checks.conditions import evaluate_all
from loopr.cli import main
from loopr.gates.gates import (
    GateResponse,
    apply_gate_response,
    build_gate_payload,
    gate_is_satisfied,
    render_gate_1_body,
    request_gate,
)
from loopr.models.common import GateId
from loopr.models.interrogation import AcceptanceCriterion, InterrogationState
from loopr.models.judge import JudgeResponse
from loopr.state.store import StateStore


def test_gate1_problem_statement_revision_updates_state(greenfield_state: InterrogationState) -> None:
    greenfield_state.problem_statement = "the wrong outcome, stated badly"
    payload = build_gate_payload(
        GateId.GATE_1_BABY_PRD, "t", render_gate_1_body(greenfield_state, "tldr")
    )
    request_gate(greenfield_state, payload)

    response = GateResponse(
        gate=GateId.GATE_1_BABY_PRD,
        confirmed=False,
        payload_digest=payload.digest,
        problem_statement_revision="the actually-correct outcome, stated properly",
        amendment="the original TL;DR misstated the outcome",
    )
    apply_gate_response(greenfield_state, response)

    assert greenfield_state.problem_statement == "the actually-correct outcome, stated properly"
    assert greenfield_state.gates[GateId.GATE_1_BABY_PRD].user_amendment == (
        "the original TL;DR misstated the outcome"
    )


def test_gate1_revision_never_silently_discarded_even_without_confirm(
    greenfield_state: InterrogationState,
) -> None:
    """The bug this regression targets directly: confirmed=False used to mean nothing happened."""
    payload = build_gate_payload(
        GateId.GATE_1_BABY_PRD, "t", render_gate_1_body(greenfield_state, "tldr")
    )
    request_gate(greenfield_state, payload)

    response = GateResponse(
        gate=GateId.GATE_1_BABY_PRD,
        confirmed=False,
        payload_digest=payload.digest,
        acceptance_criteria_revision=["the corrected criterion, still not confirmed"],
    )
    apply_gate_response(greenfield_state, response)

    assert [c.text for c in greenfield_state.acceptance_criteria] == [
        "the corrected criterion, still not confirmed"
    ]


def test_gate1_revision_requires_fresh_confirm_even_if_confirmed_true_was_sent(
    greenfield_state: InterrogationState,
) -> None:
    """A revision + confirmed=True in the same response must NOT mark the gate confirmed -- a
    revision always requires a subsequent, genuine re-confirm once conditions re-pass."""
    payload = build_gate_payload(
        GateId.GATE_1_BABY_PRD, "t", render_gate_1_body(greenfield_state, "tldr")
    )
    request_gate(greenfield_state, payload)

    response = GateResponse(
        gate=GateId.GATE_1_BABY_PRD,
        confirmed=True,
        payload_digest=payload.digest,
        problem_statement_revision="a corrected outcome",
    )
    apply_gate_response(greenfield_state, response)

    assert greenfield_state.gates[GateId.GATE_1_BABY_PRD].confirmed is False
    assert gate_is_satisfied(greenfield_state, GateId.GATE_1_BABY_PRD, payload.digest) is False


def test_revision_routes_through_structural_check_not_a_blind_overwrite(
    greenfield_state: InterrogationState,
) -> None:
    """A revision that would fail condition 2's structural check (no observable predicate) must NOT
    sail through just because it arrived via a Gate 1 amendment field."""
    greenfield_state.acceptance_criteria = [AcceptanceCriterion(text="it returns a 200")]
    payload = build_gate_payload(
        GateId.GATE_1_BABY_PRD, "t", render_gate_1_body(greenfield_state, "tldr")
    )
    request_gate(greenfield_state, payload)

    response = GateResponse(
        gate=GateId.GATE_1_BABY_PRD,
        confirmed=False,
        payload_digest=payload.digest,
        acceptance_criteria_revision=["it works well"],  # no observable predicate -- vague
    )
    apply_gate_response(greenfield_state, response)

    outcome = evaluate_all(greenfield_state)
    c2_result = next(r for r in outcome.results if r.condition.value == "c2_acceptance")
    assert c2_result.overall is False, (
        "a structurally vague revision must fail condition 2's structural check, exactly like any "
        "fresh vague answer would -- it must not be trusted just because it arrived as a revision"
    )


def _drive(state_path: Path, state_dir: Path, tmp_path: Path, expect_gate1_revision: bool) -> None:
    answer_path = tmp_path / "answer.json"
    judge_response_path = tmp_path / "judge_response.json"
    gate_response_path = tmp_path / "gate_response.json"
    answers = iter(
        [
            "on-call stops losing an hour to manual failover",
            "the page shows a 200 within 5 seconds",
            "mobile app is deferred -- not funded this quarter",
            "no boss-said constraints -- clean slate",
        ]
    )
    revised_once = not expect_gate1_revision  # if we don't want a revision, treat it as already done

    code = main(["step", "--state", str(state_path)])
    for _ in range(60):
        if code == exit_codes.COMPLETE:
            return
        if code == exit_codes.JUDGE_REQUIRED:
            request = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
            call_type = request["call_type"]
            if call_type == "boundary_proposal":
                response = JudgeResponse(
                    call_id=request["call_id"],
                    drafted_text="this phase covers failover automation only",
                    reason="drafted",
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
        elif code == exit_codes.GATE_REQUIRED:
            meta = json.loads((state_dir / "pending_gate.json").read_text(encoding="utf-8"))
            if meta["gate"] == "gate_1_baby_prd" and not revised_once:
                gate_response_path.write_text(
                    json.dumps(
                        {
                            "confirmed": False,
                            "problem_statement_revision": (
                                "on-call stops losing an hour to manual failover, corrected: "
                                "specifically the 3am pages"
                            ),
                            "amendment": "the original TL;DR missed the 3am-specific framing",
                        }
                    ),
                    encoding="utf-8",
                )
                revised_once = True
            else:
                gate_response_path.write_text(json.dumps({"confirmed": True}), encoding="utf-8")
            code = main(
                ["step", "--state", str(state_path), "--gate-response", str(gate_response_path)]
            )
        else:
            raise AssertionError(f"unexpected exit code {code}")
    raise AssertionError("did not reach COMPLETE")


def test_full_run_gate1_correction_lands_in_emitted_artifact(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)

    _drive(state_path, store.dir, tmp_path, expect_gate1_revision=True)

    final_state = store.load()
    assert "corrected: specifically the 3am pages" in (final_state.problem_statement or "")

    emit_code = main(["emit", "--state", str(state_path)])
    assert emit_code == exit_codes.COMPLETE
    baby_prd = (repo / ".claude" / "loopr" / "baby_prd.md").read_text(encoding="utf-8")
    assert "corrected: specifically the 3am pages" in baby_prd, (
        "the Gate 1 correction must actually land in the emitted artifact, not be silently discarded"
    )
