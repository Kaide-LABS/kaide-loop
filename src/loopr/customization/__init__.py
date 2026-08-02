"""Prompt customization. Implements CUSTOMIZATION_PHASE_1_SPEC.md Phase 1."""

from __future__ import annotations

from loopr.customization.customize import apply_customization_response, build_customization_request
from loopr.customization.fidelity import check_fidelity
from loopr.customization.templates import (
    TemplateDiscoveryError,
    VacuousSkeletonError,
    discover_template,
    extract_skeleton,
    inventory_placeholders,
)

__all__ = [
    "TemplateDiscoveryError",
    "VacuousSkeletonError",
    "apply_customization_response",
    "build_customization_request",
    "check_fidelity",
    "discover_template",
    "extract_skeleton",
    "inventory_placeholders",
]
