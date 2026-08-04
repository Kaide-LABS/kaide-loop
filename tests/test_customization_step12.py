"""`loopr customize --step 12` end to end. Implements CUSTOMIZATION_PHASE_2_SPEC.md SS5.

Mirrors test_customization_step11.py exactly, adapted for step12's own subagent config (Sonnet,
high effort) and its own real precedent file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopr import exit_codes
from loopr.cli import main
from loopr.customization.customize import (
    STEP12_SUBAGENT_DESCRIPTION,
    STEP12_SUBAGENT_EFFORT,
    STEP12_SUBAGENT_MODEL,
    STEP12_SUBAGENT_NAME,
    apply_step12_customization_response,
)
from loopr.customization.templates import find_conditional_blocks
from loopr.models.common import CustomizationStep, Verdict
from loopr.models.judge import JudgeResponse
from loopr.state.store import StateStore

REAL_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "prompts" / "Template_prompts"
REAL_LOOPR_DIR = Path(__file__).resolve().parents[1] / "prompts" / "loopr"


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


def _seed_real_step12_template(repo: Path) -> None:
    templates_dir = repo / "prompts" / "Template_prompts"
    templates_dir.mkdir(parents=True, exist_ok=True)
    real_text = (REAL_TEMPLATES_DIR / "step_12").read_text(encoding="utf-8")
    (templates_dir / "step_12").write_text(real_text, encoding="utf-8")


def _seed_step10_execution_artifacts(repo: Path, *, phase_count: int = 4) -> None:
    (repo / "PHASE_1_SPEC.md").write_text(
        f"# PHASE_1_SPEC.md\n\n## SS0 Phase Plan Header\n\n**Phase 1 of {phase_count}.**\n\n"
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


def _plausible_step12_customization(template_text: str, *, load_bearing_citations: bool) -> str:
    """Mirrors test_customization_step11.py's helper exactly, built from
    prompts/loopr/step12_review.md. Unlike step11's block, step_12's own text DOES state an exact
    fallback line ("No citation re-verification gate required for this project.") -- the real
    precedent still doesn't use it byte-for-byte (it opens with it, then adds real reasoning), which
    is why layer 1 only checks the raw marker is gone, never mandates exact replacement wording."""
    output = (REAL_LOOPR_DIR / "step12_review.md").read_text(encoding="utf-8").replace(
        "[PHASE_COUNT]", "4"
    )
    if load_bearing_citations:
        full_block = next(b for b in find_conditional_blocks(template_text, CustomizationStep.STEP_12) if len(b) > 100)
        assert full_block in template_text
        start = output.index("No citation re-verification gate required")
        end = output.index("\n\n", start)
        no_citation_paragraph = output[start:end]
        output = output.replace(
            no_citation_paragraph,
            "This project anchors its retrieval design on arXiv:2005.11401 (Lewis et al., RAG). "
            "Before approving this phase, verify the paper's methods section still supports the "
            "architectural claim and record a SS0.5 Citation Re-Verification Gate (status PASSED + "
            "query trail) in the next phase spec.",
        )
    return output


@pytest.fixture
def confirmed_state_with_step10_executed(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step12_template(repo)
    _seed_step10_execution_artifacts(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)
    return repo, state_path


def test_customize_step12_refuses_before_six_conditions_pass(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step12_template(repo)
    _seed_step10_execution_artifacts(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0

    code = main(["customize", "--state", str(state_path), "--step", "12"])
    assert code == exit_codes.HALT


def test_customize_step12_refuses_when_step10_only_customized_not_executed(tmp_path: Path) -> None:
    """CUSTOMIZATION_PHASE_2_SPEC.md SS5.1, step12's side: same gate as step11 -- both depend only
    on step10's real output (SS4), neither on each other."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step12_template(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)

    code = main(["customize", "--state", str(state_path), "--step", "12"])
    assert code == exit_codes.HALT

    subagent_path = repo / ".claude" / "agents" / f"{STEP12_SUBAGENT_NAME}.md"
    assert not subagent_path.exists()


def test_customize_step12_produces_fidelity_verified_subagent_with_real_phase_count(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    repo, state_path = confirmed_state_with_step10_executed
    judge_response_path = tmp_path / "customize_judge_response.json"

    code = main(["customize", "--state", str(state_path), "--step", "12"])
    assert code == exit_codes.JUDGE_REQUIRED
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request["call_type"] == "step12_customization"
    assert "Phase 1 of 4" in request["inputs"]["phase_1_spec_text"]

    template_text = (repo / "prompts" / "Template_prompts" / "step_12").read_text(encoding="utf-8")
    customized = _plausible_step12_customization(template_text, load_bearing_citations=False)
    response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")

    code = main(
        ["customize", "--state", str(state_path), "--step", "12", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request2["call_type"] == "step12_fidelity_judge"

    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="genuinely specific")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "12", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    subagent_path = repo / ".claude" / "agents" / f"{STEP12_SUBAGENT_NAME}.md"
    assert subagent_path.exists()
    frontmatter, body = _parse_subagent(subagent_path.read_text(encoding="utf-8"))
    assert frontmatter["name"] == STEP12_SUBAGENT_NAME
    assert frontmatter["model"] == STEP12_SUBAGENT_MODEL
    assert frontmatter["effort"] == STEP12_SUBAGENT_EFFORT
    assert frontmatter["description"] == STEP12_SUBAGENT_DESCRIPTION
    assert "4" in body

    final_state = StateStore(state_path).load()
    assert final_state.customization is not None
    assert final_state.customization.step12_fidelity is not None
    assert final_state.customization.step12_fidelity.overall is True


def test_citation_gate_decision_without_load_bearing_citations(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    """CUSTOMIZATION_PHASE_2_SPEC.md SS5.6: no citations -- step_12's own stated fallback line is a
    starting point, not literally byte-exact in the real precedent (verified in templates.py's own
    registry comment); layer 1 only checks the raw marker is gone."""
    repo, state_path = confirmed_state_with_step10_executed
    judge_response_path = tmp_path / "jr.json"
    template_text = (repo / "prompts" / "Template_prompts" / "step_12").read_text(encoding="utf-8")

    main(["customize", "--state", str(state_path), "--step", "12"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    customized = _plausible_step12_customization(template_text, load_bearing_citations=False)
    response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "12", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="genuine reasoning, no filler")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "12", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    output_text = (repo / ".claude" / "agents" / f"{STEP12_SUBAGENT_NAME}.md").read_text(encoding="utf-8")
    assert "No citation re-verification gate required" in output_text
    assert "<<CITATION_GATE_BLOCK" not in output_text


def test_citation_gate_decision_with_load_bearing_citations(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    repo, state_path = confirmed_state_with_step10_executed
    judge_response_path = tmp_path / "jr.json"
    template_text = (repo / "prompts" / "Template_prompts" / "step_12").read_text(encoding="utf-8")

    main(["customize", "--state", str(state_path), "--step", "12"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    customized = _plausible_step12_customization(template_text, load_bearing_citations=True)
    response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "12", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="real citation, real gate logic")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "12", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    output_text = (repo / ".claude" / "agents" / f"{STEP12_SUBAGENT_NAME}.md").read_text(encoding="utf-8")
    assert "arXiv:2005.11401" in output_text
    assert "No citation re-verification gate required" not in output_text
    assert "<<CITATION_GATE_BLOCK" not in output_text


def test_step12_judge_request_never_carries_frontmatter_content(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    repo, state_path = confirmed_state_with_step10_executed

    code = main(["customize", "--state", str(state_path), "--step", "12"])
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
    assert f"name: {STEP12_SUBAGENT_NAME}" not in request_raw
    assert f"model: {STEP12_SUBAGENT_MODEL}" not in request_raw
    assert f"effort: {STEP12_SUBAGENT_EFFORT}" not in request_raw
    assert STEP12_SUBAGENT_DESCRIPTION not in request_raw

    response = JudgeResponse(call_id=request["call_id"], drafted_text="some drafted body", reason="drafted")
    body = apply_step12_customization_response(response)
    assert not body.startswith("---")
    assert f"model: {STEP12_SUBAGENT_MODEL}" not in body
    assert f"effort: {STEP12_SUBAGENT_EFFORT}" not in body

    template_text = (repo / "prompts" / "Template_prompts" / "step_12").read_text(encoding="utf-8")
    customized = _plausible_step12_customization(template_text, load_bearing_citations=False)
    good_response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    good_response_path = tmp_path / "good_response.json"
    good_response_path.write_text(good_response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "12", "--judge-response", str(good_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED
    fidelity_request_raw = (state_path.parent / "pending_judge.json").read_text(encoding="utf-8")
    assert f"name: {STEP12_SUBAGENT_NAME}" not in fidelity_request_raw
    assert f"model: {STEP12_SUBAGENT_MODEL}" not in fidelity_request_raw
