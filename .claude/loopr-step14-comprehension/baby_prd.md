# Baby PRD

## TL;DR
After every phase of any loopr-driven build, I (the operator) can actually explain in plain language
what got built, why the real decisions were made, where the domain-specific judgment calls live, and
where the shipped code diverges from what the spec claimed -- without having read every line myself.
That becomes true for me specifically, running real builds (the motivating case is a Sand FDE artifact
that took three or four hours to ship, fast enough that I lost the thread of what it actually did).
The outcome is comprehension, not documentation for someone else: the faster loopr builds, the more
disconnected I get from what it built, and this closes that gap. A second, equally real outcome:
because explaining a build clearly is itself a check -- you cannot explain what you do not understand
-- a comprehension pass that comes out vague is evidence of a gap every green test suite already
missed, so this becomes a second, independent correctness signal, not just a communication aid. -- 2 acceptance criterion(ia), 1 scope edge(s) named.

## Problem statement
After every phase of any loopr-driven build, I (the operator) can actually explain in plain language
what got built, why the real decisions were made, where the domain-specific judgment calls live, and
where the shipped code diverges from what the spec claimed -- without having read every line myself.
That becomes true for me specifically, running real builds (the motivating case is a Sand FDE artifact
that took three or four hours to ship, fast enough that I lost the thread of what it actually did).
The outcome is comprehension, not documentation for someone else: the faster loopr builds, the more
disconnected I get from what it built, and this closes that gap. A second, equally real outcome:
because explaining a build clearly is itself a check -- you cannot explain what you do not understand
-- a comprehension pass that comes out vague is evidence of a gap every green test suite already
missed, so this becomes a second, independent correctness signal, not just a communication aid.

## Acceptance criteria
- Mechanical checks, third-party runnable:

1. COMPREHENSION.md exists at repo root after every phase, with all six maintained sections
   (plain-language walkthrough, architecture walkthrough, decisions and tradeoffs, domain mechanics,
   honesty audit, open items) and the append-only phase log present.
2. Section 1 (plain-language walkthrough) is genuinely legible to a non-technical reader -- no
   unexplained jargon, no file paths in the prose, no assumed stack knowledge.
3. Section 2 (architecture walkthrough) names real files that actually exist in the repo -- a third
   party can grep every filename mentioned and confirm it resolves.
4. Section 5 (honesty audit) names at least one real gap between spec and shipped code, or explicitly
   states a full comparison was run and found none -- never silence on this section.
5. The maintained sections (1-6) reflect the CURRENT state of the system, not a concatenation of
   previous phases -- verifiable by checking that a decision overturned in a later phase is not still
   stated as current in section 3.
6. The append-only log has exactly one entry per completed phase, and earlier entries are
   byte-identical to when they were originally written -- diffable, not silently edited.
7. Every domain figure (a threshold, statistic, or methodology number) in the file either carries a
   source citation or is explicitly marked as needing verification -- zero unmarked figures stated
   from memory.

A third party could run all seven independently: grep for filenames (3), diff the phase log against
its own git history (6), grep for citation markers or "[UNVERIFIED]"-style tags (7), and read section
5 for an explicit gap-or-none statement (4) without needing to ask the builder what they meant.
- Mechanical checks, third-party runnable:

1. `ls COMPREHENSION.md` shows the file exists at repo root after every phase, and it contains all
   six maintained sections (plain-language walkthrough, architecture walkthrough, decisions and
   tradeoffs, domain mechanics, honesty audit, open items) plus the append-only phase log.
2. Section 1 (plain-language walkthrough) is genuinely legible to a non-technical reader -- no
   unexplained jargon, no file paths in the prose, no assumed stack knowledge.
3. Grep every filename mentioned in section 2 (architecture walkthrough) against the real repo tree --
   each one matches a file that actually exists.
4. Section 5 (honesty audit) contains at least one real named gap between spec and shipped code, or
   explicitly states a full comparison was run and found none -- it never fails to address this at
   all.
5. The maintained sections (1-6) reflect the CURRENT state of the system, not a concatenation of
   previous phases -- checkable because a decision a later phase overturns no longer shows as current
   in section 3.
6. The append-only log contains exactly one entry per completed phase, and diffing an earlier entry
   against its original commit shows it is byte-identical -- it was never silently edited.
7. Every domain figure (a threshold, statistic, or methodology number) in the file either carries a
   source citation or is explicitly marked as needing verification -- a grep for stated figures with
   no adjacent citation or "[UNVERIFIED]" tag returns nothing.

A third party could run all seven independently and reach the same pass/fail without asking the
builder what they meant.

## Scope edges
- **out**: Out of scope for now, deferred, naming concrete boundaries -- including the real structural question
this directive itself asked to have flagged:

- **Whether Step 14 is a separate dispatched subagent or a section inline within step12's own
  prompt -- a proposal, not assumed.** The current template runs PHASE APPROVAL through PHASE
  ADVANCEMENT in one continuous step12 dispatch, ending "Stop after the handoff line. Do not begin
  implementing Phase (N+1)." Inserting a mandatory step between approval and advancement means either
  splitting step12 into two dispatches (approve -> stop -> Step 14 -> something resumes advancement),
  or keeping it a single dispatch with Step 14 as a new section step12 itself executes between its
  own PHASE APPROVAL and PHASE ADVANCEMENT sections. This build's proposed answer, to be confirmed at
  the boundary gate: Step 14 is a SEPARATE subagent (matching its own name and the fact that
  comprehension work wants a fresh, non-adversarial context distinct from step12's red-team posture,
  not step12's leftover mindset), dispatched by the architect/driver immediately after step12 reports
  APPROVED and before PHASE ADVANCEMENT proceeds -- meaning step12's own template needs a real,
  disclosed amendment: stop after approval instead of continuing straight into advancement, so Step 14
  can run in between. If this proposal is rejected, the build stops rather than shipping an
  unconfirmed structural change to how every existing project's step12 already works.
- Retroactive backfill. Projects with phases that already closed before this feature existed (this
  project's own completed CUSTOMIZATION series, its BUILD_COMPLETE.md track) do not get a
  COMPREHENSION.md written for their already-closed phases. Prospective only, starting from the next
  phase closed after this ships.
- Re-litigating PHASE APPROVAL. Step 14 runs strictly after step12 has already approved -- it audits
  and documents, it does not un-approve a phase or add a new veto path. A real gap Step 14 finds goes
  in section 5 (honesty audit) and section 6 (open items), it does not block VERSION CONTROL or
  reverse the approval commit already made.
- loopr dispatch's decide() routing table. Same discipline as the AUDITOR: Step 14 is not a fourth
  target decide() can name. It is architect/driver-dispatched, outside the three-target zero-LLM
  state machine, matching CUSTOMIZATION_PHASE_3_SPEC.md's own G5 guard.
- Audience other than the operator. Section 1's "non-technical reader" bar is about the operator's
  own plain-language comprehension, not a documentation deliverable for external readers, collaborators,
  or a future hire -- explicitly stated in the directive itself.
- New domain-research tooling. Verifying domain figures (rule: no fabricated numbers) reuses the same
  web-search/paper-search/arXiv-MCP capabilities step10 already has, per the same graceful-degradation
  discipline (`docs/mcp-setup.md`) -- this build does not invent a separate research pipeline. -- user-stated

## Boundary
This build adds Step 14 -- a mandatory comprehension pass -- to every loopr-driven build's phase close-out. Proposed structure: a SEPARATE subagent (loopr-step14), dispatched by the architect/driver immediately after step12 reports a phase APPROVED and before PHASE ADVANCEMENT proceeds -- requiring a disclosed amendment to step12's own template so it stops after approval instead of continuing straight into advancement. Step 14 reads the real, current code (never restates the PRD, specs, or the executor's own handoff claims) and writes/maintains COMPREHENSION.md at repo root: six maintained sections rewritten each phase to reflect current truth (plain-language walkthrough, technical architecture walkthrough naming real files, decisions and tradeoffs, domain mechanics, an honesty audit of spec-vs-shipped gaps, and open items), plus an append-only per-phase log preserving history the maintained sections overwrite. Every domain figure must carry a source or be marked needing verification -- no figures stated from memory.

It does not cover: retroactive backfill for phases that already closed before this shipped (prospective only); re-litigating step12's approval (Step 14 documents and audits, it never un-approves a phase or blocks version control -- a real gap it finds goes into the honesty-audit and open-items sections, not a new veto); any change to loopr dispatch's decide() routing table (Step 14 is not a fourth target it can name, same discipline as the AUDITOR); an audience beyond the operator (the plain-language bar is for the operator's own comprehension, not external documentation); and any new domain-research tooling (reuses step10's existing web-search/paper-search/arXiv-MCP capabilities and graceful-degradation discipline, per docs/mcp-setup.md, rather than building a separate pipeline).

The separate-subagent-vs-inline-section structural question is a proposal here, not a settled fact -- if rejected at this gate, the build stops rather than shipping an unconfirmed change to how every existing project's step12 template already works.
