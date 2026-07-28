"""Evidence-bundle construction: commit-based ownership, never git blame (guard G-14)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from loopr.brownfield.evidence import discover_patterns


def _commit(repo_root: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo_root, check=True)


def test_recurring_decorator_pattern_discovered(repo_root: Path) -> None:
    for name in ("a", "b", "c"):
        (repo_root / f"{name}.py").write_text(
            "@retry_with_backoff\ndef call():\n    pass\n", encoding="utf-8"
        )
    _commit(repo_root, "add three files")

    bundles = discover_patterns(repo_root, ["a.py", "b.py", "c.py"])
    decorator_bundles = [b for b in bundles if b.pattern_id == "decorator:retry_with_backoff"]
    assert len(decorator_bundles) == 1
    assert decorator_bundles[0].occurrence_count == 3


def test_below_threshold_not_elevated_to_pattern(repo_root: Path) -> None:
    for name in ("a", "b"):
        (repo_root / f"{name}.py").write_text(
            "@rare_decorator\ndef call():\n    pass\n", encoding="utf-8"
        )
    _commit(repo_root, "add two files")

    bundles = discover_patterns(repo_root, ["a.py", "b.py"])
    assert not any(b.pattern_id == "decorator:rare_decorator" for b in bundles)


def test_ownership_is_commit_based(repo_root: Path) -> None:
    for name in ("a", "b", "c"):
        (repo_root / f"{name}.py").write_text(
            "@shared_pattern\ndef call():\n    pass\n", encoding="utf-8"
        )
    _commit(repo_root, "single-author commit")

    bundles = discover_patterns(repo_root, ["a.py", "b.py", "c.py"])
    bundle = next(b for b in bundles if b.pattern_id == "decorator:shared_pattern")
    # Single author across all history -> top author commit share is 1.0.
    assert bundle.git_top_author_commit_share == 1.0
    assert bundle.git_major_author_count == 1


def test_naming_flag_populates_signal_qualifier(repo_root: Path) -> None:
    for name in ("a", "b", "c"):
        (repo_root / f"{name}.py").write_text(
            "@legacy_retry\ndef call():\n    pass\n", encoding="utf-8"
        )
    _commit(repo_root, "legacy pattern")

    bundles = discover_patterns(repo_root, ["a.py", "b.py", "c.py"])
    bundle = next(b for b in bundles if b.pattern_id == "decorator:legacy_retry")
    assert bundle.naming_flags is True
    assert any("no validated basis" in q for q in bundle.signal_qualifiers)
