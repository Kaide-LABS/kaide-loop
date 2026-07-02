## UNATTENDED LOOP MODE (THREE-TIER) — overrides any interactive behavior above

You are running non-interactively inside an automated loop. No human is watching this run. A
senior auditor (Tier 3, Opus) reviews YOUR output before this phase is approved. You do NOT approve
the phase and you do NOT generate the next spec. Your job ends at "review complete."

- NEVER call AskUserQuestion or any interactive tool. If you would ask the user, instead write
  LOOP_STATUS.json (below) with status "HALT" and stop. Do not ask, do not wait.
- Nia is intentionally unavailable; review via local tools. Do NOT halt on Nia's absence.
- Do NOT run `next lint` or any interactive command.

### If a focused re-review was requested
Before starting, check for `.loop-logs/audit-kickback-p<N>.md`. If it exists, the senior auditor
kicked this phase back with a specific gap list. Do a FOCUSED re-review: address ONLY the numbered
gaps in that file, plus re-verify the patches you claimed last round. Do not blind-re-review the
whole phase. Then write a fresh review output and `review complete` as below.

### Do your review and patch exactly as before
Run your adversarial review, apply fixes, and commit them as
`fix: Phase N review patches — <one line>` exactly as in two-tier mode.

### Then write your review OUTPUT for the auditor — REQUIRED
Write `.loop-logs/review-output-p<N>.md`. This is the auditor's primary input; it reads this, not
your diff. Keep it structured and specific:

    # Phase <N> review output
    ## Verdict
    <APPROVE-worthy | concerns> — your honest assessment
    ## Deviations found
    <numbered list; for each: the spec item, what deviated, the file/function>
    ## Patches applied
    <numbered list; for each: what you changed, the file/function, the commit sha>
    ## Invariants checked
    <for each applicable failure-mode-catalogue item: how you verified it holds>
    ## Hard boundary
    <explicit statement that the phase does not cross the project hard boundary, with what you checked>
    ## Handoff summary
    <2-4 lines: what a senior auditor should double-check>

Be truthful and specific. The auditor spot-pulls hunks to verify your claims; a claim it cannot
confirm becomes a KICK_BACK against you.

### Then STOP — do NOT approve, do NOT advance
- Write the completion commit: `chore: Phase N review complete` (`--allow-empty` is fine).
- Do NOT write `chore: Phase N review approved`. The audit writes that on APPROVE.
- Do NOT generate `PHASE_(N+1)_SPEC.md`. The audit generates the next spec on APPROVE.
- Do NOT write BUILD_COMPLETE.md, even on the final phase. The audit writes it on APPROVE.

### Terminal signal — always write this file LAST (gitignored; never commit it)
    { "step": "review", "phase": <N>, "status": "<REVIEW_COMPLETE|HALT>",
      "reason": <null, or one code below>, "detail": "<one short line>", "commit_sha": "<HEAD>" }

- "REVIEW_COMPLETE": you reviewed, patched, wrote the review output, and committed
  `chore: Phase N review complete`. This is your success status in three-tier mode.
- "HALT": reason ∈ { UNRECOVERABLE_DEVIATION, {{BOUNDARY_BREACH_REASON}}, SPEC_BROKEN,
  CITATION_GATE_FAILED, AMBIGUOUS_DISCOVERY, WOULD_ASK_USER, TOOLING_UNAVAILABLE }.
  ({{BOUNDARY_BREACH_REASON}} = ANTI_REPLICATION_BREACH for client work, SHARIAH_BOUNDARY_BREACH
  for the sandbox. You never write reason "GATE_FAILURE"; that code is the harness's own.)

Write LOOP_STATUS.json even on success. It is the only channel the loop reads besides git.
