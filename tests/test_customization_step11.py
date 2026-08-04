"""`loopr customize --step 11` end to end. Implements CUSTOMIZATION_PHASE_2_SPEC.md SS5.

Mirrors tests/test_customization_cli.py's structure and helpers (deliberately duplicated, not
imported -- test files in this project are self-contained, matching the existing precedent set by
test_customization_fidelity.py's own duplicated helpers).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopr import exit_codes
from loopr.cli import main
from loopr.customization.customize import (
    STEP11_SUBAGENT_DESCRIPTION,
    STEP11_SUBAGENT_EFFORT,
    STEP11_SUBAGENT_MODEL,
    STEP11_SUBAGENT_NAME,
    apply_step11_customization_response,
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


def _seed_real_step11_template(repo: Path) -> None:
    templates_dir = repo / "prompts" / "Template_prompts"
    templates_dir.mkdir(parents=True, exist_ok=True)
    real_text = (REAL_TEMPLATES_DIR / "STEP _11").read_text(encoding="utf-8")
    (templates_dir / "STEP _11").write_text(real_text, encoding="utf-8")


def _seed_step10_execution_artifacts(repo: Path, *, phase_count: int = 4) -> None:
    """The SS1.1 gate's real deliverables, detected by content, not filename (2026-08-04 review
    patch): a modernised PRD, found by a real '## MODERNIZATION CHANGELOG' heading LINE, deliberately
    under a NON-default filename (matching this project's own real practice, verified against
    prompts/loopr/step10_prd_modernization.md -- "loopr-PRD.md", not the template's stated default
    "ULTIMATE_PRD.md"); and its Phase-N-spec companion, found by a real 'Phase Plan Header' heading
    line PLUS an explicit "built from" claim naming the detected PRD's filename -- PHASE_1_SPEC.md is
    just this fixture's chosen name for it, not a filename the detector relies on."""
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


def _plausible_step11_customization(template_text: str, *, load_bearing_citations: bool) -> str:
    """A genuinely-passing customization of the REAL STEP_11 template, built from the real
    human-produced precedent (prompts/loopr/step11_build.md) -- the most robust fixture available,
    already validated (tests/test_customization_fidelity.py) to pass structurally once PHASE_COUNT
    is resolved. `load_bearing_citations` swaps which way the citation-gate decision resolves."""
    output = (REAL_LOOPR_DIR / "step11_build.md").read_text(encoding="utf-8").replace(
        "[PHASE_COUNT]", "4"
    )
    if load_bearing_citations:
        # Only the FULL instructional block (not the bare checklist-section form) is relevant here --
        # the checklist is dropped wholesale regardless of this decision.
        full_block = next(b for b in find_conditional_blocks(template_text, CustomizationStep.STEP_11) if len(b) > 100)
        assert full_block in template_text
        # The real precedent's replacement paragraph ("No citation re-verification gate applies...")
        # is what stands in for the "no citations" case already (unmodified above). For "has
        # citations", replace that WHOLE paragraph (extracted by blank-line boundary, not
        # hand-retyped, to avoid a transcription mismatch against the source's own line wrapping)
        # with real-looking inclusion content.
        start = output.index("No citation re-verification gate applies")
        end = output.index("\n\n", start)
        no_citation_paragraph = output[start:end]
        output = output.replace(
            no_citation_paragraph,
            "This project anchors its retrieval design on arXiv:2005.11401 (Lewis et al., RAG). "
            "Before writing PHASE_N_SPEC.md at a phase boundary that depends on this claim, verify "
            "the paper's methods section still supports it and record a SS0.5 Citation "
            "Re-Verification Gate (status PASSED + query trail) in the generated spec.",
        )
    return output


@pytest.fixture
def confirmed_state_with_step10_executed(tmp_path: Path) -> tuple[Path, Path]:
    """A repo with the real STEP_11 template, real step10 execution artifacts on disk, and a state
    file driven to COMPLETE -- everything SS1.1's gate requires."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step11_template(repo)
    _seed_step10_execution_artifacts(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)
    return repo, state_path


def test_customize_step11_refuses_before_six_conditions_pass(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step11_template(repo)
    _seed_step10_execution_artifacts(repo)
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0

    code = main(["customize", "--state", str(state_path), "--step", "11"])
    assert code == exit_codes.HALT


def test_customize_step11_refuses_when_step10_only_customized_not_executed(tmp_path: Path) -> None:
    """CUSTOMIZATION_PHASE_2_SPEC.md SS5.1, demonstrated firing: the six conditions pass and
    step10's PROMPT could even be fidelity-verified, but step10 was never actually RUN against this
    project -- no PHASE_1_SPEC.md, no modernised PRD on disk. Must refuse, not infer readiness from
    CustomizationState.step10_fidelity."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step11_template(repo)
    # Deliberately NOT calling _seed_step10_execution_artifacts -- step10 was never executed here,
    # only (hypothetically) customized elsewhere.
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)

    code = main(["customize", "--state", str(state_path), "--step", "11"])
    assert code == exit_codes.HALT

    subagent_path = repo / ".claude" / "agents" / f"{STEP11_SUBAGENT_NAME}.md"
    assert not subagent_path.exists()


def test_customize_step11_refusal_does_not_clear_an_unrelated_pending_step10_request(
    tmp_path: Path,
) -> None:
    """Regression: the SS1.1 gate check must run BEFORE any pending-file mutation. A refused
    `--step 11` call must never destroy a genuinely in-flight step10 judge request that just
    happens to be pending at the same moment -- confirmed by driving step10 to JUDGE_REQUIRED first,
    then attempting (and being refused for) step11, then confirming step10's own pending request is
    still exactly where it was."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_real_step11_template(repo)
    templates_dir = repo / "prompts" / "Template_prompts"
    (templates_dir / "STEP_10").write_text(
        "STEP 10 TITLE\n\nROLE\n\nAct as an architect for [PROJECT_NAME].\n\n"
        "1. FIRST SECTION\n\nDo the first thing.\n\n2. SECOND SECTION\n\nDo the second thing.\n",
        encoding="utf-8",
    )
    # Deliberately NOT seeding step10 execution artifacts -- step11 must be refused below.
    state_path = tmp_path / "state.json"
    assert main(["init", "--repo", str(repo), "--mode", "greenfield", "--state", str(state_path)]) == 0
    store = StateStore(state_path)
    _drive_to_complete(state_path, store.dir, tmp_path)

    code = main(["customize", "--state", str(state_path), "--step", "10"])
    assert code == exit_codes.JUDGE_REQUIRED
    pending_path = store.dir / "pending_judge.json"
    assert pending_path.exists()
    step10_request_before = json.loads(pending_path.read_text(encoding="utf-8"))
    assert step10_request_before["call_type"] == "step10_customization"

    code = main(["customize", "--state", str(state_path), "--step", "11"])
    assert code == exit_codes.HALT

    assert pending_path.exists(), (
        "step10's pending judge request was deleted by a refused, unrelated --step 11 call"
    )
    step10_request_after = json.loads(pending_path.read_text(encoding="utf-8"))
    assert step10_request_after == step10_request_before


def test_customize_step11_produces_fidelity_verified_subagent_with_real_phase_count(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    """CUSTOMIZATION_PHASE_2_SPEC.md SS5.2, demonstrated against a REAL PHASE_1_SPEC.md SS0 header
    (not a synthetic fixture standing in for one) and SS1's subagent-dispatch amendment together: the
    judge request carries the real file's content, and the final subagent has correct
    frontmatter (model: sonnet, effort: low)."""
    repo, state_path = confirmed_state_with_step10_executed
    judge_response_path = tmp_path / "customize_judge_response.json"

    code = main(["customize", "--state", str(state_path), "--step", "11"])
    assert code == exit_codes.JUDGE_REQUIRED
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request["call_type"] == "step11_customization"
    # The real PHASE_1_SPEC.md content (with a real phase count) reached the judge.
    assert "Phase 1 of 4" in request["inputs"]["phase_1_spec_text"]

    template_text = (repo / "prompts" / "Template_prompts" / "STEP _11").read_text(encoding="utf-8")
    customized = _plausible_step11_customization(template_text, load_bearing_citations=False)
    response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")

    code = main(
        ["customize", "--state", str(state_path), "--step", "11", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED  # layer-2 fidelity judge call
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    assert request2["call_type"] == "step11_fidelity_judge"

    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="genuinely specific")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "11", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    subagent_path = repo / ".claude" / "agents" / f"{STEP11_SUBAGENT_NAME}.md"
    assert subagent_path.exists()
    frontmatter, body = _parse_subagent(subagent_path.read_text(encoding="utf-8"))
    assert frontmatter["name"] == STEP11_SUBAGENT_NAME
    assert frontmatter["model"] == STEP11_SUBAGENT_MODEL
    assert frontmatter["effort"] == STEP11_SUBAGENT_EFFORT
    assert frontmatter["description"] == STEP11_SUBAGENT_DESCRIPTION
    assert "4" in body  # the real, resolved phase count
    assert "[PHASE_COUNT]" not in body or "TEMPLATE CUSTOMIZATION CHECKLIST" not in body  # sanity

    final_state = StateStore(state_path).load()
    assert final_state.customization is not None
    assert final_state.customization.step11_fidelity is not None
    assert final_state.customization.step11_fidelity.overall is True


def test_citation_gate_decision_without_load_bearing_citations(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    """CUSTOMIZATION_PHASE_2_SPEC.md SS5.6, one side: no load-bearing citations -- the block is
    resolved per STEP_11's own stated fallback (removed, replaced with real project reasoning, since
    STEP_11's block specifies no fixed replacement line -- see templates.py's registry comment)."""
    repo, state_path = confirmed_state_with_step10_executed
    judge_response_path = tmp_path / "jr.json"
    template_text = (repo / "prompts" / "Template_prompts" / "STEP _11").read_text(encoding="utf-8")

    main(["customize", "--state", str(state_path), "--step", "11"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    customized = _plausible_step11_customization(template_text, load_bearing_citations=False)
    response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "11", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED  # layer 1 passed
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="genuine reasoning, no filler")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "11", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    output_text = (repo / ".claude" / "agents" / f"{STEP11_SUBAGENT_NAME}.md").read_text(encoding="utf-8")
    assert "No citation re-verification gate applies" in output_text
    assert "<<CITATION_GATE_INGESTION_BLOCK" not in output_text


def test_citation_gate_decision_with_load_bearing_citations(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    """CUSTOMIZATION_PHASE_2_SPEC.md SS5.6, the other side: load-bearing citations -- the block is
    resolved by including real, project-specific citation content, not the fallback."""
    repo, state_path = confirmed_state_with_step10_executed
    judge_response_path = tmp_path / "jr.json"
    template_text = (repo / "prompts" / "Template_prompts" / "STEP _11").read_text(encoding="utf-8")

    main(["customize", "--state", str(state_path), "--step", "11"])
    request = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    customized = _plausible_step11_customization(template_text, load_bearing_citations=True)
    response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    judge_response_path.write_text(response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "11", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED
    request2 = json.loads((state_path.parent / "pending_judge.json").read_text(encoding="utf-8"))
    response2 = JudgeResponse(call_id=request2["call_id"], passed=True, reason="real citation, real gate logic")
    judge_response_path.write_text(response2.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "11", "--judge-response", str(judge_response_path)]
    )
    assert code == exit_codes.OK

    output_text = (repo / ".claude" / "agents" / f"{STEP11_SUBAGENT_NAME}.md").read_text(encoding="utf-8")
    assert "arXiv:2005.11401" in output_text
    assert "No citation re-verification gate applies" not in output_text
    assert "<<CITATION_GATE_INGESTION_BLOCK" not in output_text


def test_step11_judge_request_never_carries_frontmatter_content(
    confirmed_state_with_step10_executed: tuple[Path, Path], tmp_path: Path
) -> None:
    """Same dedicated-test pattern as 6eebfe6's test_judge_request_never_carries_frontmatter_content,
    proven again for step11's two new call types rather than assumed to have transferred."""
    repo, state_path = confirmed_state_with_step10_executed

    code = main(["customize", "--state", str(state_path), "--step", "11"])
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
    assert f"name: {STEP11_SUBAGENT_NAME}" not in request_raw
    assert f"model: {STEP11_SUBAGENT_MODEL}" not in request_raw
    assert f"effort: {STEP11_SUBAGENT_EFFORT}" not in request_raw
    assert STEP11_SUBAGENT_DESCRIPTION not in request_raw

    response = JudgeResponse(call_id=request["call_id"], drafted_text="some drafted body", reason="drafted")
    body = apply_step11_customization_response(response)
    assert not body.startswith("---")
    assert f"model: {STEP11_SUBAGENT_MODEL}" not in body
    assert f"effort: {STEP11_SUBAGENT_EFFORT}" not in body

    # Drive to the fidelity-judge call too, and check IT never carries frontmatter either.
    template_text = (repo / "prompts" / "Template_prompts" / "STEP _11").read_text(encoding="utf-8")
    customized = _plausible_step11_customization(template_text, load_bearing_citations=False)
    good_response = JudgeResponse(call_id=request["call_id"], drafted_text=customized, reason="drafted")
    good_response_path = tmp_path / "good_response.json"
    good_response_path.write_text(good_response.model_dump_json(), encoding="utf-8")
    code = main(
        ["customize", "--state", str(state_path), "--step", "11", "--judge-response", str(good_response_path)]
    )
    assert code == exit_codes.JUDGE_REQUIRED
    fidelity_request_raw = (state_path.parent / "pending_judge.json").read_text(encoding="utf-8")
    assert f"name: {STEP11_SUBAGENT_NAME}" not in fidelity_request_raw
    assert f"model: {STEP11_SUBAGENT_MODEL}" not in fidelity_request_raw
