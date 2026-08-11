"""`loopr customize --step 14` end to end. Implements .claude/loopr-step14-comprehension/baby_prd.md's
customize-machinery extension.

Mirrors tests/test_customization_step11.py and test_customization_step12.py's structure and helpers
exactly (deliberately duplicated, not imported -- test files in this project are self-contained,
matching the existing precedent those two files themselves already set).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopr import exit_codes
from loopr.cli import main
from loopr.customization.customize import (
    STEP14_SUBAGENT_DESCRIPTION,
    STEP14_SUBAGENT_EFFORT,
    STEP14_SUBAGENT_MODEL,
    STEP14_SUBAGENT_NAME,
    apply_step14_customization_response,
)
from loopr.customization.templates import find_unclassified_bracket_spans, unresolved_placeholders
from loopr.models.common import CustomizationStep, Verdict
from loopr.models.judge import JudgeResponse
from loopr.state.store import StateStore

REAL_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "prompts" / "Template_prompts"


def _parse_subagent(text: str) -> tuple[dict[str, str], str]:
    assert text.startswith("---\n"), "subagent file must start with YAML frontmatter"
    _, frontmatter_block, body = text.split("---\n", 2)
    frontmatter: dict[str, str] = {}
    for line in frontmatter_block.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip()
    return frontmatter, body.lstrip("\n")


def _seed_real_step14_template(repo: Path) -> None:
    templates_dir = repo / "prompts" / "Template_prompts"
    templates_dir.mkdir(parents=True, exist_ok=True)
    real_text = (REAL_TEMPLATES_DIR / "STEP_14").read_text(encoding="utf-8")
    (templates_dir / "STEP_14").write_text(real_text, encoding="utf-8")


def _seed_step10_execution_artifacts(repo: Path, *, phase_count: int = 4) -> None:
    (repo / "PHASE_1_SPEC.md").write_text(
        f"# PHASE_1_SPEC.md\n\nBuilt FROM the modernised `MY_PROJECT_PRD.md`.\n\n"
        f"## SS0 Phase Plan Header\n\n**Phase 1 of {phase_count}.**\n\n"
        "Some blueprint content.\n",
        encoding="utf-8",
    )
    (repo / "MY_PROJECT_PRD.md").write_text(
        "# My Project PRD\n\nSome content.\n\n## MODERNIZATION CHANGELOG\n\n- entry\n",
        encoding="utf-8",
    )


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


def _plausible_step14_customization(template_text: str) -> str:
    """A genuinely-passing customization of the REAL STEP_14 template: every customizer-resolvable
    placeholder filled with project-specific values, [UNVERIFIED] left untouched (not a placeholder --
    reused from step10's own runtime-emitted convention), the TEMPLATE CUSTOMIZATION CHECKLIST section
    dropped, and both real <<CUSTOMIZE: ...>> markers resolved with genuine, project-specific text."""
    output = template_text

    # Resolve the two real <<CUSTOMIZE: ...>> markers FIRST, while [PROJECT] is still literally
    # present in the searched text -- the token-fill loop below would otherwise already have turned
    # "[PROJECT]_Master_PRD.md" into "Acme_Master_PRD.md" and made this replace() a silent no-op.
    output = output.replace(
        "TEMPLATE STATUS: Base template. Customize per-project before pasting into Claude Code.\n"
        "Customization surfaces marked [PROJECT_*] and <<CUSTOMIZE: ...>>. Do not run directly.",
        "Customized for Acme Ledger; ready to run in Claude Code.",
    )
    output = output.replace(
        "3. PHASE_N_SPEC.md (the spec this phase was built against) and [PROJECT]_Master_PRD.md relevant\n"
        "   sections. <<CUSTOMIZE: confirm PRD filename/sections, same as step12's own CONTEXT INGESTION>>",
        "3. PHASE_N_SPEC.md (the spec this phase was built against) and Acme_Ledger_Master_PRD.md's\n"
        "   reconciliation-engine section, the only section this project's phases ever touch.",
    )

    for token, value in {
        "[PROJECT_NAME]": "Acme Ledger",
        "[PROJECT_REPO_NAME]": "acme-ledger",
        "[PROJECT_TAG]": "ACME-LEDGER",
        "[PROJECT]": "Acme",
        "[PHASE_COUNT]": "4",
    }.items():
        output = output.replace(token, value)

    checklist_start = output.index("## TEMPLATE CUSTOMIZATION CHECKLIST")
    output = output[:checklist_start].rstrip() + "\n"
    return output


@pytest.fixture
def confirmed_state_with_step10_executed(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step14_template(repo)
    _seed_step10_execution_artifacts(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)
    return repo, state_path


def test_customize_step14_refuses_before_six_conditions_pass(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step14_template(repo)
    _seed_step10_execution_artifacts(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0

    code = main(["customize", "--state", str(state_path), "--step", "14"])
    assert code == exit_codes.HALT


def test_customize_step14_refuses_when_step10_only_customized_not_executed(tmp_path: Path) -> None:
    """Same gate as step11/step12: all three depend only on step10's real execution artifacts on
    disk, not on each other and not on step10 merely having been customized."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step14_template(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)

    code = main(["customize", "--state", str(state_path), "--step", "14"])
    assert code == exit_codes.HALT

    subagent_path = repo / ".claude" / "agents" / f"{STEP14_SUBAGENT_NAME}.md"
    assert not subagent_path.exists()


def test_customize_step14_produces_fidelity_verified_subagent_with_real_phase_count(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    repo, state_path = confirmed_state_with_step10_executed
    judge_response_path = tmp_path / "customize_judge_response.json"

    code = main(["customize", "--state", str(state_path), "--step", "14"])
    assert code == exit_codes.JUDGE_REQUIRED
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request["call_type"] == "step14_customization"
    assert "Phase 1 of 4" in request["inputs"]["phase_1_spec_text"]
    assert request["inputs"]["repo_root"] == str(repo)

    template_text = (repo / "prompts" / "Template_prompts" / "STEP_14").read_text(encoding="utf-8")
    customized = _plausible_step14_customization(template_text)
    response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")

    code = main(
        ["customize", "--state", str(state_path), "--step", "14", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request2["call_type"] == "step14_fidelity_judge"

    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="genuinely specific")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "14", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    subagent_path = repo / ".claude" / "agents" / f"{STEP14_SUBAGENT_NAME}.md"
    assert subagent_path.exists()
    frontmatter, body = _parse_subagent(subagent_path.read_text(encoding="utf-8"))
    assert frontmatter["name"] == STEP14_SUBAGENT_NAME
    assert frontmatter["model"] == STEP14_SUBAGENT_MODEL
    assert frontmatter["effort"] == STEP14_SUBAGENT_EFFORT
    assert frontmatter["description"] == STEP14_SUBAGENT_DESCRIPTION
    assert "4" in body
    assert "Acme Ledger" in body
    assert "[PROJECT_NAME]" not in body
    assert "TEMPLATE CUSTOMIZATION CHECKLIST" not in body
    assert "[UNVERIFIED]" in body  # runtime-emitted tag, must survive

    unresolved = unresolved_placeholders(body, CustomizationStep.STEP_14)
    assert unresolved == []
    assert find_unclassified_bracket_spans(body, CustomizationStep.STEP_14) == []

    final_state = StateStore(state_path).load()
    assert final_state.customization is not None
    assert final_state.customization.step14_fidelity is not None
    assert final_state.customization.step14_fidelity.overall is True
    assert final_state.customization.step14_output_path == str(subagent_path)


def test_step14_judge_request_never_carries_frontmatter_content(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    repo, state_path = confirmed_state_with_step10_executed

    code = main(["customize", "--state", str(state_path), "--step", "14"])
    assert code == exit_codes.JUDGE_REQUIRED
    request_raw = (state_path.parent / "pending_judge.json").read_text(encoding="utf-8")
    request = json.loads(request_raw)

    assert set(request["inputs"].keys()) == {
        "template_text",
        "phase_1_spec_text",
        "repo_root",
        "problem_statement",
        "acceptance_criteria",
        "scope_edges",
        "boundary",
        "context_notes",
        "conformance_summary",
    }
    assert f"name: {STEP14_SUBAGENT_NAME}" not in request_raw
    assert f"model: {STEP14_SUBAGENT_MODEL}" not in request_raw
    assert f"effort: {STEP14_SUBAGENT_EFFORT}" not in request_raw
    assert STEP14_SUBAGENT_DESCRIPTION not in request_raw

    response = JudgeResponse(call_id=request["call_id"], drafted_text="some drafted body", reason="drafted")
    body = apply_step14_customization_response(response)
    assert not body.startswith("---")
    assert f"model: {STEP14_SUBAGENT_MODEL}" not in body
    assert f"effort: {STEP14_SUBAGENT_EFFORT}" not in body


def test_customize_step14_rejects_restructured_output(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    """A customization that drops one of the six MAINTAINED SECTIONS' numbered subsections must be
    rejected structurally (layer 1) -- these are exactly the sections whose survival this build's own
    fidelity rubric calls out explicitly."""
    repo, state_path = confirmed_state_with_step10_executed
    judge_response_path = tmp_path / "jr.json"

    template_text = (repo / "prompts" / "Template_prompts" / "STEP_14").read_text(encoding="utf-8")
    customized = _plausible_step14_customization(template_text)
    restructured = customized.replace("### 6. Open items\n", "")

    code = main(["customize", "--state", str(state_path), "--step", "14"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response = JudgeResponse(call_id=request["call_id"], drafted_text=restructured, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "14", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.HALT

    final_state = StateStore(state_path).load()
    assert final_state.customization is not None
    assert final_state.customization.step14_fidelity is not None
    assert final_state.customization.step14_fidelity.structural_pass is False
    subagent_path = repo / ".claude" / "agents" / f"{STEP14_SUBAGENT_NAME}.md"
    assert not subagent_path.exists()
