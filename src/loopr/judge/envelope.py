"""Judge envelope (de)serialisation and digests. Implements PHASE_1_SPEC.md SS6.2, SS6.3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from loopr.models.judge import JudgeRequest, JudgeResponse


def canonical_json(value: object) -> str:
    """Sorted-key, compact JSON -- used for deterministic call_id derivation."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_call_id(call_type: str, round_: int, inputs: object) -> str:
    """Deterministic -- never uuid4, never a timestamp (PHASE_1_SPEC.md SS6.2.3)."""
    payload = f"{call_type}|{round_}|{canonical_json(inputs)}"
    return digest(payload)[:16]


def write_request(path: Path, request: JudgeRequest) -> None:
    path.write_text(request.model_dump_json(indent=2) + "\n", encoding="utf-8")


def read_request(path: Path) -> JudgeRequest:
    return JudgeRequest.model_validate_json(path.read_text(encoding="utf-8"))


def read_response(path: Path) -> JudgeResponse:
    return JudgeResponse.model_validate_json(path.read_text(encoding="utf-8"))


def write_response(path: Path, response: JudgeResponse) -> None:
    path.write_text(response.model_dump_json(indent=2) + "\n", encoding="utf-8")
