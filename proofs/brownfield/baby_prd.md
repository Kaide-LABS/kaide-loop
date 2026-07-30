# Baby PRD

## TL;DR
A solo builder running loopr alone, with no second reviewer, never advances past condition 2 with an acceptance criterion that turns out -- later, expensively -- to have been unfalsifiable. The vague answer gets caught at the moment it's typed, not discovered during review, not discovered in production. -- 2 acceptance criterion(ia), 1 scope edge(s) named.

## Problem statement
A solo builder running loopr alone, with no second reviewer, never advances past condition 2 with an acceptance criterion that turns out -- later, expensively -- to have been unfalsifiable. The vague answer gets caught at the moment it's typed, not discovered during review, not discovered in production.

## Acceptance criteria
- A third party could check it with a labeled test batch: a set of C2 answers, some genuinely falsifiable (e.g. the corrected segmentation criterion -- 'matches an independently human-marked reference within tolerance') and some deliberately vague (e.g. the original 'correctly segments the topics discussed'). The check is observable and binary: for every answer in the batch, does loopr's gate accept it only if it names a concrete comparison target -- a reference output, a specific human judgment call, or a measurable threshold -- and does it ask a follow-up on every answer that only asserts a quality word ('correctly,' 'works,' 'properly') with nothing to check it against? Pass means it gets this right across the whole batch, not just on the one case that happened to trip it in this conversation.
- This phase modifies loopr's own C2 acceptance-criteria gate -- adding vagueness detection for unfalsifiable qualifiers ('correctly,' 'properly,' 'works well,' 'as expected') with no named comparison target in the same answer, triggering a follow-up question rather than an auto-rewrite. Scope: C2 only, not C1/C3/C4/C5. No semantic/LLM-based falsifiability judgment, fixed keyword-pattern check only.

Review this harder than the diff size suggests. This is loopr checking loopr -- a silent bug here doesn't just break one feature, it weakens the mechanism meant to catch bugs everywhere else, invisibly, so correct-but-fragile costs more here than elsewhere.

Specifically verify:
1. False positives: an answer with a qualifier AND a comparison target elsewhere in the same answer (not necessarily the same sentence) -- e.g. 'this works well; specifically it matches the human-marked reference within tolerance' -- must NOT trigger the follow-up.
2. False negatives: vague phrasing not on the fixed keyword list (e.g. 'behaves as intended') will not be caught by design (out of scope per C3) -- confirm this limitation is real and not silently different from what's documented, not that it's fixed.
3. The new code follows the existing @dataclass convention on this touched surface -- confirm it actually conforms, don't just take it on trust.
4. Per-list, not per-criterion: C2's existing design passes once ONE criterion clears both layers -- "the rest can remain weaker" (docs/stopping-test-spec.md). Confirm the new follow-up only fires when the list has zero criteria passing both layers cleanly, not merely because one weaker criterion in an otherwise-passing list looks vague. A version that nags on every vague criterion regardless of list state is a regression against the already-decided per-list pass condition, not a stricter version of it.

Flag anything that fails these four checks before approving the phase.

## Scope edges
- **out**: Out of scope for now: this catches vague acceptance criteria in condition 2 only -- C1, C3, C4, and C5 answers aren't checked for the same pattern yet, even though they could suffer from it too. Also out of scope: it flags the vague answer and asks a follow-up; it does not attempt to auto-generate or auto-rewrite a corrected criterion for you. And detection starts as a fixed pattern/keyword check (a list of unfalsifiable qualifiers -- 'correctly,' 'properly,' 'works well,' 'as expected' -- with no named comparison target in the same sentence), not a full semantic judgment of whether an answer is *actually* falsifiable beyond that pattern. That more general version is deferred. -- user-stated

## Boundary
This change adds vagueness-detection to loopr's own C2 acceptance-criteria gate only -- a fixed keyword-pattern check for unfalsifiable qualifiers ("correctly," "properly," "works well," "as expected") with no named comparison target in the same answer, triggering a follow-up question rather than an auto-rewrite. C1, C3, C4, and C5 are not touched. No semantic/LLM-based falsifiability judgment beyond the fixed pattern is in scope.
