# context.md

## Current state (single source of 'what's true now')
- Mode: brownfield
- Round reached: 6

## Soft context (boss-said / watch-out / judged-a-failure-if)
- _stated_: Watch-out: loopr-PRD.md section 13 currently claims loopr 'works with zero setup.' This build's own invocation design -- a bundled wrapper script calling a pip-installed loopr package -- means that's no longer literally true; there's now a one-time install step before the skill functions. If this build ships without addressing that inconsistency, it would be judged a failure even if the skill itself works perfectly, because the project's own documentation would still be making a claim the implementation contradicts.
