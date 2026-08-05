---
name: loopr
description: Spec a project properly before writing code -- interrogates a problem to a real stopping condition, proposes a boundary, and (on an existing codebase) classifies every touched convention as CONFORM/DO_NOT_REPLICATE/CONFLICT/AMBIGUOUS before any code gets written.
---

# loopr

loopr is a spec-discipline engine. It does not write code. It interrogates you until a real
stopping condition holds, drafts a confirmable baby PRD and `context.md`, and -- on an existing
codebase -- makes an explicit call on every existing pattern your work touches instead of silently
copying it. This skill is a thin orchestration layer over the `loopr` CLI, which already implements
all of this in `src/loopr/`. Nothing here reimplements interrogation, judge calls, or artifact
rendering -- it drives the existing CLI contract (`PHASE_1_SPEC.md` §6.1) faithfully.

Invoke deliberately (`/loopr`), never automatically -- a builder who just wants a quick edit should
never have this triggered on them.

## Preflight (do this first, before anything else)

Before any interrogation logic, confirm `loopr` is importable:

```
python -c "import loopr" 2>&1
```

or, equivalently, call `scripts/loopr_wrapper.py`'s `preflight()`. **If this fails, your entire
response for this invocation is the exact install command below and nothing else** -- no partial
interrogation, no vague "something went wrong." Discover the missing dependency before doing any
real work, not mid-run (the same lesson the abandoned Docker harness's auth-preflight failure
already taught, `loopr-MIGRATION.md` §7, applied to a different failure class here).

```
pip install -e .
```

(run from the kaide-loop repo root; or `pip install loopr` if/once it's published). Note honestly:
loopr's own module requires this one-time install -- see `loopr-PRD.md` §13 for the precise, amended
claim about what is and isn't zero-setup here.

## What you're orchestrating

Everything below is a thin loop over `loopr init` → `loopr step` → `loopr emit`, exactly as
`PHASE_1_SPEC.md` §6.1 already specifies. You (this session) are the invoking agent the module's own
design already assumes -- when `loopr step` returns exit code `10` (`JUDGE_REQUIRED`), you answer the
judge call yourself, honestly, per the rubric in the request envelope. This is not a new design
decision; it's the one `PHASE_1_SPEC.md` §6.2 already made for the standalone module, inherited
unchanged.

### 1. Initialize

```
loopr init --repo <target-project-path> --mode {greenfield,brownfield}
```

State lands under `<target>/.loopr-state/` (gitignored, working state). Nothing else happens yet.

### 2. Drive the interrogation loop

```
loopr step --state <target>/.loopr-state/state.json
```

Each call returns one of five outcomes. Handle exactly what the exit code says, nothing more:

| Exit | Name | What you do |
|---|---|---|
| `10` | `JUDGE_REQUIRED` | Read `pending_judge.json`. Answer its rubric honestly, scoped only to the fields it names -- never smuggle in outside context. Write your verdict to a response file, re-invoke with `--judge-response <file>`. |
| `20` | `GATE_REQUIRED` | Read `pending_gate.md`. This is a human confirm moment (boundary, brownfield conflicts, or the baby PRD TL;DR) -- show it to the user verbatim, get their real confirm/tweak/decline, re-invoke with `--gate-response <file>`. |
| `30` | `QUESTION_REQUIRED` | A targeted follow-up aimed at exactly one failing condition. Relay it to the user, get their real answer, re-invoke with `--answer <file>`. |
| `0` | `OK` | State advanced with nothing pending. Re-invoke `step` immediately. |
| `50` | `COMPLETE` | All six conditions hold. Move to step 3. |

**Every judge call, gate, and question is a real interaction with the user or a rubric-scoped
judgment call you make yourself -- never pre-filled, never faked.** See `references/stopping-test.md`
for what each of the six conditions actually checks, `references/context-md-guide.md` for the
soft-context split (and its relevance check -- confidently-phrased content unrelated to the confirmed
spec gets rejected, not accepted just because it sounds settled), `references/boundary-guide.md` for
how Gate 2's boundary proposal works, and -- brownfield only --
`references/conformance-classification-guide.md` for how existing patterns get classified and how
Gate 3 fires. `references/continuity-model.md` covers how `context.md` stays readable across repeat
runs on the same project.

### 3. Emit

```
loopr emit --state <target>/.loopr-state/state.json
```

Renders `baby_prd.md`, `context.md`, and (brownfield) `conformance-ledger.md` to
`<target>/.claude/loopr/`. Refuses unless all six conditions genuinely pass -- never emit early.

### 4. Customize step 10, step 11, step 12 (optional, once COMPLETE)

```
loopr customize --state <target>/.loopr-state/state.json --step 10
loopr customize --state <target>/.loopr-state/state.json --step 11
loopr customize --state <target>/.loopr-state/state.json --step 12
```

Produces a genuinely customized prompt from the confirmed artifacts -- not a template with
placeholders merely deleted -- and delivers it as a dispatchable subagent:
`<target>/.claude/agents/loopr-step10.md` (Opus), `loopr-step11.md` (Sonnet, low effort),
`loopr-step12.md` (Sonnet, high effort). Handle exit codes the same way as `step`: `10`
`JUDGE_REQUIRED` (answer the customization or fidelity-judgment call honestly, same discipline as any
other judge call, then re-invoke with `--judge-response`), `0` `OK` (done -- the subagent file is at
the printed path, ready to dispatch), `40` `HALT` (the fidelity check rejected the customization, or
-- step11/step12 only -- step10 has not actually *executed* against this project yet: a
fidelity-passing step10 prompt is not the same as having run it, so its real deliverables, a
modernised PRD and `PHASE_1_SPEC.md`, must already exist on disk. A restructured template or generic
filler is likewise a real failure, never silently retried; nothing is ever written to
`.claude/agents/` until it's cleared). step11 and step12 don't depend on each other -- customize
either first, or in parallel. Session topology never matters here: this reads only the state file and
confirmed artifacts, so whether you're the same session that ran the interrogation or a fresh one
makes no difference to the result. Once step10 (at minimum) is customized, step 5 below decides which
customized subagent actually runs next.

### 5. Dispatch -- decide which subagent runs next (optional, once at least step10 is customized)

```
loopr dispatch --state <target>/.loopr-state/state.json [--json] [--dry-run] [--remodernize]
```

A deterministic controller, not a judgment call -- it reads three persisted state fields plus two
live disk facts and names exactly one of `loopr-step10`, `loopr-step11`, or `loopr-step12` to run
next, or reports the build is already complete. Zero LLM calls, zero heuristics: this is the same
class of mechanism as the six-condition test's *structural* layer, never its judge layer, so there is
nothing here for you to answer or adjudicate. Print the human block verbatim to the user and dispatch
whatever it names -- do not re-derive the decision yourself, and do not second-guess a HALT by
dispatching `loopr-step10` anyway "to be safe": an unrecognised or incoherent state HALTs by design
(`loopr-PRD.md` section 6 B6, PROJECT HARD BOUNDARY) and printing the state for a human to look at is
the correct behaviour, not a gap to route around.

| Exit | Name | What you do |
|---|---|---|
| `0` | `OK` | A subagent was named and the state was updated. Dispatch the printed `Task(...)` line. |
| `50` | `COMPLETE` | `BUILD_COMPLETE.md` exists; nothing left to dispatch. |
| `40` | `HALT` | The state is incoherent. Show the printed block to the user; do not dispatch anything, especially not `loopr-step10`. |
| `2` | `USAGE` | `--remodernize` was given while a step was already in flight. |

After the dispatched subagent finishes, record it:

```
loopr dispatch-complete --state <target>/.loopr-state/state.json [--verdict {clean,minor,spec_violating}]
```

`--verdict` is required when the completed step was `loopr-step12` and forbidden otherwise -- never
default it; a defaulted verdict fabricates a review outcome that did not happen. Two more commands
exist for auditing, not for the normal loop: `loopr dispatch-verify --fixtures <dir>` re-runs the
fixture suite as a single pass/fail command, and `loopr dispatch-audit --log <path>` greps the
append-only dispatch log for every `loopr-step10` call and fails if any lacks a real warrant.

### Optional: verify reproducibility

```
loopr replay --state <state-file> --fixtures <dir>
```

Re-runs every logged judge call against a scripted fixture set and reports divergence. Useful for
auditing a completed run; not part of the normal interrogation loop.

## What this build does not do

Gate and subagent generation (the harness-facing half of the module's A5 capability) is explicitly
out of scope for this skill -- that's the interface to the parked Phase B harness (Traycer,
unassessed), and this skill does not speculatively couple to a consumer that doesn't exist yet. This
skill stops at phase-spec generation for the target project; it does not scaffold `.claude/agents/`
or `loop.gates.sh` for that project.
