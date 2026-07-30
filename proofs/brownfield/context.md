# context.md

## Current state (single source of 'what's true now')
- Mode: brownfield
- Round reached: 11

## Soft context (boss-said / watch-out / judged-a-failure-if)
- _stated_: This phase modifies loopr's own C2 acceptance-criteria gate -- adding vagueness detection for unfalsifiable qualifiers ('correctly,' 'properly,' 'works well,' 'as expected') with no named comparison target in the same answer, triggering a follow-up question rather than an auto-rewrite. Scope: C2 only, not C1/C3/C4/C5. No semantic/LLM-based falsifiability judgment, fixed keyword-pattern check only.

Review this harder than the diff size suggests. This is loopr checking loopr -- a silent bug here doesn't just break one feature, it weakens the mechanism meant to catch bugs everywhere else, invisibly, so correct-but-fragile costs more here than elsewhere.

Specifically verify:
1. False positives: an answer with a qualifier AND a comparison target elsewhere in the same answer (not necessarily the same sentence) -- e.g. 'this works well; specifically it matches the human-marked reference within tolerance' -- must NOT trigger the follow-up.
2. False negatives: vague phrasing not on the fixed keyword list (e.g. 'behaves as intended') will not be caught by design (out of scope per C3) -- confirm this limitation is real and not silently different from what's documented, not that it's fixed.
3. The new code follows the existing @dataclass convention on this touched surface -- confirm it actually conforms, don't just take it on trust.
4. Per-list, not per-criterion: C2's existing design passes once ONE criterion clears both layers -- "the rest can remain weaker" (docs/stopping-test-spec.md). Confirm the new follow-up only fires when the list has zero criteria passing both layers cleanly, not merely because one weaker criterion in an otherwise-passing list looks vague. A version that nags on every vague criterion regardless of list state is a regression against the already-decided per-list pass condition, not a stricter version of it.

Flag anything that fails these four checks before approving the phase.
- _stated_: Not a clean slate. This is personal use only -- not for MSA, not shared, no audience beyond me, so drop any framing tied to leadership position or public stakes.

One real soft-context item, unchanged from before: output register has to match the seriousness of religious content. A summary can pass every hard check in the correctness boundary -- segmented correctly, ruling attributed as reported speech, citation verbatim, ambiguity flagged -- and still fail if a hukm is rendered in phrasing that trivializes it. That's true even for an audience of one; it's about the summary being a faithful record of something I'm treating as religiously serious, not about who else reads it.
- _stated_: Not a clean slate. This is personal use only -- not for MSA, not shared, no audience beyond me, so drop any framing tied to leadership position or public stakes.

One real soft-context item, unchanged from before: output register has to match the seriousness of religious content. A summary can pass every hard check in the correctness boundary -- segmented correctly, ruling attributed as reported speech, citation verbatim, ambiguity flagged -- and still fail if a hukm is rendered in phrasing that trivializes it. That's true even for an audience of one; it's about the summary being a faithful record of something I'm treating as religiously serious, not about who else reads it.
- _stated_: Confirmed: the core boundary excludes speech-to-text. loopr's target is transcript-in -> structured-summary-out only, fed by a saved transcript file. STT and Zoom integration (bot admission, audio capture, the STT API call, auth) are outside loopr's scope entirely -- normal plumbing, built separately, bolted on after the core is proven. Do not fold STT into the core or into loopr's proving run. Proceed on that basis -- this is confirmed, not open.
- _stated_: This specific change gets reviewed harder than its diff size suggests: a silent bug in loopr's own C2 gate wouldn't just break this one feature, it would degrade every future interrogation loopr runs afterward, invisibly. That's the standard this diff should be judged against.
