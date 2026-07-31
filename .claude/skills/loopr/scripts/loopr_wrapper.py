"""Thin wrapper the loopr skill uses to drive the existing loopr CLI.

Implements SKILL_PHASE_1_SPEC.md SS6.1. Only three jobs: (a) the preflight importability check,
(b) translate SKILL.md's orchestration calls into actual `loopr` CLI invocations, (c) surface the
CLI's own exit codes and pending-file contents back to the orchestrating prompt unmodified. This
file contains NO interrogation logic, judge-call logic, or artifact-rendering logic of its own --
all of that already exists in src/loopr/. Reimplementing any of it here would be a defect (it would
break the byte-diff acceptance criterion by construction) and a scope violation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


class LooprNotInstalled(RuntimeError):
    """Raised when the loopr package isn't importable. The skill's preflight check (SKILL.md, SS4)
    surfaces this and nothing else -- no partial interrogation, no vague error."""


def preflight() -> None:
    """The skill's first action, before any interrogation logic runs."""
    try:
        import loopr  # noqa: F401
    except ImportError as exc:
        raise LooprNotInstalled(
            "loopr is not installed. Install it first: `pip install -e .` from the kaide-loop repo "
            "root (or `pip install loopr` once/if published), then retry."
        ) from exc


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Invoke the loopr CLI exactly as a human would from the command line, surfacing its exit code
    and stdout/stderr unmodified -- no interpretation of the output happens here."""
    return subprocess.run(
        [sys.executable, "-m", "loopr.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def state_dir_for(state_path: Path) -> Path:
    return state_path.parent


def read_pending_judge(state_dir: Path) -> dict[str, object]:
    payload: dict[str, object] = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
    return payload


def read_pending_gate(state_dir: Path) -> tuple[str, dict[str, object]]:
    body = (state_dir / "pending_gate.md").read_text(encoding="utf-8")
    meta: dict[str, object] = json.loads((state_dir / "pending_gate.json").read_text(encoding="utf-8"))
    return body, meta


def read_pending_question(state_dir: Path) -> dict[str, object]:
    payload: dict[str, object] = json.loads(
        (state_dir / "pending_question.json").read_text(encoding="utf-8")
    )
    return payload
