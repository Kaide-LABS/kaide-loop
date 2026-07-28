"""Atomic state persistence with a schema-version guard. Implements PHASE_1_SPEC.md SS6.3."""

from __future__ import annotations

import json
import os
from pathlib import Path

from loopr.models.interrogation import InterrogationState

_CURRENT_SCHEMA_VERSION = 1


class StateVersionError(ValueError):
    """Raised when a state file carries an unrecognised schema_version. Never silently upgraded."""


class StateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    @property
    def dir(self) -> Path:
        return self._path.parent

    def exists(self) -> bool:
        return self._path.exists()

    def load(self) -> InterrogationState:
        raw = self._path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        version = payload.get("schema_version")
        if version != _CURRENT_SCHEMA_VERSION:
            raise StateVersionError(
                f"unrecognised schema_version={version!r}; expected {_CURRENT_SCHEMA_VERSION}"
            )
        return InterrogationState.model_validate(payload)

    def save(self, state: InterrogationState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        # Canonical, diffable serialisation: sorted keys so the state file is reviewable evidence.
        payload = json.loads(state.model_dump_json())
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, self._path)
