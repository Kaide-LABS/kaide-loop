# Baby PRD

## TL;DR
I (the operator) can kick off a build and have it run through step10, then repeated step11/step12
rounds, escalating to the auditor when step12 flags something, all the way to
CUSTOMIZATION_BUILD_COMPLETE.md, without personally running loopr dispatch, reading its decision,
dispatching the named subagent, and running loopr dispatch-complete by hand for every single step --
which is exactly what I did manually, over and over, all session today. That becomes true for me
specifically, running this on real builds, not a hypothetical future user. The outcome: what took
dozens of manual command-and-dispatch round trips today becomes one kickoff, with me only stepping in
when a real gate/judgment call genuinely needs a human (a Gate 1/2/3 confirm, or a HALT). -- 1 acceptance criterion(ia), 1 scope edge(s) named.

## Problem statement
I (the operator) can kick off a build and have it run through step10, then repeated step11/step12
rounds, escalating to the auditor when step12 flags something, all the way to
CUSTOMIZATION_BUILD_COMPLETE.md, without personally running loopr dispatch, reading its decision,
dispatching the named subagent, and running loopr dispatch-complete by hand for every single step --
which is exactly what I did manually, over and over, all session today. That becomes true for me
specifically, running this on real builds, not a hypothetical future user. The outcome: what took
dozens of manual command-and-dispatch round trips today becomes one kickoff, with me only stepping in
when a real gate/judgment call genuinely needs a human (a Gate 1/2/3 confirm, or a HALT).

## Acceptance criteria
- Mechanical checks, third-party runnable:

1. Kick off the driver against a real (or realistic fixture) multi-round build and observe it
   running loopr dispatch -> dispatch the named subagent -> loopr dispatch-complete cycles back to
   back with no manual command between them -- confirmed by a driver-level log (separate from
   dispatch-log.jsonl and auditor-log.jsonl, since those are what dispatch and the auditor already
   write) showing consecutive timestamped entries with no human-authored command in between.
2. Confirm the driver stops and surfaces to a human -- never silently proceeds -- on exactly three
   real events: a `loopr dispatch` `HALT` (exit 40), any judge/gate/question moment inside a
   dispatched subagent's own run that genuinely needs a human, and a step12 escalation-eligible
   UNCERTAIN item (per today's PER-ITEM VERDICT TRACKING). The driver automates the mechanical
   round-trip only, never a judgment call -- if it ever answers a gate or judge call itself, that is
   a failure regardless of whether the answer happened to be right.
3. Confirm the driver dispatches `loopr-auditor` correctly when step12 produces a real UNCERTAIN
   item, using the exact extraction convention SKILL.md step 6 already documents -- not a
   reimplementation, the same one used by hand today.
4. Confirm the driver itself makes zero LLM calls and contains zero heuristics in its own control
   flow -- it only ever calls the existing `loopr dispatch`/`dispatch-complete` CLI and reads their
   exit codes, the same zero-judgment discipline `decide()` itself already holds. Grep the driver's
   own code/script for the absence of any judgment logic.
5. Run it for real, end to end, on an actual (even if small) multi-round scenario, and count how many
   manual interventions occurred versus how many dispatch/dispatch-complete cycles ran on their own --
   a third party could recount this from the driver log alone, without asking me.

A third party could run all five independently and reach the same pass/fail.

## Scope edges
- **out**: Out of scope for now, deferred -- naming the real architecture call explicitly rather than silently
picking a side:

- **Traycer.** This build's proposed answer -- to be confirmed explicitly at the boundary gate, not
  assumed -- is that Traycer is NOT adopted for this driver. docs/loopr-v2-agent-archetypes.md's own
  "Not in scope" section already argues native Claude Code subagents provide the context isolation
  this needs, and today's entire session is live proof: loopr-step10/11/12 and loopr-auditor were all
  dispatched successfully via the Agent tool, by hand, dozens of times. This is a disclosed deviation
  from loopr-PRD.md section 14 point 4's literal locked sequencing (which names "assess Traycer" as
  Phase B's first task) -- the same kind of deliberate, disclosed deviation already made once today
  for the AUDITOR build, not a silent reinterpretation. If the boundary gate rejects this proposal,
  the build stops here rather than proceeding on an unconfirmed architecture choice.
- Cross-provider / multi-agent-framework orchestration. Native subagents are Claude-Code-specific;
  multi-loopr's cross-provider ambitions (loopr-PRD.md section 12, docs/loopr-v2-agent-archetypes.md)
  stay exactly as deferred as they already were.
- The driver answering judge calls, gates, or questions itself. It automates only the mechanical
  dispatch -> subagent -> dispatch-complete round trip; every genuine judgment moment still stops and
  surfaces to a human, same as today's manual process -- the driver removes repetitive plumbing, not
  human judgment.
- A rework-cap / retry-limit policy for step11<->step12 ping-pong -- still the same open item named
  in loopr-PRD.md section 15, not resolved by this build either.
- Any change to `loopr dispatch`'s own `decide()` function or `DispatchState` -- the driver is a
  caller of the existing CLI, not a modification to it. -- user-stated

## Boundary
This build automates the mechanical loop the operator has been running by hand all session: kick off once, and a driver repeatedly calls loopr dispatch, dispatches the named subagent (loopr-step10/11/12, and loopr-auditor on a step12 escalation) via the Agent tool, and calls loopr dispatch-complete, cycling until dispatch reports COMPLETE. It stops and surfaces to a human on exactly three events: a loopr dispatch HALT, any genuine judge/gate/question moment inside a dispatched subagent's own run, or a step12 UNCERTAIN escalation candidate -- it never answers those itself, only removes the repetitive command-and-dispatch plumbing between them.

Proposed, not assumed: this build does NOT adopt Traycer. It uses native Claude Code subagents for the same reasoning docs/loopr-v2-agent-archetypes.md's own 'Not in scope' section already gives, and today's session is live proof they work for this. This is a disclosed deviation from loopr-PRD.md section 14 point 4's literal locked sequencing (which names assessing Traycer as Phase B's first task) -- the same kind of deliberate, disclosed deviation already made once today for the AUDITOR build. If this proposal is rejected at this gate, the build stops rather than proceeding on an unconfirmed architecture choice.

It does not cover: cross-provider or multi-agent-framework orchestration (multi-loopr's cross-provider ambitions stay exactly as deferred as before); the driver answering judge calls, gates, or questions itself; a rework-cap/retry-limit policy for step11-step12 ping-pong (still the same open item in loopr-PRD.md section 15); and any change to loopr dispatch's own decide() function or DispatchState -- the driver is a caller of the existing CLI, not a modification to it.
