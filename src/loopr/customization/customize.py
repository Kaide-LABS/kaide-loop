"""Judge-request construction and response application for step10/step11/step12 customization.

Implements CUSTOMIZATION_PHASE_1_SPEC.md SS4.1, SS4.3 layer 2, and CUSTOMIZATION_PHASE_2_SPEC.md SS2.
Each step has its own customization + fidelity judge-call pair: *_CUSTOMIZATION drafts the customized
output (drafted_text); *_FIDELITY_JUDGE judges whether that output is genuinely project-specific
(passed) -- run only after layer 1's structural check passes. step11/step12's functions are kept as
separate, parallel functions mirroring step10's exactly (not a shared parameterized abstraction) --
reusing the verified PATTERN, not re-deriving it, and not risking step10's already-reviewed,
already-shipped functions by generalizing them out from under themselves.
"""

from __future__ import annotations

from loopr.errors import LooprError
from loopr.judge.envelope import make_call_id
from loopr.models.common import JudgeCallType
from loopr.models.interrogation import InterrogationState
from loopr.models.judge import JsonValue, JudgeRequest, JudgeResponse
from loopr.rubrics import RUBRICS


class CustomizationError(LooprError):
    """Raised when a judge response for a customization call doesn't carry the field its shape
    requires -- a malformed response from the invoking agent, not a normal failure mode."""


def _conformance_summary(state: InterrogationState) -> JsonValue:
    """A derived, compact projection of the conformance ledger -- verdict, pattern id, one-line
    reason -- never the raw ledger. Brownfield only; None for greenfield."""
    if state.brownfield is None:
        return None
    return [
        {
            "pattern_id": classification.pattern_id,
            "verdict": classification.verdict.value,
            "reason": classification.reason,
        }
        for classification in state.brownfield.classifications
    ]


def build_customization_request(state: InterrogationState, template_text: str) -> JudgeRequest:
    inputs: dict[str, JsonValue] = {
        "template_text": template_text,
        "problem_statement": state.problem_statement,
        "acceptance_criteria": [c.text for c in state.acceptance_criteria],
        "scope_edges": [e.item for e in state.scope_edges],
        "boundary": state.boundary.text if state.boundary is not None else None,
        "context_notes": [n.text for n in state.context_notes],
        "conformance_summary": _conformance_summary(state),
    }
    rubric = RUBRICS[JudgeCallType.STEP10_CUSTOMIZATION]
    call_id = make_call_id(JudgeCallType.STEP10_CUSTOMIZATION.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.STEP10_CUSTOMIZATION,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


def apply_customization_response(response: JudgeResponse) -> str:
    if response.drafted_text is None:
        raise CustomizationError("STEP10_CUSTOMIZATION response must carry drafted_text")
    return response.drafted_text


def build_fidelity_judge_request(
    state: InterrogationState, template_text: str, customized_text: str
) -> JudgeRequest:
    inputs: dict[str, JsonValue] = {
        "template_text": template_text,
        "customized_text": customized_text,
        "problem_statement": state.problem_statement,
        "acceptance_criteria": [c.text for c in state.acceptance_criteria],
        "boundary": state.boundary.text if state.boundary is not None else None,
    }
    rubric = RUBRICS[JudgeCallType.STEP10_FIDELITY_JUDGE]
    call_id = make_call_id(JudgeCallType.STEP10_FIDELITY_JUDGE.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.STEP10_FIDELITY_JUDGE,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


def apply_fidelity_judge_response(response: JudgeResponse) -> tuple[bool, str]:
    if response.passed is None:
        raise CustomizationError("STEP10_FIDELITY_JUDGE response must carry passed")
    return response.passed, response.reason


def build_step11_customization_request(
    state: InterrogationState, template_text: str, phase_1_spec_text: str
) -> JudgeRequest:
    """Mirrors build_customization_request exactly, plus `phase_1_spec_text` -- CUSTOMIZATION_PHASE_2
    _SPEC.md SS1.2: [PHASE_COUNT] is genuinely customizer-resolvable here (unlike in step10) because
    step10 having executed (cli.py's find_step10_execution_artifacts gate) means PHASE_1_SPEC.md's
    own SS0 header now states it -- the judge needs that content to read it."""
    inputs: dict[str, JsonValue] = {
        "template_text": template_text,
        "phase_1_spec_text": phase_1_spec_text,
        "problem_statement": state.problem_statement,
        "acceptance_criteria": [c.text for c in state.acceptance_criteria],
        "scope_edges": [e.item for e in state.scope_edges],
        "boundary": state.boundary.text if state.boundary is not None else None,
        "context_notes": [n.text for n in state.context_notes],
        "conformance_summary": _conformance_summary(state),
    }
    rubric = RUBRICS[JudgeCallType.STEP11_CUSTOMIZATION]
    call_id = make_call_id(JudgeCallType.STEP11_CUSTOMIZATION.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.STEP11_CUSTOMIZATION,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


def apply_step11_customization_response(response: JudgeResponse) -> str:
    if response.drafted_text is None:
        raise CustomizationError("STEP11_CUSTOMIZATION response must carry drafted_text")
    return response.drafted_text


def build_step11_fidelity_judge_request(
    state: InterrogationState, template_text: str, customized_text: str
) -> JudgeRequest:
    inputs: dict[str, JsonValue] = {
        "template_text": template_text,
        "customized_text": customized_text,
        "problem_statement": state.problem_statement,
        "acceptance_criteria": [c.text for c in state.acceptance_criteria],
        "boundary": state.boundary.text if state.boundary is not None else None,
    }
    rubric = RUBRICS[JudgeCallType.STEP11_FIDELITY_JUDGE]
    call_id = make_call_id(JudgeCallType.STEP11_FIDELITY_JUDGE.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.STEP11_FIDELITY_JUDGE,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


def apply_step11_fidelity_judge_response(response: JudgeResponse) -> tuple[bool, str]:
    if response.passed is None:
        raise CustomizationError("STEP11_FIDELITY_JUDGE response must carry passed")
    return response.passed, response.reason


def build_step12_customization_request(
    state: InterrogationState, template_text: str, phase_1_spec_text: str
) -> JudgeRequest:
    """Mirrors build_step11_customization_request exactly -- same input shape, different call type
    and rubric (step12's rubric additionally covers [EXECUTOR_AGENT_FICTION])."""
    inputs: dict[str, JsonValue] = {
        "template_text": template_text,
        "phase_1_spec_text": phase_1_spec_text,
        "problem_statement": state.problem_statement,
        "acceptance_criteria": [c.text for c in state.acceptance_criteria],
        "scope_edges": [e.item for e in state.scope_edges],
        "boundary": state.boundary.text if state.boundary is not None else None,
        "context_notes": [n.text for n in state.context_notes],
        "conformance_summary": _conformance_summary(state),
    }
    rubric = RUBRICS[JudgeCallType.STEP12_CUSTOMIZATION]
    call_id = make_call_id(JudgeCallType.STEP12_CUSTOMIZATION.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.STEP12_CUSTOMIZATION,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


def apply_step12_customization_response(response: JudgeResponse) -> str:
    if response.drafted_text is None:
        raise CustomizationError("STEP12_CUSTOMIZATION response must carry drafted_text")
    return response.drafted_text


def build_step12_fidelity_judge_request(
    state: InterrogationState, template_text: str, customized_text: str
) -> JudgeRequest:
    inputs: dict[str, JsonValue] = {
        "template_text": template_text,
        "customized_text": customized_text,
        "problem_statement": state.problem_statement,
        "acceptance_criteria": [c.text for c in state.acceptance_criteria],
        "boundary": state.boundary.text if state.boundary is not None else None,
    }
    rubric = RUBRICS[JudgeCallType.STEP12_FIDELITY_JUDGE]
    call_id = make_call_id(JudgeCallType.STEP12_FIDELITY_JUDGE.value, state.round, inputs)
    return JudgeRequest(
        call_id=call_id,
        call_type=JudgeCallType.STEP12_FIDELITY_JUDGE,
        rubric_id=rubric.rubric_id,
        rubric_text=rubric.text,
        inputs=inputs,
        created_round=state.round,
    )


def apply_step12_fidelity_judge_response(response: JudgeResponse) -> tuple[bool, str]:
    if response.passed is None:
        raise CustomizationError("STEP12_FIDELITY_JUDGE response must carry passed")
    return response.passed, response.reason


# Subagent dispatch (CUSTOMIZATION_PHASE_1_SPEC.md SS1, SS6.1a, amended 2026-08-03; extended to
# step11/step12 by CUSTOMIZATION_PHASE_2_SPEC.md SS0/SS2). FIXED CONFIGURATION, written directly from
# constants here -- never a JudgeRequest input, never a JudgeResponse field, never touched by any
# build_*_request/apply_*_response function above. A judge call could never be trusted to hold a
# model/effort pin constant run to run the way a module-level constant can; the frontmatter is exactly
# as invariant as TEMPLATES_DIR_NAME or STEP10_PLACEHOLDER_ALLOWLIST in templates.py, not
# customization output.
#
# Model value confirmed against real, shipped Claude Code subagent definitions (not merely assumed,
# 6eebfe6): every real agent file's `model:` field uses a coarse tier keyword
# (inherit/sonnet/opus/haiku), never a specific dated model ID string. `effort` confirmed the same
# round as a genuine per-subagent frontmatter field (real files, claude-security plugin, values
# medium/xhigh) -- that question is closed, not re-verified here, per this phase's own directive.
STEP10_SUBAGENT_NAME = "loopr-step10"
STEP10_SUBAGENT_MODEL = "opus"
STEP10_SUBAGENT_EFFORT: str | None = None
STEP10_SUBAGENT_DESCRIPTION = (
    "Runs this project's customized step10 prompt -- PRD modernization grounded in current external "
    "sources, then the hyper-granular Phase 1 technical blueprint built from the modernised PRD. Use "
    "once `loopr customize --step 10` has produced a fidelity-verified customization and the "
    "confirmed spec is ready for architecture drafting."
)

STEP11_SUBAGENT_NAME = "loopr-step11"
STEP11_SUBAGENT_MODEL = "sonnet"
STEP11_SUBAGENT_EFFORT: str | None = "low"
STEP11_SUBAGENT_DESCRIPTION = (
    "Runs this project's customized step11 prompt -- discovers the current unbuilt phase and writes "
    "production-ready code for it from PHASE_N_SPEC.md, within the project's hard invariants and "
    "boundary. Use once `loopr customize --step 11` has produced a fidelity-verified customization "
    "and step10 has executed for this project."
)

STEP12_SUBAGENT_NAME = "loopr-step12"
STEP12_SUBAGENT_MODEL = "sonnet"
STEP12_SUBAGENT_EFFORT: str | None = "high"
STEP12_SUBAGENT_DESCRIPTION = (
    "Runs this project's customized step12 prompt -- adversarial QA review of the current phase's "
    "implementation against its spec and the project's invariants, then advances to the next phase "
    "spec on approval. Use once `loopr customize --step 12` has produced a fidelity-verified "
    "customization and step10 has executed for this project."
)


def _render_subagent(*, name: str, description: str, model: str, effort: str | None, body: str) -> str:
    """The shared wrapping logic behind render_step10_subagent/render_step11_subagent/
    render_step12_subagent -- YAML frontmatter (fixed configuration) followed by `body` verbatim,
    byte-for-byte, as the system prompt. Pure post-processing: called only AFTER both fidelity layers
    already passed on `body` alone (cli.py's cmd_customize) -- the frontmatter itself is never
    fidelity-checked, because nothing in it is drafted content with genuineness to verify
    (CUSTOMIZATION_PHASE_1_SPEC.md SS6.1a). `effort` is omitted entirely when None (step10 has no
    effort pin, only a model pin) rather than written as a blank/null field."""
    effort_line = f"effort: {effort}\n" if effort is not None else ""
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"model: {model}\n"
        f"{effort_line}"
        "---\n\n"
        f"{body}\n"
    )


def render_step10_subagent(body: str) -> str:
    return _render_subagent(
        name=STEP10_SUBAGENT_NAME,
        description=STEP10_SUBAGENT_DESCRIPTION,
        model=STEP10_SUBAGENT_MODEL,
        effort=STEP10_SUBAGENT_EFFORT,
        body=body,
    )


def render_step11_subagent(body: str) -> str:
    return _render_subagent(
        name=STEP11_SUBAGENT_NAME,
        description=STEP11_SUBAGENT_DESCRIPTION,
        model=STEP11_SUBAGENT_MODEL,
        effort=STEP11_SUBAGENT_EFFORT,
        body=body,
    )


def render_step12_subagent(body: str) -> str:
    return _render_subagent(
        name=STEP12_SUBAGENT_NAME,
        description=STEP12_SUBAGENT_DESCRIPTION,
        model=STEP12_SUBAGENT_MODEL,
        effort=STEP12_SUBAGENT_EFFORT,
        body=body,
    )
