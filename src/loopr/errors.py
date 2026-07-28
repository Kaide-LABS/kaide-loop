"""loopr's error hierarchy. cli.main() catches LooprError and maps it to exit_codes.HALT."""

from __future__ import annotations


class LooprError(Exception):
    """Base for every error that should HALT the CLI rather than crash it uncaught."""
