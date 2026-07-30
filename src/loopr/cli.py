"""Command dispatch and the exit-code contract. Implements PHASE_1_SPEC.md SS6.1.

loopr makes no outbound network call and reads no API key -- the judge is either answered
in-process (ScriptedJudgeClient, used only in tests/replay) or by writing a request envelope and
suspending (AgentJudgeClient / ResumingAgentJudgeClient), never by calling a model API directly.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from loopr import exit_codes
from loopr.artifacts.baby_prd import render_baby_prd
from loopr.artifacts.conformance_ledger import render_conformance_ledger
from loopr.artifacts.context_md import render_context_md
from loopr.errors import LooprError
from loopr.gates.gates import GateResponse
from loopr.interrogation.loop import InboundKind, InboundPayload, step
from loopr.judge.envelope import read_request, read_response
from loopr.models.common import ConditionId, GateId, Mode
from loopr.models.interrogation import InterrogationState
from loopr.models.judge import JudgeRequest, JudgeResponse
from loopr.state.store import StateStore


class ResumingJudgeClient:
    """Answers exactly one pending request from a preloaded response; anything else falls back to
    writing a fresh pending envelope and suspending -- never a live model call.

    A preloaded response is only ever matched against the FIRST judge.ask() call made inside a given
    step() invocation. step()'s brownfield precondition block (relevance/classification) can issue
    its own judge.ask() before the call the caller actually meant to answer ever gets a turn -- if
    that happens, `used` stays False and `diverged_request` records what got asked instead, so the
    caller (cmd_step) can raise loudly rather than silently losing the supplied response."""

    def __init__(self, pending_path: Path, preloaded: JudgeResponse | None) -> None:
        self._pending_path = pending_path
        self._preloaded = preloaded
        self._used = False
        self.diverged_request: JudgeRequest | None = None

    @property
    def used(self) -> bool:
        return self._used

    def ask(self, request: JudgeRequest) -> JudgeResponse | None:
        if self._preloaded is not None and not self._used and self._preloaded.call_id == request.call_id:
            self._used = True
            return self._preloaded
        if self._preloaded is not None and not self._used and self.diverged_request is None:
            self.diverged_request = request
        from loopr.judge.envelope import write_request

        write_request(self._pending_path, request)
        return None


def _pending_paths(state_dir: Path) -> tuple[Path, Path, Path, Path]:
    return (
        state_dir / "pending_judge.json",
        state_dir / "pending_gate.md",
        state_dir / "pending_gate.json",
        state_dir / "pending_question.json",
    )


def _assert_single_pending(state_dir: Path) -> None:
    judge_p, gate_md, gate_meta, question_p = _pending_paths(state_dir)
    pending = [p for p in (judge_p, gate_md, question_p) if p.exists()]
    if len(pending) > 1:
        raise LooprError(f"more than one pending file exists simultaneously: {pending}")


def _clear_pending(state_dir: Path) -> None:
    for path in _pending_paths(state_dir):
        path.unlink(missing_ok=True)


def _default_state_path(repo: str) -> Path:
    return Path(repo).resolve() / ".loopr-state" / "state.json"


def cmd_init(args: argparse.Namespace) -> int:
    state_path = Path(args.state) if args.state else _default_state_path(args.repo)
    store = StateStore(state_path)
    if store.exists():
        print(f"state already exists at {store.path}", file=sys.stderr)
        return exit_codes.USAGE
    mode = Mode(args.mode)
    brownfield = None
    if mode == Mode.BROWNFIELD:
        from loopr.models.brownfield import BrownfieldState

        brownfield = BrownfieldState()
    state = InterrogationState(
        mode=mode,
        repo_root=str(Path(args.repo).resolve()),
        max_rounds=args.max_rounds,
        brownfield=brownfield,
    )
    store.save(state)
    print(f"initialised {store.path}")
    return exit_codes.OK


def cmd_step(args: argparse.Namespace) -> int:
    store = StateStore(Path(args.state))
    state = store.load()
    state_dir = store.dir
    _assert_single_pending(state_dir)

    judge_p, gate_md, gate_meta, question_p = _pending_paths(state_dir)

    inbound: InboundPayload | None = None
    preloaded_response: JudgeResponse | None = None

    if args.gate_response:
        raw = json.loads(Path(args.gate_response).read_text(encoding="utf-8"))
        meta = json.loads(gate_meta.read_text(encoding="utf-8")) if gate_meta.exists() else {}
        gate_id_raw = meta.get("gate")
        if gate_id_raw is None:
            raise LooprError("no pending gate metadata found; cannot apply --gate-response")
        gate_response = GateResponse(
            gate=GateId(gate_id_raw),
            payload_digest=meta.get("payload_digest", ""),
            confirmed=raw.get("confirmed", False),
            amendment=raw.get("amendment"),
            boundary_text=raw.get("boundary_text"),
            declined=raw.get("declined", False),
            touched_surface=raw.get("touched_surface"),
        )
        inbound = InboundPayload(kind=InboundKind.GATE, gate_response=gate_response)

    elif args.answer:
        if not question_p.exists():
            raise LooprError("no pending question to answer")
        meta = json.loads(question_p.read_text(encoding="utf-8"))
        answer_text = Path(args.answer).read_text(encoding="utf-8").strip()
        inbound = InboundPayload(
            kind=InboundKind.ANSWER,
            answer_target=ConditionId(meta["target"]),
            answer_text=answer_text,
        )

    if args.judge_response:
        preloaded_response = read_response(Path(args.judge_response))
        if judge_p.exists():
            pending_request = read_request(judge_p)
            if pending_request.call_id != preloaded_response.call_id:
                raise LooprError(
                    f"judge response call_id={preloaded_response.call_id!r} does not match "
                    f"pending request call_id={pending_request.call_id!r}"
                )

    _clear_pending(state_dir)
    client = ResumingJudgeClient(judge_p, preloaded_response)
    outcome = step(state, client, inbound)

    if preloaded_response is not None and not client.used:
        diverged = client.diverged_request
        diverged_desc = (
            f"call_id={diverged.call_id!r} call_type={diverged.call_type.value!r}"
            if diverged is not None
            else "(no other call was made)"
        )
        raise LooprError(
            f"judge response call_id={preloaded_response.call_id!r} was never applied: a different "
            f"judge call became pending first this invocation ({diverged_desc}). The supplied "
            "response was discarded rather than silently applied elsewhere -- re-invoke `step` with "
            "no --judge-response to see the newly pending request, answer it, then resupply this "
            "response once its call becomes the active pending call."
        )

    store.save(outcome.state)

    if outcome.exit_code == exit_codes.GATE_REQUIRED and outcome.pending_gate_payload is not None:
        gate_md.write_text(outcome.pending_gate_payload.body_markdown, encoding="utf-8")
        gate_meta.write_text(
            json.dumps(
                {
                    "gate": outcome.pending_gate_payload.gate.value,
                    "payload_digest": outcome.pending_gate_payload.digest,
                }
            ),
            encoding="utf-8",
        )
    elif outcome.exit_code == exit_codes.QUESTION_REQUIRED and outcome.pending_question_text is not None:
        target = outcome.pending_question_target
        question_p.write_text(
            json.dumps(
                {"text": outcome.pending_question_text, "target": target.value if target else None}
            ),
            encoding="utf-8",
        )
        print(outcome.pending_question_text)
    elif outcome.exit_code == exit_codes.JUDGE_REQUIRED:
        print(f"judge call required: {judge_p}")
    elif outcome.exit_code == exit_codes.COMPLETE:
        print("all six conditions satisfied; run `loopr emit` to render artifacts")

    return outcome.exit_code


def cmd_status(args: argparse.Namespace) -> int:
    store = StateStore(Path(args.state))
    state = store.load()
    if args.json:
        print(state.model_dump_json(indent=2))
        return exit_codes.OK
    print(f"mode={state.mode.value} round={state.round}/{state.max_rounds}")
    for result in state.condition_results:
        print(f"  {result.condition.value}: overall={result.overall} -- {result.detail}")
    return exit_codes.OK


def cmd_emit(args: argparse.Namespace) -> int:
    store = StateStore(Path(args.state))
    state = store.load()

    if len(state.condition_results) != 6 or not all(r.overall for r in state.condition_results):
        print("refusing to emit: not all six conditions currently pass", file=sys.stderr)
        return exit_codes.HALT

    out_dir = Path(args.out) if args.out else Path(state.repo_root) / ".claude" / "loopr"
    out_dir.mkdir(parents=True, exist_ok=True)

    tldr = (
        f"{state.problem_statement} -- {len(state.acceptance_criteria)} acceptance criterion(ia), "
        f"{len(state.scope_edges)} scope edge(s) named."
    )
    (out_dir / "baby_prd.md").write_text(render_baby_prd(state, tldr), encoding="utf-8")
    (out_dir / "context.md").write_text(render_context_md(state), encoding="utf-8")
    if state.brownfield is not None:
        (out_dir / "conformance-ledger.md").write_text(
            render_conformance_ledger(state), encoding="utf-8"
        )

    print(f"emitted artifacts to {out_dir}")
    return exit_codes.COMPLETE


def cmd_replay(args: argparse.Namespace) -> int:
    store = StateStore(Path(args.state))
    state = store.load()
    fixtures_dir = Path(args.fixtures)

    divergences = 0
    for exchange in state.judge_log:
        fixture_path = fixtures_dir / f"{exchange.request.call_id}.json"
        if not fixture_path.exists():
            print(f"MISSING fixture for call_id={exchange.request.call_id}")
            divergences += 1
            continue
        fixture_response = JudgeResponse.model_validate_json(
            fixture_path.read_text(encoding="utf-8")
        )
        if fixture_response != exchange.response:
            print(f"DIVERGENT call_id={exchange.request.call_id}")
            divergences += 1
        else:
            print(f"OK call_id={exchange.request.call_id}")

    print(f"{divergences} divergence(s) out of {len(state.judge_log)} logged exchange(s)")
    return exit_codes.OK if divergences == 0 else exit_codes.HALT


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="loopr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_p = subparsers.add_parser("init")
    init_p.add_argument("--repo", required=True)
    init_p.add_argument("--mode", required=True, choices=["greenfield", "brownfield"])
    init_p.add_argument("--state", default=None)
    init_p.add_argument("--max-rounds", type=int, default=8)
    init_p.set_defaults(func=cmd_init)

    step_p = subparsers.add_parser("step")
    step_p.add_argument("--state", required=True)
    step_p.add_argument("--judge-response", default=None)
    step_p.add_argument("--gate-response", default=None)
    step_p.add_argument("--answer", default=None)
    step_p.set_defaults(func=cmd_step)

    status_p = subparsers.add_parser("status")
    status_p.add_argument("--state", required=True)
    status_p.add_argument("--json", action="store_true")
    status_p.set_defaults(func=cmd_status)

    emit_p = subparsers.add_parser("emit")
    emit_p.add_argument("--state", required=True)
    emit_p.add_argument("--out", default=None)
    emit_p.set_defaults(func=cmd_emit)

    replay_p = subparsers.add_parser("replay")
    replay_p.add_argument("--state", required=True)
    replay_p.add_argument("--fixtures", required=True)
    replay_p.set_defaults(func=cmd_replay)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result: int = args.func(args)
        return result
    except LooprError as exc:
        print(f"HALT: {exc}", file=sys.stderr)
        return exit_codes.HALT


if __name__ == "__main__":
    sys.exit(main())
