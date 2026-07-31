# Conformance classification guide (brownfield only)

Condensed from `docs/conformance-classification-spec.md` (2544 words). Read that for full worked
examples and the research grounding behind each evidence signal. Brownfield-only; unaffected by and
separate from the six-condition stopping test.

## Why this exists

On an existing codebase there are two sources of truth: the confirmed spec, and the patterns already
in the code -- and they can conflict. A model that blindly pattern-matches existing code faithfully
reproduces its mistakes. This mechanism makes that conflict explicit: every pattern the touched
surface implicates gets one of four verdicts, never silently inherited.

**Honest framing:** this is a novel mechanism, not applied validated technique -- no prior art,
labelled dataset, or published baseline exists for convention-vs-cruft discrimination. It's carried
by its human-escalation path (CONFLICT → Gate 3, AMBIGUOUS → open question), not by classifier
accuracy. Never claim otherwise in generated output.

## Touched-surface discovery -- two stages, no new dependency

1. **Cheap pre-filter** (deterministic, free): keyword/dependency-graph search seeded from
   `problem_statement`/`acceptance_criteria`/`scope_edges`. Cast deliberately wide -- this stage
   optimizes recall, not precision.
2. **Relevance judge** (one LLM call, file paths + short summaries only, never full file contents):
   reasons about which pre-filtered candidates are actually relevant, using the model's own language
   understanding as the "semantic" layer.

**Why not Nia or Context7:** researched and rejected, not just skipped. Nia's free tier is limited;
real usage is paid ($50-99+/seat/month) -- breaks the hard no-paid-dependency rule outright. Context7's
indexing backend is a proprietary hosted service (not embeddable) AND indexes public library docs,
not arbitrary private repos -- wrong tool even ignoring licensing. The two-stage design above gets
the same practical benefit (catching relevant-but-differently-worded files) with zero new
service/cost/setup.

The resulting file list is confirmed/adjusted as **an added section of Gate 2**, not a new gate.

## Candidate qualification (structural, no model call)

A pattern qualifies for classification if it's **recurring** (`occurrence_count >= 3` -- twice could
be coincidence, three reads as intentional; confirmed, not a placeholder) OR a **structural
touchpoint** (appears once but the new work must interact with it regardless -- centrality qualifies
instead of count).

## The evidence bundle (per candidate, structural only)

`pattern_id`, `description`, `locations`, `occurrence_count`, `centrality` (core/peripheral),
`git_last_touched_days_ago`, `git_top_author_commit_share`, `git_major_author_count` (commit-based
ownership concentration -- **never `git blame`**, which agrees with commit-based ownership on only
0-40% of developers), `deprecation_markers`, `naming_flags`, `signal_qualifiers` (explicit caveat
text for each weak signal present -- e.g. staleness alone is never sufficient for
DO_NOT_REPLICATE; a deprecation marker may indicate correct "on-hold" debt, not cruft).

## The judge call and four-way verdict

Shape 2: the evidence bundle plus `problem_statement`, `acceptance_criteria`, `scope_edges`,
`boundary` -- never raw code, never other candidates.

- **CONFORM** -- real, current convention: recurring/central, actively maintained, no deprecation
  markers, no conflict with stated intent. Applied silently.
- **DO_NOT_REPLICATE** -- cruft signals (isolated, stale, single-author, deprecation-marked, or
  inconsistent with the dominant approach) AND no conflict with intent. Applied silently (avoided).
  A pattern that is BOTH cruft-shaped and conflicts with intent is CONFLICT, not this.
- **CONFLICT** -- conforming to it, or simply coexisting with it, would make the stated outcome, an
  acceptance criterion, or the boundary NOT hold. Same load-bearing bar condition 6 already uses.
- **AMBIGUOUS** -- evidence signals genuinely conflict with each other, no confident call possible.
  Not a new mechanism: logged as an `OpenQuestion` in condition 6's existing ledger, judged
  load-bearing the normal way, resolved by a follow-up or swept into the round cap. No seventh
  condition.

CONFORM and DO_NOT_REPLICATE write to `conformance-ledger.md`, no gate. CONFLICT verdicts batch into
**Gate 3** -- all conflicts from one pass shown together, one confirmation, not one interrupt per
pattern (the same fatigue mitigation Gate 1/2 already use).

## Gate chronology: Gate 3 before Gate 1

Touched-surface confirmation rides on Gate 2, so classification runs during interrogation, before
the baby PRD is drafted. **Gate 3, when it fires, therefore happens before Gate 1, not after** --
written-up order (1, 2, 3) is not chronological order (2, 3, 1). A CONFLICT can be load-bearing
enough to change an acceptance criterion, so it must resolve before Gate 1's TL;DR is drafted, not
after. Gate 3 correctly never fires if zero patterns reach CONFLICT -- graceful degradation, not a
bug.
