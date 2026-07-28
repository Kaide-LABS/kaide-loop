"""C5 misplaced-note routing must relocate, not duplicate.

Regression test for the proof-run finding: a context_notes entry judged misplaced (its content is
really testable spec content) is folded into acceptance_criteria, but the original ContextNote was
left standing in context_notes too -- so the same content rendered into both context.md and the
baby PRD. The fix must remove the entry once it is relocated.
"""

from __future__ import annotations

from loopr.interrogation.loop import _apply_judge_exchange
from loopr.models.common import JudgeCallType, NoteSource
from loopr.models.interrogation import ContextNote, InterrogationState
from loopr.models.judge import JudgeRequest, JudgeResponse


def test_misplaced_note_is_removed_from_context_notes_not_duplicated(
    greenfield_state: InterrogationState,
) -> None:
    note_text = "never let the model fabricate a ruling"
    greenfield_state.context_notes = [ContextNote(text=note_text, source=NoteSource.STATED)]

    request = JudgeRequest(
        call_id="deadbeefdeadbeef",
        call_type=JudgeCallType.C5_SOFT_CONTEXT,
        rubric_id="c5_soft_context_v1",
        rubric_text="rubric",
        inputs={"context_note": note_text, "acceptance_criteria": []},
        created_round=1,
    )
    response = JudgeResponse(
        call_id="deadbeefdeadbeef",
        passed=False,
        misplaced=True,
        reason="expressible as an acceptance criterion",
    )

    state = _apply_judge_exchange(greenfield_state, request, response)

    assert any(c.text == note_text for c in state.acceptance_criteria)
    assert not any(n.text == note_text for n in state.context_notes), (
        "misplaced note must be removed from context_notes once relocated to acceptance_criteria -- "
        "leaving it renders the same content into both context.md and the baby PRD"
    )


def test_misplaced_note_only_removes_the_matching_entry(
    greenfield_state: InterrogationState,
) -> None:
    misplaced_text = "citations must be verbatim"
    genuine_text = "tone must match the seriousness of the content"
    greenfield_state.context_notes = [
        ContextNote(text=misplaced_text, source=NoteSource.STATED),
        ContextNote(text=genuine_text, source=NoteSource.STATED),
    ]

    request = JudgeRequest(
        call_id="feedfacefeedface",
        call_type=JudgeCallType.C5_SOFT_CONTEXT,
        rubric_id="c5_soft_context_v1",
        rubric_text="rubric",
        inputs={"context_note": misplaced_text, "acceptance_criteria": []},
        created_round=1,
    )
    response = JudgeResponse(
        call_id="feedfacefeedface",
        passed=False,
        misplaced=True,
        reason="expressible as an acceptance criterion",
    )

    state = _apply_judge_exchange(greenfield_state, request, response)

    assert [n.text for n in state.context_notes] == [genuine_text]
