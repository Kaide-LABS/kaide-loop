# Baby PRD

## TL;DR
Automate the spec-driven loop I currently run manually via the step 10, 11, and 12 prompts.
Right now I have to paste the step 10 prompt into a separate architect session by hand each time,
customized for whatever project I'm working on, then paste step 11 and step 12 in turn. I want that
automated -- invoked through the skill directly, instead of manually copying prompts between
sessions. -- 1 acceptance criterion(ia), 1 scope edge(s) named.

## Problem statement
Automate the spec-driven loop I currently run manually via the step 10, 11, and 12 prompts.
Right now I have to paste the step 10 prompt into a separate architect session by hand each time,
customized for whatever project I'm working on, then paste step 11 and step 12 in turn. I want that
automated -- invoked through the skill directly, instead of manually copying prompts between
sessions.

## Acceptance criteria
- If the loop kicks off and runs end-to-end -- executing the spec-driven build across all the phases
that were specced out in the PRD, with each phase actually getting built according to what the spec
outlined -- then that's how you'd know it worked. Not a feeling, an observable run: it starts, it
processes phase after phase per the spec, and it completes.

## Scope edges
- **out**: Both native Claude Code subagents and a Traycer-based harness are out of scope for this build.
Traycer is explicitly parked (locked sequencing step 3, still unassessed against the three
invariants), and native subagents were explored but demoted to a non-locked idea. This build only
automates producing the same prompt-file artifacts (step10/11/12-style) already used manually -- not
either heavier execution mechanism. -- user-stated

## Boundary
This build automates the customization and sequencing of the step10/11/12 prompt-file workflow -- given a project's confirmed spec context, it produces the customized step10 (PRD modernization + phase-spec generation), step11 (build), and step12 (QA review + next-phase-spec) prompts, and drives their execution end-to-end without the user manually pasting each one into a separate session. It does not build or invoke native Claude Code subagents, and it does not adapt or integrate Traycer -- both remain parked, unassessed mechanisms outside this build's scope. Success is observable: the loop runs and executes the spec-driven build across every phase specced in the target project's PRD, to completion.
