# SKILL_PHASE_1_SPEC.md — Claude Code Skill Packaging (Phase 1 of 1)

Built FROM the baby PRD confirmed via a real loopr brownfield run against this repo
(2026-07-31) — `proofs/skill-packaging/` holds the emitted `baby_prd.md`, `context.md`,
and `conformance-ledger.md` this spec is derived from. Namespaced per the marker
decision in `loopr-PRD.md` §5 A3a / this build's own boundary: `PHASE_1_SPEC.md` and
`BUILD_COMPLETE.md` (the standalone-module build) stay untouched. This is a separate,
additive spec series, not a continuation of that one.

Sequencing: `loopr-MIGRATION.md` §2, step 2 — package loopr as a Claude Code skill,
now that step 1 is proven. Written by the architect from loopr's own confirmed
output, the same way Step 10's Deliverable B always worked — loopr's Phase 1 module
doesn't yet generate this tier of granular blueprint itself (that's the A5 half we're
deliberately not building; see §9 below).

---

## §0 Phase Plan Header

**Phase 1 of 1.** This is the entire skill-packaging build — there is no Phase 2
within this spec series. On approval, the review step writes `SKILL_BUILD_COMPLETE.md`
directly, not a next phase spec.

---

## §1 Confirmed baby PRD (source of truth for this spec)

**TL;DR:** A builder using Claude Code can invoke `/loopr` directly and get the
spec-discipline engine's interrogation-through-boundary-and-research-grounded-expansion,
plus phase-spec generation, without touching the raw CLI — so loopr's discipline is
one command away instead of requiring manual `loopr init`/`step`/`emit` invocation.

**Acceptance criterion (deduplicated — see §7 for why two near-identical entries
existed in the emitted baby PRD and why this spec treats them as one):**
Running `/loopr` inside a target project produces `baby_prd.md` and `context.md`
output that matches byte-for-byte with running the raw `loopr` CLI directly, given
the same answers — a third party can diff the two and confirm zero drift between the
packaged skill and the underlying module.

**Scope edge:** gate/subagent generation (the harness-facing half of A5) is out —
that's the interface to the parked Phase B/Traycer harness, not yet assessed against
the three invariants. This build covers A1–A4 plus phase-spec generation only.

**Confirmed boundary:** packages loopr's spec-discipline engine as a Claude Code
skill (`.claude/skills/loopr/`: `SKILL.md`, `references/`, `scripts/`) per
`loopr-PRD.md` §9. In scope: A1–A4 plus phase-spec generation for target projects.
Out of scope: A5's gate/subagent generation. Invocation: a bundled wrapper script
calling the already-installed `loopr` package, with a preflight check in `SKILL.md`
that fails loudly with the exact install command if `loopr` isn't importable.

**Context (`context.md`, not an acceptance criterion — shapes judgment, isn't itself
tested):** `loopr-PRD.md` §13 currently claims loopr "works with zero setup." This
build's invocation design means that's no longer literally true — there's a one-time
`pip install` before the skill functions. Shipping this build without addressing that
inconsistency would be judged a failure even if the skill itself works, because the
project's own documentation would contradict its implementation. See §6.4 and §9.

**Conformance ledger:** empty. Zero patterns crossed the recurrence threshold on the
touched surface (6 files, mostly docs/config, one Python file) — no existing
convention or cruft to honor or avoid here. Gate 3 correctly never fired.

---

## §2 Files added or modified

```
.claude/skills/loopr/
├── SKILL.md
├── references/
│   ├── stopping-test.md
│   ├── context-md-guide.md
│   ├── boundary-guide.md
│   ├── conformance-classification-guide.md
│   └── continuity-model.md
└── scripts/
    └── loopr_wrapper.py
```

**Deliberate deviation from `loopr-PRD.md` §9's original sketch — flagged, not
silent:** that section predates both the brownfield decision (section 1a) and this
build's confirmed boundary. Two differences:
- **No `assets/gate-templates/` and no `references/prompt-templates/`.** Both are
  harness-facing (gate recipes, step11/step12 templates feed Phase B), which this
  build's confirmed scope edge explicitly excludes. Build these when A5's harness
  half actually gets built, not now, on a boundary we haven't confirmed for that
  work.
- **Added `references/conformance-classification-guide.md`,** not in the original
  sketch. §9 predates `docs/conformance-classification-spec.md` existing at all —
  the brownfield mechanism (A3a) is in this build's confirmed scope, so it needs a
  reference doc same as the other four A1–A4 mechanisms do.

`loopr-PRD.md` §13 is modified (not added) — see §6.4.

---

## §3 Dependencies

None new. `SKILL.md`'s preflight check depends on the `loopr` package already being
importable (installed via `pip install -e .` from this repo, or `pip install loopr`
once/if it's ever published) — that dependency already exists from the Phase 1 build;
this spec doesn't add anything to it.

---

## §4 SKILL.md content requirements

- **Word budget: under ~5000 words**, per `loopr-PRD.md` §9. This is a real,
  checkable constraint (`wc -w`), not a suggestion — progressive disclosure only
  works if `SKILL.md` stays lean and the detail lives in `references/`.
- **Preflight check, first thing the skill does, before any interrogation logic:**
  attempt to import `loopr` (or shell out to `loopr --version`, whichever the wrapper
  script in §6 actually implements). On failure, the skill's ENTIRE output for that
  invocation is the exact install command (`pip install -e .` from this repo, or the
  published-package form) and nothing else — no partial interrogation, no vague
  "something went wrong." This is the same lesson as the Docker post-mortem's
  auth-preflight finding (`loopr-MIGRATION.md` §7), applied to a different failure
  class: **discover the missing dependency before doing any real work, not mid-run.**
- **Orchestration logic:** drive the `loopr init` → `step` (looping on
  `QUESTION_REQUIRED`/`JUDGE_REQUIRED`/`GATE_REQUIRED`) → `emit` cycle exactly as
  `PHASE_1_SPEC.md` §6.1's exit-code contract already specifies — `SKILL.md` is an
  orchestration prompt over the existing CLI contract, not a reimplementation of it.
  This is the mechanism §1's acceptance criterion tests: if `SKILL.md` drifts into
  reimplementing behavior instead of faithfully driving the CLI, the byte-diff check
  catches it.
- **Deliberate invocation only** (`/loopr`), never auto-triggered — per `loopr-PRD.md`
  §9's existing design note, unchanged by this build.

---

## §5 references/ content requirements

Each file condenses its source spec — not a byte-for-byte copy, but nothing
substantive dropped. Source specs are the confirmed, canonical versions; a reference
doc that drifts from its source is a defect, not a stylistic choice.

| Reference file | Condenses | Must preserve |
|---|---|---|
| `stopping-test.md` | `docs/stopping-test-spec.md` (2385 words) | All six conditions' pass/fail logic, the Shape 1/Shape 2 distinction, the round-cap mechanism including the 2026-07-30 generalization (§B2) and the C5 relevance-check amendment |
| `context-md-guide.md` | `loopr-PRD.md` §A2's `context.md` split rule, condition 5's amended rubric | The "changes judgment but not expressible as a spec requirement" test, and the relevance check (does it relate to problem/criteria/scope/boundary at all) |
| `boundary-guide.md` | `loopr-PRD.md` §A3 | Proposed-then-confirmed shape, "preferred not mandatory," the escape hatch (`declined`) |
| `conformance-classification-guide.md` | `docs/conformance-classification-spec.md` (2544 words) | The CONFORM/DO_NOT_REPLICATE/CONFLICT/AMBIGUOUS four-way verdict, touched-surface discovery's two-stage design, the no-external-semantic-search-dependency reasoning (so a reader doesn't wonder why Nia/Context7 aren't used), the Gate-3-before-Gate-1 chronology |
| `continuity-model.md` | `loopr-PRD.md` §7 | Immutable charter, layered `context.md`, supersession-not-deletion |

---

## §6 Implementation logic flow

### 6.1 Wrapper script (`scripts/loopr_wrapper.py`)

Thin. Its only jobs: (a) the preflight importability check (§4), (b) translate
`SKILL.md`'s orchestration calls into the actual `loopr` CLI invocations, (c) surface
the CLI's own exit codes and pending-file contents back to the orchestrating prompt
unmodified. It must NOT contain interrogation logic, judge-call logic, or artifact
rendering of its own — all of that already exists in `src/loopr/`. A wrapper that
reimplements any of that is a defect (would break §1's acceptance criterion by
construction) and a scope violation (rebuilding what Phase 1 already built).

### 6.2 State and artifact locations

Unchanged from the CLI's own defaults (`PHASE_1_SPEC.md` §6.3/§6.6): state under
`<target>/.loopr-state/`, artifacts emitted to `<target>/.claude/loopr/`. The skill
does not introduce a different location — same tool, same contract, different entry
point.

### 6.3 No new judge-call mechanism

`SKILL.md`'s own model IS the invoking agent — when `loopr step` returns
`JUDGE_REQUIRED`, the Claude Code session running the skill answers it directly, per
the existing `AgentJudgeClient` contract (`PHASE_1_SPEC.md` §6.2). This is not a new
design decision; it's the same one already resolved for the standalone module,
inherited unchanged.

### 6.4 The `loopr-PRD.md` §13 amendment

Per §1's context entry: replace the unqualified "works with zero setup" claim with
an accurate one — e.g. "works with zero setup for research grounding (native web
search baseline); the module itself requires a one-time `pip install`." Do not just
delete the zero-setup claim; state precisely what IS and isn't zero-setup, since the
original claim's spirit (no paid dependency, no heavy install) is still true and
worth keeping — only the "zero setup, full stop" framing is now inaccurate.

---

## §7 Known findings from this build's own spec run (informational — not this
spec's job to fix)

The interrogation that produced this spec's baby PRD surfaced two findings about
**loopr's own module**, not about this skill-packaging build. Recorded here for
traceability since they're why §1's acceptance criterion appears deduplicated from
two near-identical submitted entries — NOT in scope for this spec to resolve:

1. Condition 2's structural keyword heuristic doesn't recognize
   `identical`/`byte-for-byte`/`match`/`diff`-style observable-check phrasing —
   a live calibration gap in the illustrative keyword list
   (`docs/stopping-test-spec.md`, condition 2).
2. A structural-pre-filter rejection followed by a reworded resubmission creates a
   duplicate list entry with no supersession marker, confirmed in both condition 2
   (`acceptance_criteria`) and condition 3 (`scope_edges`) — one unified finding, not
   two. Recommended direction: a supersedes-pointer set at rework time, not a
   redesign of the deliberate per-list "at least one clears both layers" evaluation
   shape.

These belong in loopr's own next module fix round, separate from this build.

---

## §8 Phase acceptance criteria

- The byte-diff criterion from §1, run for real against at least one target project
  (this repo counts, having just produced this spec, but a second, different project
  is stronger evidence — not a hard requirement for approval, a strength note for the
  review step to weigh).
- `SKILL.md` under the word budget (§4), checked directly (`wc -w`).
- Each `references/` file checked against its source spec (§5's table) for content
  drift — not just "does it exist," but "does it still say what the source says."
- The preflight check actually fires correctly when `loopr` is not importable (a
  reviewer should verify this concretely — uninstall in a scratch env, or mock it —
  not just read the code and assume).
- `loopr-PRD.md` §13 no longer makes an unqualified zero-setup claim (§6.4),
  checkable directly (grep + read).

---

## §9 Explicit non-goals

- **Gate/subagent generation** (A5's harness-facing half) — confirmed scope edge,
  §1. Not deferred-but-implied; genuinely not touched by this phase.
- **`assets/gate-templates/` and `references/prompt-templates/`** — see §2's
  deviation note. These belong to the harness-facing work above, not this phase.
- **Traycer, the harness, sequencing step 3** — untouched, still parked, still
  unassessed against the three invariants.
- **The meeting bot's actual build** (sequencing step 4) — unrelated to this phase;
  its spec is separately confirmed from the greenfield proof, its build is
  independent, human-paced work.
- **Full third-party validation** (a user unfamiliar with loopr, on an unrelated
  project) — the confirmed scope edge only names gate/subagent generation, but this
  was discussed and deliberately left as a single-edge boundary rather than a second
  one; noting it here so a future reader doesn't assume it was tested and missed.
- **Fixing §7's two findings** — logged for loopr's own module, not this build's job.
