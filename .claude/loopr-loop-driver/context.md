# context.md

## Current state (single source of 'what's true now')
- Mode: brownfield
- Round reached: 5

## Soft context (boss-said / watch-out / judged-a-failure-if)
- _stated_: Real soft context, not a clean slate:

Two watch-outs, both about what a green test suite can't see:

1. Same shape as every automation built today (dispatch's own G6, the AUDITOR's dogfood-legibility
concern, step12's anti-hedging guard): the asymmetry between under- and over-automating is not
symmetric in cost. A driver that stops too often (false-positive escalations to a human) is merely
annoying. A driver that proceeds when it should have stopped -- silently missing a genuine step12
UNCERTAIN item because its parsing of step12's output was slightly off, for instance -- is a much
worse failure, because the whole point of today's PER-ITEM VERDICT TRACKING and auditor-escalation
work was to make sure genuine uncertainty gets a second look, not get silently swallowed by
automation built to reduce friction. Judged a failure even if every acceptance criterion passes on
the tested scenarios: if a real run shows the driver ever proceeding past something a human should
have seen.

2. A real, non-hypothetical risk specific to this build: unlike a pure decision function like
decide() (which has no side effects to compound), the subagents this driver dispatches take real
actions -- they write files and make git commits, per their own prompts. A driver bug that misreads
an exit code or fails to detect COMPLETE correctly would not fail cheaply; it would repeat those real
side effects. This is worth designing against, though how exactly is an implementation decision for
the build itself, not something to prescribe here.
