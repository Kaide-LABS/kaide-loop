# Baby PRD

## TL;DR
A builder using Claude Code can invoke /loopr directly and get the spec-discipline engine's interrogation-through-boundary-and-research-grounded-expansion, plus phase-spec generation, without touching the raw CLI -- so loopr's discipline is one command away instead of requiring manual loopr init/step/emit invocation. -- 2 acceptance criterion(ia), 1 scope edge(s) named.

## Problem statement
A builder using Claude Code can invoke /loopr directly and get the spec-discipline engine's interrogation-through-boundary-and-research-grounded-expansion, plus phase-spec generation, without touching the raw CLI -- so loopr's discipline is one command away instead of requiring manual loopr init/step/emit invocation.

## Acceptance criteria
- Running /loopr inside a target project produces byte-identical baby_prd.md and context.md output to running the raw loopr CLI directly, given the same answers -- a third party can diff the two and confirm zero drift between the packaged skill and the underlying module.
- Running /loopr inside a target project produces baby_prd.md and context.md output that matches byte-for-byte with running the raw loopr CLI directly, given the same answers -- a third party can diff the two and confirm zero drift between the packaged skill and the underlying module.

## Scope edges
- **out**: Gate and subagent generation (the harness-facing half of A5) is out of scope for this build -- that's the interface to the parked Phase B harness (sequencing step 3, Traycer, not yet assessed against the three invariants), and building it now would speculatively couple this skill to a consumer that doesn't exist yet. This build covers A1-A4 plus phase-spec generation only. -- user-stated

## Boundary
This build packages loopr's spec-discipline engine as a Claude Code skill (.claude/skills/loopr/): SKILL.md, references/, assets/, scripts/, per loopr-PRD.md SS9. In scope: A1-A4 (interrogation through boundary confirmation and research-grounded expansion) plus phase-spec generation for target projects. Out of scope: A5's gate/subagent generation (the harness-facing interface to the parked Phase B/Traycer harness). The invocation mechanism is a bundled wrapper script under scripts/ calling the already-installed loopr package, with a preflight check in SKILL.md that fails loudly with the exact install command if loopr isn't importable -- no mid-run discovery. New artifacts from this build are namespaced SKILL_PHASE_1_SPEC.md onward; PHASE_1_SPEC.md, BUILD_COMPLETE.md, and everything already committed for the module build stay untouched.
