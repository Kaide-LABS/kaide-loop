# CUSTOMIZATION_PHASE_1_SPEC.md — Prompt Customization & Loop Sequencing (Phase 1 of 2)

Built FROM the baby PRD confirmed via a real, live `/loopr` brownfield run against this repo
(2026-08-01). Source artifacts: `proofs/customization-layer/` (`baby_prd.md`, `context.md`,
`conformance-ledger.md`, `final_state.json`). That run reached COMPLETE in 5/8 rounds, 23 judge
exchanges, 17 patterns classified (all CONFORM, zero conflicts, so Gate 3 correctly never fired).

Namespaced per the marker decision in `SKILL_PHASE_1_SPEC.md`: `PHASE_1_SPEC.md`,
`BUILD_COMPLETE.md`, and `SKILL_PHASE_1_SPEC.md` all stay untouched. This is a third additive
series, not a continuation of either.

Written architect-side from loopr's own confirmed output, same as `SKILL_PHASE_1_SPEC.md` — loopr's
Phase 1 module does not itself generate this tier of granular blueprint (that is precisely the
capability this spec designs).

---

## §0 Phase Plan Header

**[AMENDED 2026-08-03 — now Phase 1 of 3, not 2.]** Phase 1 shipped and is approved
(`3e25f41`). Writing `CUSTOMIZATION_PHASE_2_SPEC.md` surfaced a second real dependency boundary,
same test as the original split (independently useful, independently testable): step11/step12
customization and loop sequencing don't depend on each other. The former is a token/structure
problem against two more templates; the latter is git-marker discovery and phase-advance logic that
operates on *already-customized* prompts, regardless of which mechanism produced them. Bundling them
under one "Phase 2" was the untested assumption; splitting them is the correction, not a new plan.

- **Phase 1 (this spec, done):** step10 customization, the two-layer fidelity check, the CLI surface,
  and state.
- **Phase 2 (`CUSTOMIZATION_PHASE_2_SPEC.md`):** step11/step12 customization from step10's *output*.
- **Phase 3 (spec written on Phase 2's approval):** loop sequencing to `BUILD_COMPLETE.md`.

**[NOTE ADDED 2026-08-03, forward-looking only — not a Phase 3 decision]:** §1's subagent amendment
means Phase 3 is no longer purely "what prompt to hand a human next." Once step10/11/12 dispatch as
subagents, "sequencing" plausibly means choosing *which subagent to dispatch*, not which file to
paste. Whether that changes Phase 3's mechanism (still git-marker discovery, read by an invoking
agent, just now choosing a subagent instead of a file?) or its scope is genuinely undecided — flagged
here so Phase 3's own spec starts from this question instead of rediscovering it.

---

## §1 Confirmed baby PRD (source of truth)

**TL;DR (verbatim from the confirmed run):** Automate the spec-driven loop currently run manually via
the step 10, 11, and 12 prompts — instead of hand-customizing each template and pasting it between
sessions, it is automated and invoked through the skill directly.

**Acceptance criterion (verbatim):** "If the loop kicks off and runs end-to-end — executing the
spec-driven build across all the phases that were specced out in the PRD, with each phase actually
getting built according to what the spec outlined — then that's how you'd know it worked. Not a
feeling, an observable run: it starts, it processes phase after phase per the spec, and it completes."

*Note on scope-vs-phase:* that criterion describes the **full two-phase capability**. Phase 1 alone
cannot satisfy it (no loop runs yet). Phase 1's own acceptance criteria are in §8; the confirmed
criterion above is the bar for Phase 2's completion, and must not be claimed satisfied before then.

**Scope edge (verbatim):** native Claude Code subagents and a Traycer-based harness are both out.
Traycer is parked (locked sequencing step 3, unassessed against the three invariants); native
subagents were explored but demoted to a non-locked idea. This build automates producing the same
prompt-file artifacts already used manually — not either heavier execution mechanism.

**Confirmed boundary (verbatim):** automates the customization and sequencing of the step10/11/12
prompt-file workflow — given a project's confirmed spec context, produces the customized step10, step11,
and step12 prompts and drives their execution end-to-end without the user manually pasting each one
into a separate session. Does not build or invoke native subagents; does not adapt or integrate
Traycer.

**[AMENDED 2026-08-03 — the "does not build or invoke native subagents" clause is partially
reversed.]** Disclosed, not silently rewritten — the verbatim quotes above are the confirmed record
of what was decided at Gate 2 and stay as they were said. What changes:

`loopr customize` now generates its output as a native Claude Code subagent definition
(`.claude/agents/`), not a plain prompt file, for all three steps — step10 pinned to an Opus-class
model, step11 pinned to Sonnet at low effort, step12 pinned to Sonnet at high effort. This is
**narrower than it looks**, and the boundary is precise: it is subagent *generation as the dispatch
surface* for already-customized prompts. It is not:

- the full V2 archetype system (`docs/loopr-v2-agent-archetypes.md` — ARCHITECT/EXECUTOR/REVIEWER/
  AUDITOR roles, the escalation chain, structured reviewer verdicts, the two-layer scratch files) —
  still forward spec, still not built now;
- Traycer, still parked, still unassessed;
- the Phase B harness (build→review→audit *loop*, git-marker phase discovery, gates-as-ground-truth,
  the audit tier) — still parked. Generating a subagent that *can run* step11 is not the same as
  building the loop that decides *when* to run it; see the amended §7.2 and §9.

This is the original PRD's A5 design (`.claude/agents/` generation, pinned models), narrower than
A5 ever was — A5 covered build/review/audit subagents for the harness; this covers exactly the three
prompts this build already customizes, nothing else. See §6.1 for the mechanism, §7.1 for a
consequence this has for maker/checker separation that the original scope edge couldn't have, §9 for
the precise remaining boundary.

**Soft context:** none. The run's `context.md` records an explicit clean slate, with a note that a
larger set of project-scope decisions (multi-loopr, per-step model control, revised subagent design)
were deliberately deferred and logged outside the interrogation. Those are **not** inputs to this
spec. See §9.

### 1.1 Disclosed correction to the confirmed problem statement

The confirmed `problem_statement` contains one imprecise clause, caught by the user at Gate 1 and
**disclosed rather than silently carried**: it reads as though step10/11/12 are pasted into the
architect session. They are not. The accurate description of *the author's own workflow*:

> **Customization** happens architect-side (templates tailored to the project). **Execution** of the
> customized step10/11/12 prompts happens in a *separate executor session* — the one that builds and
> reviews. The architect session additionally holds a higher-level review role above the executor's
> own step12 review.

**Read that as one valid topology, not as the architecture.** The two-session split is how this
project's author works; it is not a requirement of the mechanism, and this spec must not encode it as
one. A user doing architecture and execution in a single Claude Code session is a first-class case,
not a degraded one. See §4.4, where this is a hard implementation constraint rather than a
preference.

This correction could not be applied to the live run's artifact: Gate 1 had no amendment mechanism at
the time (found during that run, fixed afterward in `71203b1`). The raw artifact in
`proofs/customization-layer/baby_prd.md` therefore retains the imprecise wording, by design, as an
honest record. **This spec supersedes it on that point** — see §4.4, where the correction is
load-bearing, not cosmetic.

---

## §2 Files added or modified

| File | Change |
|---|---|
| `src/loopr/models/common.py` | Add `JudgeCallType.STEP10_CUSTOMIZATION`; add `CustomizationStep` enum |
| `src/loopr/models/judge.py` | Add the new call type to `ALLOWED_INPUTS_V3`; bump `CURRENT_ENVELOPE_VERSION` to 3 (**never edit v1/v2 in place** — the version-gating contract, `models/judge.py` lines 23–30) |
| `src/loopr/models/customization.py` | **New.** `TemplateSkeleton`, `PlaceholderBinding`, `CustomizedPrompt`, `FidelityResult` |
| `src/loopr/customization/__init__.py` | **New.** |
| `src/loopr/customization/templates.py` | **New.** Template discovery, skeleton extraction, placeholder inventory |
| `src/loopr/customization/fidelity.py` | **New.** The structural (layer-1) fidelity check |
| `src/loopr/customization/customize.py` | **New.** Judge-request construction and response application |
| `src/loopr/rubrics/texts.py` | Add the step10-customization rubric text |
| `src/loopr/cli.py` | Add `loopr customize` subcommand (§6.1) |
| `src/loopr/state/store.py` | No change expected — verify the new state field round-trips |
| `src/loopr/models/interrogation.py` | Add `customization: CustomizationState \| None` |
| `.claude/skills/loopr/SKILL.md` | Add the customize step to the orchestration loop; keep under the ~5000-word budget (currently 788) |
| `tests/test_customization_templates.py`, `tests/test_customization_fidelity.py`, `tests/test_customization_cli.py` | **New.** |

**Conform to (from the run's own conformance ledger, all 17 CONFORM):** `from __future__ import
annotations` in every new module (mandated, `loopr-MIGRATION.md` §8); `@model_validator` for
invariants on new Pydantic models; `@pytest.fixture` and `@pytest.mark.parametrize` in new tests;
`ConfigDict(extra="forbid")` on every model. Nothing was classified DO_NOT_REPLICATE — there is no
cruft to avoid on this touched surface.

---

## §3 Dependencies

**None new.** Template parsing is plain-text line scanning over files already in the repo — no
templating engine, no parser library. Adding one would breach the single-runtime-dependency
invariant (`pydantic` only) that `tests/test_no_paid_dependency.py` mechanically enforces.

---

## §4 The customization mechanism

### 4.1 Judge call shape and scope — a deliberate, disclosed widening

Customization is a judge call returning `drafted_text`, reusing the response shape added for
`boundary_proposal` in `fb98b9f`. **No new `JudgeResponse` field is required** — verified against the
current source: `drafted_text: str | None` exists at `src/loopr/models/judge.py:123`, and
`check_response_shape`'s exactly-one-of validator already includes it alongside
`passed`/`verdict`/`selected_files`. Reuse it; do not add a parallel field.

Its inputs are wider than any existing call:

```
STEP10_CUSTOMIZATION: frozenset({
    "template_text", "problem_statement", "acceptance_criteria",
    "scope_edges", "boundary", "context_notes", "conformance_summary",
})
```

**This must be stated plainly rather than smuggled in.** `docs/stopping-test-spec.md`'s Shape 1 /
Shape 2 discipline exists to make *judgments* reproducible — a judge deciding pass/fail on a field
sees only that field, so its verdict cannot drift on ambient context. Customization is not a
judgment; it is a **synthesis**, structurally the same as `boundary_proposal`, which already reads
four fields. The discipline that still applies, and must not be relaxed: the input set is
**explicitly enumerated and version-gated**, never "the whole transcript" and never "whatever is in
state." Same reproducibility guarantee, wider declared surface.

`conformance_summary` is a derived, compact projection of the conformance ledger (verdict + pattern
id + one-line reason), not the raw ledger — brownfield only, absent for greenfield.

### 4.2 Placeholder inventory — and the literal-token trap

Real inventory, counted from the actual files in `prompts/Template_prompts/`:

| Token | Occurrences | Source |
|---|---|---|
| `[PROJECT_TAG]` | 14 | user-supplied |
| `[PHASE_COUNT]` | 7 | **step10 output** — see §5 |
| `[PROJECT_REPO_NAME]` | 5 | derivable from repo root |
| `[PROJECT_NAME]` | 5 | user-supplied |
| `[PRD_FILENAME]` | 5 | derivable / user-confirmed |
| `[EXECUTOR_AGENT_FICTION]` | 5 | user-supplied (see §7.1) |
| `[PROJECT]` | 2 | user-supplied |
| `<<CUSTOMIZE: …>>` blocks | 14 distinct | judge-drafted |
| `<<CITATION_GATE_BLOCK>>` / `<<CITATION_GATE_INGESTION_BLOCK>>` | 2 | judge-drafted (include-or-remove) |

**The trap, and it is a real one:** `[UNVERIFIED]` (3 occurrences) and `[EXECUTOR]` (2) match the
same bracket shape but are **not placeholders**. `[UNVERIFIED]` is a tag the executing model is
instructed to *emit* in its own output; `[EXECUTOR]` appears inside reject-pattern shorthand
(`"[EXECUTOR] may have written X -- reject"`). A naive fill-every-bracket implementation corrupts
both, silently degrading the template's actual instructions.

**Therefore: the placeholder set is an explicit allowlist, never a regex sweep.** Any bracket token
encountered that is not on the allowlist is left verbatim and reported, never guessed at. Add a
regression test asserting `[UNVERIFIED]` and `[EXECUTOR]` survive customization unmodified.

**Second trap, file-level:** the templates on disk are named `STEP_10`, `STEP _11` (note the space),
and `step_12` — inconsistent casing, an embedded space, no extensions. Discovery must handle these
as they are, or normalize explicitly; a tidy glob pattern will silently miss `STEP _11`.

**Third trap, and the most consequential one found in Phase 1: multi-line, punctuation-bearing
fill-in blocks are invisible to a token-shaped regex entirely. [ADDED 2026-08-03]** `STEP_10` §3
contains `[PROJECT HARD BOUNDARY -- fill per project: …]` — a 303-character, 5-line block with
hyphens, colons, slashes, parentheses, and newlines. A placeholder regex built for short tokens
(`[A-Za-z0-9 _]` only, single-line) cannot match it at all — not "doesn't match, reports it", simply
never sees it. Left unclassified, layer 1 would pass a customization that ships this block completely
unfilled: the template's own generic examples in place of the project's actual inviolable constraint,
in the single field STEP_10 itself calls the one "the review agent can grep for it and HALT" on.
Undetected across four commits (b020ade through 1ccc8dd) before being found.

Two consequences: (1) the placeholder-discovery mechanism needs a WIDE scan (multi-line, tolerant of
punctuation) as well as the narrow one, not just a bigger allowlist; (2) "resolved" for a block like
this cannot mean "token absent" the way it does for `[PROJECT_NAME]` — a genuine resolution replaces
it with several sentences of prose, not a short value. The template's own original block text is the
sentinel: a customization where that exact text still appears verbatim never touched it.

**Standing rule this trap forces, and it applies beyond this one token [ADDED 2026-08-03]: any
completeness or fidelity check must use a mechanism INDEPENDENT of the one it verifies.** A
completeness check that asks "did the narrow regex find anything it didn't classify?" — checking the
narrow regex's own output against itself — certifies itself; it is structurally blind to anything
that regex's character class cannot match in the first place, which is exactly how this trap slipped
past both the original placeholder allowlist AND a first-draft completeness test built the same way.
Concretely: a wide, permissive scan (any `[...]` span, multi-line, punctuation-tolerant, bounded only
against runaway matches) is the ORACLE for what bracket-shaped constructs exist in a template. The
narrow, short-token classification is checked AGAINST that oracle's output, never the reverse. Any
span the wide scan finds that neither the short-token sets nor an explicit, reviewed registry of
known multi-line blocks accounts for must fail loudly as unclassified — never silently treated as
"probably fine" by a check that can't see it. This is the same lesson the gap-analysis mechanism in
§4.3 below already encodes for section headers (built deliberately not sharing code with the
header regexes it cross-checks); this trap is that same lesson recurring on the token side.

### 4.3 Two-layer fidelity check — the same discipline loopr applies to itself

"Customized properly" was the vague part of the confirmed criterion. It is made checkable by
applying loopr's own two-layer pattern to the customization output:

**Layer 1 — structural (deterministic, pure code, no model call).** Extract the template's section
skeleton *before* customization, extract it again from the output, and compare.

**The three templates use three different header conventions — verified against the actual files, and
this is the single biggest implementation trap in Phase 1:**

| Template | Convention | Sections |
|---|---|---|
| `STEP_10` | **No markdown headers at all** (`grep -c '^#'` → 0). Unnumbered heading lines (`ROLE`, `DELIVERABLES (…)`, `WHY THIS MUST BE AIRTIGHT (loop context)`) plus numbered sections (`1. CONTEXTUALIZE …`) | **3 + 6 = 9** |
| `STEP _11` | markdown `##` | 9 |
| `step_12` | markdown `##` + `###` | 11 + 6 |

**[CORRECTED 2026-08-01 — this table previously said "2 + 6" for `STEP_10`, and that error shipped
into the first implementation.]** The missing ninth section is `WHY THIS MUST BE AIRTIGHT (loop
context)` at line 52. It is **not** all-caps — it ends in a lowercase parenthetical — so any
character class built for ALL-CAPS headers silently drops it, and the fidelity check then cannot
detect that section being dropped, reordered, or mangled by a customizer. The original wrong count
came from a grep whose regex carried the same lowercase blind spot, which is exactly why the
verification rule below exists.

**Verification rule, mandatory: the template file is the oracle, never this table.** Confirming that
extraction "matches the spec's stated count" is not verification — if the spec is wrong, that check
passes green on a real defect, which is precisely what happened here. Assert against the file
itself, and cross-check with the gap analysis below. Treat the counts in this table as a sanity
reference that has already been wrong once, not as ground truth.

**Structural cross-check — gap analysis (required, and it is what catches the partial-extraction
case a count floor cannot).** A minimum-count floor detects total extraction failure (0 sections) but
not partial failure — 8 of 9 sailed through a floor of 2 unnoticed. After extracting, scan the
regions *between* consecutive detected sections for lines that structurally look like headers but
were not captured: unindented, short, followed by a blank line, not sentence-cased body prose, not a
list item. Any such candidate is a suspected missed section and must be reported, not silently
tolerated. This is convention-independent, so it does not inherit the blind spot of whichever regex
it is checking.

**Doc-title handling must be a declared decision, not a regex accident.** `STEP_10` line 1
(`STEP 10 -- PRD MODERNIZATION + …`) must not be excluded merely because `+` happens to fall outside
the character class — that would leave the exclusion accidentally masking an untested mechanism.
**[VERIFIED 2026-08-02]** The implementation excludes line 1 unconditionally (`index > 0` in
`extract_skeleton`, independent of whether the line would otherwise match the section pattern), so
the exclusion holds on its own declared merits, not on the `+` accident. Decide explicitly whether
the document title is part of the skeleton — the recommendation is to exclude it in all three
templates (a title is not a section), and it is implemented deliberately in each convention.

**Over-capture is a known, accepted tradeoff — decided, not left open. [DECIDED 2026-08-02]** The
all-caps detector treats a standalone all-caps line with a trailing lowercase parenthetical as a
section header (this is precisely the fix for the missing-ninth-section defect above). This can
false-positive on customizer-generated output: `STEP_10` §3's `[PROJECT HARD BOUNDARY -- fill per
project: …]` block is free text, not an allowlisted placeholder, and a customizer could plausibly
emit a standalone line such as `ANTI-REPLICATION BOUNDARY (customer IP)` while filling it — which
would register as a section the template doesn't have, and HALT the fidelity check on a false
structural mismatch.

Two fixes were considered and rejected: (1) tightening the all-caps pattern (e.g. requiring
blank-line isolation on both sides) does not work for this template specifically — `STEP_10` is
written in a loose one-sentence-per-paragraph style where nearly every line, header or body prose, is
blank-line-isolated, so isolation does not distinguish the two cases here; (2) any tightening broadly
risks reintroducing the original, strictly worse defect (a missed real section silently passing).
**Decision: accept the false-positive risk and document it, rather than tighten the pattern.** The
asymmetry is deliberate and matches SS4.3's own stated priority: a false HALT costs a retry (the
fidelity detail message names exactly which line was treated as an unexpected section, and the
customizer can be asked to fold the boundary text into existing prose instead of a standalone
all-caps line); a false PASS costs silent corruption of the artifact everything downstream trusts.
Between an occasional false HALT and any reintroduced risk of a false PASS, the false HALT is
strictly cheaper. Not implemented in code — this is a documented risk acceptance, not a defect to
patch.

Two consequences, both load-bearing:

1. **A markdown-header extractor finds literally nothing in `STEP_10`** — which is precisely the
   template Phase 1 customizes. Extraction must be per-convention and declared explicitly per
   template, never one generic regex.
2. **Numbered lines are ambiguous across templates.** `1. CONTEXTUALIZE …` is a section header in
   step10; `1. List all PHASE_N_SPEC.md files …` is an ordinary list item in step11. A naive
   numbered-line rule over-captures badly — raw counts are 10 in step11 and 18 in step12, nearly all
   of them list items, not sections.

**Guard against the vacuous pass — mandatory, not optional.** If extraction yields an empty or
implausibly short skeleton, the check must HALT, never pass. Comparing two empty lists "succeeds"
while verifying nothing — a fidelity check reporting green having checked nothing is worse than no
check at all, because it manufactures false confidence in exactly the artifact everything downstream
trusts. Assert a minimum section count per template, derived from the template file itself at
runtime rather than hardcoded from the table above.

Given a non-vacuous skeleton, the customized output **fails structurally** if any of these hold:
- a section header from the template is missing;
- headers appear in a different order;
- any allowlisted placeholder token remains unresolved;
- a recognized multi-line fill-in block (§4.2's third trap — e.g. the hard-boundary block) survives
  byte-identical from the template, found via the independent wide-scan oracle;
- a `<<CUSTOMIZE: …>>` marker survives into the output (it is an instruction to the customizer, and
  must never reach the executing agent).

**Layer 2 — judge (runs only if layer 1 passes).** Rubric: *is the injected content genuinely
specific to this project — naming its actual files, invariants, boundary, and stack — or is it
generic filler that would read identically for any project? Verbatim template text with placeholders
merely deleted is a fail, not a pass.*

Layer 1 exists because it directly encodes the user's own standing rule for template
customization: preserve every section, in the same order, with the same headers — fill and adapt,
never restructure, condense, or rewrite. That rule is not a style preference here; downstream steps
parse these prompts' structure, so structural drift is a correctness failure. Layer 2 exists because
layer 1 alone cannot distinguish real customization from placeholder-deletion.

### 4.4 Where this runs — session topology is not a dependency

The *reason* customization historically lived in a dedicated architect session was that the project's
context lived there, in that session's context window. **That is no longer true:** the context now
lives in committed artifacts (`baby_prd.md`, `context.md`, `conformance-ledger.md`) produced by
loopr's interrogation.

Once context is on disk, session topology becomes invisible to the mechanism. `loopr customize` reads
a state file and a set of artifact files; it has no way to observe — and no reason to care — whether
the session invoking it is the same one that ran the interrogation. Both topologies are therefore
first-class:

| Topology | Interrogation | Customization | Execution |
|---|---|---|---|
| **Two-session** (this project's author) | architect session | executor session | executor session |
| **Single-session** | one session | same session | same session |

Neither is a fallback. This is the same principle already recorded for the harness question — loopr
must never assume a multi-agent runtime exists, because the adoption story is "drop it in a repo and
get the discipline, zero setup." A tool that only works if you maintain two Claude Code tabs has the
same adoption problem as one that requires a harness, and for the same reason.

**Hard implementation constraint, not a preference:** nothing in `loopr customize`, its state, or
`SKILL.md`'s orchestration may read, assume, or branch on session identity or role. No "am I the
architect" check, no session-role config field, no separate architect/executor code paths. If an
implementation finds itself wanting one, that is a design error to report, not to satisfy — it means
context has crept back out of the artifacts and into the session, which is the thing this design
exists to prevent.

This is the direct application of the same repo-as-ground-truth principle that motivated moving off
the two-window web/Code split originally — and it generalizes past the author's own setup, which is
the point. See §7.1 for what this costs and §7.3 for what single-session use specifically depends on.

---

## §5 Sequencing — the two-pass finding

**Step11 and step12 cannot be customized up front.** Several of their placeholders are only knowable
after step10 has *executed*, not merely after it has been customized:

- `[PHASE_COUNT]` (7 occurrences) comes from step10's Deliverable B — `PHASE_1_SPEC.md` §0's phase
  plan header. It does not exist until step10 runs.
- `<<project-specific MAY-NOT invariants>>`, `<<HARD BOUNDARY specifics>>`, `<<PRD section
  structure>>`, and `<<per-project compliance audit>>` all derive from the *modernised* PRD, which is
  step10's Deliverable A.

So the real order is: **customize step10 → execute step10 → customize step11/12 from its output →
run the loop.** Phase 1 covers the first step only. Any implementation that batches all three
customizations up front will produce step11/12 prompts with fabricated or empty values in exactly
the fields the review agent depends on — a silent failure, not a loud one.

---

## §6 Implementation logic flow

### 6.1 CLI surface

```
loopr customize --state <state.json> --step 10 [--out DIR]
```

Exit codes reuse the existing contract (`src/loopr/exit_codes.py`) unchanged: `10 JUDGE_REQUIRED`
when the customization judge call is pending, `0 OK` on success, `40 HALT` on a fidelity failure.
**Do not invent new exit codes.** A layer-1 fidelity failure is a HALT, not a silent retry — it means
the customizer restructured the template, which is exactly the failure this check exists to catch.

Refuses to run unless all six conditions pass on the supplied state — customizing from an
unconfirmed spec is the same class of error as emitting a baby PRD early, and `cmd_emit`'s existing
guard (`cli.py`) is the precedent to follow.

### 6.1a Output target — `.claude/agents/`, not a plain file [ADDED 2026-08-03]

Per §1's amendment, the fidelity-checked output is written as a subagent definition, not a bare
markdown file:

```
.claude/agents/loopr-step10.md   -- model: opus (see table below)
.claude/agents/loopr-step11.md   -- model: sonnet, effort: low
.claude/agents/loopr-step12.md   -- model: sonnet, effort: high
```

| Step | Model | Effort | Rationale |
|---|---|---|---|
| 10 | Opus-class | — | Guaranteed floor, config-declared not operator-remembered — the reasoning already settled in `docs/loopr-v2-agent-archetypes.md`'s Step-10 correction (a Sonnet-low pass pinned an uninstallable dependency and declared no escalation needed; Opus-high caught it on self-verification). That reasoning transfers unchanged; it never depended on the archetype system around it. |
| 11 | Sonnet | Low | Confirmed by the user 2026-08-03. Matches the V2 doc's EXECUTOR tier (most output volume, checked immediately downstream by step12). |
| 12 | Sonnet | High | Confirmed by the user 2026-08-03. Matches the V2 doc's REVIEWER tier (judgment work, scoped to one phase against one spec). |

**Frontmatter schema is NOT yet verified against Claude Code's actual subagent-authoring
requirements — flagged explicitly rather than asserted.** The working assumption is YAML frontmatter
with at minimum `name`, `description`, `model`, and an `effort` field for step11/12 — modeled on this
project's own visible agent roster (e.g. `Explore`, `claude-code-guide`) and this session's own
`/model` / `/effort` mechanics. Whoever implements this must confirm the real schema (does `effort`
exist as a frontmatter field at all, or only as a session-level `/effort` command with no per-subagent
equivalent — if the latter, step11/step12's effort split cannot be config-declared the way step10's
model can, and that gap must be reported, not silently dropped) before writing `customize.py`'s
output path. Do not guess a schema and ship it unverified — same discipline as every prior claim in
this document that turned out to need checking against the real thing.

The `--out DIR` flag's meaning changes accordingly: it now roots the `.claude/agents/` path, not a
free-standing output location. `CustomizationState.step10_output_path` (§6.2) stores the actual
subagent file path — the field's *meaning* (where the fidelity-checked output landed) is unchanged;
only what kind of file lives there changes.

### 6.2 State

```
CustomizationState:
  step10_template_path: str
  step10_skeleton: TemplateSkeleton      # captured pre-customization
  step10_bindings: list[PlaceholderBinding]
  step10_output_path: str | None
  step10_fidelity: FidelityResult | None
```

Hung off `InterrogationState.customization`, optional, absent for runs that never customize.

### 6.3 Placeholder binding

User-supplied values (`[PROJECT_NAME]`, `[PROJECT_TAG]`, `[PROJECT]`, `[EXECUTOR_AGENT_FICTION]`) are
collected via the existing `QUESTION_REQUIRED` mechanism — one targeted question per unresolved
binding, never batched, matching `step()`'s existing one-interaction-per-invocation rule. Derivable
values (`[PROJECT_REPO_NAME]`, `[PRD_FILENAME]`) are proposed with a confirm, never silently assumed.

---

## §7 Known tensions — disclosed, not resolved by this phase

### 7.1 Maker/checker separation — identical in both topologies, plus one extra cost in single-session

`step_12`'s `[EXECUTOR_AGENT_FICTION]` device exists because a reviewer reviews far more critically
when it believes a *different* agent wrote the code. Running step11 and step12 in one session makes
that separateness partly fictional — the reviewing context already holds the building context's
reasoning.

**This is unchanged between the two topologies.** Even in a two-session split, step11 and step12 both
run in the executor session, so build-vs-review is already same-context there. Single-session use does
not make this particular weakness worse.

**Single-session does add one further, subtler cost:** the same context that formed the spec during
interrogation also reviews the build against it — so the reviewer carries the spec author's own
rationalizations, not merely the builder's. Worth naming plainly; not fatal, not resolved by this
phase, and not a reason to prefer one topology in the spec.

The template already anticipates the core problem, and its mitigation is honest rather than
pretended: when `prompts/loopr/step12_review.md` was customized for loopr's own build, the fiction was
replaced with a true statement — it is *genuinely a separate pass* on the same phase, and should be
treated with identical skepticism regardless. Phase 2 must carry that same honesty into whatever it
generates, in both topologies.

**[AMENDED 2026-08-03 — partially closed, not by this phase's original design.]** ~~This is a real,
disclosed weakening versus genuinely separate agents, not a solved problem. Native subagents would
restore platform-enforced separation — and are explicitly out of scope by the confirmed scope edge.
Do not quietly re-derive them here.~~ Per §1's amendment, step11 and step12 now dispatch as separate
native subagents (`loopr-step11`, `loopr-step12`), each with its own model/effort config. That
restores real, platform-enforced separation for the build-vs-review split specifically — not because
this phase set out to solve it, but as a consequence of the subagent-dispatch decision landing here.

**What this does and does not fix, stated precisely so it isn't overclaimed:** two separate subagent
*invocations* means step12 does not inherit step11's conversation by default — closer to genuine
separateness than one session running both. It does **not** mean `[EXECUTOR_AGENT_FICTION]` becomes
unnecessary or that the honesty requirement from the paragraph above lapses: a subagent can still be
invoked with context bleeding in depending on how dispatch is wired (e.g., if the same orchestrating
session passes step11's transcript to step12 explicitly), and single-session *interrogation* still
means the spec-author bias described above is unaffected regardless of build/review separation. Don't
let "subagents now exist" quietly stand in for "separation is solved" — it closes the platform-level
gap this section named, not the two other costs named beside it.

### 7.2 "Drives execution end-to-end" without a full harness

**[CORRECTED 2026-08-03 — this section previously said "Phase 2's work" for loop termination; that
was already stale before the subagent amendment. §0 splits loop sequencing into Phase 3, not Phase 2
— this section was not updated when that split happened. Fixed here, along with the subagent
consequence.]**

Reconciling the boundary ("drives their execution end-to-end") with what's still excluded (Traycer,
the full build→review→audit loop): the module still never orchestrates the *loop* itself — no
git-marker phase discovery, no gates-as-ground-truth, no audit tier, none of Phase B's three
invariants implemented here. What changed per §1's amendment is narrower than "the module now
orchestrates": it emits a *dispatchable subagent* instead of a plain prompt, but something external
still decides *when* to dispatch it — that decision is Phase 3's work (loop sequencing to
`BUILD_COMPLETE.md`), not this phase's, and not automatic just because a subagent exists to receive
the dispatch.

Phase discovery is still carried *inside* the step11/12 prompts themselves (git commit markers:
`feat: Phase N implementation (TAG)`, `chore: Phase N review approved (TAG)`) — the module does not
reimplement it in Phase 1 or Phase 2. Whether Phase 3, once subagents exist as the dispatch surface,
still needs a human or invoking agent to read git state and choose which subagent to run next, or
whether subagent dispatch changes that design, is an open question for Phase 3's own spec — not
answered here, and not assumed either way by this amendment.

### 7.3 Context pressure in single-session use

One session running interrogation, customization, and multi-phase execution accumulates considerably
more context than a two-session split, and may hit limits mid-build.

**The design already tolerates this, and that tolerance must not be accidentally removed.** loopr's
own state lives in `.loopr-state/state.json` on disk, and step11/12 phase discovery derives from git
commit markers rather than session memory — so a session that exhausts its context can be restarted
and resume exactly where it was. That resumability is what makes single-session use genuinely viable
rather than merely permitted, and it is load-bearing for the single-session topology specifically.
Any Phase 1 or Phase 2 design that parks required state in the session rather than on disk breaks
this, and would be a defect even though it might pass every other check.

---

## §8 Phase 1 acceptance criteria

The confirmed criterion in §1 is the **Phase 2** bar and must not be claimed before then. Phase 1's:

1. `loopr customize --step 10` against a real confirmed state produces a step10 prompt whose every
   allowlisted placeholder is resolved and whose section skeleton matches the template exactly —
   verified by the layer-1 check, run independently, not merely reported by the customizer.
2. `[UNVERIFIED]` and `[EXECUTOR]` survive customization byte-identical (§4.2's trap).
3. No `<<CUSTOMIZE: …>>` marker appears anywhere in the output.
4. A deliberately restructured customization (a section dropped or reordered) is **rejected** by the
   layer-1 check — the check must be demonstrated firing, not merely present.
5. A placeholder-deletion-only "customization" (template text with tokens stripped, nothing
   project-specific injected) is **rejected** by the layer-2 judge.
6. Refuses to run against a state where the six conditions do not all pass.
7. **Topology independence (§4.4):** no code path, state field, or `SKILL.md` instruction reads or
   branches on session identity or role — verified by inspection, *and* demonstrated concretely: a
   customization interrupted after the judge call and resumed from the state file in a fresh process
   produces byte-identical output to one completed in a single process. This reuses the crash-safety
   property `PHASE_1_SPEC.md` §8's B-5 criterion already establishes; it is the same guarantee, tested
   against this new command.
8. `mypy --strict` clean; full suite green; `test_no_paid_dependency` and
   `test_no_hardcoded_domain` still passing.

---

## §9 Explicit non-goals

- **Step11/step12 customization** — Phase 2, gated on the §5 dependency. **Loop sequencing** —
  Phase 3, per §0's amendment.
- **[AMENDED 2026-08-03]** ~~Native Claude Code subagents; Traycer; any harness — confirmed scope
  edge. Untouched.~~ Native subagent *generation for step10/11/12 dispatch* is now in scope (§1, §6.1a)
  — that clause is superseded, not the whole line. **Still fully out, unamended:** Traycer; the Phase
  B harness as a loop (build→review→audit orchestration, git-marker phase discovery,
  gates-as-ground-truth, the audit tier); any code that decides *when* to dispatch a subagent (that's
  Phase 3's open question, not decided by this amendment).
- **Gate/subagent generation for the harness's build/review/audit tiers (A5's original,
  broader sense)** — already excluded by `SKILL_PHASE_1_SPEC.md`; unchanged here. Do not read this
  phase's narrow subagent generation (three specific, already-customized prompts) as reopening that
  broader exclusion — it is a different, smaller thing wearing the same mechanism.
- **The deferred project-scope decisions** — multi-loopr, per-step model control, revised subagent
  count. Explicitly deferred by the user during the run that produced this spec's baby PRD, recorded
  in that run's `context.md`, and logged outside it. **Not inputs to this spec**, including the
  "mandatory self-verification before declaring a pass complete" idea, which is a genuinely good
  candidate for the step10 template but was deferred with the rest and must not be smuggled in here.
- **Gate 3 `conflict_overrides`** — proposed but deliberately unimplemented in `71203b1` (no run has
  ever produced a CONFLICT verdict to design against). Unrelated to this build.
- **Fixing the C2/C3 duplicate-entry finding** (structural-rejection reworks leaving superseded list
  entries) — logged against loopr's own module, separate work.
