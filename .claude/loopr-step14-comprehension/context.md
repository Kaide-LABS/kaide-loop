# context.md

## Current state (single source of 'what's true now')
- Mode: brownfield
- Round reached: 6

## Soft context (boss-said / watch-out / judged-a-failure-if)
- _stated_: Real soft context, not a clean slate:

1. The directive's own premise cuts both ways: "a comprehension pass that comes out vague is evidence
of a gap" -- but Step 14 itself could produce vague, generic prose (the exact failure this whole
project has repeatedly guarded against, e.g. "the system processes the data" instead of naming real
files) while still technically satisfying criterion 1 (all six sections present). A phase that gets a
technically-complete but generic COMPREHENSION.md has failed the actual purpose even though every
acceptance criterion superficially passes. Judged a failure even if criteria pass: if section 1 or 2
could be true of any project, not this one specifically.

2. The user named domain-figure fabrication as "the failure mode I care most about... the one that
would do the most damage if this artifact reaches an outside reader" -- stated even though the
confirmed scope restricts the audience to the operator only. The risk matters regardless of the
audience scope, because the stated motivating case (a Sand FDE artifact) implies this file could
plausibly leave the operator's hands later even though building it FOR external readers is out of
scope. Treat criterion 7 (every domain figure sourced or marked unverified) as load-bearing, not a
formality.

3. A real cost/latency tradeoff from the confirmed structural choice: a separate, fresh-context
subagent dispatched after every single phase means a full independent code-comprehension pass gets
paid for every phase, not once at the end -- on a multi-phase build this compounds. This is the
correct tradeoff for honesty (a fresh reader can't inherit the executor's or reviewer's
rationalizations), but it is a real, disclosed cost, not a free feature.

4. Because Step 14 runs fresh each time with no memory of prior phases, it must read the EXISTING
COMPREHENSION.md's append-only log section before writing anything, specifically to avoid touching
prior entries -- criterion 6 (earlier entries byte-identical) is not automatically satisfied just
because the maintained sections get correctly rewritten; it requires the fresh subagent to actively
preserve what it didn't write.
