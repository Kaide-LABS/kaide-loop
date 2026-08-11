"""Prompt-customization models. Implements CUSTOMIZATION_PHASE_1_SPEC.md SS6.2.

TemplateSkeleton's non-vacuousness is enforced at extraction time (customization/templates.py), not
here -- a schema-level minimum would have to be hardcoded per template, which
CUSTOMIZATION_PHASE_1_SPEC.md SS4.3 explicitly rejects ("derived from the template file itself at
runtime rather than hardcoded"). FidelityResult mirrors ConditionResult's own two-layer invariant
(models/interrogation.py) -- the same discipline loopr applies to its own six-condition test, applied
here to customization output.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from loopr.models.common import CustomizationStep, LooprBase


class TemplateSkeleton(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    convention: str = Field(min_length=1)
    """Which header convention this skeleton was extracted under -- e.g. "all_caps" for STEP_10,
    "markdown_h2" / "markdown_h2_h3" for STEP_11/step_12. Declared explicitly per template
    (CUSTOMIZATION_PHASE_1_SPEC.md SS4.3); never inferred generically."""
    sections: list[str] = Field(min_length=1)


class PlaceholderBinding(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    token: str = Field(min_length=1)
    value: str


class CustomizedPrompt(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    step: CustomizationStep
    template_path: str = Field(min_length=1)
    output_text: str = Field(min_length=1)


class FidelityResult(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    structural_pass: bool
    judge_pass: bool | None = None
    overall: bool
    detail: str = Field(min_length=1)

    @model_validator(mode="after")
    def check_two_layer_invariant(self) -> "FidelityResult":
        if self.overall:
            if not self.structural_pass:
                raise ValueError("overall cannot be True when structural_pass is False")
            if self.judge_pass is not True:
                raise ValueError("overall cannot be True unless judge_pass is True")
        return self


class CustomizationState(LooprBase):  # type: ignore[explicit-any]  # pydantic BaseModel's inherited model_config: ClassVar[ConfigDict] is Any-typed internally; no real Any in loopr code
    """CUSTOMIZATION_PHASE_2_SPEC.md SS2 flagged a real design question here: whether three parallel
    field groups (step10_*/step11_*/step12_*) should become dict[CustomizationStep,
    StepCustomization], since a fourth group would be past the point flat fields tolerate.

    DECIDED (2026-08-03): stay flat. Reasoning, not left implicit: (1) the spec's own framing already
    calls three "tolerable" -- this phase brings the count to exactly three, not past it; (2) there is
    no foreseeable fourth group -- Phase 3 (loop sequencing, CUSTOMIZATION_PHASE_1_SPEC.md SS0) reads
    already-customized prompts, it does not customize a fourth template, so the dimension this would
    need to scale along isn't actually growing; (3) a generic dict-keyed structure here would be the
    textbook premature abstraction this project's own conventions reject -- three concrete, always-
    known-in-advance field groups are more legible as flat, independently-typed fields than as a dict
    requiring its own runtime shape validation to recover what Pydantic already gives named fields for
    free. Revisit only if a real fourth group is ever proposed, not preemptively."""

    step10_template_path: str | None = None
    step10_skeleton: TemplateSkeleton | None = None
    """CUSTOMIZATION_PHASE_2_SPEC.md SS0/SS4.4, relaxed from Phase 1's original required fields
    (2026-08-03): a state customizing step11/step12 need not have customized step10 in THIS state at
    all -- CUSTOMIZATION_PHASE_1_SPEC.md SS4.4's hard topology-independence constraint means step10
    may have been customized and executed via a wholly separate session/state file, and this state is
    only ever asked whether step10's real ARTIFACTS exist on disk (SS1.1's gate), never whether this
    state's own step10_* fields are populated. Requiring them unconditionally would make that
    legitimate case impossible to represent. step10's own customize flow still always populates both
    together, immediately, before ever reading them back -- unaffected in practice."""
    step10_bindings: list[PlaceholderBinding] = Field(default_factory=list)
    step10_output_path: str | None = None
    step10_fidelity: FidelityResult | None = None

    step11_template_path: str | None = None
    step11_skeleton: TemplateSkeleton | None = None
    step11_bindings: list[PlaceholderBinding] = Field(default_factory=list)
    step11_output_path: str | None = None
    step11_fidelity: FidelityResult | None = None

    step12_template_path: str | None = None
    step12_skeleton: TemplateSkeleton | None = None
    step12_bindings: list[PlaceholderBinding] = Field(default_factory=list)
    step12_output_path: str | None = None
    step12_fidelity: FidelityResult | None = None

    step14_template_path: str | None = None
    """The comprehension pass's own field group (.claude/loopr-step14-comprehension/baby_prd.md,
    2026-08-11) -- mirrors step11/step12's shape exactly, kept flat for the same reason the class
    docstring above already gives (a genuinely fourth field group was flagged and deferred at Phase 2;
    this is that fourth group, and it is still just one more named, always-known-in-advance set of
    fields, not the trigger for a dict-keyed rewrite)."""
    step14_skeleton: TemplateSkeleton | None = None
    step14_bindings: list[PlaceholderBinding] = Field(default_factory=list)
    step14_output_path: str | None = None
    step14_fidelity: FidelityResult | None = None

    @model_validator(mode="after")
    def check_output_precedes_fidelity(self) -> "CustomizationState":
        for step_name, path, fidelity in (
            ("step10", self.step10_output_path, self.step10_fidelity),
            ("step11", self.step11_output_path, self.step11_fidelity),
            ("step12", self.step12_output_path, self.step12_fidelity),
            ("step14", self.step14_output_path, self.step14_fidelity),
        ):
            if fidelity is not None and path is None:
                raise ValueError(f"{step_name}_fidelity requires {step_name}_output_path to be set first")
        return self
