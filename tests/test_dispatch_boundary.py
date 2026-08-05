"""The executable form of CUSTOMIZATION_PHASE_3_SPEC.md SS7's hard-boundary greps (guards G1-G3, G5,
G7, G8). Where SS7 names a manual review-agent check, this file is that check made mechanical.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from loopr.dispatch.controller import decide
from loopr.dispatch.log import audit_step10_calls
from loopr.models.common import DispatchStateId, DispatchTarget, Step10Warrant
from loopr.models.dispatch import DispatchDecision, DispatchState

CONTROLLER_PATH = Path(__file__).resolve().parents[1] / "src" / "loopr" / "dispatch" / "controller.py"
CONTROLLER_SOURCE = CONTROLLER_PATH.read_text(encoding="utf-8")
CONTROLLER_TREE = ast.parse(CONTROLLER_SOURCE)


def _find_function(name: str) -> ast.FunctionDef:
    for node in ast.walk(CONTROLLER_TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name!r} not found in controller.py")


DECIDE_NODE = _find_function("decide")


# --- G1: escalation-by-default (the hard boundary; auto-reject on breach) ---


def test_decide_has_no_else_or_try_blocks() -> None:
    """No `else:`/`elif`-trailing-else and no `try:` anywhere inside `decide()` -- a swallowed
    exception or a catch-all branch is a silent escalation path. `match`/`case` is exempt from the
    'else' ban: its one wildcard arm (below) is a static-typing proof, not a routing branch -- checked
    separately by `test_decide_ends_in_assert_never_not_a_routing_fallback`."""
    for node in ast.walk(DECIDE_NODE):
        if isinstance(node, ast.Try):
            raise AssertionError("decide() must not contain a try/except block")
        if isinstance(node, ast.If) and node.orelse:
            raise AssertionError(
                "decide() must not contain an else/elif branch -- every branch must be a "
                "standalone guard clause with an early return"
            )


def test_decide_source_contains_no_else_colon_or_try_colon() -> None:
    """Belt-and-braces text-level check matching SS7 G1's own literal wording ('grep for these') for
    the two constructs that are unambiguous as real syntax regardless of surrounding prose: an actual
    `else:`/`try:` block opener. (A bare word like "default" or "except" can legitimately appear in
    a docstring that explains this very rule -- `test_decide_has_no_else_or_try_blocks` above already
    checks the real AST, which prose text can't fool either way.)"""
    decide_source = ast.get_source_segment(CONTROLLER_SOURCE, DECIDE_NODE)
    assert decide_source is not None
    assert not re.search(r"\belse\s*:", decide_source)
    assert not re.search(r"\btry\s*:", decide_source)


def test_decide_ends_in_assert_never_not_a_routing_fallback() -> None:
    """SS6.2 point 3: the final branch over Step12Verdict ends in typing.assert_never, proven
    unreachable by mypy --strict, never a routing fallback that could silently reach step10."""
    match_nodes = [node for node in ast.walk(DECIDE_NODE) if isinstance(node, ast.Match)]
    assert len(match_nodes) == 1
    last_case = match_nodes[0].cases[-1]
    assert isinstance(last_case.pattern, ast.MatchAs) and last_case.pattern.pattern is None
    call = last_case.body[-1]
    assert isinstance(call, ast.Expr) and isinstance(call.value, ast.Call)
    func = call.value.func
    assert isinstance(func, ast.Attribute) and func.attr == "assert_never"


def test_step10_target_construction_appears_only_in_rows_1_and_2() -> None:
    """SS7 G1: any return/construction of a decision with target=DispatchTarget.STEP_10 outside
    S2_STEP10_IN_FLIGHT (row 2) and S1_PRE_STEP10 (row 3) is the escalation-by-default breach."""
    step10_returns = 0
    for node in ast.walk(DECIDE_NODE):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            for keyword in node.value.keywords:
                if (
                    keyword.arg == "target"
                    and isinstance(keyword.value, ast.Attribute)
                    and keyword.value.attr == "STEP_10"
                ):
                    step10_returns += 1
    # S2's two warrant branches (greenfield-resume, remodernize-resume) plus S1's fresh dispatch.
    assert step10_returns == 3


def test_len_step10_warrant_is_exactly_two() -> None:
    assert len(Step10Warrant) == 2


def test_no_forbidden_identifiers_or_comments_in_controller_module() -> None:
    pattern = re.compile(
        r"uncertain|fallback|safe(r|ty)?[_ ]?default|when in doubt|just in case|to be safe",
        re.IGNORECASE,
    )
    match = pattern.search(CONTROLLER_SOURCE)
    assert match is None, f"forbidden pattern found: {match.group(0)!r}"


def test_full_trace_produces_zero_step10_dispatches() -> None:
    """SS7 G1 positive check: the SS6.4 trace (also asserted step-by-step in
    test_dispatch_transitions.py) produces zero step10 dispatches."""
    from loopr.dispatch.controller import apply_completion_transition, apply_dispatch_transition
    from loopr.models.common import CustomizationStep, Step12Verdict

    state = DispatchState()
    targets = []

    decision = decide(state, artifacts_present=True, build_complete_present=False)
    targets.append(decision.target)
    state = apply_dispatch_transition(state, decision.target)
    state = apply_completion_transition(state, CustomizationStep.STEP_11, None)

    decision = decide(state, artifacts_present=True, build_complete_present=False)
    targets.append(decision.target)
    state = apply_dispatch_transition(state, decision.target)
    state = apply_completion_transition(state, CustomizationStep.STEP_12, Step12Verdict.CLEAN)

    decision = decide(state, artifacts_present=True, build_complete_present=False)
    targets.append(decision.target)

    assert DispatchTarget.STEP_10 not in targets


def test_every_step10_decision_has_a_non_none_warrant() -> None:
    for warrant in Step10Warrant:
        decision = DispatchDecision(
            state_id=DispatchStateId.S1_PRE_STEP10,
            target=DispatchTarget.STEP_10,
            reason="test",
            step10_warrant=warrant,
            step10_declined_because=None,
            build_round=0,
        )
        assert decision.step10_warrant is not None


def test_step10_decision_unconstructable_without_warrant() -> None:
    with pytest.raises(Exception):
        DispatchDecision(
            state_id=DispatchStateId.S1_PRE_STEP10,
            target=DispatchTarget.STEP_10,
            reason="test",
            step10_warrant=None,
            step10_declined_because=None,
            build_round=0,
        )


# --- G2: non-total routing ---


def test_decide_matches_every_step12verdict_member_explicitly() -> None:
    """Documents the negative compile-time assertion SS7 G2 names ('a test that removes a routing
    arm fails to type-check') -- that check is `mypy --strict` itself, not something pytest can
    exercise at runtime (removing an arm and re-running mypy would require mutating source on disk).
    What IS checked here at runtime: every real Step12Verdict member has its own explicit `case`
    clause in the match statement (no member is silently merged into the wildcard branch)."""
    match_node = next(node for node in ast.walk(DECIDE_NODE) if isinstance(node, ast.Match))
    matched_members = set()
    for case in match_node.cases[:-1]:  # last case is the assert_never wildcard
        pattern = case.pattern
        if isinstance(pattern, ast.MatchValue) and isinstance(pattern.value, ast.Attribute):
            matched_members.add(pattern.value.attr)
        elif isinstance(pattern, ast.MatchSingleton) and pattern.value is None:
            matched_members.add("NONE")
    assert matched_members == {"CLEAN", "MINOR", "SPEC_VIOLATING", "NONE"}


# --- G3: silence read as evidence ---


def test_non_step10_decision_unconstructable_without_declined_because() -> None:
    with pytest.raises(Exception):
        DispatchDecision(
            state_id=DispatchStateId.S3_STEP10_DONE,
            target=DispatchTarget.STEP_11,
            reason="test",
            step10_warrant=None,
            step10_declined_because=None,
            build_round=0,
        )


def test_dispatch_audit_halts_on_missing_warrant() -> None:
    records = [
        {
            "state_id": "s1_pre_step10",
            "target": "loopr-step10",
            "reason": "planted",
            "step10_warrant": None,
            "step10_declined_because": None,
            "build_round": 0,
            "ts": "2026-08-05T00:00:00Z",
        }
    ]
    entries = audit_step10_calls(records)
    assert any(not entry.valid for entry in entries)


# --- G5: scope leak into Phase B ---


_FORBIDDEN_IMPORT_MODULES = ("loopr.judge", "loopr.gates", "loopr.interrogation", "subprocess")


def test_controller_imports_nothing_from_the_forbidden_modules() -> None:
    imported_modules: list[str] = []
    for node in ast.walk(CONTROLLER_TREE):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)

    for imported in imported_modules:
        for forbidden in _FORBIDDEN_IMPORT_MODULES:
            assert not (imported == forbidden or imported.startswith(forbidden + ".")), (
                f"controller.py imports {imported!r}, which is or is under the forbidden module "
                f"{forbidden!r}"
            )


def test_controller_module_contains_no_git_substring() -> None:
    assert "git" not in CONTROLLER_SOURCE.lower()


def test_decide_signature_is_exactly_state_artifacts_present_build_complete_present() -> None:
    args = [arg.arg for arg in DECIDE_NODE.args.args]
    assert args == ["state", "artifacts_present", "build_complete_present"]


# --- G7: redundant source of truth for "has step10 run" ---


_MODELS_DIR = Path(__file__).resolve().parents[1] / "src" / "loopr" / "models"
_FORBIDDEN_FIELD_PATTERN = re.compile(r"step10_(done|executed)\s*:")


def test_no_persisted_step10_done_boolean_on_any_model() -> None:
    for path in _MODELS_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        match = _FORBIDDEN_FIELD_PATTERN.search(text)
        assert match is None, f"{path} declares a forbidden cached field: {match.group(0)!r}"


# --- G8: reimplementing the step10 artifact check ---


_DISPATCH_DIR = Path(__file__).resolve().parents[1] / "src" / "loopr" / "dispatch"


def test_dispatch_package_never_globs_for_markdown_itself() -> None:
    for path in _DISPATCH_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "glob(" not in text, (
            f"{path} calls glob() directly -- artifact detection must go through the existing "
            "find_step10_execution_artifacts, never a reimplementation (SS7 guard G8)"
        )
