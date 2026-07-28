"""Acceptance A-6, A-5: JudgeRequest scope enforcement and extra='forbid' on every model."""

from __future__ import annotations

import inspect
from typing import cast

import pytest
from pydantic import BaseModel, ValidationError

import loopr.models as loopr_models
from loopr.models.common import JudgeCallType
from loopr.models.judge import ALLOWED_INPUTS, JsonValue, JudgeRequest


@pytest.mark.parametrize("call_type", list(JudgeCallType))
def test_correct_scope_is_accepted(call_type: JudgeCallType) -> None:
    inputs = cast(
        "dict[str, JsonValue]", {key: f"value-for-{key}" for key in ALLOWED_INPUTS[call_type]}
    )
    request = JudgeRequest(
        call_id="abc123",
        call_type=call_type,
        rubric_id="r1",
        rubric_text="text",
        inputs=inputs,
        created_round=1,
    )
    assert request.inputs == inputs


@pytest.mark.parametrize("call_type", list(JudgeCallType))
def test_over_scoped_inputs_rejected(call_type: JudgeCallType) -> None:
    inputs = cast("dict[str, JsonValue]", {key: "v" for key in ALLOWED_INPUTS[call_type]})
    inputs["__extra_field_not_in_scope__"] = "v"
    with pytest.raises(ValidationError, match="scope violation"):
        JudgeRequest(
            call_id="abc123",
            call_type=call_type,
            rubric_id="r1",
            rubric_text="text",
            inputs=inputs,
            created_round=1,
        )


@pytest.mark.parametrize("call_type", list(JudgeCallType))
def test_under_scoped_inputs_rejected(call_type: JudgeCallType) -> None:
    allowed = list(ALLOWED_INPUTS[call_type])
    if len(allowed) < 2:
        pytest.skip("call type has a single scoped field; cannot under-scope")
    inputs = cast("dict[str, JsonValue]", {key: "v" for key in allowed[:-1]})
    with pytest.raises(ValidationError, match="scope violation"):
        JudgeRequest(
            call_id="abc123",
            call_type=call_type,
            rubric_id="r1",
            rubric_text="text",
            inputs=inputs,
            created_round=1,
        )


def test_every_model_forbids_extra_fields() -> None:
    checked = 0
    for name in dir(loopr_models):
        obj = getattr(loopr_models, name)
        if inspect.isclass(obj) and issubclass(obj, BaseModel):
            assert obj.model_config.get("extra") == "forbid", f"{name} does not forbid extra fields"
            checked += 1
    assert checked >= 10


def test_judge_request_is_frozen() -> None:
    inputs = cast(
        "dict[str, JsonValue]", {key: "v" for key in ALLOWED_INPUTS[JudgeCallType.C1_OUTCOME]}
    )
    request = JudgeRequest(
        call_id="x",
        call_type=JudgeCallType.C1_OUTCOME,
        rubric_id="r",
        rubric_text="t",
        inputs=inputs,
        created_round=1,
    )
    with pytest.raises(Exception):
        request.call_id = "changed"
