"""The dispatch-loop driver -- the mechanical half of the manual round-trip the operator ran by hand
throughout the 2026-08-06 LOOPR-LOOP-DRIVER session: `loopr dispatch` -> dispatch the named subagent
via the Agent tool -> `loopr dispatch-complete` -> repeat. Implements the confirmed baby PRD at
.claude/loopr-loop-driver/baby_prd.md.

WHY THIS IS A SCRIPT AND NOT A FULL AUTOMATION (the one architectural constraint this build cannot
design around, baby_prd.md's own framing): only a live Claude Code session can invoke the Agent tool
to actually dispatch a subagent (Task(subagent_type=...)). A standalone script has no way to do that
itself. So this script does the mechanical, judgment-free parts only -- call `loopr dispatch`, parse
its exit code/output, call `loopr dispatch-complete`, log every mechanical action -- and hands back
to the invoking session exactly what to do next. The session is the one that runs Task(...), reads
the dispatched subagent's own output, and decides whether that output shows a genuine gate/judge/
question moment or a step12 UNCERTAIN escalation candidate. See .claude/skills/loopr/SKILL.md step 7
for the exact protocol a session follows to run this loop end to end.

ZERO JUDGMENT IN THIS FILE (grep-verifiable, baby_prd.md acceptance criterion 4): this module never
calls an LLM, never reads a subagent's own output, never inspects `reason`/`step10_declined_because`
text content, and never decides which subagent runs next -- `loopr dispatch`'s decide() (src/loopr/
dispatch/controller.py) owns that alone, unmodified, called only as a subprocess. The two safety
guards below (round cap, no-progress) compare already-structured DispatchDecision FIELDS (state_id,
target, build_round) for exact equality across log records -- the same class of deterministic,
total-over-a-small-space mechanism decide() itself is, never a heuristic guess over free text.

Three subcommands:
  dispatch    Wraps `loopr dispatch --json` (plus this script's two safety guards, both exit HALT/40
              like a real loopr HALT). Logs the outcome and prints the CLI's own output unmodified.
  complete    Wraps `loopr dispatch-complete`. Logs the outcome and prints the CLI's own output
              unmodified.
  log-stop    Pure bookkeeping: appends a STOP entry the session supplies verbatim (never inspects or
              validates its content) so the two judgment-based stop conditions (a genuine gate/judge/
              question moment inside a dispatched subagent's own run, and a step12 escalation-eligible
              UNCERTAIN item) are recoverable from driver-log.jsonl alongside the two this script's
              own control flow can see (HALT, COMPLETE) -- baby_prd.md acceptance criterion 1/5.

The log: one JSON object per line, `sort_keys=True`, append-only, timestamped here (never by the
wrapped CLI) -- same convention as src/loopr/dispatch/log.py's `dispatch-log.jsonl` and the
auditor-log.jsonl snippet in SKILL.md step 6, and deliberately a SEPARATE file
(`<state-dir>/driver-log.jsonl`) from both, per baby_prd.md acceptance criterion 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loopr_wrapper import LooprNotInstalled, preflight, run_cli, state_dir_for  # noqa: E402

# Mirrors src/loopr/exit_codes.py exactly (PHASE_1_SPEC.md SS6.1) -- duplicated as bare constants
# rather than `from loopr import exit_codes` so this script never imports anything from src/loopr/
# beyond what it invokes as a subprocess (matching loopr_wrapper.py's own existing boundary: it calls
# the CLI as a black box, it does not import the module's internals).
_OK = 0
_HALT = 40
_COMPLETE = 50

_DRIVER_LOG_NAME = "driver-log.jsonl"
_DEFAULT_MAX_ROUNDS = 20
"""A structural circuit breaker, not a policy on rework ping-pong (that stays the open item named in
loopr-PRD.md section 15 -- this cap is deliberately generous enough not to fire on legitimate step11/
step12 cycling, and exists only to bound a scenario where a bug in THIS script -- not in `decide()`
-- caused it to keep re-invoking `dispatch` without the state ever reaching COMPLETE or HALT. Context.
md's soft context 2 names why this matters here specifically: the subagents this loop dispatches take
real, non-idempotent actions (file writes, git commits), so a misread exit code repeating rounds
forever would repeat real side effects, not fail cheaply. Override with --max-rounds for a genuinely
long build."""

_REPEAT_GUARD_WINDOW = 3
"""If the last N logged dispatch decisions are byte-identical in (state_id, target, build_round) --
which a healthy loop can never produce, since a completion always changes at least one of those three
fields -- something downstream of decide() (most likely dispatch-complete silently failing to mutate
state) is broken, and continuing would repeat whatever side effect the unchanging target performs.
This compares structured fields only, never decision text -- see module docstring."""

JsonDict = dict[str, object]


def _driver_log_path(state_path: Path) -> Path:
    return state_dir_for(state_path) / _DRIVER_LOG_NAME


def _append(log_path: Path, kind: str, detail: Mapping[str, object]) -> None:
    """Append one line. Mirrors src/loopr/dispatch/log.py's `append_decision` shape exactly (ts added
    here, sort_keys=True, append-only, never rewritten) so the three logs in a state directory
    (dispatch-log.jsonl, auditor-log.jsonl, driver-log.jsonl) are uniformly diffable/greppable."""
    payload: JsonDict = dict(detail)
    payload["kind"] = kind
    payload["ts"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _read(log_path: Path) -> list[JsonDict]:
    """Mirrors src/loopr/dispatch/log.py's `read_log`: an absent log reads as empty, not an error."""
    if not log_path.exists():
        return []
    records: list[JsonDict] = []
    for raw_line in log_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        records.append(json.loads(stripped))
    return records


def _check_guards(log_path: Path, max_rounds: int) -> str | None:
    """Both structural, both total over the log's own already-recorded facts, neither inspecting a
    decision's `reason`/`*_declined_because` text. Returns a HALT message, or None if clear to proceed.
    """
    dispatch_ok_records = [r for r in _read(log_path) if r.get("kind") == "dispatch_ok"]

    if len(dispatch_ok_records) >= max_rounds:
        return (
            f"driver round cap reached ({len(dispatch_ok_records)} >= {max_rounds} logged "
            "dispatch_ok rounds). This is this script's own safety guard, not a loopr dispatch HALT "
            "-- re-run with a higher --max-rounds if this build genuinely needs more rounds."
        )

    if len(dispatch_ok_records) >= _REPEAT_GUARD_WINDOW:
        window = dispatch_ok_records[-_REPEAT_GUARD_WINDOW:]
        keys = {
            (
                r["decision"]["state_id"],  # type: ignore[index]
                r["decision"]["target"],  # type: ignore[index]
                r["decision"]["build_round"],  # type: ignore[index]
            )
            for r in window
        }
        if len(keys) == 1:
            return (
                f"the last {_REPEAT_GUARD_WINDOW} dispatch decisions are identical "
                f"(state_id/target/build_round={next(iter(keys))!r}) -- a healthy loop always changes "
                "at least one of those fields after a completion, so this indicates dispatch-complete "
                "did not actually advance state (or this script mis-invoked it). Stopping rather than "
                "repeating whatever side effect the unchanging target performs."
            )
    return None


def cmd_dispatch(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    log_path = _driver_log_path(state_path)

    guard_failure = _check_guards(log_path, args.max_rounds)
    if guard_failure is not None:
        _append(log_path, "guard_halt", {"reason": guard_failure})
        print(f"HALT: {guard_failure}", file=sys.stderr)
        return _HALT

    cli_args = ["dispatch", "--state", str(state_path), "--json"]
    if args.remodernize:
        cli_args.append("--remodernize")
    if args.modernized_prd_path:
        cli_args += ["--modernized-prd-path", args.modernized_prd_path]
    if args.phase_1_spec_path:
        cli_args += ["--phase-1-spec-path", args.phase_1_spec_path]
    if args.build_complete_path:
        cli_args += ["--build-complete-path", args.build_complete_path]

    result = run_cli(cli_args)
    code = result.returncode
    stdout, stderr = result.stdout.strip(), result.stderr.strip()

    if code == _HALT:
        _append(log_path, "dispatch_halt", {"stdout": stdout, "stderr": stderr})
    elif code == _COMPLETE:
        _append(
            log_path, "dispatch_complete_terminal", {"decision": json.loads(stdout)}
        )
    elif code == _OK:
        _append(log_path, "dispatch_ok", {"decision": json.loads(stdout)})
    else:
        _append(
            log_path,
            "dispatch_unexpected_exit",
            {"exit_code": code, "stdout": stdout, "stderr": stderr},
        )

    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    return code


def cmd_complete(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    log_path = _driver_log_path(state_path)

    cli_args = ["dispatch-complete", "--state", str(state_path)]
    if args.verdict is not None:
        cli_args += ["--verdict", args.verdict]

    result = run_cli(cli_args)
    code = result.returncode
    stdout, stderr = result.stdout.strip(), result.stderr.strip()

    kind = "complete_ok" if code == _OK else "complete_error"
    _append(
        log_path,
        kind,
        {
            "exit_code": code,
            "verdict": args.verdict,
            "stdout": stdout,
            "stderr": stderr,
        },
    )

    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    return code


def cmd_log_stop(args: argparse.Namespace) -> int:
    """Pure bookkeeping -- see module docstring. Never called by `dispatch`/`complete` themselves;
    only the session calls this, after its own (unscriptable) reading of a subagent's real output."""
    state_path = Path(args.state)
    log_path = _driver_log_path(state_path)
    detail: JsonDict = {"reason": args.reason}
    if args.subagent is not None:
        detail["subagent"] = args.subagent
    _append(log_path, f"stop_{args.kind}", detail)
    print(
        f"logged: kind=stop_{args.kind} subagent={args.subagent!r} reason={args.reason!r}"
    )
    return _OK


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="driver.py")
    sub = parser.add_subparsers(dest="command", required=True)

    dispatch_p = sub.add_parser("dispatch")
    dispatch_p.add_argument("--state", required=True)
    dispatch_p.add_argument("--max-rounds", type=int, default=_DEFAULT_MAX_ROUNDS)
    dispatch_p.add_argument("--remodernize", action="store_true")
    dispatch_p.add_argument("--modernized-prd-path", default=None)
    dispatch_p.add_argument("--phase-1-spec-path", default=None)
    dispatch_p.add_argument("--build-complete-path", default=None)
    dispatch_p.set_defaults(func=cmd_dispatch)

    complete_p = sub.add_parser("complete")
    complete_p.add_argument("--state", required=True)
    complete_p.add_argument(
        "--verdict", choices=["clean", "minor", "spec_violating"], default=None
    )
    complete_p.set_defaults(func=cmd_complete)

    log_stop_p = sub.add_parser("log-stop")
    log_stop_p.add_argument("--state", required=True)
    log_stop_p.add_argument(
        "--kind", required=True, choices=["subagent_gate", "step12_uncertain"]
    )
    log_stop_p.add_argument("--reason", required=True)
    log_stop_p.add_argument("--subagent", default=None)
    log_stop_p.set_defaults(func=cmd_log_stop)

    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        preflight()
    except LooprNotInstalled as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser = _build_parser()
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
