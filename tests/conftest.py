"""Shared fixtures. Implements PHASE_1_SPEC.md SS1.6."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from loopr.models.common import Mode
from loopr.models.interrogation import InterrogationState


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    return root


@pytest.fixture
def greenfield_state(repo_root: Path) -> InterrogationState:
    return InterrogationState(mode=Mode.GREENFIELD, repo_root=str(repo_root))


@pytest.fixture
def brownfield_state(repo_root: Path) -> InterrogationState:
    from loopr.models.brownfield import BrownfieldState

    return InterrogationState(
        mode=Mode.BROWNFIELD, repo_root=str(repo_root), brownfield=BrownfieldState()
    )
