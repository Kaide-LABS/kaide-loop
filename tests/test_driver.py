"""Real, subprocess-level tests for `.claude/skills/loopr/scripts/driver.py` -- the mechanical half
of the loopr-loop-driver build (.claude/loopr-loop-driver/baby_prd.md). Invokes the actual script via
subprocess, exactly as a live Claude Code session would from Bash, rather than importing its
functions and mocking the CLI -- the acceptance criteria this build is graded against are about real
exit-code handling and real log output, not internal call shapes.

Covers baby_prd.md's confirmed acceptance criteria 1, 2 (the HALT stop condition; the other two stop
conditions are judgment calls this script never makes itself -- see test_log_stop_records_the_two_
judgment_based_stop_conditions), and 4 (grep-verifiable zero-heuristics, test_driver_script_has_no_
judgment_logic below).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from loopr.cli import main as loopr_main
from loopr import exit_codes

REPO_ROOT = Path(__file__).resolve().parent.parent
DRIVER_SCRIPT = REPO_ROOT / ".claude" / "skills" / "loopr" / "scripts" / "driver.py"


def _run_driver(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(DRIVER_SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _init_state(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    state_path = tmp_path / "state.json"
    code = loopr_main(
        [
            "init",
            "--repo",
            str(repo),
            "--mode",
            "greenfield",
            "--state",
            str(state_path),
        ]
    )
    assert code == exit_codes.OK
    return state_path


def _driver_log_records(state_path: Path) -> list[dict[str, object]]:
    log_path = state_path.parent / "driver-log.jsonl"
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_driver_script_has_no_judgment_logic() -> None:
    """Acceptance criterion 4, literally: grep the driver's own code for the absence of any judgment
    logic. It must never call an LLM, never import loopr's judge/interrogation/gates modules, and
    never branch on decision TEXT (reason / step10_declined_because) -- only on structured exit
    codes and the small set of DispatchDecision fields the two safety guards compare for equality."""
    source = DRIVER_SCRIPT.read_text(encoding="utf-8")
    forbidden_imports = [
        "loopr.judge",
        "loopr.interrogation",
        "loopr.gates",
        "anthropic",
        "openai",
    ]
    for token in forbidden_imports:
        assert token not in source, (
            f"found forbidden import/reference {token!r} in driver.py"
        )
    # Never branches on a decision's free-text fields -- only on structured exit codes and the three
    # fields the safety guards compare for exact equality (state_id/target/build_round).
    forbidden_content_access = [
        'decision["reason"]',
        "decision.reason",
        '["step10_declined_because"]',
    ]
    for token in forbidden_content_access:
        assert token not in source, (
            f"found decision-content access {token!r} in driver.py"
        )


def test_dispatch_ok_logs_decision_and_prints_json(tmp_path: Path) -> None:
    state_path = _init_state(tmp_path)

    result = _run_driver(["dispatch", "--state", str(state_path)])

    assert result.returncode == exit_codes.OK, result.stderr
    payload = json.loads(result.stdout)
    assert payload["target"] == "loopr-step10"
    assert payload["step10_warrant"] == "greenfield_no_artifacts"

    records = _driver_log_records(state_path)
    assert len(records) == 1
    assert records[0]["kind"] == "dispatch_ok"
    assert records[0]["decision"]["target"] == "loopr-step10"
    assert "ts" in records[0]


def test_dispatch_halt_from_loopr_is_logged_and_relayed(tmp_path: Path) -> None:
    """A real loopr-dispatch HALT (incoherent state), not a driver-guard HALT -- confirms the driver
    correctly recognises exit 40 from the wrapped CLI and never fabricates a decision to log."""
    from loopr.state.store import StateStore

    state_path = _init_state(tmp_path)
    store = StateStore(state_path)
    state = store.load()
    state.dispatch.build_round = (
        1  # incoherent: no artifacts on disk, yet a round is recorded built
    )
    store.save(state)

    result = _run_driver(["dispatch", "--state", str(state_path)])

    assert result.returncode == exit_codes.HALT
    assert "HALT" in result.stderr
    assert "loopr-step10" not in result.stderr

    records = _driver_log_records(state_path)
    assert len(records) == 1
    assert records[0]["kind"] == "dispatch_halt"


def test_dispatch_terminal_when_build_complete_present(tmp_path: Path) -> None:
    state_path = _init_state(tmp_path)
    repo = state_path.parent / "repo"
    (repo / "BUILD_COMPLETE.md").write_text("done", encoding="utf-8")

    result = _run_driver(["dispatch", "--state", str(state_path)])

    assert result.returncode == exit_codes.COMPLETE
    payload = json.loads(result.stdout)
    assert payload["state_id"] == "s0_terminal"

    records = _driver_log_records(state_path)
    assert records[-1]["kind"] == "dispatch_complete_terminal"


def test_complete_ok_after_dispatch(tmp_path: Path) -> None:
    state_path = _init_state(tmp_path)
    dispatch_result = _run_driver(["dispatch", "--state", str(state_path)])
    assert dispatch_result.returncode == exit_codes.OK

    complete_result = _run_driver(["complete", "--state", str(state_path)])

    assert complete_result.returncode == exit_codes.OK, complete_result.stderr
    assert "active_step=none" in complete_result.stdout

    records = _driver_log_records(state_path)
    assert records[-1]["kind"] == "complete_ok"


def test_complete_errors_when_nothing_in_flight(tmp_path: Path) -> None:
    state_path = _init_state(tmp_path)

    result = _run_driver(["complete", "--state", str(state_path)])

    assert result.returncode == exit_codes.USAGE
    records = _driver_log_records(state_path)
    assert records[-1]["kind"] == "complete_error"


def test_log_stop_records_the_two_judgment_based_stop_conditions(
    tmp_path: Path,
) -> None:
    """`log-stop` never inspects or judges its input -- it only appends what the session (which DID
    the judging, by reading a subagent's real output) supplies verbatim. Covers both non-HALT stop
    conditions named in baby_prd.md acceptance criterion 2."""
    state_path = _init_state(tmp_path)

    gate_result = _run_driver(
        [
            "log-stop",
            "--state",
            str(state_path),
            "--kind",
            "subagent_gate",
            "--subagent",
            "loopr-step11",
            "--reason",
            "step11 asked whether to use library X or Y; genuinely ambiguous, needs a human call.",
        ]
    )
    assert gate_result.returncode == exit_codes.OK

    uncertain_result = _run_driver(
        [
            "log-stop",
            "--state",
            str(state_path),
            "--kind",
            "step12_uncertain",
            "--subagent",
            "loopr-step12",
            "--reason",
            "step12 flagged item X as UNCERTAIN (confidence 0.4); auditor dispatched, verdict FALSE_ALARM.",
        ]
    )
    assert uncertain_result.returncode == exit_codes.OK

    records = _driver_log_records(state_path)
    assert [r["kind"] for r in records] == [
        "stop_subagent_gate",
        "stop_step12_uncertain",
    ]
    assert records[0]["subagent"] == "loopr-step11"
    assert records[1]["subagent"] == "loopr-step12"


def test_round_cap_guard_halts_before_calling_loopr(tmp_path: Path) -> None:
    """The driver's own structural safety guard -- not a `loopr dispatch` HALT. Pre-seed the log with
    enough dispatch_ok records (varying build_round so the no-progress guard doesn't fire first) to
    hit a small --max-rounds, and confirm the guard fires without ever invoking the real CLI (state
    stays untouched, since a genuine `loopr dispatch` call was never made)."""
    from loopr.state.store import StateStore

    state_path = _init_state(tmp_path)
    log_path = state_path.parent / "driver-log.jsonl"
    with open(log_path, "a", encoding="utf-8") as handle:
        for round_n in range(3):
            handle.write(
                json.dumps(
                    {
                        "kind": "dispatch_ok",
                        "ts": "2026-08-06T00:00:00Z",
                        "decision": {
                            "state_id": f"s{round_n}",
                            "target": "loopr-step11",
                            "build_round": round_n,
                        },
                    }
                )
                + "\n"
            )

    store = StateStore(state_path)
    before = store.load()

    result = _run_driver(["dispatch", "--state", str(state_path), "--max-rounds", "3"])

    assert result.returncode == exit_codes.HALT
    assert "round cap" in result.stderr

    after = store.load()
    assert before == after  # the real CLI was never invoked; state is untouched

    records = _driver_log_records(state_path)
    assert records[-1]["kind"] == "guard_halt"
    assert "round cap" in records[-1]["reason"]


def test_no_progress_guard_halts_on_identical_repeated_decisions(
    tmp_path: Path,
) -> None:
    """Three byte-identical (state_id, target, build_round) dispatch_ok records in a row can never
    come from a healthy loop (a completion always changes at least one of those fields) -- this is
    the guard against a driver bug that misreads an exit code and re-dispatches the same target,
    repeating whatever real side effect it performs (context.md soft-context risk 2)."""
    state_path = _init_state(tmp_path)
    log_path = state_path.parent / "driver-log.jsonl"
    with open(log_path, "a", encoding="utf-8") as handle:
        for _ in range(3):
            handle.write(
                json.dumps(
                    {
                        "kind": "dispatch_ok",
                        "ts": "2026-08-06T00:00:00Z",
                        "decision": {
                            "state_id": "s4_step11_in_flight",
                            "target": "loopr-step11",
                            "build_round": 2,
                        },
                    }
                )
                + "\n"
            )

    result = _run_driver(["dispatch", "--state", str(state_path), "--max-rounds", "20"])

    assert result.returncode == exit_codes.HALT
    assert "identical" in result.stderr

    records = _driver_log_records(state_path)
    assert records[-1]["kind"] == "guard_halt"
    assert "identical" in records[-1]["reason"]


def test_complete_with_approving_verdict_refuses_without_step14_ok(tmp_path: Path) -> None:
    """The core, functional Step 14 gate (.claude/loopr-step14-comprehension/baby_prd.md, 2026-08-11):
    an APPROVING step12 completion (--verdict clean/minor) must not be logged until step14-complete
    has recorded a step14_ok entry for the SAME build_round -- otherwise the driver would let the
    loop proceed straight past step12's approval into the next dispatch with Step 14 never having
    run, exactly the sequencing this build exists to make load-bearing rather than advisory."""
    state_path = _init_state(tmp_path)
    dispatch_result = _run_driver(["dispatch", "--state", str(state_path)])
    assert dispatch_result.returncode == exit_codes.OK  # names loopr-step10, build_round=0

    result = _run_driver(["complete", "--state", str(state_path), "--verdict", "clean"])

    assert result.returncode == exit_codes.HALT
    assert "step14" in result.stderr.lower()

    records = _driver_log_records(state_path)
    assert records[-1]["kind"] == "guard_halt"
    assert "step14_ok" in records[-1]["reason"]

    # And the real CLI was never invoked for this refused completion -- state stays whatever the
    # prior dispatch left it as, not advanced by a completion that should not have been allowed.
    from loopr.state.store import StateStore

    state = StateStore(state_path).load()
    assert state.dispatch.active_step is not None  # dispatch-complete never ran


def _seed_step12_active_with_dispatch_ok_record(state_path: Path, *, build_round: int = 0) -> None:
    """Puts the real state into `active_step=STEP_12` (so the real `loopr dispatch-complete
    --verdict ...` the guard eventually lets through will actually succeed, not USAGE-refuse for a
    verdict on a non-step12 completion) and seeds a matching `dispatch_ok` driver-log record (so the
    guard has a build_round to check against) -- without driving a full step10->step11->step12
    lifecycle, which these guard-focused tests have no need to exercise."""
    from loopr.models.common import CustomizationStep
    from loopr.state.store import StateStore

    store = StateStore(state_path)
    state = store.load()
    state.dispatch.active_step = CustomizationStep.STEP_12
    state.dispatch.build_round = build_round
    store.save(state)

    log_path = state_path.parent / "driver-log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "kind": "dispatch_ok",
                    "ts": "2026-08-11T00:00:00Z",
                    "decision": {
                        "state_id": "s6_step12_in_flight",
                        "target": "loopr-step12",
                        "reason": "step12 is already the active step; resuming it.",
                        "step10_warrant": None,
                        "step10_declined_because": "step10 artifacts present on disk; no --remodernize given.",
                        "build_round": build_round,
                    },
                }
            )
            + "\n"
        )


def test_complete_with_approving_verdict_succeeds_after_step14_complete(tmp_path: Path) -> None:
    """The unblocked path: once step14-complete has logged a step14_ok record for the current
    build_round, the same completion that was refused above now proceeds normally."""
    state_path = _init_state(tmp_path)
    _seed_step12_active_with_dispatch_ok_record(state_path, build_round=1)

    step14_result = _run_driver(["step14-complete", "--state", str(state_path)])
    assert step14_result.returncode == exit_codes.OK

    records_before = _driver_log_records(state_path)
    assert records_before[-1]["kind"] == "step14_ok"
    assert records_before[-1]["build_round"] == 1

    result = _run_driver(["complete", "--state", str(state_path), "--verdict", "clean"])
    assert result.returncode == exit_codes.OK, result.stderr

    records = _driver_log_records(state_path)
    assert records[-1]["kind"] == "complete_ok"


def test_complete_with_spec_violating_verdict_is_never_gated_by_step14(tmp_path: Path) -> None:
    """A spec_violating verdict means the phase was NOT approved -- no step14 comprehension pass is
    owed for a round that never got approved, so this completion must never be blocked by the guard,
    with or without a step14_ok record on the log."""
    state_path = _init_state(tmp_path)
    _seed_step12_active_with_dispatch_ok_record(state_path, build_round=1)

    result = _run_driver(["complete", "--state", str(state_path), "--verdict", "spec_violating"])
    assert result.returncode == exit_codes.OK, result.stderr

    records = _driver_log_records(state_path)
    assert records[-1]["kind"] == "complete_ok"


def test_complete_with_no_verdict_is_never_gated_by_step14(tmp_path: Path) -> None:
    """A step10/step11 completion (`--verdict` omitted entirely) is likewise never subject to this
    guard -- it is scoped narrowly to an APPROVING step12 completion, per the guard's own docstring."""
    state_path = _init_state(tmp_path)
    _run_driver(["dispatch", "--state", str(state_path)])

    result = _run_driver(["complete", "--state", str(state_path)])
    assert result.returncode == exit_codes.OK, result.stderr

    records = _driver_log_records(state_path)
    assert records[-1]["kind"] == "complete_ok"


def test_step14_complete_halts_when_nothing_dispatched_yet(tmp_path: Path) -> None:
    state_path = _init_state(tmp_path)

    result = _run_driver(["step14-complete", "--state", str(state_path)])

    assert result.returncode == exit_codes.HALT
    assert "no dispatch_ok record" in result.stderr


@pytest.mark.parametrize("bad_max_rounds", [1])
def test_round_cap_does_not_false_positive_on_legitimate_ping_pong(
    tmp_path: Path, bad_max_rounds: int
) -> None:
    """Sanity check the no-progress guard's own false-positive risk: three DIFFERENT decisions (a
    legitimate step11<->step12 ping-pong, varying state_id even at the same build_round) must NOT
    trip the guard."""
    state_path = _init_state(tmp_path)
    log_path = state_path.parent / "driver-log.jsonl"
    decisions = [
        {"state_id": "s5_step11_done", "target": "loopr-step12", "build_round": 1},
        {
            "state_id": "s9_step12_spec_violating",
            "target": "loopr-step11",
            "build_round": 1,
        },
        {"state_id": "s5_step11_done", "target": "loopr-step12", "build_round": 1},
    ]
    with open(log_path, "a", encoding="utf-8") as handle:
        for decision in decisions:
            handle.write(
                json.dumps(
                    {
                        "kind": "dispatch_ok",
                        "ts": "2026-08-06T00:00:00Z",
                        "decision": decision,
                    }
                )
                + "\n"
            )

    result = _run_driver(["dispatch", "--state", str(state_path), "--max-rounds", "20"])

    # The guard does not fire (the three decisions differ), so this falls through to a real `loopr
    # dispatch` call against the freshly-initialized state on disk (untouched by the fabricated log
    # above) -- which legitimately names step10, exit OK. The assertion that matters here is that the
    # guard did NOT halt it.
    assert result.returncode == exit_codes.OK
    records = _driver_log_records(state_path)
    assert records[-1]["kind"] == "dispatch_ok"
    assert records[-1]["decision"]["target"] == "loopr-step10"
