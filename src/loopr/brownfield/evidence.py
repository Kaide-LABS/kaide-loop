"""Evidence-bundle construction from git, grep, and a lightweight import/decorator scan.

Implements PHASE_1_SPEC.md SS6.7.2. Every signal here is pure code -- no model call.

As amended 2026-07-28: ownership is commit-based (git log), never git blame -- the two agree on
only 0-40% of developers, and only commit-based ownership concentration is associated with
defect-proneness (arXiv:2408.12807, RQ1, RQ4, section V Recommendation 1).
"""

from __future__ import annotations

import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

from loopr.models.brownfield import EvidenceBundle
from loopr.models.common import Centrality

_MIN_OCCURRENCES = 3  # confirmed, not a placeholder (docs/conformance-classification-spec.md SS2)

_DECORATOR_RE = re.compile(r"^\s*@([A-Za-z_][A-Za-z0-9_.]*)")
_IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))")
_DEPRECATION_RE = re.compile(r"\b(TODO|FIXME|DEPRECATED|legacy|hack)\b", re.IGNORECASE)
_NAMING_DENYLIST_RE = re.compile(r"(_v1|old_|legacy|deprecated)", re.IGNORECASE)


def _run_git(repo_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _last_touched_days_ago(repo_root: Path, path: str) -> int | None:
    output = _run_git(repo_root, "log", "-1", "--format=%ct", "--", path)
    if not output or not output.strip():
        return None
    try:
        commit_epoch = int(output.strip())
    except ValueError:
        return None
    return max(0, int((time.time() - commit_epoch) // 86400))


def _ownership(repo_root: Path, path: str) -> tuple[float | None, int | None]:
    output = _run_git(repo_root, "log", "--format=%ae", "--", path)
    if not output:
        return None, None
    authors = [line.strip() for line in output.splitlines() if line.strip()]
    if not authors:
        return None, None
    counts = Counter(authors)
    total = sum(counts.values())
    top_share = max(counts.values()) / total
    major_count = sum(1 for share in counts.values() if share / total >= 0.05)
    return top_share, major_count


def _candidate_key(kind: str, name: str) -> str:
    return f"{kind}:{name}"


def _scan_candidates(repo_root: Path, touched_surface: list[str]) -> dict[str, list[str]]:
    """Map candidate key -> list of 'file:line' locations."""
    locations: dict[str, list[str]] = defaultdict(list)
    for relative_path in touched_surface:
        full_path = repo_root / relative_path
        try:
            text = full_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            deco_match = _DECORATOR_RE.match(line)
            if deco_match:
                key = _candidate_key("decorator", deco_match.group(1))
                locations[key].append(f"{relative_path}:{line_no}")
                continue
            import_match = _IMPORT_RE.match(line)
            if import_match:
                module = import_match.group(1) or import_match.group(2) or ""
                if module:
                    key = _candidate_key("import", module)
                    locations[key].append(f"{relative_path}:{line_no}")
    return locations


def _nearby_deprecation_markers(repo_root: Path, locations: list[str]) -> list[str]:
    markers: list[str] = []
    for location in locations:
        relative_path, _, line_str = location.rpartition(":")
        try:
            line_no = int(line_str)
        except ValueError:
            continue
        full_path = repo_root / relative_path
        try:
            lines = full_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        window_start = max(0, line_no - 3)
        window_end = min(len(lines), line_no + 2)
        for line in lines[window_start:window_end]:
            match = _DEPRECATION_RE.search(line)
            if match:
                markers.append(match.group(1).upper())
    return sorted(set(markers))


def _signal_qualifiers(
    git_last_touched_days_ago: int | None,
    deprecation_markers: list[str],
    occurrence_count: int,
    naming_flags: bool,
) -> list[str]:
    qualifiers: list[str] = []
    if git_last_touched_days_ago is not None and git_last_touched_days_ago > 180:
        qualifiers.append(
            "staleness alone is not sufficient for DO_NOT_REPLICATE; stable mature code is also old"
        )
    if deprecation_markers:
        qualifiers.append(
            "a deprecation marker may indicate on-hold debt (correct code blocked on an external "
            "event), not cruft"
        )
    if occurrence_count == _MIN_OCCURRENCES:
        qualifiers.append("at the minimum recurrence threshold; weak evidence of intentionality")
    if naming_flags:
        qualifiers.append("naming heuristic only; no validated basis")
    return qualifiers


def discover_patterns(repo_root: Path, touched_surface: list[str]) -> list[EvidenceBundle]:
    """A candidate qualifies as a pattern at occurrence_count >= 3
    (docs/conformance-classification-spec.md SS2). Structural-touchpoint qualification (appears
    once but is central) is deferred to a future calibration pass -- see PHASE_1_SPEC.md SS8.5."""
    candidates = _scan_candidates(repo_root, touched_surface)
    bundles: list[EvidenceBundle] = []

    for key, locations in sorted(candidates.items()):
        occurrence_count = len(locations)
        if occurrence_count < _MIN_OCCURRENCES:
            continue

        distinct_files = {loc.rpartition(":")[0] for loc in locations}
        centrality = Centrality.CORE if len(distinct_files) >= _MIN_OCCURRENCES else Centrality.PERIPHERAL

        days_ago_values = [
            d
            for d in (_last_touched_days_ago(repo_root, f) for f in sorted(distinct_files))
            if d is not None
        ]
        last_touched = min(days_ago_values) if days_ago_values else None

        shares: list[float] = []
        major_counts: list[int] = []
        for file_path in sorted(distinct_files):
            share, major = _ownership(repo_root, file_path)
            if share is not None:
                shares.append(share)
            if major is not None:
                major_counts.append(major)
        top_author_share = max(shares) if shares else None
        major_author_count = max(major_counts) if major_counts else None

        markers = _nearby_deprecation_markers(repo_root, locations)
        kind, _, name = key.partition(":")
        naming_flags = bool(_NAMING_DENYLIST_RE.search(name)) or any(
            _NAMING_DENYLIST_RE.search(loc) for loc in locations
        )

        bundles.append(
            EvidenceBundle(
                pattern_id=key,
                description=f"{kind} '{name}' recurring across the touched surface",
                locations=sorted(locations),
                occurrence_count=occurrence_count,
                centrality=centrality,
                git_last_touched_days_ago=last_touched,
                git_top_author_commit_share=top_author_share,
                git_major_author_count=major_author_count,
                deprecation_markers=markers,
                naming_flags=naming_flags,
                signal_qualifiers=_signal_qualifiers(
                    last_touched, markers, occurrence_count, naming_flags
                ),
            )
        )
    return bundles
