# Greenfield proof run — FINDINGS

Target project: `../loopr-proof-meeting-bot/` (created fresh alongside kaide-loop, `git init` only,
nothing else). Real, interactive interrogation run in chat; every judge verdict below was rendered
honestly by the invoking agent per each call's rubric, not pre-scripted.

## Invocation method used (and why)

`loopr` was run **from within kaide-loop's own environment** (installed via `pip install -e .` in
this repo), invoked with `--repo` pointing at the external target folder:

```
loopr init --repo "C:\Users\hp\loopr-proof-meeting-bot" --mode greenfield
loopr step  --state "C:\Users\hp\loopr-proof-meeting-bot\.loopr-state\state.json" ...
loopr emit  --state "C:\Users\hp\loopr-proof-meeting-bot\.loopr-state\state.json"
```

This is what PHASE_1_SPEC.md §6.1's `--repo PATH` argument and `_default_state_path` (`cli.py`)
actually support and expect — `--repo` takes an arbitrary filesystem path, and state defaults to
`<repo>/.loopr-state/state.json`. There is no requirement (and no support) for installing loopr
*inside* the target project; loopr is a tool invoked against a repo, not software living in it.
State (`.loopr-state/`) and artifacts (`.claude/loopr/`) both landed correctly under the target
folder, exactly as §6.3/§6.4/A5 specify. This run's artifacts are additionally mirrored here per
§8.3, since the acceptance gate lives in kaide-loop.

## Rounds and cap

**6 of 8 rounds used. Round cap NOT hit — no force-resolution occurred, no `Assumption` was
generated, `open_questions` is empty.** Every condition converged via genuine judge/structural
passes, not a forced guess.

## Judge calls — 6 total, zero flips/nondeterminism observed

| # | Round | Call type | Verdict | Note |
|---|---|---|---|---|
| 1 | 2 | `c1_outcome` | pass | Outcome-stated, not solution-first |
| 2 | 3 | `c2_acceptance` | pass | ≥1 sub-check independently checkable |
| 3 | 4 | `c3_scope_edges` | pass | Concrete boundary objects named |
| 4 | 5 | `c5_soft_context` | **misplaced** (not pass) | First soft-context note was actually testable spec content in disguise — correctly caught and folded into acceptance criteria, not counted as C5 |
| 5 | 5 | `c2_acceptance` (re-fired) | pass | Re-judged after the misplaced note changed the criteria list |
| 6 | 6 | `c5_soft_context` (re-asked) | pass | Second, genuinely subjective note (tonal register) accepted as real soft context |

Full envelopes and verdicts: `judge_exchange_log.md`. No call_id repeated with a different response
(no nondeterminism to observe in a single run by construction — replay would be the tool for that,
not this proof). Every `call_id` was hash-derived, never random.

## Gate chronology

Gate 2 (boundary) fired at round 4, confirmed at round 4. Gate 3 correctly never fired (greenfield —
no brownfield state). Gate 1 (baby PRD, TL;DR-first) fired last, at round 6, after both prior gates
were already settled — **exactly the chronology PHASE_1_SPEC.md §6.6.1 and the PRD's gate-numbering
note require (2 → 3[N/A] → 1), not the written-up order (1, 2, 3).**

## Scope-creep catch — worked as designed

Condition 3 (scope edges) drew out live-Zoom/STT exclusion from the user directly, and the module's
structural check (`check_c3_scope_edges`) and judge call both required it be a *concrete* boundary
object, not a vague one — it correctly passed a scope edge that named the Zoom SDK, an STT provider,
and a meeting-join network call as tripwires. The **boundary proposal** (drafted by the invoking
agent, since loopr's own module never calls an LLM — see below) explicitly carried the same exclusion
forward into the confirmed boundary text. No drift toward scoping in live Zoom/STT work occurred in
this run; the user stated the exclusion clearly and unprompted, so this proof does not distinguish
"the tool caught a user's temptation to scope-creep" from "the user never tried" — worth being honest
about, since it's a weaker signal than a case where the user pushed back.

## A design point clarified during the run (not a defect)

Gate 2's rendered payload body is a bare header until a `boundary_text` is supplied — the module
itself never proposes boundary content. This is *correct*, not a gap: per §6.2's LLM-routing
decision, loopr's own state machine never calls a model, so "loopr analyzes and proposes a boundary"
(PRD §A3) can only mean the **invoking agent** performs that analysis and supplies it via
`--gate-response --boundary-text`. Confirmed by reading `gates/gates.py` and `interrogation/loop.py`
directly rather than assumed.

## One content-duplication observation (context.md, minor)

The first soft-context note (judged `misplaced=True`) still appears verbatim in the emitted
`context.md`, in addition to being folded into `acceptance_criteria` — i.e. the same content now
exists in both the baby PRD's acceptance criteria and `context.md`'s soft-context section, rather
than being removed from `context_notes` once relocated. Not a G-7 (context.md rot) violation — the
renderer is not a blind append-only writer, and nothing here will compound across iterations within
this run — but it is a real, observable duplication a careful reader would notice, and worth a
cheap follow-up fix (deleting/marking the note superseded once its content is judged misplaced and
relocated).

## Acceptance signals (loopr-PRD.md §3)

**C-1, TL;DR moment:** Genuinely worked. The user's actual response to the Gate 1 TL;DR was "Yeah
that works" — no correction, no "that's not quite it." The TL;DR read back the outcome, the
correctness-boundary criteria, and the scope exclusion faithfully; nothing was generic or off.

**C-2, scope-creep catch:** Partially demonstrated, honestly caveated above — the boundary did
visibly carry the live-Zoom/STT exclusion forward as a named, confirmed boundary, and condition 3's
judge explicitly required (and got) a concrete boundary object rather than a vague one. What this run
does *not* show is the tool actively resisting a user who was trying to smuggle Zoom/STT scope in —
the user stated the exclusion cleanly from the start. Recommend a second calibration pass (or a
deliberate stress-test) where the user tries to sneak scope in, to get the stronger form of this
signal.

**C-3, no-rework readiness:** The baby PRD looks buildable as emitted — outcome, two acceptance
criteria (both judge-confirmed testable-in-part), one scope edge, and a confirmed boundary that
together capture the correctness boundary (reported-speech attribution, verbatim-or-omit citations,
explicit ambiguity-flagging, no fabrication) as *real, testable requirements*, not left implicit. The
tonal-register concern correctly landed in `context.md` rather than being smuggled into the spec as
an untestable acceptance criterion, which is itself evidence the C5 misplaced-routing mechanism works
as designed. No gap was identified in this run that the interrogation should have caught and didn't —
though a single run is not strong evidence of that; only building against this spec would surface a
spec-dropped gap if one exists.

## Correctness boundary — landed as real requirements, not dropped

Confirmed present in the emitted artifacts:
- Reported-speech attribution for rulings — acceptance criterion (baby_prd.md)
- Verbatim-or-omit citation matching — acceptance criterion
- Explicit flagging of ambiguous passages, never smoothed over — acceptance criterion
- No fabrication — acceptance criterion (folded in via the first misplaced note) AND implicitly
  reinforced by context.md's framing
- Tonal/register seriousness — context.md, correctly kept out of the spec as non-testable

## Calibration input (PHASE_1_SPEC.md §8.5)

- Rounds used: 6/8. Cap not hit — no calibration signal on the cap's tightness from this run alone.
- Structural-check false positives/negatives observed: none — every structural pre-check behaved as
  documented (C1 non-empty gate, C3 concrete-object requirement, C4 hash-bound confirmation, C5's
  explicit clean-slate offer, which fired the C5 question twice, correctly, once per genuine attempt).
- Recommendation: keep `max_rounds = 8` — nothing here argues for changing it, but a single 6-round
  clean run is weak calibration evidence on its own; the brownfield run and/or a deliberately
  adversarial greenfield run would strengthen this.
