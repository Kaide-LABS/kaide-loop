"""Re-exports brownfield entry points. Implements PHASE_1_SPEC.md SS1.5."""

from loopr.brownfield.classify import build_classify_request, route_verdict
from loopr.brownfield.discovery import (
    apply_relevance_response,
    build_relevance_request,
    prefilter_candidates,
)
from loopr.brownfield.evidence import discover_patterns

__all__ = [
    "apply_relevance_response",
    "build_classify_request",
    "build_relevance_request",
    "discover_patterns",
    "prefilter_candidates",
    "route_verdict",
]
