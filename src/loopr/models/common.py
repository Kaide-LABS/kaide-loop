"""Shared base model and enums. Implements PHASE_1_SPEC.md SS3.1."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class LooprBase(BaseModel):  # type: ignore[explicit-any]  # pydantic's own ConfigDict TypedDict carries Any-typed fields (e.g. json_encoders); no real Any in loopr code
    """Base for every loopr model. extra='forbid' is set once here and inherited everywhere."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        frozen=False,
    )


class Mode(str, Enum):
    GREENFIELD = "greenfield"
    BROWNFIELD = "brownfield"


class ConditionId(str, Enum):
    C1_OUTCOME = "c1_outcome"
    C2_ACCEPTANCE = "c2_acceptance"
    C3_SCOPE_EDGES = "c3_scope_edges"
    C4_BOUNDARY = "c4_boundary"
    C5_SOFT_CONTEXT = "c5_soft_context"
    C6_NO_UNKNOWNS = "c6_no_unknowns"


class JudgeCallType(str, Enum):
    """Deliberately does NOT include C4 -- condition 4 itself is a pure state-machine check, no
    rubric. BOUNDARY_PROPOSAL is a distinct thing: a one-off drafting call that runs UPSTREAM of
    condition 4, to give Gate 2 real content to show, before condition 4's own confirm-only check
    ever runs. Added 2026-08-01 -- see docs/stopping-test-spec.md Condition 4's boundary-drafting
    amendment."""

    C1_OUTCOME = "c1_outcome"
    C2_ACCEPTANCE = "c2_acceptance"
    C3_SCOPE_EDGES = "c3_scope_edges"
    C5_SOFT_CONTEXT = "c5_soft_context"
    C6_LOAD_BEARING = "c6_load_bearing"
    BF_RELEVANCE = "bf_relevance"
    BF_CLASSIFY = "bf_classify"
    BOUNDARY_PROPOSAL = "boundary_proposal"
    STEP10_CUSTOMIZATION = "step10_customization"
    STEP10_FIDELITY_JUDGE = "step10_fidelity_judge"
    """Layer 2 of the customization fidelity check (CUSTOMIZATION_PHASE_1_SPEC.md SS4.3) -- a
    distinct call type from STEP10_CUSTOMIZATION, not mentioned by name in that spec's SS2 file
    list (which said to add "the new call type", singular). Required because JudgeResponse's
    exactly-one-of-four shape means a single response can carry drafted_text (the customization) OR
    passed (the genuineness judgment), never both -- two structurally different response shapes
    cannot share one call type under the existing schema. Disclosed deviation, not silent."""
    STEP11_CUSTOMIZATION = "step11_customization"
    STEP11_FIDELITY_JUDGE = "step11_fidelity_judge"
    STEP12_CUSTOMIZATION = "step12_customization"
    STEP12_FIDELITY_JUDGE = "step12_fidelity_judge"
    """CUSTOMIZATION_PHASE_2_SPEC.md SS2: step11 and step12 each need their own customization +
    fidelity pair, same shape as step10's -- four new types, not two. Both response shapes are
    unchanged from step10's (drafted_text / passed via the existing exactly-one-of validator);
    the four operation types SS3 describes (fill, multi-line fill-in block, section deletion,
    conditional include-or-replace) are all resolved within ONE holistic drafted_text response per
    call, exactly as step10's fill and fill-in-block resolution already are -- no new JudgeResponse
    field or shape was needed."""


class QuestionStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DEFERRED_NON_LOAD_BEARING = "deferred_non_load_bearing"


class QuestionOrigin(str, Enum):
    MODULE = "module"
    USER = "user"
    PATTERN_AMBIGUITY = "pattern_ambiguity"


class ScopeEdgeKind(str, Enum):
    OUT = "out"
    DEFERRED = "deferred"


class NoteSource(str, Enum):
    STATED = "stated"
    INFERRED = "inferred"


class Verdict(str, Enum):
    CONFORM = "conform"
    DO_NOT_REPLICATE = "do_not_replicate"
    CONFLICT = "conflict"
    AMBIGUOUS = "ambiguous"


class Centrality(str, Enum):
    CORE = "core"
    PERIPHERAL = "peripheral"


class GateId(str, Enum):
    GATE_1_BABY_PRD = "gate_1_baby_prd"
    GATE_2_BOUNDARY = "gate_2_boundary"
    GATE_3_CONFLICTS = "gate_3_conflicts"


class CustomizationStep(str, Enum):
    """Identifies which template a discovery/skeleton-extraction result belongs to. All three exist
    as a type since template discovery must handle all three on-disk files' inconsistent naming
    (CUSTOMIZATION_PHASE_1_SPEC.md SS4.2) -- only STEP_10 is wired to the `loopr customize` CLI in
    Phase 1; STEP_11/STEP_12 customization itself is Phase 2, not built here."""

    STEP_10 = "step_10"
    STEP_11 = "step_11"
    STEP_12 = "step_12"


class DispatchTarget(str, Enum):
    """The three subagents Phase 3 routes between. Values are the literal subagent NAMES, matching
    STEP10_SUBAGENT_NAME / STEP11_SUBAGENT_NAME / STEP12_SUBAGENT_NAME in customization/customize.py
    so a decision is directly usable as a dispatch argument with no translation layer.

    No fourth member. Adding one is adding a subagent type, which the confirmed scope edge
    (.claude/loopr/baby_prd.md, scope edge 4) puts out of scope for this phase -- including the
    auditor tier and anything from docs/loopr-v2-agent-archetypes.md."""

    STEP_10 = "loopr-step10"
    STEP_11 = "loopr-step11"
    STEP_12 = "loopr-step12"


class Step10Warrant(str, Enum):
    """The ONLY two circumstances under which the Opus-tier step10 subagent may be dispatched
    (loopr-PRD.md section 6 B6, PROJECT HARD BOUNDARY).

    This enum is CLOSED. A third member meaning uncertainty, defaulting, or 'when in doubt' is the
    exact regression the confirmed acceptance criteria name as most load-bearing -- adding one would
    make an unwarranted escalation representable, and representable is the first step to reachable.
    If a future state cannot be classified into one of these two, the correct behaviour is HALT
    (exit_codes.HALT), never a step10 dispatch."""

    GREENFIELD_NO_ARTIFACTS = "greenfield_no_artifacts"
    """step10's execution artifacts do not exist on disk. Live disk truth, checked every time via
    templates.find_step10_execution_artifacts() -- never cached into a step10_done state field that
    could drift out of sync with the real artifact (confirmed boundary: 'one source of truth for that
    fact, not two')."""

    EXPLICIT_REMODERNIZATION = "explicit_remodernization"
    """The operator explicitly asked for re-modernization (`loopr dispatch --remodernize`). An
    operator act, never an inference."""


class Step12Verdict(str, Enum):
    """The severity distinction the confirmed acceptance criteria require. Three-valued by design.

    Note the disclosed tension with step_12's own template, which says approval is 'either clean or
    not' with 'no approve with minor follow-ups' -- these reconcile rather than conflict (loopr-PRD.md
    section 15): MINOR means step12 APPROVED the phase after patching the issue itself, which the
    template's own THE FIX section already describes. MINOR and CLEAN route identically; the
    distinction is a logging and falsifiability requirement, not a routing one. Do not 'simplify' it
    away -- the acceptance criteria require the two to be separately enumerable."""

    CLEAN = "clean"
    MINOR = "minor"
    SPEC_VIOLATING = "spec_violating"


class DispatchStateId(str, Enum):
    """The complete, finite set of states the controller can be in (CUSTOMIZATION_PHASE_3_SPEC.md
    section 6.2). Exhaustive by construction: decide() matches every member and the final branch is
    guarded by typing.assert_never, so adding a member without a routing rule is a mypy --strict
    error rather than a runtime surprise."""

    S0_TERMINAL = "s0_terminal"
    S1_PRE_STEP10 = "s1_pre_step10"
    S2_STEP10_IN_FLIGHT = "s2_step10_in_flight"
    S3_STEP10_DONE = "s3_step10_done"
    S4_STEP11_IN_FLIGHT = "s4_step11_in_flight"
    S5_STEP11_DONE = "s5_step11_done"
    S6_STEP12_IN_FLIGHT = "s6_step12_in_flight"
    S7_STEP12_CLEAN = "s7_step12_clean"
    S8_STEP12_MINOR = "s8_step12_minor"
    S9_STEP12_SPEC_VIOLATING = "s9_step12_spec_violating"
