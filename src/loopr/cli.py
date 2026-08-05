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
from loopr.customization.customize import (
    STEP10_SUBAGENT_NAME,
    STEP11_SUBAGENT_NAME,
    STEP12_SUBAGENT_NAME,
    apply_customization_response,
    apply_fidelity_judge_response,
    apply_step11_customization_response,
    apply_step11_fidelity_judge_response,
    apply_step12_customization_response,
    apply_step12_fidelity_judge_response,
    build_customization_request,
    build_fidelity_judge_request,
    build_step11_customization_request,
    build_step11_fidelity_judge_request,
    build_step12_customization_request,
    build_step12_fidelity_judge_request,
    render_step10_subagent,
    render_step11_subagent,
    render_step12_subagent,
)
from loopr.customization.fidelity import apply_judge_layer, check_fidelity
from loopr.customization.templates import (
    Step10ArtifactAmbiguityError,
    discover_template,
    extract_skeleton,
    find_gap_candidates,
    find_step10_execution_artifacts,
)
from loopr.dispatch.controller import (
    apply_completion_transition,
    apply_dispatch_transition,
    apply_remodernize_reset,
    check_coherence,
    decide,
)
from loopr.dispatch.log import append_decision, audit_step10_calls, read_log
from loopr.dispatch.render import render_halt, render_human, render_json
from loopr.errors import LooprError
from loopr.gates.gates import GateResponse
from loopr.interrogation.loop import InboundKind, InboundPayload, step
from loopr.judge.envelope import read_request, read_response
from loopr.models.common import ConditionId, CustomizationStep, DispatchStateId, GateId, Mode, Step12Verdict
from loopr.models.customization import CustomizationState
from loopr.models.dispatch import DispatchState
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
            problem_statement_revision=raw.get("problem_statement_revision"),
            acceptance_criteria_revision=raw.get("acceptance_criteria_revision"),
            scope_edges_revision=raw.get("scope_edges_revision"),
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


def cmd_customize(args: argparse.Namespace) -> int:
    """`loopr customize --step {10,11,12}`. Implements CUSTOMIZATION_PHASE_1_SPEC.md SS6.1,
    CUSTOMIZATION_PHASE_2_SPEC.md SS0. Dispatches to a per-step handler -- each step's
    CustomizationState field group (step10_*/step11_*/step12_*) is a distinct, statically-typed set
    of attributes, not a generic/reflective lookup, so each handler addresses its own fields directly
    rather than through an abstraction that would defeat mypy --strict's field-level checking."""
    if args.step == 10:
        if args.modernized_prd_path:
            print(
                "refusing to customize step10: --modernized-prd-path is invalid here -- step10 "
                "PRODUCES this artifact, it does not consume it. This flag applies to --step 11/12 "
                "only.",
                file=sys.stderr,
            )
            return exit_codes.HALT
        if args.phase_1_spec_path:
            print(
                "refusing to customize step10: --phase-1-spec-path is invalid here -- step10 "
                "PRODUCES this artifact, it does not consume it. This flag applies to --step 11/12 "
                "only.",
                file=sys.stderr,
            )
            return exit_codes.HALT
        return _cmd_customize_step10(args)
    if args.step == 11:
        return _cmd_customize_step11(args)
    return _cmd_customize_step12(args)


def _resolve_override_path(raw: str | None, flag_name: str) -> Path | None | str:
    """Shared single-flag validation for --modernized-prd-path / --phase-1-spec-path (`customize`,
    `dispatch`): a supplied path must exist and be a file, or a clear error string is returned to
    print-and-HALT on -- never a raw stack trace, never a silent fallback to the default as though
    the flag hadn't been given. Returns None if `raw` is falsy (the flag was omitted). NOT used for
    --build-complete-path -- see _resolve_build_complete_override, which has different, deliberately
    weaker validation for a real semantic reason."""
    if not raw:
        return None
    candidate = Path(raw)
    if not candidate.is_file():
        return f"{flag_name} {raw!r} does not exist or is not a file"
    return candidate


def _resolve_build_complete_override(raw: str | None) -> Path | None | str:
    """--build-complete-path is NOT validated like the two step10-artifact overrides above: those
    substitute in real content the tool needs to read, so a missing path is always a mistake. This
    flag instead names WHICH marker file to check for existence -- and "does not exist yet" is the
    normal, expected, load-bearing answer for a project that is genuinely still mid-build (the exact
    case this flag exists to make expressible; see CUSTOMIZATION_PHASE_3_SPEC.md SS4.1's amendment).
    Requiring existence up front would make that case impossible to express at all. Only rejected if
    the path exists but is not a plain file (e.g. a directory) -- a genuine, unambiguous misuse, not
    a normal "not complete yet" state. Returns None if `raw` is falsy (the flag was omitted)."""
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.exists() and not candidate.is_file():
        return f"--build-complete-path {raw!r} exists but is not a file"
    return candidate


def _resolve_step10_artifact_overrides(
    args: argparse.Namespace,
) -> tuple[Path | None, Path | None] | str:
    """Validates and resolves --modernized-prd-path / --phase-1-spec-path (step11/step12/dispatch)
    into Path overrides for find_step10_execution_artifacts. Returns (prd_override,
    phase_1_spec_override) -- either or both may be None -- on success, or an error message string to
    print and HALT on if a supplied path does not exist or is not a file."""
    prd_override = _resolve_override_path(args.modernized_prd_path, "--modernized-prd-path")
    if isinstance(prd_override, str):
        return prd_override

    phase_1_spec_override = _resolve_override_path(args.phase_1_spec_path, "--phase-1-spec-path")
    if isinstance(phase_1_spec_override, str):
        return phase_1_spec_override

    return prd_override, phase_1_spec_override


def _customize_preamble(
    args: argparse.Namespace,
) -> tuple[StateStore, InterrogationState, Path, Path, ResumingJudgeClient] | int:
    """Shared setup identical across all three steps: load state, check the six-condition gate,
    resolve any preloaded judge response against the pending request, and hand back a ready judge
    client. Returns an int (an exit code to return immediately) if that gate fails; the caller must
    check `isinstance(result, int)` before unpacking."""
    store = StateStore(Path(args.state))
    state = store.load()
    state_dir = store.dir

    if len(state.condition_results) != 6 or not all(r.overall for r in state.condition_results):
        print("refusing to customize: not all six conditions currently pass", file=sys.stderr)
        return exit_codes.HALT

    _assert_single_pending(state_dir)
    judge_p, _gate_md, _gate_meta, _question_p = _pending_paths(state_dir)

    preloaded_response: JudgeResponse | None = None
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
    return store, state, state_dir, judge_p, client


def _cmd_customize_step10(args: argparse.Namespace) -> int:
    """Implements CUSTOMIZATION_PHASE_1_SPEC.md SS6.1. Reuses the exact exit-code contract
    unchanged: 10 JUDGE_REQUIRED while a customization judge call is pending, 0 OK on success, 40
    HALT on a fidelity failure -- a fidelity failure is a HALT, not a silent retry, the same way any
    other invariant violation is."""
    preamble = _customize_preamble(args)
    if isinstance(preamble, int):
        return preamble
    store, state, state_dir, judge_p, client = preamble

    repo_root = Path(state.repo_root)
    # CUSTOMIZATION_PHASE_1_SPEC.md SS6.1a (amended 2026-08-03): the delivered artifact is now a
    # dispatchable subagent under .claude/agents/, not a free-standing prompt file. --out roots that
    # directory directly (same convention cmd_emit already uses for its own --out).
    agents_dir = Path(args.out) if args.out else repo_root / ".claude" / "agents"
    subagent_path = agents_dir / f"{STEP10_SUBAGENT_NAME}.md"

    if state.customization is None:
        template_path = discover_template(repo_root, CustomizationStep.STEP_10)
        template_text = template_path.read_text(encoding="utf-8")
        skeleton = extract_skeleton(template_text, CustomizationStep.STEP_10)
        # Structural cross-check (CUSTOMIZATION_PHASE_1_SPEC.md SS4.3, corrected 2026-08-01): the
        # gap analysis is convention-independent, so it does not share extract_skeleton's own blind
        # spot -- reported here so a mismatch is visible, not silently tolerated. It is advisory,
        # not a hard failure: it deliberately over-reports (e.g. colon-terminated sub-labels the
        # all_caps convention correctly treats as non-sections still get flagged here), by design.
        gap_candidates = find_gap_candidates(template_text, skeleton.sections)
        if gap_candidates:
            print(
                f"NOTE: gap analysis found {len(gap_candidates)} heading-shaped line(s) not in the "
                f"extracted skeleton -- review whether any of these is a missed section: "
                f"{gap_candidates}",
                file=sys.stderr,
            )
        state.customization = CustomizationState(
            step10_template_path=str(template_path), step10_skeleton=skeleton
        )

    customization = state.customization
    # step10's own flow (immediately above, or on a prior invocation) always sets both fields
    # together before they are ever read here -- CustomizationState allows them to be absent only to
    # support a state that never customized step10 at all (SS4.4 topology independence, see
    # models/customization.py), which is not this code path.
    assert customization.step10_template_path is not None
    assert customization.step10_skeleton is not None
    template_text = Path(customization.step10_template_path).read_text(encoding="utf-8")

    # The judge-drafted body is staged OUTSIDE .claude/agents/ until BOTH fidelity layers pass on it
    # -- a fidelity-failing draft must never become a live, dispatchable subagent (SS6.1a). This is
    # internal working state, alongside pending_judge.json etc., not a delivered artifact.
    draft_path = state_dir / "step10_draft.md"

    if customization.step10_output_path is None:
        request = build_customization_request(state, template_text)
        response = client.ask(request)
        if response is None:
            store.save(state)
            print(f"judge call required: {judge_p}")
            return exit_codes.JUDGE_REQUIRED
        customized_text = apply_customization_response(response)
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(customized_text, encoding="utf-8")
        customization.step10_output_path = str(draft_path)
        store.save(state)

    if customization.step10_fidelity is None or not customization.step10_fidelity.overall:
        output_path = Path(customization.step10_output_path)
        output_text = output_path.read_text(encoding="utf-8")

        output_skeleton = extract_skeleton(output_text, CustomizationStep.STEP_10)
        structural = check_fidelity(
            customization.step10_skeleton,
            output_skeleton,
            template_text,
            output_text,
            CustomizationStep.STEP_10,
        )
        if not structural.structural_pass:
            customization.step10_fidelity = structural
            store.save(state)
            print(f"HALT: fidelity check failed structurally: {structural.detail}", file=sys.stderr)
            return exit_codes.HALT

        fidelity_request = build_fidelity_judge_request(state, template_text, output_text)
        fidelity_response = client.ask(fidelity_request)
        if fidelity_response is None:
            store.save(state)
            print(f"judge call required: {judge_p}")
            return exit_codes.JUDGE_REQUIRED
        judge_passed, judge_reason = apply_fidelity_judge_response(fidelity_response)
        final = apply_judge_layer(structural, judge_passed, judge_reason)
        customization.step10_fidelity = final
        if not final.overall:
            store.save(state)
            print(f"HALT: fidelity check failed at layer 2: {judge_reason}", file=sys.stderr)
            return exit_codes.HALT

        # Both layers passed on the plain body -- promote to the live subagent registry. Frontmatter-
        # wrapping is pure post-processing (SS1, SS6.1a): fixed configuration written from constants,
        # never itself fidelity-checked, since nothing in it is drafted content. step10_output_path's
        # MEANING is unchanged ("where the fidelity-checked output landed") -- only what kind of file
        # lives there changes, and only now, at the moment it actually lands.
        agents_dir.mkdir(parents=True, exist_ok=True)
        subagent_path.write_text(render_step10_subagent(output_text), encoding="utf-8")
        customization.step10_output_path = str(subagent_path)
        store.save(state)

    print(f"step10 customized successfully: {customization.step10_output_path}")
    return exit_codes.OK


def _step10_execution_gate_message(
    step: int,
    repo_root: Path,
    prd_path_override: Path | None = None,
    phase_1_spec_path_override: Path | None = None,
) -> str | None:
    """CUSTOMIZATION_PHASE_2_SPEC.md SS1.1, shared by step11 and step12. Returns an error message if
    step10 has not actually EXECUTED in the target project, else None. Checked BEFORE
    _customize_preamble runs (not after) so a refusal here never clears an unrelated, genuinely
    pending judge/gate/question file belonging to a different step's in-flight call --
    _customize_preamble's own _clear_pending is unconditional once invoked, and step11/step12 add a
    failure path step10 alone never had. The two overrides (2026-08-04) are threaded straight through
    to find_step10_execution_artifacts -- the caller must pass the SAME resolved values here and at
    its later re-lookup, or the early gate could pass while the real lookup afterward disagrees."""
    try:
        artifacts = find_step10_execution_artifacts(
            repo_root, prd_path_override, phase_1_spec_path_override
        )
    except Step10ArtifactAmbiguityError as exc:
        return f"refusing to customize step{step}: {exc}"
    if artifacts is not None:
        return None
    return (
        f"refusing to customize step{step}: step10 has not actually executed in this project -- no "
        "modernised PRD (a *.md file with a '## MODERNIZATION CHANGELOG' heading line) found at "
        "repo root. Customizing step10 (a fidelity-passing PROMPT) is not the same as RUNNING it "
        "against the project (CUSTOMIZATION_PHASE_2_SPEC.md SS1.1). If step10's real deliverables "
        "exist but aren't auto-detectable, point at them directly with --modernized-prd-path / "
        "--phase-1-spec-path."
    )


def _cmd_customize_step11(args: argparse.Namespace) -> int:
    """Implements CUSTOMIZATION_PHASE_2_SPEC.md SS1, SS6.1a's extension to step11. Mirrors
    _cmd_customize_step10 exactly, plus the SS1.1 gating condition: refuses to run unless step10 has
    actually EXECUTED in the target project (real artifacts on disk), not merely been customized."""
    overrides = _resolve_step10_artifact_overrides(args)
    if isinstance(overrides, str):
        print(f"refusing to customize step11: {overrides}", file=sys.stderr)
        return exit_codes.HALT
    prd_override, phase_1_spec_override = overrides

    early_repo_root = Path(StateStore(Path(args.state)).load().repo_root)
    gate_message = _step10_execution_gate_message(11, early_repo_root, prd_override, phase_1_spec_override)
    if gate_message is not None:
        print(gate_message, file=sys.stderr)
        return exit_codes.HALT

    preamble = _customize_preamble(args)
    if isinstance(preamble, int):
        return preamble
    store, state, state_dir, judge_p, client = preamble

    repo_root = Path(state.repo_root)
    artifacts = find_step10_execution_artifacts(repo_root, prd_override, phase_1_spec_override)
    assert artifacts is not None  # already confirmed by the early gate check above
    _prd_path, phase_1_spec_path = artifacts
    phase_1_spec_text = phase_1_spec_path.read_text(encoding="utf-8")

    agents_dir = Path(args.out) if args.out else repo_root / ".claude" / "agents"
    subagent_path = agents_dir / f"{STEP11_SUBAGENT_NAME}.md"

    if state.customization is None:
        state.customization = CustomizationState()
    if state.customization.step11_template_path is None:
        template_path = discover_template(repo_root, CustomizationStep.STEP_11)
        template_text = template_path.read_text(encoding="utf-8")
        skeleton = extract_skeleton(template_text, CustomizationStep.STEP_11)
        gap_candidates = find_gap_candidates(template_text, skeleton.sections)
        if gap_candidates:
            print(
                f"NOTE: gap analysis found {len(gap_candidates)} heading-shaped line(s) not in the "
                f"extracted skeleton -- review whether any of these is a missed section: "
                f"{gap_candidates}",
                file=sys.stderr,
            )
        state.customization.step11_template_path = str(template_path)
        state.customization.step11_skeleton = skeleton

    customization = state.customization
    assert customization.step11_template_path is not None
    assert customization.step11_skeleton is not None
    template_text = Path(customization.step11_template_path).read_text(encoding="utf-8")

    draft_path = state_dir / "step11_draft.md"

    if customization.step11_output_path is None:
        request = build_step11_customization_request(state, template_text, phase_1_spec_text)
        response = client.ask(request)
        if response is None:
            store.save(state)
            print(f"judge call required: {judge_p}")
            return exit_codes.JUDGE_REQUIRED
        customized_text = apply_step11_customization_response(response)
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(customized_text, encoding="utf-8")
        customization.step11_output_path = str(draft_path)
        store.save(state)

    if customization.step11_fidelity is None or not customization.step11_fidelity.overall:
        output_path = Path(customization.step11_output_path)
        output_text = output_path.read_text(encoding="utf-8")

        output_skeleton = extract_skeleton(output_text, CustomizationStep.STEP_11)
        structural = check_fidelity(
            customization.step11_skeleton,
            output_skeleton,
            template_text,
            output_text,
            CustomizationStep.STEP_11,
        )
        if not structural.structural_pass:
            customization.step11_fidelity = structural
            store.save(state)
            print(f"HALT: fidelity check failed structurally: {structural.detail}", file=sys.stderr)
            return exit_codes.HALT

        fidelity_request = build_step11_fidelity_judge_request(state, template_text, output_text)
        fidelity_response = client.ask(fidelity_request)
        if fidelity_response is None:
            store.save(state)
            print(f"judge call required: {judge_p}")
            return exit_codes.JUDGE_REQUIRED
        judge_passed, judge_reason = apply_step11_fidelity_judge_response(fidelity_response)
        final = apply_judge_layer(structural, judge_passed, judge_reason)
        customization.step11_fidelity = final
        if not final.overall:
            store.save(state)
            print(f"HALT: fidelity check failed at layer 2: {judge_reason}", file=sys.stderr)
            return exit_codes.HALT

        agents_dir.mkdir(parents=True, exist_ok=True)
        subagent_path.write_text(render_step11_subagent(output_text), encoding="utf-8")
        customization.step11_output_path = str(subagent_path)
        store.save(state)

    print(f"step11 customized successfully: {customization.step11_output_path}")
    return exit_codes.OK


def _cmd_customize_step12(args: argparse.Namespace) -> int:
    """Implements CUSTOMIZATION_PHASE_2_SPEC.md SS1, SS6.1a's extension to step12. Mirrors
    _cmd_customize_step11 exactly (same SS1.1 gate, step10 does not distinguish step11 from step12
    readiness -- both depend only on step10's output, per SS4)."""
    overrides = _resolve_step10_artifact_overrides(args)
    if isinstance(overrides, str):
        print(f"refusing to customize step12: {overrides}", file=sys.stderr)
        return exit_codes.HALT
    prd_override, phase_1_spec_override = overrides

    early_repo_root = Path(StateStore(Path(args.state)).load().repo_root)
    gate_message = _step10_execution_gate_message(12, early_repo_root, prd_override, phase_1_spec_override)
    if gate_message is not None:
        print(gate_message, file=sys.stderr)
        return exit_codes.HALT

    preamble = _customize_preamble(args)
    if isinstance(preamble, int):
        return preamble
    store, state, state_dir, judge_p, client = preamble

    repo_root = Path(state.repo_root)
    artifacts = find_step10_execution_artifacts(repo_root, prd_override, phase_1_spec_override)
    assert artifacts is not None  # already confirmed by the early gate check above
    _prd_path, phase_1_spec_path = artifacts
    phase_1_spec_text = phase_1_spec_path.read_text(encoding="utf-8")

    agents_dir = Path(args.out) if args.out else repo_root / ".claude" / "agents"
    subagent_path = agents_dir / f"{STEP12_SUBAGENT_NAME}.md"

    if state.customization is None:
        state.customization = CustomizationState()
    if state.customization.step12_template_path is None:
        template_path = discover_template(repo_root, CustomizationStep.STEP_12)
        template_text = template_path.read_text(encoding="utf-8")
        skeleton = extract_skeleton(template_text, CustomizationStep.STEP_12)
        gap_candidates = find_gap_candidates(template_text, skeleton.sections)
        if gap_candidates:
            print(
                f"NOTE: gap analysis found {len(gap_candidates)} heading-shaped line(s) not in the "
                f"extracted skeleton -- review whether any of these is a missed section: "
                f"{gap_candidates}",
                file=sys.stderr,
            )
        state.customization.step12_template_path = str(template_path)
        state.customization.step12_skeleton = skeleton

    customization = state.customization
    assert customization.step12_template_path is not None
    assert customization.step12_skeleton is not None
    template_text = Path(customization.step12_template_path).read_text(encoding="utf-8")

    draft_path = state_dir / "step12_draft.md"

    if customization.step12_output_path is None:
        request = build_step12_customization_request(state, template_text, phase_1_spec_text)
        response = client.ask(request)
        if response is None:
            store.save(state)
            print(f"judge call required: {judge_p}")
            return exit_codes.JUDGE_REQUIRED
        customized_text = apply_step12_customization_response(response)
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(customized_text, encoding="utf-8")
        customization.step12_output_path = str(draft_path)
        store.save(state)

    if customization.step12_fidelity is None or not customization.step12_fidelity.overall:
        output_path = Path(customization.step12_output_path)
        output_text = output_path.read_text(encoding="utf-8")

        output_skeleton = extract_skeleton(output_text, CustomizationStep.STEP_12)
        structural = check_fidelity(
            customization.step12_skeleton,
            output_skeleton,
            template_text,
            output_text,
            CustomizationStep.STEP_12,
        )
        if not structural.structural_pass:
            customization.step12_fidelity = structural
            store.save(state)
            print(f"HALT: fidelity check failed structurally: {structural.detail}", file=sys.stderr)
            return exit_codes.HALT

        fidelity_request = build_step12_fidelity_judge_request(state, template_text, output_text)
        fidelity_response = client.ask(fidelity_request)
        if fidelity_response is None:
            store.save(state)
            print(f"judge call required: {judge_p}")
            return exit_codes.JUDGE_REQUIRED
        judge_passed, judge_reason = apply_step12_fidelity_judge_response(fidelity_response)
        final = apply_judge_layer(structural, judge_passed, judge_reason)
        customization.step12_fidelity = final
        if not final.overall:
            store.save(state)
            print(f"HALT: fidelity check failed at layer 2: {judge_reason}", file=sys.stderr)
            return exit_codes.HALT

        agents_dir.mkdir(parents=True, exist_ok=True)
        subagent_path.write_text(render_step12_subagent(output_text), encoding="utf-8")
        customization.step12_output_path = str(subagent_path)
        store.save(state)

    print(f"step12 customized successfully: {customization.step12_output_path}")
    return exit_codes.OK


def _format_dispatch_state_one_line(dispatch_state: DispatchState) -> str:
    """The one-line state summary `dispatch-complete` prints on success (CUSTOMIZATION_PHASE_3_
    SPEC.md SS4.2). Not `render_human`/`render_json` -- there is no `DispatchDecision` at this point,
    only the state a subsequent `loopr dispatch` will read."""
    active_step = dispatch_state.active_step.value if dispatch_state.active_step is not None else "none"
    verdict = (
        dispatch_state.last_step12_verdict.value
        if dispatch_state.last_step12_verdict is not None
        else "none"
    )
    return (
        f"active_step={active_step} build_round={dispatch_state.build_round} "
        f"last_step12_verdict={verdict}"
    )


def cmd_dispatch(args: argparse.Namespace) -> int:
    """`loopr dispatch`. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS4.1: names which of the three
    already-generated subagents runs next. `dispatch/controller.py`'s `check_coherence()` runs first,
    always -- an incoherent state HALTs and dispatches nothing, never step10 "to be safe"."""
    overrides = _resolve_step10_artifact_overrides(args)
    if isinstance(overrides, str):
        print(f"HALT: {overrides}", file=sys.stderr)
        return exit_codes.HALT
    prd_override, phase_1_spec_override = overrides

    build_complete_override = _resolve_build_complete_override(args.build_complete_path)
    if isinstance(build_complete_override, str):
        print(f"HALT: {build_complete_override}", file=sys.stderr)
        return exit_codes.HALT

    store = StateStore(Path(args.state))
    state = store.load()
    repo_root = Path(state.repo_root)
    dispatch_state = state.dispatch

    if args.remodernize:
        if dispatch_state.active_step is not None:
            print(
                "refusing --remodernize: active_step is already "
                f"{dispatch_state.active_step.value!r} -- cannot re-modernize on top of an "
                "in-flight step.",
                file=sys.stderr,
            )
            return exit_codes.USAGE
        dispatch_state = apply_remodernize_reset(dispatch_state)

    try:
        artifacts = find_step10_execution_artifacts(repo_root, prd_override, phase_1_spec_override)
    except Step10ArtifactAmbiguityError as exc:
        print(f"HALT: {exc}", file=sys.stderr)
        return exit_codes.HALT
    artifacts_present = artifacts is not None
    if build_complete_override is not None:
        build_complete_path = build_complete_override
        build_complete_marker_name = build_complete_override.name
    else:
        build_complete_path = repo_root / "BUILD_COMPLETE.md"
        build_complete_marker_name = "BUILD_COMPLETE.md"
    build_complete_present = build_complete_path.exists()

    coherence_failure = check_coherence(dispatch_state, artifacts_present)
    if coherence_failure is not None:
        print(render_halt(coherence_failure, dispatch_state), file=sys.stderr)
        return exit_codes.HALT

    decision = decide(dispatch_state, artifacts_present, build_complete_present)
    if decision.state_id == DispatchStateId.S0_TERMINAL:
        # decide()'s signature stays a bare bool (G5) -- it has no way to know WHICH path was
        # checked, only whether it existed. The CLI layer, which does know, overwrites the reason
        # here so the WHY line stays honest about which marker actually fired once more than one
        # marker name is in play (2026-08-05).
        decision.reason = (
            f"{build_complete_marker_name} exists at the target repository root; the build is "
            "complete."
        )
    print(render_json(decision) if args.json else render_human(decision))

    terminal = decision.state_id == DispatchStateId.S0_TERMINAL
    if args.dry_run:
        return exit_codes.COMPLETE if terminal else exit_codes.OK

    log_path = store.dir / "dispatch-log.jsonl"
    append_decision(log_path, decision)

    if terminal:
        return exit_codes.COMPLETE

    assert decision.target is not None  # unconstructable otherwise, models/dispatch.py SS3.3
    state.dispatch = apply_dispatch_transition(dispatch_state, decision.target)
    store.save(state)
    return exit_codes.OK


def cmd_dispatch_complete(args: argparse.Namespace) -> int:
    """`loopr dispatch-complete`. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS4.2: records that the
    currently-active step finished and applies the SS6.3 transition. `--verdict` has no default -- a
    defaulted verdict would be a silently-fabricated fact about a review that happened outside this
    process."""
    store = StateStore(Path(args.state))
    state = store.load()
    dispatch_state = state.dispatch

    if dispatch_state.active_step is None:
        print("refusing dispatch-complete: nothing is in flight (active_step is None).", file=sys.stderr)
        return exit_codes.USAGE

    completed_step = dispatch_state.active_step
    step12_completing = completed_step == CustomizationStep.STEP_12

    if not step12_completing and args.verdict is not None:
        print(
            f"refusing dispatch-complete: --verdict is meaningful only for step12, not "
            f"{completed_step.value!r}.",
            file=sys.stderr,
        )
        return exit_codes.USAGE
    if step12_completing and args.verdict is None:
        print("refusing dispatch-complete: step12 completion requires --verdict.", file=sys.stderr)
        return exit_codes.USAGE

    verdict = Step12Verdict(args.verdict) if args.verdict is not None else None
    state.dispatch = apply_completion_transition(dispatch_state, completed_step, verdict)
    store.save(state)
    print(_format_dispatch_state_one_line(state.dispatch))
    return exit_codes.OK


def cmd_dispatch_verify(args: argparse.Namespace) -> int:
    """`loopr dispatch-verify`. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS4.4: the third-party
    fixture runner. Loads every `*.json` fixture, feeds its state + disk facts straight to `decide()`
    (fixtures encode already-coherent states, one per enumerated `DispatchStateId`), and diffs the
    result against the fixture's `expected` block."""
    fixtures_dir = Path(args.fixtures)
    total = 0
    mismatches = 0
    for fixture_path in sorted(fixtures_dir.glob("*.json")):
        total += 1
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        dispatch_state = DispatchState.model_validate(payload["state"])
        artifacts_present = bool(payload["artifacts_present"])
        build_complete_present = bool(payload["build_complete_present"])
        decision = decide(dispatch_state, artifacts_present, build_complete_present)
        expected = payload["expected"]
        actual = {
            "state_id": decision.state_id.value,
            "target": decision.target.value if decision.target is not None else None,
            "step10_warrant": (
                decision.step10_warrant.value if decision.step10_warrant is not None else None
            ),
        }
        if actual != expected:
            print(f"MISMATCH {fixture_path.name}: expected {expected} got {actual}")
            mismatches += 1
        else:
            print(f"OK {fixture_path.name}")

    print(f"{total - mismatches}/{total} fixture(s) matched")
    return exit_codes.OK if mismatches == 0 else exit_codes.HALT


def cmd_dispatch_audit(args: argparse.Namespace) -> int:
    """`loopr dispatch-audit`. Implements CUSTOMIZATION_PHASE_3_SPEC.md SS4.5: the Opus-avoidance
    check. A separate check from the fixture suite by explicit requirement -- reads the JSONL
    dispatch log directly and reports every `loopr-step10` record, HALTing if any lacks a valid
    `Step10Warrant`."""
    log_path = Path(args.log)
    records = read_log(log_path)
    entries = audit_step10_calls(records)
    invalid = [entry for entry in entries if not entry.valid]

    for entry in entries:
        warrant_display = entry.warrant if entry.warrant is not None else "MISSING"
        round_display = entry.record.get("build_round")
        reason_display = entry.record.get("reason")
        print(f"loopr-step10 round={round_display} warrant={warrant_display} reason={reason_display}")

    if invalid:
        print(
            f"HALT: {len(invalid)} loopr-step10 dispatch(es) found with a missing or unrecognised "
            "warrant.",
            file=sys.stderr,
        )
        return exit_codes.HALT

    print(f"{len(entries)} loopr-step10 dispatch(es) found, all carrying a valid warrant.")
    return exit_codes.OK


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

    customize_p = subparsers.add_parser("customize")
    customize_p.add_argument("--state", required=True)
    customize_p.add_argument("--step", type=int, required=True, choices=[10, 11, 12])
    customize_p.add_argument("--out", default=None)
    customize_p.add_argument("--judge-response", default=None)
    # Manual override for find_step10_execution_artifacts' SS1.1 gate (2026-08-04): --step 11/12
    # only -- step10 PRODUCES these artifacts, it does not consume them (validated in cmd_customize).
    # A mature repo can legitimately carry more than one valid phase-spec artifact permanently, so
    # this is a standing override, not a one-time cleanup flag.
    customize_p.add_argument("--modernized-prd-path", default=None)
    customize_p.add_argument("--phase-1-spec-path", default=None)
    customize_p.set_defaults(func=cmd_customize)

    dispatch_p = subparsers.add_parser("dispatch")
    dispatch_p.add_argument("--state", required=True)
    dispatch_p.add_argument("--json", action="store_true")
    dispatch_p.add_argument("--dry-run", action="store_true")
    dispatch_p.add_argument("--remodernize", action="store_true")
    # Same override mechanism as `customize` (2026-08-04) -- dispatch calls the same
    # find_step10_execution_artifacts gate and can hit the same standing ambiguity, with no other
    # path for a human to resolve it (found live via this project's own first real dispatch run).
    dispatch_p.add_argument("--modernized-prd-path", default=None)
    dispatch_p.add_argument("--phase-1-spec-path", default=None)
    # A repo can host more than one loopr-managed build with its own completion marker (this repo
    # does: BUILD_COMPLETE.md for the base module, CUSTOMIZATION_BUILD_COMPLETE.md for this series)
    # -- --state tracks one specific project, so the S0_TERMINAL check must be scoped to that
    # project's own marker, not a hardcoded repo-root filename that happens to belong to a different
    # build (2026-08-05, found live via this project's own first real dispatch run).
    dispatch_p.add_argument("--build-complete-path", default=None)
    dispatch_p.set_defaults(func=cmd_dispatch)

    dispatch_complete_p = subparsers.add_parser("dispatch-complete")
    dispatch_complete_p.add_argument("--state", required=True)
    dispatch_complete_p.add_argument(
        "--verdict", default=None, choices=["clean", "minor", "spec_violating"]
    )
    dispatch_complete_p.set_defaults(func=cmd_dispatch_complete)

    dispatch_verify_p = subparsers.add_parser("dispatch-verify")
    dispatch_verify_p.add_argument("--fixtures", required=True)
    dispatch_verify_p.set_defaults(func=cmd_dispatch_verify)

    dispatch_audit_p = subparsers.add_parser("dispatch-audit")
    dispatch_audit_p.add_argument("--log", required=True)
    dispatch_audit_p.set_defaults(func=cmd_dispatch_audit)

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
