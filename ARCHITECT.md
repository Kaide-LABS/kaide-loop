# ARCHITECT.md

This is kaide-loop's own orientation file, read automatically by the `loopr` skill's "Session role"
step whenever `/loopr` is invoked in this repo (see `.claude/skills/loopr/SKILL.md`). The generic
architect-role definition lives there now, not here -- this file carries only what's specific to
*this* project: where to pick up current status, and constraints this project has already learned
the hard way. If this file starts accumulating history instead of pointers, that's a bug in the
file, not a feature.

## Where to pick up context

1. **`CUSTOMIZATION_BUILD_COMPLETE.md`** (if present) — whether the customization-layer series
   (step10/11/12 automation + dispatch controller) is done, and what's still open. As of the last
   update: all 3 phases shipped and approved; one disclosed open item (criterion 9, dogfood
   legibility of `loopr dispatch` — unverified until someone actually runs it for real).
2. **`loopr-PRD.md` §12** (explicitly out of v1) and **§15** (open decisions) — what's deliberately
   deferred and what's still genuinely unresolved.
3. **`.claude/loopr/`** (`baby_prd.md`, `context.md`, `conformance-ledger.md`) — if present, these are
   the confirmed artifacts from the most recent `/loopr` interrogation run. Read them before assuming
   you know the current scope; a stale assumption here is worse than not knowing.
4. **`docs/loopr-v2-agent-archetypes.md`** — forward spec only (ARCHITECT/EXECUTOR/REVIEWER/AUDITOR
   archetypes, multi-loopr). Not built, not in scope, unless explicitly revived.

## Standing constraints for this project (apply regardless of what you're working on)

- No paid dependency, ever. This has already driven multiple rejected approaches (Nia, Context7) —
  check `loopr-PRD.md` §8 before proposing an external service.
- Commits stay neutral: no AI attribution, no Co-Authored-By, no "Generated with" lines.
- Disclosed amendments, never silent rewrites, to anything already confirmed or shipped — but keep
  the disclosure itself short (2026-08-06: this had been ballooning into multi-paragraph essays per
  fix; a sentence or two plus a pointer to where the real detail lives is enough).
- Verify against the real file or the real command output before reporting something as true —
  a prior report, a docstring, or your own memory of an earlier session is not verification.
- Primary vs secondary work is classified by the architect, not asked about — see
  `.claude/skills/loopr/SKILL.md`'s "Primary vs secondary work" section. Secondary (directive-shaped)
  work gets dispatched to a subagent directly, no pre-dispatch confirmation round-trip.

## FIRST MOVE

Check whether `CUSTOMIZATION_BUILD_COMPLETE.md` exists and what it says is still open. Check
`loopr-PRD.md` §15 for open decisions. Then ask the operator what they want to work on — do not
assume, and do not start writing code before scope is confirmed (via `/loopr` if the work is new,
substantive, or touches an existing convention).
