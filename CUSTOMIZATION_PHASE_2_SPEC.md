# CUSTOMIZATION_PHASE_2_SPEC.md — step11/step12 Customization (Phase 2 of 3)

Built on Phase 1's approved output (`3e25f41`) and the same confirmed baby PRD as Phase 1
(`proofs/customization-layer/`). No new interrogation — the boundary, scope edge, and acceptance
criterion from that run still govern this phase; nothing here reopens them.

Scope narrowed from the original "Phase 2 of 2" (see `CUSTOMIZATION_PHASE_1_SPEC.md` §0's amendment):
this phase is step11/step12 customization only. Loop sequencing to `BUILD_COMPLETE.md` is now
Phase 3, on a real dependency boundary — sequencing operates on already-customized prompts
regardless of what produced them, and doesn't need this phase's mechanism to exist first in any
technical sense, only chronologically (there is no build to sequence without a step11 prompt to run).

**[AMENDED 2026-08-03 — written before `CUSTOMIZATION_PHASE_1_SPEC.md`'s subagent amendment; this
spec inherits it, not written against it originally.]** Both steps' output is now a subagent
definition (`.claude/agents/loopr-step11.md`, `loopr-step12.md`), not a plain file — step11 pinned
Sonnet at low effort, step12 pinned Sonnet at high effort, confirmed by the user 2026-08-03. See
`CUSTOMIZATION_PHASE_1_SPEC.md` §1 and §6.1a for the full reasoning and the precise, narrower-than-it-
looks boundary of what this does and doesn't reopen — this spec doesn't repeat it, only what's
specific to step11/step12 is noted here (§2, §6, §7.1).

---

## §0 Phase Plan Header

**Phase 2 of 3.** Deliverable: `loopr customize --step 11` and `loopr customize --step 12`, both
gated on step10 having genuinely *executed* (§1.1), each independently fidelity-checked the same way
step10's output already is.

---

## §1 What step10 executing actually provides — the two-pass dependency, concrete now

`CUSTOMIZATION_PHASE_1_SPEC.md` §5 named the dependency in the abstract. Grounded now against the
real templates:

### 1.1 Gating condition

`loopr customize --step 11` and `--step 12` must refuse to run unless step10 has produced its two
real deliverables in the target project: a modernised PRD and `PHASE_1_SPEC.md` (Deliverable A and B
per the step10 template's own §4/§5). **Customizing step10 is not the same as running it** —
Phase 1 produces a prompt; running that prompt against a real project is what produces the artifacts
this phase reads. Check for their existence directly; do not infer readiness from
`CustomizationState.step10_fidelity` alone, which only proves the *prompt* was well-formed, not that
it was ever executed.

### 1.2 What step10's output actually resolves, verified per-token, not assumed

Full token-set diff, computed directly against the three real files, not carried from memory:

```
present in all three:        [PHASE_COUNT]  [PROJECT_NAME]  [PROJECT_REPO_NAME]
STEP_10-only (dropped):      [PRD_FILENAME]  [RESEARCH FOCUS]  [UNVERIFIED]
new in STEP_11:               [ ]  [EXECUTOR]  [PROJECT]  [PROJECT_TAG]
                               [implemented instead]  [reason]  [specified]
                               [wanted to do]  [why the invariant prevents it]
new in step_12:                [ ]  [EXECUTOR]  [EXECUTOR_AGENT_FICTION]
                               [PROJECT]  [PROJECT_TAG]
```

| Token | step10 classification | step11/12 classification | Why |
|---|---|---|---|
| `[PHASE_COUNT]` | non-placeholder (unknowable) | **customizer-resolvable** | `PHASE_1_SPEC.md` §0's phase plan header states it once step10 has run |
| `[PROJECT_NAME]`, `[PROJECT_REPO_NAME]` | customizer-resolvable | customizer-resolvable, unchanged | Same source, independent of step10 |
| `[PROJECT]` | *(absent — verified, not in STEP_10's real inventory)* | customizer-resolvable, new | First appears here |
| `[PROJECT_TAG]` | *(absent from STEP_10)* | customizer-resolvable, new | Git commit tag convention |
| `[EXECUTOR_AGENT_FICTION]` | *(absent from STEP_10)* | customizer-resolvable, new — step12 only | See §7.1 |
| `[EXECUTOR]` | non-placeholder | non-placeholder, new occurrence but same rule | Reject-pattern shorthand, both templates |
| `[UNVERIFIED]`, `[RESEARCH FOCUS]`, `[PRD_FILENAME]` | step10-specific | **do not occur** — verified above, not assumed | N/A |
| `[ ]` | *(absent from STEP_10)* | non-placeholder, new class | Checkbox markup in the customization-checklist section (§3.3) — a single space matches the narrow token regex |
| `[specified]`, `[implemented instead]`, `[reason]`, `[wanted to do]`, `[why the invariant prevents it]` | *(absent from STEP_10)* | non-placeholder, new sub-category — step11 only | Agent-emitted output-format placeholders inside the AUTONOMOUS CRITIQUE example block, filled by the *executor* at runtime, not the customizer — same underlying rule as `[EXECUTOR]`, different reason, worth distinguishing in the registry docstring (§7.2) |

**`[PHASE_COUNT]`'s flip is the one existing engineering trap most likely to recur if this phase is
implemented by extending step10's registries in place rather than declaring step-scoped ones.** The
existing `STEP10_PLACEHOLDER_ALLOWLIST` / `NON_PLACEHOLDER_BRACKET_TOKENS` naming already signals
per-step scope; keep that discipline literal. A single shared allowlist across all three steps would
either wrongly resolve `[PHASE_COUNT]` for step10 or wrongly refuse it for step11/12 — there is no
correct single answer, which is exactly why step-scoping exists.

---

## §2 Files added or modified

| File | Change |
|---|---|
| `src/loopr/models/common.py` | Add `JudgeCallType.STEP11_CUSTOMIZATION`, `STEP11_FIDELITY_JUDGE`, `STEP12_CUSTOMIZATION`, `STEP12_FIDELITY_JUDGE` (four, not two — step11 and step12 each need their own customization + fidelity pair, same as step10 did) |
| `src/loopr/models/judge.py` | `ALLOWED_INPUTS_V4`. **Bump to 4, never edit V3 in place** — same version-gating contract as every prior bump (`models/judge.py` lines 23–30) |
| `src/loopr/customization/templates.py` | Extend `STEP10_PLACEHOLDER_ALLOWLIST` naming pattern to `STEP11_PLACEHOLDER_ALLOWLIST` / `STEP12_PLACEHOLDER_ALLOWLIST` and matching non-placeholder sets — **do not generalize into one shared set** (§1.2). Add a `SECTION_DELETIONS` registry per step (§3.3) and a `CONDITIONAL_BLOCKS` registry per step (§3.4), same explicit-registration discipline as `STEP10_FILL_IN_BLOCK_MARKERS` — reviewed additions only, never inferred. |
| `src/loopr/customization/fidelity.py` | Skeleton comparison must subtract declared-for-deletion sections before comparing (§3.3) — the raw template skeleton is no longer the exact target. |
| `src/loopr/customization/customize.py` | Extend for four new judge call types; add conditional-block resolution (§3.4) as a third response shape alongside token-fill and section-deletion. |
| `src/loopr/rubrics/texts.py` | Four new rubric texts. |
| `src/loopr/cli.py` | `loopr customize --step {10,11,12}` — extend the existing subcommand's choices, not a new subcommand. Add the step10-execution gate (§1.1). Output target per `CUSTOMIZATION_PHASE_1_SPEC.md` §6.1a: `.claude/agents/loopr-step11.md` (Sonnet, low effort), `.claude/agents/loopr-step12.md` (Sonnet, high effort) — same unverified-frontmatter-schema caveat applies, do not re-verify independently, the open question is shared across all three steps. |
| `src/loopr/models/customization.py` | `CustomizationState` gains `step11_*` / `step12_*` field groups mirroring `step10_*` exactly. Consider whether the flat-field-per-step shape from Phase 1 should become a `dict[CustomizationStep, StepCustomization]` here — three parallel field groups is tolerable, this is the point past which a fourth would not be; not urgent, worth a decision in this phase since the shape gets harder to change later. |
| `tests/test_customization_templates.py` (extended), `tests/test_customization_fidelity.py` (extended), new: `tests/test_customization_step11.py`, `tests/test_customization_step12.py` | |

**Also required, carried from Phase 1's review handoff, not new work discovered here:** add the
registry-regression test flagged at Phase 1's close — monkeypatch `STEP10_FILL_IN_BLOCK_MARKERS` to
empty and confirm the hard-boundary span reappears in `find_unclassified_bracket_spans`'s output.
Small, do it first, before extending the pattern to two more steps that would otherwise inherit the
same untested edge three times over instead of once.

---

## §3 The three new operation types

Phase 1 had one operation: fill a short token. This phase needs three more, each verified against
the real files, not designed from the token list alone.

### 3.1 Fill (unchanged from Phase 1)

`[PROJECT_NAME]`, `[PROJECT_TAG]`, etc. — short value replaces short token. Same mechanism, extended
registries.

### 3.2 Multi-line fill-in block (unchanged mechanism, verify no new instances)

Phase 1's `STEP10_FILL_IN_BLOCK_MARKERS` pattern (template's own text as the sentinel) is reusable
as-is. **Run the independent-oracle wide scan against both real templates as the first implementation
step, not an afterthought** — Phase 1's own review found its worst defect this way, twice, and the
`[PROJECT_*]` finding already flagged at Phase 1's close (§7.2) means this scan is known to surface
*something*, just not yet triaged.

### 3.3 Section deletion — new, and it changes the fidelity contract

Both templates end in a `## TEMPLATE CUSTOMIZATION CHECKLIST` section whose own body text instructs:
*"remove before pasting to Claude Code."* This is not a fill target — it is scaffolding for the human
who customizes the template by hand, and the customized *output* must not contain it at all.

**Consequence for `fidelity.py`:** Phase 1's skeleton check requires the output's skeleton to equal
the template's skeleton, in order, nothing missing. That rule is now wrong for step11/step12 as
written. The correct check: output skeleton equals template skeleton **minus every section declared
in a new `SECTION_DELETIONS` registry** (one entry per step: the checklist header string), same
explicit-registration discipline as the fill-in-block registry — a check that silently accepts *any*
missing section would reopen exactly the vacuous-pass risk Phase 1 closed for the opposite case
(section presence). Verify the delta, don't just loosen the equality.

### 3.4 Conditional include-or-replace — new

`<<CITATION_GATE_BLOCK>>` (step12) and `<<CITATION_GATE_INGESTION_BLOCK>>` (step11) are neither
fill targets nor deletions. Per the templates' own instructions: include verbatim if the project has
load-bearing arXiv citations anchoring its architecture, otherwise replace with a single stated line
("no citation re-verification gate required for this project" — the templates already specify the
replacement text; use it verbatim, don't paraphrase it).

This is a judgment call, not a structural one — whether *this* project has load-bearing citations
isn't decidable by pattern-matching. Route it through the customization judge call (§3.1's mechanism
already carries `conformance_summary`; this needs the confirmed spec's own content, which the
customization judge already receives in full) rather than inventing a fifth judge call type for a
single boolean. State this as the judge's decision, with a reason, same as every other judgment in
this system — don't let a binary decision skip the reasoning requirement just because it's binary.

---

## §4 Sequencing within this phase

step11 and step12 do not depend on each other — both depend only on step10's output (§1), not on one
another. Customize in either order, or in parallel; there's no ordering constraint to encode. Do not
build one assuming the other has already run.

---

## §5 Acceptance criteria

1. Both `--step 11` and `--step 12` refuse to run unless step10's actual output artifacts exist in
   the target project (§1.1) — demonstrated by attempting against a project with only a customized
   (not executed) step10 prompt, and confirming refusal.
2. `[PHASE_COUNT]` resolves correctly for step11/step12 against a real `PHASE_1_SPEC.md` §0 header —
   demonstrated against a real one, not a synthetic fixture standing in for it.
3. The independent-oracle wide scan returns `[]` against both real templates once implemented, or
   names exactly what it finds if not — the `[PROJECT_*]` finding from Phase 1's close gets resolved
   here, not carried forward again.
4. A customization that leaves the `TEMPLATE CUSTOMIZATION CHECKLIST` section in the output is
   **rejected** by the corrected skeleton check (§3.3) — demonstrated firing, not merely present.
5. A customization that drops a *real* section (not the checklist) is still rejected — confirms §3.3's
   subtraction didn't accidentally loosen the check for everything else.
6. The citation-gate decision (§3.4) is demonstrated both ways: a project with no load-bearing
   citations gets the single-line replacement verbatim; a project with them gets the block preserved.
7. `mypy --strict` clean; full suite green; `test_no_paid_dependency`, `test_no_hardcoded_domain`
   still passing; the carried-forward registry-regression test (§2) passing.

---

## §6 Explicit non-goals

- **Loop sequencing to `BUILD_COMPLETE.md`** — Phase 3, per §0's amendment. Git-marker phase
  discovery, detecting terminal state, telling the invoking agent which customized prompt runs next.
  None of it here.
- **[AMENDED 2026-08-03]** ~~Native subagents, Traycer, any harness — confirmed scope edge, unchanged
  since the original interrogation.~~ Subagent *generation* for step11/step12 is now in scope (see
  the amendment note under the title). **Still fully out:** Traycer; the Phase B harness as a loop
  (build→review→audit orchestration, git-marker phase discovery, gates-as-ground-truth, audit tier);
  and — still true even with subagents generated — whatever decides *when* to dispatch one. That's
  Phase 3's open question per `CUSTOMIZATION_PHASE_1_SPEC.md` §0's forward note, not settled by this
  phase generating the subagents that a future dispatcher would target.
- **Re-deciding `[PHASE_COUNT]`'s step10 classification** — it stays non-placeholder there. §1.2's
  table is additive, not a reopening.

---

## §7 Known tensions, disclosed

### 7.1 `[EXECUTOR_AGENT_FICTION]` and topology independence

`CUSTOMIZATION_PHASE_1_SPEC.md` §7.1 already covers the honest version of this: when
`prompts/loopr/step12_review.md` was hand-customized for loopr's own build, the fiction was replaced
with a true statement, since the build and review passes are genuinely separate there. Whether this
mechanism should *detect* single-vs-two-session topology and adjust the drafted value is tempting and
**must be rejected** — it would violate §4.4's hard constraint (no code path may branch on session
identity). The customization judge drafts *a* value for `[EXECUTOR_AGENT_FICTION]` grounded in the
confirmed spec content available to it; if that content doesn't establish genuine separateness, the
fiction is the honest default, not a topology-detection outcome. Keep the judge blind to topology,
same as everything else in this system already is.

**[NOTE ADDED 2026-08-03]** Subagent dispatch (§2, per `CUSTOMIZATION_PHASE_1_SPEC.md` §1/§6.1a)
changes the ground truth this rubric is drafting *about*, not the rule above. Step11 and step12 now
dispatch as genuinely separate subagents by default — see Phase 1's amended §7.1 for exactly what
that does and doesn't fix (real separation for build-vs-review, not a general solve for every context
bleed). This phase's judge call still doesn't get to know that, and still shouldn't — it drafts from
confirmed spec content, same as always; it's a fact for a human reading the output to know, not an
input the judge branches on.

### 7.2 The `[PROJECT_*]` finding from Phase 1's close

Now identified precisely (§1.2's table, §3's line 5 of the STEP_11 grep): `Customization surfaces are
marked [PROJECT_*] and <<CUSTOMIZE: ...>>` — descriptive prose in the templates' own opening
paragraph, referencing a token *pattern* by example, not a literal token. The independent-oracle wide
scan will find `[PROJECT_*]` as a bracket span; it needs classifying as non-placeholder (documentation
about the template, not a fill target), same category as `[EXECUTOR]`, for a different underlying
reason — worth naming the distinction in the registry's docstring so a future reader doesn't conflate
"looks like a token but isn't" with "is agent-emitted," which are different reasons landing in the
same set.
