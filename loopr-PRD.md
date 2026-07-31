# loopr — Product Requirements Document (v1)

> **Status:** Ultimate PRD, expanded from a confirmed baby PRD, updated 2026-07-27 to fold in
> everything decided since first expansion (brownfield in v1 scope, the six-condition stopping test
> operationalized in `docs/stopping-test-spec.md`, the pattern-conformance classification specified
> in `docs/conformance-classification-spec.md`), and **modernized 2026-07-28** against verified
> current dependency versions and 2024–2026 literature — see `## MODERNIZATION CHANGELOG` at the foot
> of this document, and `docs/modernization_log.md` for the version pins.
> `loopr-MIGRATION.md` is now a historical record of how those decisions were reached, not the active
> overlay — this PRD is the current source of truth again.
> **Form factor:** standalone portable module first (Python), Claude Code skill after it's proven
> (ports to Codex/Cursor later still).
> **Author's method note:** This PRD was specced using the exact workflow loopr automates. It is a dogfood artifact.

---

## TL;DR (read this; confirm or correct it)

loopr is a spec-discipline engine, packaged first as a standalone module and later as a Claude Code
skill, that makes a builder **spec properly before writing code** — on a fresh project or an existing
one. Instead of lunging at a build from a fuzzy ask, loopr interrogates the user until it genuinely
understands the problem (with a real stopping condition, not a vibe), splits what it learns into a
hard spec (`PRD`) and soft context (`context.md`: the boss-said, watch-out, judged-a-failure-if
stuff), proposes a **boundary** that both arbitrates in-scope-versus-later and powers a senior audit,
expands a human-confirmed **baby PRD** into a robust **ultimate PRD** grounded in current docs and
research, and generates the customized build/review/audit subagents and gates that drive a phased,
crash-safe Claude Code loop to a working build.

**On an existing codebase**, loopr additionally makes an explicit call on every existing pattern the
work touches — CONFORM, DO_NOT_REPLICATE, or CONFLICT (escalate) — so it never silently reproduces a
codebase's mistakes just because they're already there. See section 5 A3a.

The promise, in one line: **a stranger who uses loopr instead of just opening Claude Code and typing gets a far better put-together, well-specced build that actually addresses the constraints and problem it was built for, where the only gaps left are things they never thought to spec, never things the spec captured and the build dropped.**

Four interview-gold properties are first-class in loopr and its README: the **boundary-audited third tier** (Opus catches what the Sonnet review missed), **git-marker phase discovery** (crash-safe, idempotent, resumable), **deterministic gates re-run as ground truth** (the checker cannot cheat; read-only subagents enforce it), and — for brownfield — **explicit convention-vs-cruft classification** instead of blind pattern-matching. These are distributed-systems instincts (state machines, crash recovery, idempotency, component distrust) wearing an LLM costume.

---

## 1. Problem and thesis

Coding is largely solved: Claude Code writes features fast. Speccing is not. The real bottleneck a builder hits is disciplined problem-definition, research grounding, and scope control, which is judgment most builders neither have nor apply. So they type a fuzzy ask, Claude lunges, and the output is sloppy: technically plausible, wrong for the actual problem.

loopr's thesis: **the value is the rigor from the start, not the loop.** The loop is a commodity now; everyone has one. The disciplined spec front-end (research-backed PRD, front-loaded failure-mode analysis, deterministic anchoring, maker-checker-auditor tiers) is what actually produces non-sloppy builds, and nobody has packaged it for a stranger to run. loopr packages exactly that.

## 2. Target user

**V1 user:** a builder with a problem, on either a fresh repo (greenfield) or an existing one (brownfield). Someone who wants it specced properly before code, whether that's a new project or a feature/overhaul on something that already exists. **Updated 2026-07-27:** brownfield was originally deferred out of v1 (see prior revision, preserved in `loopr-MIGRATION.md` section 1); that call is reversed. Greenfield has one source of truth (the spec); brownfield has two (the spec, and the patterns already in the code), and they can conflict — a model that blindly pattern-matches an existing codebase will faithfully reproduce its mistakes. loopr's brownfield mode makes that conflict explicit instead of silently inheriting it (section 5 A3a).

**Not v1 (deferred):** B2C polish, throwaway scripts, and anyone who explicitly wants a quick unspecced hack are non-users by design; loopr's whole value is the discipline they're skipping.

## 3. The Magic Moment (how a stranger knows it worked)

Three acceptance criteria, firing at three moments and catching three different failure modes. loopr is successful when it produces all three:

1. **Spec-time TL;DR moment.** The user reads a tight summary of the baby PRD and thinks "this understood my problem better than I did." Because users skim at best, the confirm-gate leads with a skimmable TL;DR; the gate is only as strong as what the user actually reads.
2. **Scope-creep catch.** During speccing, the boundary visibly flags something as out-of-scope-for-now that the user would otherwise have wrongly built.
3. **No-rework build.** The customized prompts run to a build that gets the ~80% right, and the remaining gaps are net-new things the user never thought to spec, never things the spec captured and the build dropped. A well-specced build fails only where the spec was silent.

Criterion 3 has a direct consequence: those net-new gaps are not a failure, they are the next iteration's input. They flow into `context.md` and an additive phase-spec series (see Continuity). loopr never claims to spec perfectly on turn one; it guarantees the gaps are always net-new scope.

## 4. Product shape

Two phases. **Phase A (the spec engine) is the shipped v1 core**, built first as a standalone
portable module (Python) and proven before any Claude Code skill packaging — see the locked
sequencing in `loopr-MIGRATION.md` section 2. **Phase B (the phased loop) is parked**, much later,
targeting a Traycer (Apache-2.0) adaptation rather than the author's original Docker loop (abandoned
— see `loopr-MIGRATION.md` sections 1 and 7 for the failure notes).

```
Phase A — SPEC ENGINE (v1 core)
  A1 Interrogate → stopping condition met (6-check test, operationalized: docs/stopping-test-spec.md)
  A2 Emit baby PRD + context.md → HUMAN GATE 1 (confirm via TL;DR)
  A3 Propose boundary → HUMAN GATE 2 (confirm/tweak)
    A3a [brownfield only] Touched-surface + pattern classification → HUMAN GATE 3 (conflicts only)
        operationalized: docs/conformance-classification-spec.md
  A4 Research-grounded expansion → ultimate PRD (no heavy human gate; trusted expansion)
  A5 Generate customized build/review/audit subagents + gates

Phase B — PHASED LOOP (parked, much later, Traycer-based)
  Build (Sonnet) → Review (Sonnet, read-only) → Audit (Opus, read-only) → Approve → next phase
  git-marker discovery • gates as ground truth • boundary-audited tier • supervised-first-run
  … repeat until BUILD_COMPLETE
```

**On gate numbering vs. chronology:** Gate 1 is written up before Gate 2 in this document (A2 before
A3), but condition 4 of the six-condition test (A1) requires the boundary to already be confirmed
before interrogation can stop and the baby PRD gets drafted — so Gate 2 (and, for brownfield, Gate 3)
actually fire chronologically *before* Gate 1, during interrogation. Gate 1 is the final confirm on
an already-fully-settled spec, not the first thing a user sees. See
`docs/conformance-classification-spec.md` section 6 for the full reasoning.

---

## 5. Phase A — the spec engine (v1 core)

### A1. Interrogation with a real stopping condition

loopr does not spec on first contact. It interrogates the user, iteratively, grouped questions, flagging its own assumptions, pushing hardest on load-bearing unknowns. The hard part is the **stopping condition**, because a stranger's Claude will otherwise ask two questions and lunge.

**The six-condition sufficiency test.** Interrogation ends, and only ends, when all six hold:

1. **Outcome-stated problem.** The problem is expressed as a desired outcome, not a pre-chosen solution.
2. **At least one testable acceptance criterion.** The user can name, concretely, how they would know it worked.
3. **Named scope edges.** What is explicitly out / deferred is named.
4. **Proposed-and-confirmed boundary.** The in-versus-later arbiter exists (see A3).
5. **Captured soft context.** The stakeholder constraints and watch-outs (the things that would make the build judged a failure even if technically correct) are written to `context.md`.
6. **No load-bearing unknown remains.** No open question whose answer would materially change the spec.

Any condition false → keep asking, targeted at the false one. All true → stop and draft the baby PRD. This test is loopr's keystone and the single most important thing it encodes that a naive Claude does not have.

**Operationalized:** each condition's concrete pass/fail check (a cheap structural check plus a
scoped LLM judge call, never given more than the field(s) its rubric needs) is specified in full in
`docs/stopping-test-spec.md`, confirmed. That document is the implementation-ready version of the
six bullets above; this section stays the conceptual summary.

**Research grounding (added 2026-07-28).** The three load-bearing design choices in A1 were checked
against current literature. Two are supported; one is genuinely novel and is now labelled as such.

- **The deterministic-anchor rule holds, and is more necessary than assumed.** The strongest current
  stress-test of judge reliability finds that no judge is uniformly reliable, and — critically —
  that judges are unstable even against *identical* repeated input: mean stochastic-stability score
  of **37.50%** on the ordinal benchmark, where 100% is the floor a reliable judge should hit
  ([Dev et al., *Judge Reliability Harness*, arXiv:2603.05399](https://arxiv.org/abs/2603.05399),
  §3.2, §5, Table 5). Formatting-only perturbations degraded judgments *more* than semantic ones
  (§6). This is direct support for "a judge call never has the last word alone." *Caveat, stated
  honestly:* that study is explicitly preliminary — 10 samples per benchmark — so it is strong
  directional evidence, not a precise effect size. Note also that the paper does not itself
  recommend a deterministic anchor; the anchor is loopr's inference from its data.
- **Per-field scoping (one judge call per condition, never one holistic call) holds, via a
  constraint-batching result.** When an LLM was asked to satisfy all fourteen elicitation-quality
  criteria in a single generation, only **1 of 30** outputs satisfied all of them; when targeted at
  one criterion at a time, single-criterion avoidance ran at **84.3%**, and the targeted questions
  beat human-authored ones with a **93.5%** win probability (odds ratio 2.662, p = 4.23×10⁻⁸)
  ([Shen, Singhal & Breaux, arXiv:2507.02858](https://arxiv.org/abs/2507.02858), §IV-C, §V-D).
  This is the citation that supports the Shape 1 / Shape 2 discipline and the
  "ask toward the lowest-numbered false condition, one at a time" rule. Independently, the same
  study found **98% (144/146)** of good follow-up questions needed at most four prior speaker turns
  of context (§IV-A, §V-B) — i.e. question quality is driven by *local* context, not deep history,
  which is the same claim the scoping discipline makes.
- **The `max_rounds = 8` cap is not falsified, and is mildly supported — but remains a design
  choice, not an empirical optimum.** Across seven frontier models run under chain-of-thought in a
  requirements-elicitation benchmark, *every* model self-terminated at **≤ 8.12 turns** on average;
  the single model that ran to the 20-turn ceiling (19.98 avg) was called out by the authors as
  "lack[ing] an effective stopping criterion" and scored *worse* coverage (IRE 0.13) than models
  stopping at half that ([Jin et al., *ReqElicitGym*, arXiv:2602.18306](https://arxiv.org/abs/2602.18306),
  Table 4, §5.1). *Two honest caveats:* no published work runs a turn-budget ablation, so the cost
  of truncating at 8 is unmeasured; and one within-model contrast (DeepSeek V3.2: 11.38 turns →
  IRE 0.32 vs. 5.73 turns → IRE 0.19) runs the other way. Keep 8 as the calibratable default
  `docs/stopping-test-spec.md` already calls it.
- **A principled stopping rule for elicitation is unbuilt prior art — this is loopr's novelty
  claim.** No system in the reviewed literature defines one: termination is a hard turn cap, a model
  whim, or user fatigue. ReqElicitGym's own Future Directions section names the gap ("LLMs ...
  **often lack effective stopping criteria**", §6.2), and LLMREI observed its bot ending interviews
  when users signalled time pressure, which "may also result in missed opportunities to gather
  crucial information" ([Korn, Gorsch & Vogelsang, arXiv:2507.02564](https://arxiv.org/abs/2507.02564),
  §IV-E3). The six-condition test is therefore not an implementation of known technique; it is a
  proposal in an open area, and should be claimed that way.
- **The completeness ceiling is real, and it validates the force-resolution design.** Best-in-class
  implicit-requirement coverage was **0.32** (most models 0.07–0.20), and aesthetic/style
  requirements were elicited at **< 0.01** (ReqElicitGym, Tables 4 and 6); a separate study
  elicited **73.7%** of requirements including partials, i.e. ~26% missed (LLMREI, §IV-E2). Coverage
  does not converge to 1 by asking more questions. That is precisely why condition 6's round cap
  force-resolves into a *visible written assumption* rather than looping — and it is independent
  support for acceptance criterion 3 in section 3 (the residual gaps are net-new, not spec-dropped).

### A2. Baby PRD + context.md, and the TL;DR-first gate

loopr emits two artifacts:

- **The baby PRD:** the small, confirmable core spec. Ships with a **TL;DR built for the skim** at the top.
- **`context.md`:** the soft context. The rule for what belongs here: **it belongs in `context.md` if it would change how the build is judged but cannot be expressed as a spec requirement.** Examples: "my boss cares about X," "avoid pattern Y for political reasons," "the real audience is Z, not the stated one." loopr must teach this split with examples, because the split is judgment a stranger lacks. Cramming politics into the PRD corrupts the spec; losing it builds a technically-correct thing that fails the real test.

**HUMAN GATE 1 (hard):** loopr presents the TL;DR first, asks the user to confirm or correct, and will not proceed until confirmed. Always the last gate to fire chronologically (section 4) — by the time a user sees it, boundary confirmation (Gate 2) and, for brownfield, any pattern conflicts (Gate 3, A3a) are already resolved.

### A3. Boundary proposal and confirmation

The boundary does two jobs: it is the **scope arbiter** (how loopr decides "that's a later phase, not now" during speccing) and it is the **fuel for the audit tier** (what the senior auditor checks the review did not let slip).

loopr does **not** demand a boundary upfront; a stranger will not have one. After `context.md` exists, loopr **analyzes and proposes** a boundary in plain language, states it, and asks the user to confirm or tweak. A shallow user accepts; a deep user sharpens.

**Boundary is preferred, not strictly mandatory.** If there genuinely is no hard boundary, the audit tier degrades gracefully to auditing against the failure-mode catalogue only. loopr always proposes one; it strongly prefers one because it powers both scope arbitration and the audit; it survives without one.

**HUMAN GATE 2 (hard):** confirm/tweak the boundary. For brownfield projects, this same confirmation
also covers the touched-surface file list (see A3a) — one added, boundable section in the same
confirm moment, not a separate step. Gate 2 remains the second hard gate of the spec phase; brownfield
adds a conditional third (A3a), not a fourth.

### A3a. Brownfield only — pattern conformance and HUMAN GATE 3

Applies only when loopr is pointed at an existing codebase. Full mechanism specified in
`docs/conformance-classification-spec.md`, confirmed; summary here:

- **Touched-surface discovery.** Once the boundary is confirmed, loopr proposes the files/modules the
  confirmed spec actually implicates — a cheap keyword/dependency-graph pre-filter, then an LLM
  relevance-judge pass over that shortlist (this is the "semantic search" step; deliberately does
  NOT add a new external dependency — see section 8 for why Nia and Context7 were both considered and
  rejected for this specific job). Confirmed as part of HUMAN GATE 2, above.
- **Pattern classification.** Within the touched surface, every recurring pattern (three or more
  occurrences) or structural touchpoint the new work must interact with gets an explicit call:
  - **CONFORM** — a real, current convention. Applied silently.
  - **DO_NOT_REPLICATE** — cruft: isolated, stale, deprecation-marked, or a one-off inconsistent with
    the surface's dominant approach. Applied silently (i.e., avoided).
  - **CONFLICT** — following the pattern, or simply coexisting with it, would make the stated
    outcome, an acceptance criterion, or the boundary not hold. Escalated, never silently resolved
    either direction — the same escalate-don't-overrule shape already used for boundary confirmation
    and the Step 10 research pass, now pointed at code.
  - **AMBIGUOUS** — the evidence signals genuinely conflict and no confident call is possible. Not a
    new mechanism: logged as an `OpenQuestion` feeding the six-condition test's own condition 6
    ledger, judged load-bearing the same way any other open question is, resolved by a targeted
    follow-up or the round-cap force-resolution. No seventh stopping-test condition was needed.
- **CONFORM / DO_NOT_REPLICATE calls** are written to a new persistent artifact, `conformance-ledger.md`
  (A5 output, see below) — routine, no gate.
- **CONFLICT calls, batched, are HUMAN GATE 3** — the third and last hard gate of the spec phase, and
  conditional: it only fires if a real conflict was found. Chronologically, Gate 3 fires *before*
  Gate 1 (see section 4's gate-numbering note) — a conflict can be load-bearing enough to change an
  acceptance criterion, so it needs resolving before the baby PRD is drafted, not after.

**Research grounding and an honest novelty flag (added 2026-07-28).** A3a was checked against the
technical-debt, code-ownership, and coding-convention literature. The result is mostly *negative*,
and that changes how A3a must be built and claimed — not whether it is built.

- **The convention-vs-cruft discrimination is not a studied problem.** Searches across coding-convention
  detection, idiom mining, convention-vs-anti-pattern classification, and obsolete-pattern detection
  surfaced no prior work on distinguishing an intentional convention from accumulated cruft. The
  closest prior art, NATURALIZE, *defines* a convention as statistical frequency — "an equilibrium
  that everyone expects" — and suggests changes "only when there is sufficient evidence of emerging
  consensus in the codebase" ([Allamanis, Barr, Bird & Sutton, arXiv:1402.4182](https://arxiv.org/abs/1402.4182),
  §1, §2), over identifier names and whitespace only. **Majority is correctness, by construction** —
  which is exactly the assumption A3a exists to break. Consequence: A3a has no validated
  discriminator, no labelled dataset, and no published baseline. It is a new proposal, and the
  README, the acceptance criteria, and any external claim must say so. The same paper does support
  the *motivation*: roughly one third of code reviews contain feedback about convention adherence.
- **Two of the evidence signals are not what they were assumed to be, and one is now changed.**
  - `git_distinct_authors` as a **raw count** is contradicted. The validated ownership metric is
    commit-based *concentration*, not headcount: "the number of code authors and the ownership values
    approximated by the line-based ownership **should not be a concern** for a quality improvement
    plan as these metrics are **weakly associated with defect-proneness**"
    ([Thongtanunam & Tantithamthavorn, arXiv:2408.12807](https://arxiv.org/abs/2408.12807), §V,
    Recommendation 1). What does predict defect-proneness is top-developer commit share
    (`OWN_COMMIT`) and the count of developers above a 5% ownership threshold (`MAJOR_COMMIT`),
    median AUC 0.80 (RQ4). **Change applied:** the evidence bundle replaces the raw author count with
    commit-ownership concentration. See the changelog entry and `PHASE_1_SPEC.md` §3. Note also that
    commit-based and line-based ownership disagree substantially — "only 0% to 40% of developers can
    be identified by both" (RQ1) — so the implementation must use `git log` (commit-based), not
    `git blame`.
  - `git_last_touched_days_ago` is **confounded, and stays only as a weak signal**. Old is not bad:
    a conservative distribution "emphasi[zes] stability over currency, which naturally leads to a
    higher TL but potentially more stable systems," and "findings that equate newer with safer **may
    overstate risk**" ([Panter & Eisty, arXiv:2601.11693](https://arxiv.org/abs/2601.11693), §5.1.1,
    §7.0.3). That review also names loopr's exact problem as an open gap: metrics need data to
    "**distinguish between deliberate protective delay and debt accruing neglect**" (§5.3.4,
    Research Gap 4). Staleness therefore may never be sufficient on its own for a DO_NOT_REPLICATE
    verdict — it must co-occur with at least one other cruft signal.
- **Deprecation markers are a weaker signal than assumed, and are directionally ambiguous.** Roughly
  8% of self-admitted-technical-debt comments (27 of 335) are "on-hold" debt — code that is correct
  and intentional, blocked on an external event, e.g. `// TODO ... it can be removed if ever the
  doParse() method is not final!` ([Maipradit et al., arXiv:1901.09511](https://arxiv.org/abs/1901.09511),
  §1, Fig. 1). Separating those needs a trained classifier reaching only AUC 0.83; a regex cannot.
  A `TODO` is therefore evidence of *acknowledged* debt, which is not the same as cruft to avoid —
  and is a legitimate AMBIGUOUS trigger rather than an automatic DO_NOT_REPLICATE.
- **Correction to an assumption not previously written down.** The frequently-cited F1 figures of
  92.8% / 96.7% for SATD tooling measure *lifecycle-action tracking of already-identified comments*,
  not debt detection; detection itself is delegated to a `TODO/FIXME/XXX/HACK` regex with no reported
  precision ([Sheikhaei & Tian, arXiv:2304.07829](https://arxiv.org/abs/2304.07829), §III-B, §IV-B).
  Naive comment-diffing produced 783 false positives from 3,370 candidates in one project. Nothing in
  loopr previously claimed these numbers; this is recorded so a future revision does not import them.

**Net effect on the design: none of the above falsifies A3a's architecture.** The four verdicts, the
two-stage touched-surface discovery, the two-tier ledger, and Gate 3 all stand. What changes is (a)
one signal swap, (b) staleness demoted to never-sufficient-alone, (c) `deprecation_markers` treated
as ambiguity-triggering rather than cruft-proving, and (d) the framing: **A3a is a novel proposal
carried by its human-escalation path, not an application of validated technique.** The AMBIGUOUS →
`OpenQuestion` route and the CONFLICT → Gate 3 route are therefore load-bearing, not decorative, and
Phase 1's acceptance criteria must *measure* classification quality against human judgment rather
than assume it (see `PHASE_1_SPEC.md` §8).

**One reliability risk, logged not escalated.** `PatternClassification.verdict` is a four-way
categorical, while all six stopping-test conditions are binary. Judge reliability degrades markedly
as the output space widens — 15–25 points across four frontier judges moving from binary to a
six-level ordinal scale (arXiv:2603.05399, §5–6, Table 4). Four-way *nominal* was not itself tested,
so this is an adjacent risk rather than a measured one, but it means the conformance classifier is
loopr's least reliable judge call by construction. Existing mitigations (AMBIGUOUS as a first-class
verdict; CONFLICT escalating to a human) are the right shape; the deterministic pre-checks in
`docs/conformance-classification-spec.md` §2–3 remain mandatory rather than advisory.

### A4. Research-grounded expansion to the ultimate PRD

Only after the baby PRD and boundary are confirmed does loopr research (targeted at a clarified problem, never a fuzzy one) and expand the confirmed core into the robust **ultimate PRD**.

**No heavy human gate on the ultimate PRD.** By design, the human reviews the small thing (baby PRD) and trusts the expansion, because the ultimate PRD is a faithful expansion of an already-confirmed core. loopr presents the ultimate PRD's TL;DR and proceeds; it does not ask the user to review it line by line.

Grounding stack (see section 9): native web search (baseline), plus optional academic (paper-search) and library-doc (Context7) grounding when available.

### A5. Prompt and gate generation

loopr generates, customized from the ultimate PRD and `context.md`:

- The build, review, and audit **subagents** (`.claude/agents/`), each with its model pinned and its tools scoped (see B1).
- The project's **gates** (`loop.gates.sh` equivalent) for the detected stack.
- The **failure-mode catalogue** the audit tier checks against (from A1/A4 analysis).
- **`PHASE_1_SPEC.md`** at the repo root, the loop's entry point — the one loopr-produced file that
  stays at root by design, since it has to be the obvious thing a human or the future harness points
  at (see section 9 for why everything else does NOT live at root).
- **`conformance-ledger.md`** (brownfield only) — every CONFORM/DO_NOT_REPLICATE call from A3a, plus
  the resolution of any confirmed CONFLICT, so the build tier later knows what to follow and what to
  avoid without re-deriving it.

**Artifact locations:** baby PRD, ultimate PRD, `context.md`, and `conformance-ledger.md` all live
under `.claude/loopr/` in the target repo, not scattered at root — a stranger's repo shouldn't fill up
with loopr's working files. See section 9 for how this relates to the skill's own packaging directory.

---

## 6. Phase B — the phased build-review-audit loop (next slice)

### B1. Tier and subagent architecture

Three tiers, each a Claude Code subagent, model pinned per role:

- **Build (Sonnet):** writes the phase. Tools: Read, Write, Edit, Bash, Grep, Glob.
- **Review (Sonnet, read-only):** adversarially reviews and reports; patches via its own commit. Tools: Read, Grep, Glob. **Read-only is deliberate:** the reviewer literally cannot write approval into the code, enforcing maker/checker separation by tool permission, not prompt discipline.
- **Audit (Opus, read-only):** senior auditor. Reads the review's OUTPUT (not the whole diff), the failure-mode catalogue, and the boundary. Verdict: APPROVE / KICK_BACK / HALT. Owns the approval and next-spec generation on APPROVE. Direct-patches only on a catastrophic missed boundary breach; otherwise HALTs for the human. Tools: Read, Grep, Glob.

Model-per-subagent and per-subagent read-only tools are native Claude Code capabilities; loopr configures them, it does not invent them.

### B2. git-marker phase discovery

State is derived from git commit markers every pass, so the loop is crash-safe and resumable: kill it mid-run, restart, it re-derives exactly where it was. Markers gate discovery (`feat: Phase N implementation`, `chore: Phase N review complete`, `chore: Phase N review approved`, `chore: Phase N audit kickback`, terminal `BUILD_COMPLETE.md`). The reviewed-but-not-audited state and the KICK_BACK re-review are routed by marker counts, so even the round ceiling survives a crash.

### B3. Gates as ground truth

After an audit APPROVE, loopr re-runs the project's deterministic gates itself (typecheck, tests, build, secret scan) and treats them as ground truth over any model's self-report. If gates fail, the approval is overridden and the loop HALTs. This is the deterministic anchor: the strong model still faces the compiler.

### B4. The boundary-audited third tier

The audit's narrow job: did the junior reviewer MISS anything on the known high-stakes invariants and the hard boundary, and do its claimed checks actually hold? It is cheap because it audits the review's output, not the codebase. It is the headline differentiator, and it is inseparable from the failure-mode catalogue and boundary produced in Phase A. **If the audit tier ships in v1, the failure-mode analysis and boundary ship in v1; they are coupled.**

### B5. Supervised-first-run on-ramp

Unattended is the destination; **supervised-first-run is the on-ramp.** loopr defaults to supervised (pause at each phase boundary) on the first run of any given project, then unattended after. This protects a stranger from an unproven loop going hands-off on their first try, and it mirrors the discipline the author uses.

---

## 7. Continuity model (iteration without losing the founding context)

- **Immutable charter.** The founding baby PRD and original `context.md` are committed once and re-read on every iteration as grounding. git preserves them permanently; loopr's job is to never overwrite them.
- **Layered `context.md`.** As new asks arrive, `context.md` grows in structured layers, never a blind append blob: a **current-state header** loopr maintains as the single source of "what's true now" (so any fresh subagent orients in seconds), a **sectioned body** (original intent, stakeholder constraints, watch-outs), and a **supersession rule** (a changed constraint is marked superseded with a pointer to its replacement, never deleted). This preserves the audit trail while keeping the header always-true, so the file stays readable at iteration ten instead of rotting into noise.
- **Additive phase specs.** New work is a new additive phase-spec series building on the committed foundation, never a rewrite of the originals.

Acceptance criterion 3 and this continuity model are the same mechanism from two ends: the build reveals what the interrogation missed, and the missed things flow into `context.md` for the next pass.

## 8. Grounding and dependencies

**Baseline: native Claude web search.** Zero-install, already in Claude Code. loopr works out of the box with web search alone for design-space and doc grounding.

**Optional enhancements (used if present, never required):**
- **paper-search-mcp** (MIT, free-first, multi-source incl. arXiv/PubMed/bioRxiv/Semantic Scholar) for academic and technical grounding. Genuinely vendorable; hits public APIs.
- **Context7** (MIT server, free tier, no API key needed for basic use) for current, version-specific library docs so the build does not hallucinate API syntax. **Note:** Context7's docs engine is a proprietary hosted service; loopr depends on it, it does not embed it. **Therefore loopr falls back to native web search for doc grounding when Context7 is unavailable,** preserving the "don't hallucinate API syntax" property.

**Hard rule: no paid dependency, ever.** A paid dependency in a free skill kills adoption before anyone sees value. (This is why the author's prior Nia dependency is replaced.) A separate arXiv MCP is intentionally omitted as redundant with paper-search.

**Same rule re-applied to brownfield touched-surface discovery (2026-07-27).** Semantic/vector search
over the target repo was considered for finding relevant files by meaning rather than exact keyword
match, and both existing candidates were researched and rejected:
- **Nia** — has a limited free tier (3 indexing jobs) but real usage is paid ($50-99+/seat/month as
  of early 2026); breaks the no-paid-dependency rule directly.
- **Context7** — its MCP interface is MIT-licensed, but the indexing/parsing/crawling engine behind
  it is a proprietary hosted service, not something loopr can embed. It also indexes public
  library/API documentation, not arbitrary private repositories — the wrong tool for this job even
  ignoring licensing.

**Resolution:** a two-stage discovery instead — a cheap, free, deterministic keyword/dependency-graph
pre-filter, followed by an LLM relevance-judge call over the shortlist (using the model's own language
understanding as the "semantic" layer). Gets the practical benefit without a new service, cost, or
setup step. Full detail: `docs/conformance-classification-spec.md` section 1.

### 8a. Pinned stack versions (added 2026-07-28)

Canonical copy with verification method and dates: `docs/modernization_log.md`. Summary:

| Component | Pinned | Verified how |
|---|---|---|
| Python | **3.14** (floor `>=3.14`); toolchain confirmed on 3.14.4 | `py --version` → `Python 3.14.4`; [python.org/downloads](https://www.python.org/downloads/) |
| Pydantic | **`pydantic>=2.13,<3`** (latest 2.13.4) | `pip index versions pydantic` → LATEST 2.13.4 |
| mypy | **`mypy>=2.3,<3`** (latest 2.3.0) | `pip index versions mypy` → LATEST 2.3.0; [changelog](https://mypy.readthedocs.io/en/stable/changelog.html) |

Three notes that matter for the build:

- **No Pydantic API correction was needed.** This PRD never committed to Pydantic syntax beyond
  `extra="forbid"`, and that spelling is current: `model_config = ConfigDict(extra='forbid')` is the
  documented v2 form ([Pydantic configuration docs](https://docs.pydantic.dev/latest/api/config/)).
  Reported plainly rather than inventing a change, per this step's own instruction.
- **mypy 2.x dropped the ability to *run* under Python 3.9** (it can still type-check 3.9 code via
  `--python-version`). Irrelevant to loopr, which targets 3.14, but recorded so the pin is not
  loosened carelessly.
- **These are loopr's own build-time pins**, not a constraint on target projects. loopr specs
  projects in any stack; nothing here is written into a generated artifact.

## 9. Packaging and distribution

loopr ships as a Claude Code skill:

```
.claude/skills/loopr/
├── SKILL.md              # lean orchestration prompt (< ~5000 words)
├── references/
│   ├── stopping-test.md          # the six-condition sufficiency test
│   ├── context-md-guide.md       # what belongs in context.md vs PRD (with examples)
│   ├── boundary-guide.md         # how to propose/confirm a boundary
│   ├── continuity-model.md       # charter + layered context.md rules
│   └── prompt-templates/         # step11_build / step12_review / step12_5_audit templates
├── assets/
│   └── gate-templates/           # per-stack run_gates recipes
└── scripts/
    └── (optional helpers, e.g. marker/discovery utilities)
```

**Two distinct `.claude/` subtrees — don't conflate them:**
- `.claude/skills/loopr/` — the skill's own packaged code (SKILL.md, references, assets, scripts).
  Only present once step 2 (skill packaging) ships; this is loopr's installation, the same on every
  project.
- `.claude/loopr/` — a given project's generated artifacts from a loopr *run* (baby PRD, ultimate PRD,
  `context.md`, `conformance-ledger.md` for brownfield). Present as soon as the standalone module runs
  on a project, even before skill packaging exists; different content on every project loopr touches.

Design notes grounded in the skill spec:
- **Progressive disclosure.** `SKILL.md` stays lean; the detailed procedures and templates live in `references/`/`assets/` and cost zero context until read. This is the intended pattern and keeps loopr from bloating the window.
- **Generated, not shipped, subagents.** The build/review/audit prompts are customized per project, so loopr **generates** `.claude/agents/loopr-builder.md`, `loopr-reviewer.md`, `loopr-auditor.md` into the user's repo with the customized bodies, pinned models, and scoped tools. The templates in `references/prompt-templates/` are the blanks; the generated agents are the filled copies.
- **Deliberate invocation.** loopr is user-invocable (`/loopr`) and deliberately started, not auto-triggered on any coding request, so it never hijacks a user who just wanted a quick edit.
- **Scripts run out-of-context.** Any bundled helper script executes via bash; its code never enters the context window, only its output.

## 10. Failure-mode catalogue (loopr's own; dogfooding Step 0)

The high-stakes ways loopr fails, front-loaded so the audit-of-loopr and the build have a map:

- **Premature draft.** loopr drafts the baby PRD before the six conditions hold. Mitigation: the stopping test is a hard gate, not a suggestion.
- **Unread gate.** The user rubber-stamps the baby PRD without reading it. Mitigation: TL;DR-first, built for the skim.
- **Boundary over-fit to examples.** loopr proposes a boundary flavored by the author's context (Shariah/anti-replication) rather than the user's real one. Mitigation: boundary is analyzed from *this* user's `context.md`, and the author's snapshot examples are marked as illustrations, not the method.
- **Context.md rot.** Blind appends make the file unreadable by iteration ten. Mitigation: layered structure + current-state header + supersession pointers.
- **Silent two-tier.** The audit tier is configured but never fires, so the build is approved with no senior check. Mitigation: discovery routes an explicit AUDIT state; supervised-first-run surfaces it visibly.
- **Checker writes approval.** The reviewer approves its own work. Mitigation: read-only tools; the reviewer has no write hands.
- **Google/Kaide leakage.** Author-internal constraints (Google-only stack, teardown SOP) leak into a stranger's spec. Mitigation: explicitly dropped; these are not part of loopr.
- **Silent cruft inheritance (brownfield).** loopr reproduces an existing codebase's bad pattern
  because it pattern-matched instead of judging. Mitigation: A3a's explicit CONFORM/DO_NOT_REPLICATE/
  CONFLICT call on every pattern the touched surface contains; this is the entire reason A3a exists.
- **Conflict-gate fatigue (brownfield).** HUMAN GATE 3 turns into a long, rubber-stampable list, same
  failure shape as "unread gate" above. Mitigation: Gate 3 is scoped to CONFLICT verdicts only —
  routine CONFORM/DO_NOT_REPLICATE calls apply silently and never reach the user.
- **Touched-surface miss (brownfield).** The relevant file for a pattern conflict never gets included
  in the touched surface, so a real conflict is never even evaluated. Mitigation: two-stage discovery
  (keyword/dependency-graph pre-filter deliberately cast wide, then an LLM relevance pass) and the
  user reviews/adjusts the proposed list at Gate 2, rather than loopr silently trusting its own guess.

*Three entries added 2026-07-28 from the research pass (section 5 A1 and A3a grounding blocks):*

- **Judge nondeterminism read as signal.** The same field, judged twice, returns different verdicts,
  and the loop treats the flip as new information — asking a redundant follow-up, or stopping on a
  lucky pass. Measured stochastic-stability of 37.50% on an ordinal benchmark makes this a real
  mechanism, not a hypothetical (arXiv:2603.05399, Table 5). Mitigations, all three required: the
  deterministic structural check gates the judge call, so a judge flip alone can never flip a
  condition from false to true without the structural layer also passing; every judge call's exact
  serialized input and returned verdict is persisted, so a flip is detectable after the fact rather
  than invisible; and the round cap bounds how many times a flip can cost a round.
- **Overclaimed brownfield validation.** loopr's README, or the module's own output, presents the
  CONFORM/DO_NOT_REPLICATE call as a validated technique when no prior art, labelled dataset, or
  published baseline exists (A3a grounding block). This is a *credibility* failure, not a code
  failure, and it is the one most likely to be committed by a well-meaning summary. Mitigation:
  the novelty flag is written into the PRD, into `PHASE_1_SPEC.md` §8, and into the acceptance
  criteria as a requirement to measure classification agreement against human judgment on the real
  brownfield proof project — not to assert it.
- **Signal laundering in the evidence bundle.** A weak or confounded signal (staleness; a `TODO`
  marker) is passed to the judge with the same apparent weight as a strong one, and the judge —
  which cannot know the provenance — treats the bundle as uniformly reliable evidence. Mitigation:
  staleness is never sufficient alone for DO_NOT_REPLICATE; `deprecation_markers` triggers AMBIGUOUS
  rather than proving cruft; and the rubric names each signal's known weakness inline so the judge is
  told what not to over-trust. The review agent checks the rubric text for these qualifiers.

## 11. Human gates (summary)

- **Spec phase (2 hard gates, always; a conditional 3rd for brownfield):** confirm/tweak boundary
  (Gate 2, also covers the touched-surface list for brownfield) → [brownfield only, conditional]
  confirm any pattern CONFLICTs (Gate 3) → confirm baby PRD via TL;DR (Gate 1, chronologically last —
  see section 4). Gate 3 never fires if no conflict was found. Nothing else blocks.
- **Build phase:** supervised-first-run per project (pause at phase boundaries), unattended after.
- **Ultimate PRD:** no heavy gate; trusted expansion of a confirmed core.

## 12. Explicitly out of v1 (deferred)

- The web-to-Code auto-relay (author's personal workflow; a stranger does everything in Claude Code).
- Docker (native subagents replace it; the fresh-context-per-phase property loopr wanted is native to subagents).
- Codex / Cursor ports.
- Full idea-to-deploy autonomy (the vision, not v1).
- A budget ceiling, cost telemetry, kill switch, and preflight-readiness audit for the loop (real gaps, deferred to the loop-hardening slice).

## 13. Success metrics

- **Primary:** the three acceptance criteria in section 3 are reproducibly hit on strangers' greenfield problems.
- **Adoption:** research grounding works with zero setup (native web-search baseline); optional research enhancers are one free install each. **The module itself is not zero-setup** -- as of the skill-packaging build (`SKILL_PHASE_1_SPEC.md` SS6.4), running loopr at all requires a one-time `pip install -e .` (or `pip install loopr` once/if published) before the skill or CLI is usable. The original "zero setup" framing's spirit -- no paid dependency, no heavy install -- still holds; only the "zero setup, full stop" claim was inaccurate and is corrected here.
- **Author-proof:** loopr specced with loopr (this PRD) and the sandbox build run under the generated loop, with the failures captured feeding both loopr's design and the README.

## 14. Build phasing for loopr itself (locked sequencing, see `loopr-MIGRATION.md` section 2)

1. **Standalone spec-discipline module (Python), proven on a real greenfield project AND a real
   brownfield project.** The six-condition stopping test (`docs/stopping-test-spec.md`, confirmed)
   plus, for brownfield, the pattern-conformance classification (`docs/conformance-classification-spec.md`,
   confirmed) — baby-PRD/`context.md`/`conformance-ledger.md` emission, all three hard gates. This
   alone, proven, is the first shippable milestone. Not built yet.
2. **Package as a Claude Code skill** (`.claude/skills/loopr/`, section 9) — only after step 1 is
   proven. Not a v1-launch requirement; a packaging step after the core is validated.
3. **Prompt/gate/subagent generation** (the A5 outputs) — customized per project once the module
   exists.
4. **Phased loop (Phase B), parked, much later** — adapting Traycer (Apache-2.0), not a native port
   of the abandoned Docker harness. First task when this step begins: actually assess Traycer against
   the three invariants (`loopr-PRD.md` section 6/`loopr-MIGRATION.md` section 5); it hasn't been
   evaluated yet, only named as a target.

Prove 1 before touching 2-4. This replaces an earlier version of this section that assumed skill
packaging and the Docker-ported loop were the near-term path; both were superseded by the sequencing
decision recorded in `loopr-MIGRATION.md`.

## 15. Open decisions (honest, refreshed 2026-07-27)

**Genuinely open right now, blocking nothing but worth tracking:**
- Interrogation question-generation/grouping logic — not yet specified.
- The `context.md`-vs-baby-PRD split classifier — not yet specified.
- ~~Standalone module's exact interface/CLI surface — not yet specified.~~ **[RESOLVED 2026-07-28]**
  Decided as part of the Step 10 modernization, because it is the same question as "how does a judge
  call actually get invoked," which Phase 1 cannot be built without. **Decision: the module never
  calls an LLM API itself.** It is a pure, resumable state machine over a persisted state file; when
  a judge call is required it emits one structured `JudgeRequest` envelope and exits on a
  distinguished exit code, and the invoking agent (Claude Code by default, using that session's own
  model) supplies the verdict on the next invocation. No API key, no network, no paid dependency — a
  direct consequence of the section 8 hard rule rather than a free choice. Full reasoning, the
  `JudgeClient` protocol, the exit-code contract, and the headless test binding are in
  `PHASE_1_SPEC.md` §6. A direct-API binding is an explicit Phase 1 non-goal.
- `PHASE_1_SPEC.md`'s file location, if this decision is ever revisited (currently: stays at repo
  root by design, everything else under `.claude/loopr/` — see section 5 A5, `docs/conformance-classification-spec.md`
  section 9).
- Traycer suitability — named as the step-3/Phase-B adaptation target, not yet evaluated against the
  three invariants.

**Deferred until step 2 (skill packaging), not decided now:**
- Final naming of the two PRDs in user-facing copy ("baby PRD" is internal; user-facing may want gentler terms).
- Whether loopr generates subagents into `.claude/agents/` or keeps tier prompts in a `loop/` folder referenced by an orchestrator; leaning `.claude/agents/` for native model+tool enforcement.
- The exact `run_gates` stack-detection strategy for arbitrary projects.
- Whether the loop orchestration lives in `SKILL.md` prose or a bundled driver script; to be decided by evidence from proving step 1, not guessed now.

**Resolved since the prior revision of this PRD (kept here for traceability, not re-litigated):**
- Brownfield scope, the six-condition operationalization, the pattern-conformance classification, the
  three-gate structure, the semantic-search question, and artifact file locations — all decided; see
  sections 2, 5 (A1/A3/A3a/A5), 8, 9, and 11 above, or `loopr-MIGRATION.md` for the decision history.

---

## MODERNIZATION CHANGELOG

### Entry 2 — 2026-07-28 (Step 10: PRD modernization + Phase 1 blueprinting)

Scope: ground this PRD in verified current reality, then build `PHASE_1_SPEC.md` from the result.
This entry is additive to Entry 1 below, not a replacement. **No locked architectural decision was
changed, and no ## OPEN ARCHITECTURE QUESTIONS block was required** — see "Escalations considered
and declined" at the end of this entry for the two candidates and why each was judged an enhancement
rather than a falsification.

**A. Version and API pinning** — new section 8a; canonical copy in `docs/modernization_log.md`
(created this pass; did not previously exist).

| Change | Source |
|---|---|
| Python pinned to `>=3.14`; toolchain confirmed on 3.14.4 | Local `py --version` → `Python 3.14.4`; [python.org/downloads](https://www.python.org/downloads/) |
| Pydantic pinned to `>=2.13,<3` (latest 2.13.4) | `pip index versions pydantic` → `LATEST: 2.13.4` |
| mypy pinned to `>=2.3,<3` (latest 2.3.0) | `pip index versions mypy` → `LATEST: 2.3.0`; [mypy changelog](https://mypy.readthedocs.io/en/stable/changelog.html) |
| Recorded that mypy 2.x cannot *run* under Python 3.9 (can still check 3.9 via `--python-version`) | [mypy changelog](https://mypy.readthedocs.io/en/stable/changelog.html) |

**Corrected syntax/config: none — reported plainly rather than invented.** This PRD never committed
to Pydantic API shape beyond `extra="forbid"`, and that remains current;
`model_config = ConfigDict(extra='forbid')` is the documented v2 form
([Pydantic config docs](https://docs.pydantic.dev/latest/api/config/)). Nothing in the PRD was found
to be hallucinated or outdated at the API level.

**B. Literature validation of the core methods** — new grounding blocks in section 5 A1 and 5 A3a.

| Design element | Verdict | Source |
|---|---|---|
| Deterministic check anchors every judge call | **Supported, and more necessary than assumed** — no judge uniformly reliable; stochastic-stability mean 37.50% on identical repeated input | [arXiv:2603.05399](https://arxiv.org/abs/2603.05399) §3.2, §5, Table 5 |
| Per-field judge scoping (Shape 1 / Shape 2), never one holistic call | **Supported** — batching 14 criteria into one call left only 1/30 outputs clean; single-criterion targeting hit 84.3% avoidance and a 93.5% win probability (OR 2.662, p=4.23×10⁻⁸) | [arXiv:2507.02858](https://arxiv.org/abs/2507.02858) §IV-C, §V-D |
| Local scope is sufficient for good follow-ups | **Supported** — 98% (144/146) of follow-up questions needed ≤4 prior speaker turns | [arXiv:2507.02858](https://arxiv.org/abs/2507.02858) §IV-A, §V-B |
| `max_rounds = 8` | **Not falsified; mildly supported** — all 7 models under CoT self-terminated at ≤8.12 turns avg; the one model hitting the 20-turn ceiling was flagged as lacking a stopping criterion and scored worse (IRE 0.13) | [arXiv:2602.18306](https://arxiv.org/abs/2602.18306) Table 4, §5.1 |
| A principled elicitation stopping rule exists in prior art | **Null — nobody has built one.** Termination is a turn cap, a model whim, or user fatigue. loopr's six-condition test is a novel proposal, not applied technique | [arXiv:2602.18306](https://arxiv.org/abs/2602.18306) §3.5, §6.2; [arXiv:2507.02564](https://arxiv.org/abs/2507.02564) §IV-E3 |
| Force-resolve-to-visible-assumption (vs. loop until complete) | **Supported** — coverage does not converge: best implicit-requirement coverage 0.32, style requirements <0.01; 73.7% incl. partials elsewhere | [arXiv:2602.18306](https://arxiv.org/abs/2602.18306) Tables 4, 6; [arXiv:2507.02564](https://arxiv.org/abs/2507.02564) §IV-E2 |
| Convention-vs-cruft discrimination (A3a's core task) | **Null — not a studied problem.** Nearest prior art defines convention *as* frequency, the exact assumption A3a exists to break | [arXiv:1402.4182](https://arxiv.org/abs/1402.4182) §1, §2 |

**C. Enhancements applied within the locked architecture** (three, all in A3a):

1. **`git_distinct_authors` (raw count) → commit-ownership concentration.** Author headcount is
   contradicted as a quality signal — "weakly associated with defect-proneness"; the validated
   metric is top-developer commit share (`OWN_COMMIT`) plus developers above a 5% threshold
   (`MAJOR_COMMIT`), median AUC 0.80 ([arXiv:2408.12807](https://arxiv.org/abs/2408.12807) §V Rec. 1,
   RQ4). Implementation must use `git log`, not `git blame` — the two identify only 0–40% of the same
   developers (RQ1). **This edits a field in the already-confirmed
   `docs/conformance-classification-spec.md` §3;** a dated pointer has been added there so the two
   documents cannot silently diverge. `PHASE_1_SPEC.md` §3 carries the new field.
2. **Staleness demoted to never-sufficient-alone.** Old-and-stable is a real category; "findings that
   equate newer with safer may overstate risk," and distinguishing "deliberate protective delay from
   debt accruing neglect" is named as an open research gap
   ([arXiv:2601.11693](https://arxiv.org/abs/2601.11693) §5.1.1, §7.0.3, §5.3.4).
3. **`deprecation_markers` reclassified from cruft-proving to ambiguity-triggering.** ~8% of SATD
   comments (27/335) are "on-hold" debt — correct, intentional code blocked on an external event —
   and separating them needs a classifier at AUC 0.83, not a regex
   ([arXiv:1901.09511](https://arxiv.org/abs/1901.09511) §1, Fig. 1).

**D. Failure-mode catalogue extended** — three entries added to section 10: *judge nondeterminism
read as signal*, *overclaimed brownfield validation*, *signal laundering in the evidence bundle*.
Each carries its mitigation and a review-agent check.

**E. Open decision resolved** — section 15's "standalone module's exact interface/CLI surface" is
closed. The module never calls an LLM API; it emits a `JudgeRequest` envelope and exits, and the
invoking agent answers. This follows from the section 8 no-paid-dependency rule rather than being a
free choice. Full contract in `PHASE_1_SPEC.md` §6. **[UNVERIFIED — design decision, not a
literature or vendor claim; no external source applies.]**

**F. A citation deliberately NOT made.** [arXiv:2504.11972](https://arxiv.org/abs/2504.11972) reports
that "zero-shot, context-free judging often yields the best evaluation performance," which reads as
direct support for Shape 1 scoping. It is not, and it is recorded here so a later revision does not
reach for it: in that paper "context" means the **ground-truth source passage** withheld from a judge
grading two short strings (§6.3), not conversational history; "zero-shot" separately means 0 few-shot
exemplars, and the two ablations were never run together. The authors' own conclusion is that prompt
configuration *barely matters* (variance ≤0.0037), and they attribute the result to the task being
too simple for extra input to help. Citing it for per-field scoping would invert the paper's thesis.

**G. Citation-discipline disclosure (tooling gap).** Literature grounding used `/arxiv` and
`/paper-search`. `/paper-search`'s **arXiv** source was found returning newest-on-arXiv regardless of
query; it was patched mid-pass (query terms now AND-joined under `all:`) and re-verified on two
distinct queries returning distinct, on-topic results before any citation was relied upon.
`/paper-search`'s **Google Scholar** source returns an empty list unconditionally and was **not**
fixed — very likely Google anti-scraping rather than a code defect. **Disclosed, unresolved gap:**
no Google Scholar coverage in this pass. Practical exposure is non-arXiv venues (notably ICSE/FSE/
EMSE software-engineering proceedings) that arXiv preprints may not mirror; the A3a null finding in
particular would be strengthened or weakened by better SE-venue coverage, and should be re-checked if
Scholar access is restored. All claims above are traceable to arXiv primary sources whose methods
sections were read, not abstracts.

**Escalations considered and declined** (stating these explicitly, since silence would be
indistinguishable from not having looked):

- *Candidate 1: the A3a evidence signals are largely unvalidated, and two are contradicted.* Declined
  as an escalation. The research does not show the CONFORM/DO_NOT_REPLICATE/CONFLICT architecture is
  wrong; it shows the architecture is **novel and its signals are weak**. That is answered by fixing
  the signals (change C), relabelling the claim (A3a grounding block), and making the human
  escalation path carry real load — all of which sit *on top of* the locked design rather than
  through it. Escalating would have been the safer-looking move and the wrong one.
- *Candidate 2: four-way `PatternClassification.verdict` vs. measured judge degradation on wider
  output spaces (15–25 points, binary → 6-level ordinal).* Declined. Four-way **nominal** was not
  tested — the finding is adjacent, not on-point — and the design's existing AMBIGUOUS verdict and
  Gate 3 escalation are exactly the right mitigations. Logged as a named risk in A3a instead.

### Entry 1 — 2026-07-27 (brownfield scope reversal + operationalization specs)

Recorded retrospectively for continuity; this predates the Step 10 pass above and is unchanged by it.
Brownfield moved into v1 scope (sections 2, 5 A3a, 11), the six-condition stopping test was
operationalized (`docs/stopping-test-spec.md`), the pattern-conformance classification was specified
(`docs/conformance-classification-spec.md`), the three-gate structure and gate chronology were
settled (sections 4, 11), the semantic-search dependency question was researched and closed without a
new dependency (section 8), and artifact locations were fixed under `.claude/loopr/` (section 9).
Decision history: `loopr-MIGRATION.md` sections 1a, 2, 6.
