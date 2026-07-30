"""loopr's error hierarchy. cli.main() catches LooprError and maps it to exit_codes.HALT."""

from __future__ import annotations


class LooprError(Exception):
    """Base for every error that should HALT the CLI rather than crash it uncaught."""


class StateLoadError(LooprError):
    """A state file failed to load: corrupt JSON, a pydantic validation failure, or an unrecognised
    schema_version. Every load failure maps to this one clean, named error -- never an uncaught
    traceback -- matching how every other failure mode in this module HALTs cleanly."""
