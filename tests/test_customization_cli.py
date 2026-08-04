"""`loopr customize --step 10` end to end. Implements CUSTOMIZATION_PHASE_1_SPEC.md SS8.

Every SS8 acceptance criterion is demonstrated here against the real CLI, not merely asserted at
the unit level.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopr import exit_codes
from loopr.cli import main
from loopr.customization.customize import (
    STEP10_ALLOWLIST_INPUT_DEPENDENCIES,
    STEP10_SUBAGENT_DESCRIPTION,
    STEP10_SUBAGENT_MODEL,
    STEP10_SUBAGENT_NAME,
    STEP11_ALLOWLIST_INPUT_DEPENDENCIES,
    STEP12_ALLOWLIST_INPUT_DEPENDENCIES,
    apply_customization_response,
    build_customization_request,
    build_step11_customization_request,
    build_step12_customization_request,
)
from loopr.customization.templates import (
    STEP10_PLACEHOLDER_ALLOWLIST,
    STEP11_PLACEHOLDER_ALLOWLIST,
    STEP12_PLACEHOLDER_ALLOWLIST,
    find_fill_in_blocks,
    find_unclassified_bracket_spans,
    unresolved_placeholders,
)
from loopr.models.common import CustomizationStep, Mode, Verdict
from loopr.models.interrogation import InterrogationState
from loopr.models.judge import JudgeResponse
from loopr.state.store import StateStore

REAL_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "prompts" / "Template_prompts"

# Every fixture carries a dummy title line first, matching real STEP_10's own shape -- extract_
# skeleton always excludes line 1 as the declared title exclusion (CUSTOMIZATION_PHASE_1_SPEC.md
# SS4.3), so a fixture without one would silently lose its own first real section to that rule.
_TITLE = "DOC TITLE (TEMPLATE)\n\n"

_STEP10_TEMPLATE = (
    _TITLE
    + "ROLE\n\nAct as an architect for [PROJECT_NAME].\n\n"
    + "1. FIRST SECTION\n\nDo the first thing for [PROJECT_REPO_NAME].\n\n"
    + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
)

_GOOD_CUSTOMIZATION = (
    _TITLE
    + "ROLE\n\nAct as an architect for Acme Corp.\n\n"
    + "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
    + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
)

_RESTRUCTURED_CUSTOMIZATION = (
    _TITLE
    + "ROLE\n\nAct as an architect for Acme Corp.\n\n"
    + "1. FIRST SECTION\n\nDo the first thing for acme-repo.\n\n"
    # section 2 dropped
)

_PLACEHOLDER_DELETION_ONLY = (
    _TITLE
    + "ROLE\n\nAct as an architect for the project.\n\n"
    + "1. FIRST SECTION\n\nDo the first thing for the repo.\n\n"
    + "2. SECOND SECTION\n\nDo the second thing. Mark anything unverifiable as [UNVERIFIED].\n"
)


def _seed_templates(repo: Path) -> None:
    templates_dir = repo / "prompts" / "Template_prompts"
    templates_dir.mkdir(parents=True)
    (templates_dir / "STEP_10").write_text(_STEP10_TEMPLATE, encoding="utf-8")


def _parse_subagent(text: str) -> tuple[dict[str, str], str]:
    """Splits a rendered subagent file into (frontmatter dict, body) for test assertions -- a
    deliberately simple, test-only parser (no YAML dependency, matching the project's own
    single-runtime-dependency invariant); real frontmatter values here are plain single-line scalars
    with no colons of their own, so naive key/value splitting on the first ':' is safe."""
    assert text.startswith("---\n"), "subagent file must start with YAML frontmatter"
    _, frontmatter_block, body = text.split("---\n", 2)
    frontmatter: dict[str, str] = {}
    for line in frontmatter_block.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip()
    return frontmatter, body.lstrip("\n")


def _answer_pending_judge(state_dir: Path, answer_path: Path) -> None:
    request = json.loads((state_dir / "pending_judge.json").read_text(encoding="utf-8"))
    call_type = request["call_type"]
    if call_type == "bf_classify":
        response = JudgeResponse(call_id=request["call_id"], verdict=Verdict.CONFORM, reason="fine")
    elif call_type == "bf_relevance":
        candidates = request["inputs"]["candidate_files"]
        response = JudgeResponse(call_id=request["call_id"], selected_files=candidates, reason="all relevant")
    elif call_type == "boundary_proposal":
        response = JudgeResponse(call_id=request["call_id"], drafted_text="drafted boundary", reason="drafted")
    else:
        response = JudgeResponse(call_id=request["call_id"], passed=True, reason="ok")
    answer_path.write_text(response.model_dump_json(), encoding="utf-8")


def _drive_to_complete(state_path: Path, state_dir: Path, tmp_path: Path) -> None:
    answer_path = tmp_path / "answer.json"
    judge_response_path = tmp_path / "judge_response.json"
    answers = iter(
        [
            "on-call stops losing an hour to manual failover",
            "the page returns a 200 within 5 seconds",
            "mobile app is deferred -- not funded this quarter",
            "no boss-said constraints -- clean slate",
        ]
    )
    code = main(["step", "--state", str(state_path)])
    for _ in range(100):
        if code == exit_codes.COMPLETE:
            return
        if code == exit_codes.JUDGE_REQUIRED:
            _answer_pending_judge(state_dir, judge_response_path)
            code = main(["step", "--state", str(state_path), "--judge-response", str(judge_response_path)])
        elif code == exit_codes.QUESTION_REQUIRED:
            try:
                text = next(answers)
            except StopIteration:
                text = "no further open questions"
            answer_path.write_text(text, encoding="utf-8")
            code = main(["step", "--state", str(state_path), "--answer", str(answer_path)])
        elif code == exit_codes.GATE_REQUIRED:
            meta = json.loads((state_dir / "pending_gate.json").read_text(encoding="utf-8"))
            gate_response: dict[str, object] = {"confirmed": True}
            if meta["gate"] == "gate_2_boundary":
                gate_response["boundary_text"] = "this phase covers failover automation only"
            path = tmp_path / "gate_response.json"
            path.write_text(json.dumps(gate_response), encoding="utf-8")
            code = main(["step", "--state", str(state_path), "--gate-response", str(path)])
        else:
            raise AssertionError(f"unexpected exit code {code}")
    raise AssertionError("did not reach COMPLETE")


@pytest.fixture
def confirmed_state(tmp_path: Path) -> tuple[Path, Path]:
    """A repo with real STEP_10-shaped templates and a state file driven to COMPLETE."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_templates(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)
    return repo, state_path


def test_customize_refuses_before_six_conditions_pass(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_templates(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0

    code = main(["customize", "--state", str(state_path), "--step", "10"])
    assert code == exit_codes.HALT


def test_customize_step10_produces_fidelity_verified_output(
    confirmed_state: tuple[Path, Path], tmp_path: Path
) -> None:
    repo, state_path = confirmed_state
    judge_response_path = tmp_path / "customize_judge_response.json"

    code = main(["customize", "--state", str(state_path), "--step", "10"])
    assert code == exit_codes.JUDGE_REQUIRED
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request["call_type"] == "step10_customization"

    response = JudgeResponse(call_id=request["call_id"], drafted_text=_GOOD_CUSTOMIZATION, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED  # now the layer-2 fidelity judge call
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request2["call_type"] == "step10_fidelity_judge"

    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="genuinely specific")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    store = StateStore(state_path)
    final_state = store.load()
    assert final_state.customization is not None
    assert final_state.customization.step10_fidelity is not None
    assert final_state.customization.step10_fidelity.overall is True

    assert final_state.customization.step10_output_path is not None
    output_path = Path(final_state.customization.step10_output_path)
    # CUSTOMIZATION_PHASE_1_SPEC.md SS6.1a: the delivered artifact is a dispatchable subagent under
    # .claude/agents/, not a free-standing prompt file.
    assert output_path == repo / ".claude" / "agents" / f"{STEP10_SUBAGENT_NAME}.md"
    output_text = output_path.read_text(encoding="utf-8")

    frontmatter, body = _parse_subagent(output_text)
    assert frontmatter["name"] == STEP10_SUBAGENT_NAME
    assert frontmatter["description"] == STEP10_SUBAGENT_DESCRIPTION
    assert frontmatter["model"] == STEP10_SUBAGENT_MODEL
    # STEP 3: fidelity checking applies to the BODY, unchanged in substance from before this
    # amendment -- same assertions as the pre-subagent version of this test.
    # JudgeResponse.drafted_text is whitespace-stripped by LooprBase's str_strip_whitespace=True.
    assert body.rstrip("\n") == _GOOD_CUSTOMIZATION.strip()
    assert "[UNVERIFIED]" in body
    assert "[PROJECT_NAME]" not in body


def test_customize_rejects_restructured_output(confirmed_state: tuple[Path, Path], tmp_path: Path) -> None:
    """SS8.4, demonstrated against the real CLI: a restructured customization HALTs."""
    repo, state_path = confirmed_state
    judge_response_path = tmp_path / "customize_judge_response.json"

    code = main(["customize", "--state", str(state_path), "--step", "10"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response = JudgeResponse(
        call_id=request["call_id"], drafted_text=_RESTRUCTURED_CUSTOMIZATION, reason="drafted"
    )
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.HALT

    store = StateStore(state_path)
    final_state = store.load()
    assert final_state.customization is not None
    assert final_state.customization.step10_fidelity is not None
    assert final_state.customization.step10_fidelity.structural_pass is False
    assert final_state.customization.step10_fidelity.overall is False
    # A fidelity-failing draft must never be promoted into the live, dispatchable subagent registry
    # (CUSTOMIZATION_PHASE_1_SPEC.md SS6.1a) -- step10_output_path still points at the internal
    # staging draft, not .claude/agents/.
    subagent_path = repo / ".claude" / "agents" / f"{STEP10_SUBAGENT_NAME}.md"
    assert not subagent_path.exists()
    assert Path(final_state.customization.step10_output_path) != subagent_path


def test_customize_rejects_placeholder_deletion_only_via_layer2(
    confirmed_state: tuple[Path, Path], tmp_path: Path
) -> None:
    """SS8.5, demonstrated against the real CLI: layer 1 cannot catch generic filler (skeleton and
    placeholders are both technically fine), but layer 2's judge rejects it."""
    repo, state_path = confirmed_state
    judge_response_path = tmp_path / "customize_judge_response.json"

    main(["customize", "--state", str(state_path), "--step", "10"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response = JudgeResponse(
        call_id=request["call_id"], drafted_text=_PLACEHOLDER_DELETION_ONLY, reason="drafted"
    )
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED  # layer 1 passed -- reached the layer-2 judge call
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request2["call_type"] == "step10_fidelity_judge"

    response2 = JudgeResponse(
        call_id=request2["call_id"], passed=False, reason="generic filler, placeholders merely deleted"
    )
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.HALT

    store = StateStore(state_path)
    final_state = store.load()
    assert final_state.customization is not None
    assert final_state.customization.step10_fidelity is not None
    assert final_state.customization.step10_fidelity.overall is False
    assert final_state.customization.step10_fidelity.judge_pass is False
    # Layer 2 rejected it too -- still never promoted (same guard as the layer-1 rejection above).
    subagent_path = repo / ".claude" / "agents" / f"{STEP10_SUBAGENT_NAME}.md"
    assert not subagent_path.exists()
    assert Path(final_state.customization.step10_output_path) != subagent_path


def test_judge_request_never_carries_frontmatter_content(
    confirmed_state: tuple[Path, Path], tmp_path: Path
) -> None:
    """CUSTOMIZATION_PHASE_1_SPEC.md SS1/SS6.1a's critical design point, demonstrated rather than
    merely implemented-correctly-by-inspection: the subagent frontmatter (name/description/model) is
    FIXED CONFIGURATION written from constants -- it must never be a JudgeRequest input, never appear
    anywhere in what the judge is shown, and drafting a body must never require or produce it."""
    repo, state_path = confirmed_state

    code = main(["customize", "--state", str(state_path), "--step", "10"])
    assert code == exit_codes.JUDGE_REQUIRED
    request_raw = (state_path.parent / "pending_judge.json").read_text(encoding="utf-8")
    request = json.loads(request_raw)

    # The declared, version-gated input scope is unchanged by the subagent-dispatch amendment --
    # exactly what CUSTOMIZATION_PHASE_1_SPEC.md SS4.1 specified, plus `repo_root` (added 2026-08-04:
    # the judge cannot honestly resolve [PROJECT_NAME]/[PROJECT_REPO_NAME]/[PRD_FILENAME], all three
    # genuinely on STEP10_PLACEHOLDER_ALLOWLIST, without it).
    assert set(request["inputs"].keys()) == {
        "template_text",
        "repo_root",
        "problem_statement",
        "acceptance_criteria",
        "scope_edges",
        "boundary",
        "context_notes",
        "conformance_summary",
    }
    # Nothing in the full request envelope (inputs, rubric_text, or otherwise) carries a frontmatter
    # line -- checked as an exact frontmatter-line substring, not just the bare word, since e.g.
    # "opus" alone could plausibly appear in unrelated prose.
    assert f"name: {STEP10_SUBAGENT_NAME}" not in request_raw
    assert f"model: {STEP10_SUBAGENT_MODEL}" not in request_raw
    assert STEP10_SUBAGENT_DESCRIPTION not in request_raw

    # apply_customization_response returns the BODY alone -- frontmatter-wrapping happens nowhere
    # inside the judge-request/response layer, only later, as separate post-processing in cli.py.
    response = JudgeResponse(call_id=request["call_id"], drafted_text=_GOOD_CUSTOMIZATION, reason="drafted")
    body = apply_customization_response(response)
    assert not body.startswith("---")
    assert f"model: {STEP10_SUBAGENT_MODEL}" not in body
    assert f"name: {STEP10_SUBAGENT_NAME}" not in body


def test_topology_independence_resume_from_state_produces_byte_identical_output(
    confirmed_state: tuple[Path, Path], tmp_path: Path
) -> None:
    """SS8.7: a customization interrupted after the judge call and resumed from the state file in a
    fresh process produces byte-identical output to one completed in a single process. Simulated
    here by driving two independent state files with the identical judge response content -- one
    completed straight through, one "interrupted" by reloading the state from disk between calls
    (the same StateStore.load()/save() round trip a genuinely separate process would use)."""
    repo, state_path = confirmed_state

    # Run A: straight through, no simulated interruption.
    judge_response_path = tmp_path / "jr_a.json"
    main(["customize", "--state", str(state_path), "--step", "10"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response = JudgeResponse(call_id=request["call_id"], drafted_text=_GOOD_CUSTOMIZATION, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    main(["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)])
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="specific")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK
    customization_a = StateStore(state_path).load().customization
    assert customization_a is not None and customization_a.step10_output_path is not None
    assert Path(customization_a.step10_output_path) == repo / ".claude" / "agents" / f"{STEP10_SUBAGENT_NAME}.md"
    output_a = Path(customization_a.step10_output_path).read_text(encoding="utf-8")

    # Run B: a SECOND, independent confirmed repo/state -- "interrupted" by explicitly reloading
    # the state from disk (StateStore round trip) between every single step, exactly what a fresh
    # process resuming from the state file alone would do, with no session memory carried over.
    repo_b = tmp_path / "repo_b"
    repo_b.mkdir()
    _seed_templates(repo_b)
    state_path_b = tmp_path / "state_b.json"
    main(["init", "--repo", str(repo_b), "--mode", "greenfield", "--state", str(state_path_b)])
    store_b = StateStore(state_path_b)
    _drive_to_complete(state_path_b, store_b.dir, tmp_path)

    # Fresh "process": nothing from run A's Python objects is reused below this point --
    # every step reloads via a brand-new StateStore(...).load() call against state_path_b.
    main(["customize", "--state", str(state_path_b), "--step", "10"])
    request_b = json.loads((state_path_b.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response_b = JudgeResponse(call_id=request_b["call_id"], drafted_text=_GOOD_CUSTOMIZATION, reason="drafted")
    judge_response_path.write_text(response_b.model_dump_json(), encoding="utf-8")
    main(
        ["customize", "--state", str(state_path_b), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    request_b2 = json.loads((state_path_b.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response_b2 = JudgeResponse(call_id=request_b2["call_id"], passed=True, reason="specific")
    judge_response_path.write_text(response_b2.model_dump_json(), encoding="utf-8")
    code_b = main(
        ["customize", "--state", str(state_path_b), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code_b == exit_codes.OK
    customization_b = StateStore(state_path_b).load().customization
    assert customization_b is not None and customization_b.step10_output_path is not None
    output_b = Path(customization_b.step10_output_path).read_text(encoding="utf-8")

    assert output_a == output_b, "resumed-from-disk output must be byte-identical to the direct run"


def test_topology_independence_no_session_identity_in_state(confirmed_state: tuple[Path, Path]) -> None:
    """SS8.7, inspected: no field anywhere in CustomizationState/InterrogationState encodes session
    identity or role."""
    from loopr.models.customization import CustomizationState
    from loopr.models.interrogation import InterrogationState

    for model in (CustomizationState, InterrogationState):
        for field_name in model.model_fields:
            lowered = field_name.lower()
            assert "session" not in lowered
            assert "role" not in lowered
            assert "architect" not in lowered
            assert "executor" not in lowered


def _seed_real_step10_template(repo: Path) -> None:
    templates_dir = repo / "prompts" / "Template_prompts"
    templates_dir.mkdir(parents=True)
    real_text = (REAL_TEMPLATES_DIR / "STEP_10").read_text(encoding="utf-8")
    (templates_dir / "STEP_10").write_text(real_text, encoding="utf-8")


def _plausible_real_step10_customization(template_text: str) -> str:
    """A genuinely-passing customization of the REAL STEP_10 template: every customizer-resolvable
    placeholder filled with project-specific values, [RESEARCH FOCUS]/[PHASE_COUNT]/[UNVERIFIED]
    left untouched (they are not placeholders -- CUSTOMIZATION_PHASE_1_SPEC.md SS4.2), and the
    hard-boundary block replaced with real, project-specific prose (SS4.2's third trap)."""
    output = template_text
    for token, value in {
        "[PROJECT_NAME]": "Acme Ledger",
        "[PROJECT_REPO_NAME]": "acme-ledger",
        "[PRD_FILENAME]": "ACME_LEDGER_PRD.md",
    }.items():
        output = output.replace(token, value)
    [block] = find_fill_in_blocks(template_text, CustomizationStep.STEP_10)
    output = output.replace(
        block,
        "This build may never expose, compute, or feed back into Acme Ledger's proprietary "
        "reconciliation algorithm, whether directly or by wrapping it.",
    )
    return output


def test_full_cli_run_against_real_step10_template_produces_passing_subagent(tmp_path: Path) -> None:
    """SS8 re-demonstrated end to end against the REAL template file in prompts/Template_prompts/
    (every other test in this file uses a small synthetic fixture for isolation) -- a full
    CLI-driven `loopr customize --step 10` run against a real confirmed state produces a real
    .claude/agents/loopr-step10.md with correct frontmatter and a fidelity-passing body. This is the
    output-format change's own gate: the prior Phase 1 green was established against a plain-file
    shape that no longer exists, so it carries no weight for this amendment on its own."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step10_template(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)

    template_text = (repo / "prompts" / "Template_prompts" / "STEP_10").read_text(encoding="utf-8")
    customized = _plausible_real_step10_customization(template_text)
    judge_response_path = tmp_path / "real_judge_response.json"

    code = main(["customize", "--state", str(state_path), "--step", "10"])
    assert code == exit_codes.JUDGE_REQUIRED
    request = json.loads((store.dir / "pending_judge.json").read_text(encoding="utf-8"))
    assert request["call_type"] == "step10_customization"
    response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")

    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED  # layer 1 passed on the real 9-section skeleton
    request2 = json.loads((store.dir / "pending_judge.json").read_text(encoding="utf-8"))
    assert request2["call_type"] == "step10_fidelity_judge"
    response2 = JudgeResponse(
        call_id=request2["call_id"],
        passed=True,
        reason="names Acme Ledger's real repo, PRD filename, and reconciliation-algorithm boundary",
    )
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")

    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    subagent_path = repo / ".claude" / "agents" / f"{STEP10_SUBAGENT_NAME}.md"
    assert subagent_path.exists()
    frontmatter, body = _parse_subagent(subagent_path.read_text(encoding="utf-8"))
    assert frontmatter["name"] == STEP10_SUBAGENT_NAME
    assert frontmatter["model"] == STEP10_SUBAGENT_MODEL
    assert frontmatter["description"] == STEP10_SUBAGENT_DESCRIPTION

    # Body-level checks -- the same fidelity substance as before this amendment, now inside a
    # subagent file's body instead of being the whole file.
    assert "[RESEARCH FOCUS]" in body  # runtime-derived, must survive (SS4.2)
    assert "[PHASE_COUNT]" in body  # runtime-derived, must survive (SS4.2)
    assert "[UNVERIFIED]" in body  # non-placeholder tag, must survive (SS4.2)
    assert "[PROJECT_NAME]" not in body
    assert "[PROJECT_REPO_NAME]" not in body
    assert "[PRD_FILENAME]" not in body
    assert "PROJECT HARD BOUNDARY" not in body  # SS4.2's third trap, genuinely resolved

    final_state = StateStore(state_path).load()
    assert final_state.customization is not None
    assert final_state.customization.step10_fidelity is not None
    assert final_state.customization.step10_fidelity.overall is True
    assert final_state.customization.step10_fidelity.structural_pass is True
    assert final_state.customization.step10_fidelity.judge_pass is True
    assert final_state.customization.step10_output_path == str(subagent_path)


# ============================================================================
# 2026-08-04 review patch: the customization judge's inputs never included repo_root, so
# [PROJECT_NAME]/[PROJECT_REPO_NAME]/[PRD_FILENAME] (genuinely on STEP10_PLACEHOLDER_ALLOWLIST) had
# no honest resolution path -- a real defect found live while dogfooding `loopr customize --step 10`
# against this repo's own Phase 3 run. Regression coverage below.
# ============================================================================


def test_step10_customization_request_carries_correct_repo_root_value(tmp_path: Path) -> None:
    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path / "my-project"))
    request = build_customization_request(state, template_text="template body")
    assert request.inputs["repo_root"] == str(tmp_path / "my-project")


def test_step11_customization_request_carries_correct_repo_root_value(tmp_path: Path) -> None:
    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path / "my-project"))
    request = build_step11_customization_request(
        state, template_text="template body", phase_1_spec_text="**Phase 1 of 3.**"
    )
    assert request.inputs["repo_root"] == str(tmp_path / "my-project")


def test_step12_customization_request_carries_correct_repo_root_value(tmp_path: Path) -> None:
    state = InterrogationState(mode=Mode.GREENFIELD, repo_root=str(tmp_path / "my-project"))
    request = build_step12_customization_request(
        state, template_text="template body", phase_1_spec_text="**Phase 1 of 3.**"
    )
    assert request.inputs["repo_root"] == str(tmp_path / "my-project")


def test_fidelity_judge_requests_do_not_carry_repo_root() -> None:
    """Scoped narrowly, per the fix's own instruction: repo_root belongs to the three CUSTOMIZATION
    call types only -- fidelity judging only checks the customization judge's already-drafted
    output, it never resolves anything itself, so adding repo_root there would be scope creep, not
    part of this fix."""
    from loopr.customization.customize import (
        build_fidelity_judge_request,
        build_step11_fidelity_judge_request,
        build_step12_fidelity_judge_request,
    )

    state = InterrogationState(mode=Mode.GREENFIELD, repo_root="/some/repo")
    for request in (
        build_fidelity_judge_request(state, template_text="t", customized_text="c"),
        build_step11_fidelity_judge_request(state, template_text="t", customized_text="c"),
        build_step12_fidelity_judge_request(state, template_text="t", customized_text="c"),
    ):
        assert "repo_root" not in request.inputs


@pytest.mark.parametrize(
    ("step_name", "allowlist", "dependencies"),
    [
        ("step10", STEP10_PLACEHOLDER_ALLOWLIST, STEP10_ALLOWLIST_INPUT_DEPENDENCIES),
        ("step11", STEP11_PLACEHOLDER_ALLOWLIST, STEP11_ALLOWLIST_INPUT_DEPENDENCIES),
        ("step12", STEP12_PLACEHOLDER_ALLOWLIST, STEP12_ALLOWLIST_INPUT_DEPENDENCIES),
    ],
)
def test_allowlist_input_dependencies_are_complete(
    step_name: str, allowlist: frozenset[str], dependencies: dict[str, frozenset[str]]
) -> None:
    """The regression flagged twice and never yet written: every token on a step's
    PLACEHOLDER_ALLOWLIST (genuinely customizer-resolvable) must have an explicit, recorded answer
    -- in customize.py's STEP<N>_ALLOWLIST_INPUT_DEPENDENCIES -- to what input facts its resolution
    depends on, even if that answer is "none, the baseline fields suffice" (an empty frozenset, never
    a missing entry). A token present in the allowlist but absent from the dependency map is exactly
    how [PROJECT_NAME]/[PROJECT_REPO_NAME]/[PRD_FILENAME] silently shipped without repo_root."""
    assert set(dependencies.keys()) == allowlist, (
        f"{step_name}: PLACEHOLDER_ALLOWLIST and ALLOWLIST_INPUT_DEPENDENCIES have drifted apart -- "
        f"in allowlist but undeclared: {allowlist - set(dependencies.keys())}; "
        f"declared but not on the allowlist: {set(dependencies.keys()) - allowlist}"
    )


def test_allowlist_input_dependencies_are_true_for_step10() -> None:
    """Not just complete -- TRUE: every key a token's dependency entry declares is actually present
    in what the real request builder sends. Checked by calling the builder for real, not inspecting
    the dict in isolation."""
    state = InterrogationState(mode=Mode.GREENFIELD, repo_root="/some/repo")
    request = build_customization_request(state, template_text="template body")
    actual_keys = set(request.inputs.keys())
    for token, needed_keys in STEP10_ALLOWLIST_INPUT_DEPENDENCIES.items():
        missing = needed_keys - actual_keys
        assert not missing, f"{token} declares dependency on {missing}, absent from the real request"


def test_allowlist_input_dependencies_are_true_for_step11_and_step12() -> None:
    state = InterrogationState(mode=Mode.GREENFIELD, repo_root="/some/repo")
    request11 = build_step11_customization_request(
        state, template_text="template body", phase_1_spec_text="**Phase 1 of 3.**"
    )
    request12 = build_step12_customization_request(
        state, template_text="template body", phase_1_spec_text="**Phase 1 of 3.**"
    )
    for request, dependencies in (
        (request11, STEP11_ALLOWLIST_INPUT_DEPENDENCIES),
        (request12, STEP12_ALLOWLIST_INPUT_DEPENDENCIES),
    ):
        actual_keys = set(request.inputs.keys())
        for token, needed_keys in dependencies.items():
            missing = needed_keys - actual_keys
            assert not missing, f"{token} declares dependency on {missing}, absent from the request"


def test_full_step10_run_resolves_project_name_repo_name_and_prd_filename_with_no_unclassified_spans(
    tmp_path: Path,
) -> None:
    """The concrete, end-to-end regression, against the REAL template (the fabricated synthetic
    fixture used elsewhere in this file never even contains [PRD_FILENAME]): with repo_root now
    available, a full customize run against a fixture repo produces output containing NO unresolved
    [PROJECT_NAME]/[PROJECT_REPO_NAME]/[PRD_FILENAME] -- checked both the substantive way
    (unresolved_placeholders, which is specifically what "still present, never filled" means) and via
    find_unclassified_bracket_spans returning [] outright, not just "fewer" than before."""
    repo = tmp_path / "my-real-project"
    repo.mkdir()
    _seed_real_step10_template(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)

    judge_response_path = tmp_path / "jr.json"
    code = main(["customize", "--state", str(state_path), "--step", "10"])
    assert code == exit_codes.JUDGE_REQUIRED
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request["inputs"]["repo_root"] == str(repo)

    # A genuine resolution of all three tokens, including [PRD_FILENAME] -- grounded in the
    # repo_root the judge was actually given, not a synthetic value disconnected from the fix.
    template_text = (repo / "prompts" / "Template_prompts" / "STEP_10").read_text(encoding="utf-8")
    customized = _plausible_real_step10_customization(template_text)
    response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="genuinely specific")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "10", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    output_path = repo / ".claude" / "agents" / f"{STEP10_SUBAGENT_NAME}.md"
    _frontmatter, body = _parse_subagent(output_path.read_text(encoding="utf-8"))

    unresolved = unresolved_placeholders(body, CustomizationStep.STEP_10)
    assert "[PROJECT_NAME]" not in unresolved
    assert "[PROJECT_REPO_NAME]" not in unresolved
    assert "[PRD_FILENAME]" not in unresolved

    assert find_unclassified_bracket_spans(body, CustomizationStep.STEP_10) == []
