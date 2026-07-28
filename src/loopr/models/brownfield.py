"""Brownfield conformance-classification models. Implements PHASE_1_SPEC.md SS3.3.

As amended 2026-07-28 -- see docs/conformance-classification-spec.md SS3 amendment note and
loopr-PRD.md section 5 A3a: git_distinct_authors is replaced by commit-ownership concentration,
staleness is never sufficient alone, and deprecation_markers triggers ambiguity rather than
proving cruft. signal_qualifiers carries those caveats to the judge explicitly.
"""

from __future__ import annotations

from pydantic import Field

from loopr.models.common import Centrality, LooprBase, Verdict


class EvidenceBundle(LooprBase):
    pattern_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    locations: list[str] = Field(min_length=1)
    occurrence_count: int = Field(ge=1)
    centrality: Centrality
    git_last_touched_days_ago: int | None = Field(default=None, ge=0)
    git_top_author_commit_share: float | None = Field(default=None, ge=0.0, le=1.0)
    git_major_author_count: int | None = Field(default=None, ge=0)
    deprecation_markers: list[str] = Field(default_factory=list)
    naming_flags: bool = False
    signal_qualifiers: list[str] = Field(default_factory=list)


class PatternClassification(LooprBase):
    pattern_id: str = Field(min_length=1)
    verdict: Verdict
    reason: str = Field(min_length=1)


class BrownfieldState(LooprBase):
    touched_surface: list[str] = Field(default_factory=list)
    touched_surface_confirmed_hash: str | None = None
    pattern_candidates: list[EvidenceBundle] = Field(default_factory=list)
    classifications: list[PatternClassification] = Field(default_factory=list)
    gate_3_confirmed: bool = False

    @property
    def gate_3_required(self) -> bool:
        """Computed, never stored -- cannot go stale (docs/conformance-classification-spec.md SS7)."""
        return any(c.verdict == Verdict.CONFLICT for c in self.classifications)
