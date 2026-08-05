"""The append-only dispatch log. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS6.5.

One JSON object per line, `sort_keys=True` for a diffable file -- matching `state/store.py`'s own
canonical-serialisation choice. Append-only: never rewritten, never truncated, never rotated. This
is the audit trail the SS8 acceptance criteria depend on, and the `ts` timestamp is added HERE, never
by `decide()` -- `DispatchDecision` stays byte-stable and directly fixture-comparable (models/
dispatch.py SS3.3's rationale) precisely because timestamping is not its job.
"""

from __future__ import annotations

import json
import typing
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from loopr.models.common import DispatchTarget, Step10Warrant
from loopr.models.dispatch import DispatchDecision
from loopr.models.judge import JsonValue


def append_decision(log_path: Path, decision: DispatchDecision) -> None:
    """Appends one JSON line for `decision`, stamped with the current UTC time. Callers must only
    call this for a decision that was actually acted on -- never for `--dry-run`, and never for a
    HALT (CUSTOMIZATION_PHASE_3_SPEC.md SS6.5: "a HALT appends nothing... writing a non-dispatch into
    it would corrupt the grep the acceptance criteria depend on"). Written after the decision has
    already been constructed and validated, so a malformed decision can never reach the log.
    """
    payload: dict[str, JsonValue] = json.loads(decision.model_dump_json())
    payload["ts"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def read_log(log_path: Path) -> list[dict[str, JsonValue]]:
    """Reads every record from the JSONL log, in file order. An absent log (nothing has ever been
    dispatched) reads as an empty list, not an error -- a zero is visibly a zero."""
    if not log_path.exists():
        return []
    records: list[dict[str, JsonValue]] = []
    for raw_line in log_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        records.append(json.loads(stripped))
    return records


class Step10AuditEntry(typing.NamedTuple):
    """One `loopr-step10` record found in the log by `audit_step10_calls`, plus the audit's verdict
    on it. `warrant` is the raw string found on the record (or `None` if absent/not a string) --
    never coerced into `Step10Warrant` silently, since a record with an unrecognised warrant is
    exactly the failure this audit exists to catch."""

    record: Mapping[str, JsonValue]
    warrant: str | None
    valid: bool


def audit_step10_calls(records: Sequence[Mapping[str, JsonValue]]) -> list[Step10AuditEntry]:
    """The Opus-avoidance check (CUSTOMIZATION_PHASE_3_SPEC.md SS4.5, SS7 guard G3): every logged
    record whose `target` is `loopr-step10`, each marked `valid` iff its `step10_warrant` is one of
    the two real `Step10Warrant` values -- a missing, null, or unrecognised warrant is `valid=False`.
    A separate, dedicated check from the fixture suite by explicit requirement, so it must be able to
    catch a planted bad record even when every fixture is green.
    """
    valid_warrants = {member.value for member in Step10Warrant}
    entries: list[Step10AuditEntry] = []
    for record in records:
        if record.get("target") != DispatchTarget.STEP_10.value:
            continue
        raw_warrant = record.get("step10_warrant")
        warrant = raw_warrant if isinstance(raw_warrant, str) else None
        valid = warrant is not None and warrant in valid_warrants
        entries.append(Step10AuditEntry(record=record, warrant=warrant, valid=valid))
    return entries
