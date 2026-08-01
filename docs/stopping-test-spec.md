# loopr — Stopping Test Operationalization Spec (for review)

Status: PROPOSED, not built. Confirm or correct before any module code is written.
Scope: this spec covers ONLY sequencing step 1 (loopr-MIGRATION.md section 2) — the
standalone spec-discipline module's six-condition stopping test. It does not touch the
harness, skill packaging, or any parked item.

Source: loopr-MIGRATION.md section 4 / loopr-PRD.md section 5 (A1). Six conditions,
all must hold to stop interrogating.

---

## Design approach (applies to all six)

Two-layer check per condition:

1. **Structural check** (deterministic, cheap, runs first) — a Pydantic model field
   exists, is non-empty, and passes a minimal shape validator. Pure code, no model call.
2. **Judge check** (LLM-as-judge, runs only if the structural check passes) — a
   forced-schema call that returns `{pass: bool, reason: str, missing: str | None}`.

The judge check comes in **two shapes**, and each condition uses exactly one:

- **Shape 1 — pure single-field check** (conditions 1, 2, 3): the judge is given
  ONLY the field under test plus its rubric — no chat history, no other fields.
  Fully reproducible and auditable in isolation.
- **Shape 2 — scoped cross-reference check** (conditions 5, 6): the judge is given
  the field under test PLUS the specific other fields its rubric explicitly names,
  and nothing beyond that. Still not the whole transcript, still reproducible given
  the same inputs — just honest that these two conditions are inherently relational
  and cannot be judged from the field alone. Condition 5 additionally reads
  `acceptance_criteria`; condition 6 additionally reads `acceptance_criteria`,
  `scope_edges`, and `boundary`.

A condition is TRUE only if both layers pass. If either fails, the module asks a
targeted follow-up question aimed specifically at the failing condition (never a
generic "anything else?") and re-runs both checks on the updated field(s) next round.

This keeps the loop from stalling on vague partial answers (structural layer) while
keeping the judge honest and cheap (each call sees only the field(s) its rubric
actually needs, never the full transcript, so it cannot rubber-stamp from vibes).

State model (conceptual, not final field names):

```
InterrogationState:
  problem_statement: str | None
  acceptance_criteria: list[str]          # >=1 required
  scope_edges: list[ScopeEdge]            # in/out/deferred, named
  boundary: Boundary | None               # proposed + confirmed flag
  context_notes: list[ContextNote]        # soft context captured so far
  open_questions: list[OpenQuestion]      # the ledger for condition 6
  round: int
  max_rounds: int = 8                     # hard cap, see condition 6
```

---

## Condition 1 — Outcome-stated problem

**Structural check:** `problem_statement` is non-empty AND is scored against a
solution-shaped pattern list (heuristic denylist: sentence's grammatical subject is a
named technology/architecture — e.g. starts with "Build a <tool>", "Use <framework>
to...", "A <system-type> that..." — with no outcome clause attached). This is a cheap
pre-filter, illustrative and untuned pending the real project test (open item 4).

**Pre-filter can only downgrade, never hard-block.** A structural-layer match sets a
`flagged: bool` on the field and is passed through to the judge as extra context
("structural pre-filter flagged this as possibly solution-shaped"); it never skips
the judge call. A valid outcome statement that happens to start with a technology
noun (e.g. "Kubernetes operator that lets on-call stop losing an hour to manual
failover") still reaches the judge and can still pass. Non-empty is the only true
hard gate at the structural layer for this condition.

**Judge rubric:** "Does this statement describe a desired real-world outcome/result
(what becomes true when this is done, for whom), or does it prescribe a specific
solution/implementation as the primary subject? Pass only if a concrete outcome is
named. A stated solution is acceptable ONLY if it is explicitly subordinate to a
stated outcome (e.g. 'I want X to happen; my current guess at how is Y' passes — 'Y'
alone does not)."

**Pass condition:** `problem_statement` non-empty AND judge returns `pass: true`
(pre-filter flag is advisory input to the judge, never a gate on its own).

**Anti-loop guard:** after 2 consecutive judge failures on this condition, the module
surfaces the judge's last two `reason` strings verbatim to the user and asks them to
restate the outcome directly, rather than asking a third open-ended question.

---

## Condition 2 — >=1 testable acceptance criterion

**Structural check:** `acceptance_criteria` has >=1 entry, each entry non-empty and
containing an observable predicate (heuristic: contains a comparator or
measurable/observable verb — "returns", "shows", "completes in", "equals", "passes",
"is visible" — not just a restated goal like "it works well").

**Judge rubric:** "For each acceptance criterion, could a third party who did not build
the system check it by observation or a concrete test, without needing to ask the
builder for a judgment call? Pass only if at least one criterion is independently
checkable this way. Reject criteria that are purely subjective ('feels fast', 'is
good') with no observable proxy."

**Pass condition:** at least one criterion structurally shaped AND judge-confirmed
checkable. (Condition is per-list — pass as soon as one criterion clears both layers;
the rest can remain weaker.)

---

## Condition 3 — Named scope edges

**Structural check:** `scope_edges` has >=1 entry, each tagged `out` or `deferred`
(not `in` — those aren't edges), with a non-empty `item` and non-empty `reason` field.
An edge with an empty reason auto-fails structurally (a scope edge without a stated
reason is not load-bearing, it's a guess).

**Judge rubric:** "Is each named edge specific enough that a builder reading it later
would know unambiguously whether a new request falls inside or outside it? Reject
vague edges ('nothing fancy', 'basic stuff only') that don't name a concrete
boundary object (a feature, an integration, a scale threshold, a user segment)."

**Pass condition:** >=1 scope edge, structurally shaped, judge-confirmed unambiguous.

---

## Condition 4 — Proposed-and-confirmed boundary

**Structural check:** `boundary` is not None, `boundary.text` non-empty, AND
`boundary.confirmed` is `True` (a boolean explicitly set only by a direct user
confirm/tweak action — never defaulted true).

**Judge rubric:** none needed — this condition is purely a state-machine check, not
a quality judgment. The quality of the boundary's content is judged once, at proposal
time (module's own A3 draft step, per PRD section 5 A3), not re-litigated here. What
this condition re-verifies is only that the user-facing confirm step actually
happened for the CURRENT boundary text (if the boundary text changes after a tweak,
`confirmed` resets to `False` until re-confirmed — prevents stale-confirmation bugs).

**Pass condition:** `confirmed == True` against the current boundary text's hash
(store `confirmed_hash`; compare against `hash(boundary.text)` — any edit invalidates
prior confirmation automatically, no separate dirty-flag to forget to set).

**Escape hatch (per PRD A3):** boundary is "preferred, not strictly mandatory." If the
user explicitly declines to set one (a distinct recorded action, not silence),
`boundary.declined = True` also satisfies this condition, and downstream audit
degrades to failure-mode-catalogue-only per the PRD.

**[AMENDED 2026-08-01 — the boundary-drafting gap.]** This section always assumed "the
module's own A3 draft step" existed ("judged once, at proposal time... not
re-litigated here," above) — but no code anywhere ever drafted one. The only two
places a `Boundary` got constructed were both reactive: on the user's own decline, or
on the user supplying `boundary_text` themselves. Gate 2 rendered with an empty
proposal section unless the user authored the boundary text themselves, which
inverts PRD A3's actual design (confirm LOOPR's draft, not the user's own text).
Closed by adding `JudgeCallType.BOUNDARY_PROPOSAL` — a one-off drafting call, Shape 2,
scoped to `problem_statement`/`acceptance_criteria`/`scope_edges`/`context_notes`, that
runs upstream of Gate 2's render whenever `state.boundary is None`. The judge drafts
plain-language boundary text; the response sets `state.boundary = Boundary(text=...,
confirmed=False)` — proposed, never confirmed by the judge itself. Genuine human
confirmation through Gate 2 remains the only path to this condition passing; nothing
about the confirm/decline/tweak/hash-invalidation mechanics above changed.

A related brownfield-only gap closed in the same pass: touched-surface discovery used
to be gated on the boundary already being confirmed/declined, so it only ran on a
LATER step — populating `touched_surface` after Gate 2 had already rendered (and
potentially been confirmed) with an empty touched-surface section, which changed the
payload digest and forced Gate 2 to re-fire a second time. This contradicted the
design ("this same confirmation also covers the touched-surface list... not a
separate step," `docs/conformance-classification-spec.md` §1). Fixed: for brownfield
mode, touched-surface discovery (prefilter + relevance judge) now runs alongside
boundary-proposal drafting, both completing before Gate 2's FIRST render — one
confirm moment, both sections populated, exactly as originally specified.

---

## Condition 5 — Captured soft context

**Structural check:** `context_notes` has >=1 entry (the PRD's `context.md` splitter
rule already narrows what counts: "would change how the build is judged but cannot be
expressed as a spec requirement"). Each note has a non-empty `text` and a `source`
tag (`stated` — user said it directly, vs `inferred` — module surfaced it and user
confirmed).

**Judge call shape:** Shape 2 (scoped cross-reference) — the judge receives the
`context_notes` entry under test PLUS the current `problem_statement`,
`acceptance_criteria`, `scope_edges`, and `boundary`. **[AMENDED 2026-07-30 — brownfield
proof finding.]** Originally scoped to `acceptance_criteria` only; widened after the
brownfield proof run demonstrated the gap this closes (see rubric note below).

**Judge rubric:** "First, relevance: does this note actually relate to the CONFIRMED
`problem_statement`, `acceptance_criteria`, `scope_edges`, or `boundary` for THIS
build? If it is well-formed, confidently phrased, or even stated as settled fact, but
has no bearing on any of those four fields, REJECT it outright as off-topic — do not
route it anywhere. Confident phrasing is not evidence of relevance. Second, only for
notes that pass the relevance check: does this note change how the finished build
would be JUDGED (accepted/rejected) without being expressible as a testable spec
requirement? If it IS expressible as one of the existing or a new acceptance
criterion, it belongs there, not here — flag as misplaced rather than failing
outright." Misplaced notes get routed back to condition 2's list rather than counted
here. Off-topic notes are rejected outright and routed nowhere — not misplaced, not a
softer failure, simply not soft context for this build.

**Why the relevance check was added (not in the original design):** the brownfield
proof run (2026-07-30) found that the original rubric had no topical-relevance check
at all — it only asked "testable vs. genuine soft context." Two deliberately smuggled
off-topic notes (content from an unrelated project) were both correctly rejected, but
only because the invoking agent reasoned outside the literal rubric text; a more
mechanical judge implementation would plausibly have passed either one, since neither
was actually ambiguous about being testable-vs-soft — they simply had nothing to do
with the build at all, which the original rubric never asked about. This is the same
gap condition 6's rubric never had, because condition 6 was Shape 2 against
`acceptance_criteria`/`scope_edges`/`boundary` from the start (inherently relational).
Condition 5 is now brought to the same standard.

**Pass condition:** >=1 note survives the judge's classification as genuinely soft
context (not misplaced, not vacuous). **If the user has nothing to add** — a real,
common case for a simple project — the module must ask explicitly ("any
boss-said/political/watch-out constraints, or is this a clean slate?") and accept an
explicit "none" as a valid pass, recorded as `context_notes = [{text: "user confirmed
no soft context", source: "stated"}]`. This prevents condition 5 becoming a forced
fishing expedition when there's genuinely nothing to capture.

---

## Condition 6 — No load-bearing unknown remains

This is the hardest one to make terminate and the one flagged as the actual gap.
Two mechanisms, combined:

**A. Explicit open-questions ledger.** Every question the module or the user raises
during interrogation (not just module-initiated ones) is logged as an `OpenQuestion`
with `text`, `status` (`open` / `resolved` / `deferred_non_load_bearing`), and
`load_bearing: bool | None` (set by judge call at logging time).

**Judge call shape:** Shape 2 (scoped cross-reference) — the judge receives the
question text PLUS the current `acceptance_criteria`, `scope_edges`, and `boundary`
fields, and nothing else. This condition is explicitly comparative by definition (see
rubric below); a judge given only the question text has no basis to compare against
and would default to always-load-bearing, defeating the ledger's purpose.

**Rubric:** "Given the current acceptance criteria, scope edges, and boundary, would a
plausible alternative answer to this question require a materially different value in
any of those three? If yes, load-bearing."

**Structural check:** no `OpenQuestion` has `status == "open" AND load_bearing ==
True`.

**B. Hard round cap as termination guarantee (the actual anti-infinite-loop fix).**
`max_rounds = 8` (configurable). At the start of round 8, ANY remaining
`status=="open"` item — load-bearing or not — is force-resolved: the module drafts
its own best-guess answer, states it plainly as an assumption in the baby PRD's
"Assumptions" section (not silently, not hidden), sets `status =
"deferred_non_load_bearing"`, and proceeds. This guarantees termination in bounded
time regardless of judge behavior, at the cost of surfacing unresolved items as
visible assumptions rather than blocking forever. The user sees these flagged
assumptions at HUMAN GATE 1 (the TL;DR confirm) and can kick any of them back into a
real question at that point — so the cap trades "loop forever" for "surface it loudly
and let the human gate catch it," which matches the PRD's own admission that the gate
is only as strong as what the user reads.

**B2. [AMENDED 2026-07-30 — brownfield proof finding, Finding 5.] Generalized to any
still-false condition, not just the C6 ledger.** The brownfield proof run reached
round 11 against `max_rounds = 8` because condition 5 kept failing without ever
producing a logged `OpenQuestion` — the cap's original scope (force-resolve the
ledger) had nothing to force-resolve, so it never fired, and nothing else bounded the
run. Closed by extending the SAME force-resolution behavior to any condition still
false at the round cap, not condition 6 alone: at the start of round 8, for each
condition among 1–5 that is still `False` and has produced no path to becoming a
logged, force-resolvable `OpenQuestion`, the module drafts its own best-guess
resolution for that condition, states it plainly as an assumption in the baby PRD's
"Assumptions" section (identical surfacing to the C6 case — not silently, not hidden,
tagged with which condition it resolves), and marks that condition's structural check
as satisfied-by-assumption rather than genuinely passed. This is not a new mechanism,
it is the existing one applied without an artificial scope boundary — the round cap's
job was always "guarantee termination in bounded time," and it should do that for the
whole six-condition test, not only for whichever part of it happens to route through
the open-questions ledger.

**Pass condition:** ledger has zero open+load-bearing items, either because they were
genuinely resolved or because the round cap force-resolved them with a visible
assumption; AND, per B2, every condition 1–5 either genuinely passed or was
force-resolved with a visible assumption by round 8. **The round cap is now a true
ceiling on the whole interrogation, not only on condition 6's backlog.**

**Why 8:** arbitrary but bounded; the real acceptance test (task 3, "prove it on a
real greenfield project") is what calibrates this number. Flagging as an open
parameter, not a hard commitment, in this spec.

---

## Cross-condition sequencing note

Conditions are checked every round, not gated in strict 1→6 order — a later question
can resolve an earlier condition's gap opportunistically. But when multiple
conditions are false simultaneously, the module asks toward the LOWEST-numbered false
condition first, matching the PRD's implied priority (outcome and acceptance criteria
are foundational; scope/boundary/context build on them; the open-questions ledger is
the catch-all last check).

---

## Decisions (closed)

1. **Round cap = 8**, kept as the starting default. Calibratable against task 3's real
   greenfield test; not to be hand-tuned blind now.
2. **Judge calls stay per-field, never combined into one holistic call.** The
   reproducibility argument holds. The only relational exceptions are the two Shape 2
   conditions (5, 6) above, and those stay scoped to the specific fields their rubric
   names — never the whole transcript.
3. **Condition 5's explicit-"none" pass is kept as designed.** Forcing a fishing
   expedition on a clean-slate project is worse than accepting a real "none."
4. **Structural heuristics in conditions 1-3 stay illustrative, not hand-tuned now** —
   real tuning deferred to the task-3 greenfield test. Condition 1's pre-filter is
   explicitly advisory-only (see above): it flags, it never hard-blocks the judge call.

No open items remain. Stopping here per instruction — no module code until this
revision is confirmed.
