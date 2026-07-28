"""Gate payload and record models. Implements PHASE_1_SPEC.md SS3.5."""

from __future__ import annotations

from pydantic import Field

from loopr.models.common import GateId, LooprBase


class GatePayload(LooprBase):
    gate: GateId
    title: str = Field(min_length=1)
    body_markdown: str = Field(min_length=1)
    digest: str = Field(min_length=1)


class GateRecord(LooprBase):
    gate: GateId
    requested_round: int = Field(ge=1)
    payload_digest: str = Field(min_length=1)
    confirmed: bool = False
    confirmed_payload_digest: str | None = None
    user_amendment: str | None = None
