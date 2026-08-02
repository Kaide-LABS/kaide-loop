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
    step10_template_path: str = Field(min_length=1)
    step10_skeleton: TemplateSkeleton
    step10_bindings: list[PlaceholderBinding] = Field(default_factory=list)
    step10_output_path: str | None = None
    step10_fidelity: FidelityResult | None = None

    @model_validator(mode="after")
    def check_output_precedes_fidelity(self) -> "CustomizationState":
        if self.step10_fidelity is not None and self.step10_output_path is None:
            raise ValueError("step10_fidelity requires step10_output_path to be set first")
        return self
