"""`loopr dispatch` / `dispatch-complete` / `dispatch-verify` / `dispatch-audit` end to end: exit
codes, output shape, state mutation. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS4, SS8 criteria 3, 5.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from loopr import exit_codes
from loopr.cli import main
from loopr.models.common import CustomizationStep, Step12Verdict
from loopr.state.store import StateStore

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "dispatch"


def _init_state(tmp_path: Path, repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    state_path = tmp_path / "state.json"
    code = main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)])
    assert code == exit_codes.OK
    return state_path


def test_dispatch_greenfield_names_step10_and_mutates_state(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)

    code = main(["dispatch", "--state", str(state_path)])
    out = capsys.readouterr().out

    assert code == exit_codes.OK
    assert "loopr-step10" in out
    assert "WARRANT" in out
    assert "greenfield_no_artifacts" in out

    store = StateStore(state_path)
    reloaded = store.load()
    assert reloaded.dispatch.active_step == CustomizationStep.STEP_10

    log_path = store.dir / "dispatch-log.jsonl"
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["target"] == "loopr-step10"


def test_dispatch_terminal_when_build_complete_present(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    (repo / "BUILD_COMPLETE.md").write_text("done", encoding="utf-8")

    code = main(["dispatch", "--state", str(state_path)])
    out = capsys.readouterr().out

    assert code == exit_codes.COMPLETE
    assert "-- nothing; build is complete" in out

    store = StateStore(state_path)
    reloaded = store.load()
    assert reloaded.dispatch.active_step is None  # no state mutation on terminal


def test_dispatch_halts_on_incoherent_state_and_never_names_step10(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)

    store = StateStore(state_path)
    state = store.load()
    state.dispatch.build_round = 1  # incoherent: no artifacts on disk, yet a round is recorded built
    store.save(state)

    code = main(["dispatch", "--state", str(state_path)])
    err = capsys.readouterr().err

    assert code == exit_codes.HALT
    assert "-- HALT" in err
    assert "loopr-step10" not in err

    log_path = store.dir / "dispatch-log.jsonl"
    assert not log_path.exists()  # nothing appended on a HALT

    reloaded = store.load()
    assert reloaded.dispatch.build_round == 1  # unchanged -- no state mutation on a HALT


def test_dispatch_dry_run_does_not_mutate_state_or_append_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)

    code = main(["dispatch", "--state", str(state_path), "--dry-run"])
    capsys.readouterr()

    assert code == exit_codes.OK
    store = StateStore(state_path)
    reloaded = store.load()
    assert reloaded.dispatch.active_step is None
    assert not (store.dir / "dispatch-log.jsonl").exists()


def test_dispatch_json_output_is_valid_dispatch_decision(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    capsys.readouterr()  # discard `loopr init`'s own stdout before capturing dispatch's

    code = main(["dispatch", "--state", str(state_path), "--json", "--dry-run"])
    out = capsys.readouterr().out
    assert code == exit_codes.OK

    payload = json.loads(out)
    assert payload["state_id"] == "s1_pre_step10"
    assert payload["target"] == "loopr-step10"
    assert payload["step10_warrant"] == "greenfield_no_artifacts"


def test_remodernize_rejected_when_a_step_is_already_in_flight(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)

    store = StateStore(state_path)
    state = store.load()
    state.dispatch.active_step = CustomizationStep.STEP_11
    store.save(state)

    code = main(["dispatch", "--state", str(state_path), "--remodernize"])
    err = capsys.readouterr().err

    assert code == exit_codes.USAGE
    assert "in-flight" in err


def test_remodernize_resets_round_and_verdict_and_dispatches_step10(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    # step10's real artifacts on disk -- otherwise this is indistinguishable from plain greenfield.
    (repo / "MODERNIZED_PRD.md").write_text(
        "## MODERNIZATION CHANGELOG\n", encoding="utf-8"
    )
    (repo / "PHASE_1_SPEC.md").write_text(
        "# Phase Plan Header\n\nBuilt from `MODERNIZED_PRD.md`.\n", encoding="utf-8"
    )

    store = StateStore(state_path)
    state = store.load()
    state.dispatch.build_round = 3
    state.dispatch.last_step12_verdict = Step12Verdict.CLEAN
    store.save(state)

    code = main(["dispatch", "--state", str(state_path), "--remodernize"])
    out = capsys.readouterr().out

    assert code == exit_codes.OK
    assert "loopr-step10" in out
    assert "explicit_remodernization" in out

    reloaded = store.load()
    assert reloaded.dispatch.active_step == CustomizationStep.STEP_10
    assert reloaded.dispatch.build_round == 0
    assert reloaded.dispatch.last_step12_verdict is None


# ============================================================================
# 2026-08-05: `--modernized-prd-path` / `--phase-1-spec-path` threaded through `dispatch`, same
# mechanism `customize` already had (bebdce3) -- found live via this project's own first real
# `loopr dispatch` run, which HALTs on this exact ambiguity (two genuine phase-spec-shaped files at
# repo root, both legitimately claiming provenance from the same PRD) with no flag to resolve it.
# ============================================================================


def _seed_colliding_step10_artifacts(repo: Path) -> None:
    """Reproduces the exact ambiguity structurally: one modernised PRD, two *.md files that each
    independently satisfy both of find_step10_execution_artifacts' Phase-N-spec signals (a real
    'Phase Plan Header' heading line, and an explicit 'built from' claim naming the PRD)."""
    (repo / "MODERNIZED_PRD.md").write_text("## MODERNIZATION CHANGELOG\n", encoding="utf-8")
    (repo / "PHASE_1_SPEC.md").write_text(
        "# Phase Plan Header\n\nBuilt from `MODERNIZED_PRD.md`.\n", encoding="utf-8"
    )
    (repo / "PHASE_2_SPEC.md").write_text(
        "# Phase Plan Header\n\nBuilt from `MODERNIZED_PRD.md`.\n", encoding="utf-8"
    )


def test_dispatch_halts_on_colliding_step10_artifacts_without_override(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    _seed_colliding_step10_artifacts(repo)

    code = main(["dispatch", "--state", str(state_path), "--dry-run"])
    err = capsys.readouterr().err

    assert code == exit_codes.HALT
    assert "HALT:" in err
    assert "PHASE_1_SPEC.md" in err
    assert "PHASE_2_SPEC.md" in err
    assert "--phase-1-spec-path" in err


def test_dispatch_phase_1_spec_path_override_resolves_the_collision(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    _seed_colliding_step10_artifacts(repo)

    code = main(
        [
            "dispatch",
            "--state",
            str(state_path),
            "--dry-run",
            "--phase-1-spec-path",
            str(repo / "PHASE_2_SPEC.md"),
        ]
    )
    out = capsys.readouterr().out

    assert code == exit_codes.OK
    assert "DISPATCH" in out
    assert "STATE" in out
    assert "WHY" in out
    assert "NOT-STEP10" in out


def test_dispatch_override_path_that_does_not_exist_errors_clearly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)

    code = main(
        [
            "dispatch",
            "--state",
            str(state_path),
            "--dry-run",
            "--phase-1-spec-path",
            str(repo / "does-not-exist.md"),
        ]
    )
    err = capsys.readouterr().err

    assert code == exit_codes.HALT
    assert "does not exist or is not a file" in err


# ============================================================================
# 2026-08-05: `--build-complete-path`, second gap from the same first real dispatch dogfood run.
# cli.py hardcoded `(repo_root / "BUILD_COMPLETE.md").exists()` -- unrelated to the project the
# given --state file actually tracks. A repo can host more than one loopr-managed build with its own
# completion marker (this repo does); the dangerous direction is a project genuinely mid-build being
# falsely reported S0_TERMINAL because an unrelated marker for a DIFFERENT build sits at repo root.
# ============================================================================


def test_dispatch_does_not_falsely_report_terminal_from_an_unrelated_build_complete_marker(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The dangerous direction, reproduced directly: an unrelated BUILD_COMPLETE.md (simulating a
    different loopr-managed build in the same repo) sits at repo root, while THIS project's own
    marker (pointed at via --build-complete-path) does not exist yet -- genuinely mid-build. Must NOT
    report S0_TERMINAL; must fall through to the normal state-based decision instead."""
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    (repo / "BUILD_COMPLETE.md").write_text("unrelated build, done", encoding="utf-8")
    # Deliberately NOT creating repo / "MY_BUILD_COMPLETE.md" -- this project's own build is not done.

    code = main(
        [
            "dispatch",
            "--state",
            str(state_path),
            "--dry-run",
            "--build-complete-path",
            str(repo / "MY_BUILD_COMPLETE.md"),
        ]
    )
    out = capsys.readouterr().out

    assert code != exit_codes.COMPLETE
    assert "s0_terminal" not in out
    assert "-- nothing; build is complete" not in out
    assert "loopr-step10" in out  # falls through to the normal greenfield decision


def test_dispatch_reports_terminal_when_override_marker_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    (repo / "MY_BUILD_COMPLETE.md").write_text("this project's own build, done", encoding="utf-8")

    code = main(
        [
            "dispatch",
            "--state",
            str(state_path),
            "--dry-run",
            "--build-complete-path",
            str(repo / "MY_BUILD_COMPLETE.md"),
        ]
    )
    out = capsys.readouterr().out

    assert code == exit_codes.COMPLETE
    assert "s0_terminal" in out
    assert "MY_BUILD_COMPLETE.md exists at the target repository root" in out
    assert "BUILD_COMPLETE.md exists" not in out.replace("MY_BUILD_COMPLETE.md exists", "")


def test_dispatch_omitting_build_complete_path_reproduces_default_behavior_unchanged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No flag given -- criterion 4/6's existing single-build-per-repo behaviour must stay byte-for-
    byte unchanged: the default filename, the default WHY text."""
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    (repo / "BUILD_COMPLETE.md").write_text("done", encoding="utf-8")

    code = main(["dispatch", "--state", str(state_path), "--dry-run"])
    out = capsys.readouterr().out

    assert code == exit_codes.COMPLETE
    assert "s0_terminal" in out
    assert "BUILD_COMPLETE.md exists at the target repository root; the build is complete." in out


def test_dispatch_build_complete_override_path_that_is_a_directory_errors_clearly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unlike --modernized-prd-path/--phase-1-spec-path, a --build-complete-path that does not exist
    yet is NOT an error (see test_dispatch_does_not_falsely_report_terminal_from_an_unrelated_
    build_complete_marker -- that's the normal "still mid-build" case this flag exists to express).
    It is only rejected if it exists but is unambiguously not a plausible marker file, e.g. a
    directory."""
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    (repo / "a-directory").mkdir()

    code = main(
        [
            "dispatch",
            "--state",
            str(state_path),
            "--dry-run",
            "--build-complete-path",
            str(repo / "a-directory"),
        ]
    )
    err = capsys.readouterr().err

    assert code == exit_codes.HALT
    assert "exists but is not a file" in err
    assert "--build-complete-path" in err


def test_dispatch_complete_usage_error_when_nothing_in_flight(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)

    code = main(["dispatch-complete", "--state", str(state_path)])
    assert code == exit_codes.USAGE


def test_dispatch_complete_usage_error_verdict_given_for_step11(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    store = StateStore(state_path)
    state = store.load()
    state.dispatch.active_step = CustomizationStep.STEP_11
    store.save(state)

    code = main(["dispatch-complete", "--state", str(state_path), "--verdict", "clean"])
    assert code == exit_codes.USAGE


def test_dispatch_complete_usage_error_step12_missing_verdict(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    store = StateStore(state_path)
    state = store.load()
    state.dispatch.active_step = CustomizationStep.STEP_12
    state.dispatch.build_round = 1
    store.save(state)

    code = main(["dispatch-complete", "--state", str(state_path)])
    assert code == exit_codes.USAGE


def test_dispatch_complete_step11_increments_build_round(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    store = StateStore(state_path)
    state = store.load()
    state.dispatch.active_step = CustomizationStep.STEP_11
    store.save(state)

    code = main(["dispatch-complete", "--state", str(state_path)])
    out = capsys.readouterr().out

    assert code == exit_codes.OK
    assert "build_round=1" in out
    reloaded = store.load()
    assert reloaded.dispatch.active_step is None
    assert reloaded.dispatch.build_round == 1


def test_dispatch_complete_step10_clears_active_step(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    store = StateStore(state_path)
    state = store.load()
    state.dispatch.active_step = CustomizationStep.STEP_10
    store.save(state)

    code = main(["dispatch-complete", "--state", str(state_path)])
    assert code == exit_codes.OK
    reloaded = store.load()
    assert reloaded.dispatch.active_step is None
    assert reloaded.dispatch.build_round == 0
    assert reloaded.dispatch.last_step12_verdict is None


def test_dispatch_complete_step12_records_verdict(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    store = StateStore(state_path)
    state = store.load()
    state.dispatch.active_step = CustomizationStep.STEP_12
    state.dispatch.build_round = 1
    store.save(state)

    code = main(
        ["dispatch-complete", "--state", str(state_path), "--verdict", "spec_violating"]
    )
    assert code == exit_codes.OK
    reloaded = store.load()
    assert reloaded.dispatch.last_step12_verdict == Step12Verdict.SPEC_VIOLATING
    assert reloaded.dispatch.active_step is None


# --- dispatch-verify: SS8 criterion 3 -- the runner shown passing AND failing ---


def test_dispatch_verify_all_real_fixtures_pass(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["dispatch-verify", "--fixtures", str(FIXTURES_DIR)])
    out = capsys.readouterr().out
    assert code == exit_codes.OK
    assert "MISMATCH" not in out
    assert "10/10" in out


def test_dispatch_verify_catches_a_corrupted_fixture(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    corrupted_dir = tmp_path / "fixtures"
    shutil.copytree(FIXTURES_DIR, corrupted_dir)
    target_path = corrupted_dir / "s7_step12_clean.json"
    payload = json.loads(target_path.read_text(encoding="utf-8"))
    payload["expected"]["target"] = "loopr-step10"  # deliberately wrong
    target_path.write_text(json.dumps(payload), encoding="utf-8")

    code = main(["dispatch-verify", "--fixtures", str(corrupted_dir)])
    out = capsys.readouterr().out

    assert code == exit_codes.HALT
    assert "MISMATCH s7_step12_clean" in out


# --- dispatch-audit ---


def test_dispatch_audit_ok_on_a_clean_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    state_path = _init_state(tmp_path, repo)
    main(["dispatch", "--state", str(state_path)])
    capsys.readouterr()

    log_path = StateStore(state_path).dir / "dispatch-log.jsonl"
    code = main(["dispatch-audit", "--log", str(log_path)])
    out = capsys.readouterr().out

    assert code == exit_codes.OK
    assert "loopr-step10 round=0 warrant=greenfield_no_artifacts" in out


def test_dispatch_audit_halts_on_a_planted_bad_record(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
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
    log_path.write_text(json.dumps(planted) + "\n", encoding="utf-8")

    code = main(["dispatch-audit", "--log", str(log_path)])
    err = capsys.readouterr().err

    assert code == exit_codes.HALT
    assert "missing or unrecognised" in err
