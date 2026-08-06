"""Regression coverage for cmd_emit's cross-project artifact-collision guard.

Incident (2026-08-06, loopr-PRD.md SS15): `loopr emit` writes to a shared out_dir with no check
for whether that directory already holds a *different* confirmed project's artifacts. This repo
hosts multiple concurrently-tracked `.loopr-state*` runs sharing one repo_root by design, so a
second project's emit silently overwrote a first project's confirmed artifacts. The fix is a
sidecar marker (`.emitted_from.json`) recording which state file last emitted into a directory --
see cmd_emit in src/loopr/cli.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from loopr import exit_codes
from loopr.cli import main
from loopr.models.common import ConditionId, Mode
from loopr.models.interrogation import ConditionResult, InterrogationState
from loopr.state.store import StateStore

_ALL_CONDITIONS = [
    ConditionId.C1_OUTCOME,
    ConditionId.C2_ACCEPTANCE,
    ConditionId.C3_SCOPE_EDGES,
    ConditionId.C4_BOUNDARY,
    ConditionId.C5_SOFT_CONTEXT,
    ConditionId.C6_NO_UNKNOWNS,
]


def _write_complete_state(state_path: Path, repo_root: Path, problem_statement: str) -> None:
    """Builds a minimal InterrogationState that already satisfies `loopr emit`'s six-conditions
    gate, bypassing the full interrogation loop -- these tests are about the emit-time collision
    guard, not about re-proving the loop reaches COMPLETE (test_cli.py already covers that)."""
    condition_results = [
        ConditionResult(
            condition=condition_id,
            structural_pass=True,
            judge_pass=None if condition_id == ConditionId.C4_BOUNDARY else True,
            overall=True,
            detail="satisfied for test fixture",
        )
        for condition_id in _ALL_CONDITIONS
    ]
    state = InterrogationState(
        mode=Mode.GREENFIELD,
        repo_root=str(repo_root),
        problem_statement=problem_statement,
        condition_results=condition_results,
    )
    StateStore(state_path).save(state)


def test_second_project_emit_to_shared_dir_halts_and_does_not_overwrite(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "shared-out"

    state_a_path = tmp_path / "state-a" / "state.json"
    state_b_path = tmp_path / "state-b" / "state.json"
    _write_complete_state(state_a_path, repo, "project A: automate on-call failover")
    _write_complete_state(state_b_path, repo, "project B: rewrite the billing export job")

    code_a = main(["emit", "--state", str(state_a_path), "--out", str(out_dir)])
    assert code_a == exit_codes.COMPLETE

    baby_prd_path = out_dir / "baby_prd.md"
    assert baby_prd_path.exists()
    before = baby_prd_path.read_bytes()
    context_before = (out_dir / "context.md").read_bytes()

    marker_path = out_dir / ".emitted_from.json"
    assert marker_path.exists()
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert Path(marker["state_path"]) == state_a_path.resolve()

    code_b = main(["emit", "--state", str(state_b_path), "--out", str(out_dir)])
    assert code_b == exit_codes.HALT

    after = baby_prd_path.read_bytes()
    context_after = (out_dir / "context.md").read_bytes()
    assert after == before, "refused emit must not touch the first project's baby_prd.md"
    assert context_after == context_before, "refused emit must not touch the first project's context.md"

    # marker must still point at project A -- the refused attempt wrote nothing, not even the marker.
    marker_after = json.loads(marker_path.read_text(encoding="utf-8"))
    assert Path(marker_after["state_path"]) == state_a_path.resolve()


def test_reemitting_same_state_file_to_same_dir_succeeds(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "shared-out"
    state_path = tmp_path / "state" / "state.json"
    _write_complete_state(state_path, repo, "single project, revised gates, re-emit is normal")

    code_first = main(["emit", "--state", str(state_path), "--out", str(out_dir)])
    assert code_first == exit_codes.COMPLETE

    code_second = main(["emit", "--state", str(state_path), "--out", str(out_dir)])
    assert code_second == exit_codes.COMPLETE
    assert (out_dir / "baby_prd.md").exists()
    assert (out_dir / ".emitted_from.json").exists()


def test_first_ever_emit_into_directory_without_marker_succeeds(tmp_path: Path) -> None:
    """Covers every directory already emitted into before this fix landed -- no marker on disk
    yet must not be treated as a collision."""
    repo = tmp_path / "repo"
    repo.mkdir()
    out_dir = tmp_path / "preexisting-out"
    out_dir.mkdir()
    # Simulate a pre-fix directory: artifacts already present, but no marker.
    (out_dir / "baby_prd.md").write_text("stale pre-fix content", encoding="utf-8")

    state_path = tmp_path / "state" / "state.json"
    _write_complete_state(state_path, repo, "fresh project targeting a pre-existing, unmarked dir")

    code = main(["emit", "--state", str(state_path), "--out", str(out_dir)])
    assert code == exit_codes.COMPLETE
    assert (out_dir / "baby_prd.md").read_text(encoding="utf-8") != "stale pre-fix content"
    assert (out_dir / ".emitted_from.json").exists()


def test_default_out_dir_also_guarded(tmp_path: Path) -> None:
    """The guard applies whether out_dir came from --out or the default -- the root cause is two
    state files targeting the same directory, not specifically the default path."""
    repo = tmp_path / "repo"
    repo.mkdir()

    state_a_path = tmp_path / "state-a" / "state.json"
    state_b_path = tmp_path / "state-b" / "state.json"
    _write_complete_state(state_a_path, repo, "project A via default out_dir")
    _write_complete_state(state_b_path, repo, "project B via default out_dir")

    code_a = main(["emit", "--state", str(state_a_path)])
    assert code_a == exit_codes.COMPLETE

    default_out_dir = repo / ".claude" / "loopr"
    before = (default_out_dir / "baby_prd.md").read_bytes()

    code_b = main(["emit", "--state", str(state_b_path)])
    assert code_b == exit_codes.HALT
    assert (default_out_dir / "baby_prd.md").read_bytes() == before
