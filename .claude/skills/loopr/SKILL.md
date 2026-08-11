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

## Session role (read this first, before Preflight)

Invoking this skill makes this session the **architect** for whatever it's about to work on: it
produces specs, directives, and reviews (via the interrogation loop below), and independently
verifies what comes back. It does **not** write the target project's own application code directly
-- that happens via a dispatched subagent (the Agent tool's `Task(...)`), never a separate manual
session/tab. This is an operator convention this skill documents for the session's own orientation,
not something the module's code enforces or knows about -- `src/loopr/` never branches on session
identity or role, and nothing in this convention should ever be threaded into a judge call's inputs.
**[AMENDED 2026-08-06]** Earlier guidance here named "a separate executor session" as the default
handoff -- superseded now that native subagent dispatch is available in-session: draft the directive,
then dispatch it directly via `Task(...)`, don't print it for the operator to relay by hand.

### Primary vs secondary work

Every request this session takes on is one or the other -- classify it yourself, it is a judgment
call, not a mechanical rule (`docs/loopr-v2-agent-archetypes.md`'s own two-orchestration-mode split,
made concrete here):

- **Primary** -- a new feature or a change significant enough that scope, boundary, or an existing
  convention genuinely needs confirming. Run it through the full interrogation loop below (step 2),
  confirm the real gates with the operator, then hand the confirmed build to the phased step10/11/12
  loop (dispatched by hand per step 5, or automated per step 7's driver, once customized).
- **Secondary** -- a directive-shaped fix, small enough that the scope is already clear from the
  request itself (a bug found and diagnosed, a small correction, a follow-up). Draft the directive,
  then **dispatch it directly to a subagent via `Task(...)` -- do not stop to ask the operator "how do
  you want to handle this" first.** The operator has said, explicitly, that this back-and-forth is
  friction they want removed by default. Independently re-verify the subagent's result afterward (the
  standard applies unchanged) -- this rule removes the *pre*-dispatch confirmation step, not the
  post-dispatch verification discipline.
  - If a secondary task needs more than one directive in a row (a debug trail where directive 3
    depends on what directive 1 surfaced), **continue the same subagent via `SendMessage` to its
    agent ID rather than spawning a fresh one each time** -- this is what makes secondary mode's
    original "one long-lived executor" design (`docs/loopr-v2-agent-archetypes.md`) work without a
    manual copy-paste tab: cumulative context lives in the continued subagent, not in the operator's
    clipboard.
  - This does not override the "Executing actions with care" judgment in the system prompt --
    destructive, hard-to-reverse, or genuinely ambiguous actions still warrant a real check-in
    regardless of primary/secondary classification. The rule removes reflexive
    permission-seeking for ordinary directive-shaped work, not judgment about real risk.

Before Preflight: check whether the target project has its own root-level orientation file (commonly
`ARCHITECT.md`, but the project may name it differently -- look for one before assuming there isn't
one). If it exists, read it fully before anything else; it carries this specific project's own
status pointers (what's built, what's open) that this skill has no way to know generically. If it
doesn't exist, proceed to Preflight directly -- its absence is not an error, just a project that
hasn't set one up.

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

**Cross-project collision guard.** A repo can host more than one concurrently-tracked
`--state` file writing to the same output directory by design (this repo does). `emit` refuses
instead of silently overwriting: it writes a sidecar marker, `.emitted_from.json`, into the output
directory alongside the rendered artifacts, recording which `--state` file's (resolved) path last
emitted there. The next `emit` into that directory checks the marker first -- same `--state` path
(the normal case: re-emitting after a gate got revised) proceeds and refreshes the marker; no
marker yet (first-ever emit into that directory) proceeds and writes one; a *different* `--state`
path refuses outright with `HALT`, printing both state paths and both problem statements to
stderr and pointing at `--out <dir>` to target somewhere else. If you see that refusal, do not
retry the same command -- pick a distinct `--out` directory per project instead.

### 4. Customize step 10, step 11, step 12, step 14 (optional, once COMPLETE)

```
loopr customize --state <target>/.loopr-state/state.json --step 10
loopr customize --state <target>/.loopr-state/state.json --step 11
loopr customize --state <target>/.loopr-state/state.json --step 12
loopr customize --state <target>/.loopr-state/state.json --step 14
```

Produces a genuinely customized prompt from the confirmed artifacts -- not a template with
placeholders merely deleted -- and delivers it as a dispatchable subagent:
`<target>/.claude/agents/loopr-step10.md` (Opus), `loopr-step11.md` (Sonnet, low effort),
`loopr-step12.md` (Sonnet, high effort), `loopr-step14.md` (Sonnet, medium effort -- the mandatory
comprehension pass, `.claude/loopr-step14-comprehension/baby_prd.md`; dispatched as a SEPARATE
subagent from step12, never a fourth `loopr dispatch` target, see step 7's own note on this). Handle
exit codes the same way as `step`: `10` `JUDGE_REQUIRED` (answer the customization or
fidelity-judgment call honestly, same discipline as any other judge call, then re-invoke with
`--judge-response`), `0` `OK` (done -- the subagent file is at the printed path, ready to dispatch),
`40` `HALT` (the fidelity check rejected the customization, or -- step11/step12/step14 only -- step10
has not actually *executed* against this project yet: a fidelity-passing step10 prompt is not the same
as having run it, so its real deliverables, a modernised PRD and `PHASE_1_SPEC.md`, must already exist
on disk. A restructured template or generic filler is likewise a real failure, never silently retried;
nothing is ever written to `.claude/agents/` until it's cleared). step11, step12, and step14 don't
depend on each other -- customize any of them first, or in parallel; all three gate only on step10's
own real execution artifacts. Session topology never matters here: this reads only the state file and
confirmed artifacts, so whether you're the same session that ran the interrogation or a fresh one
makes no difference to the result. Once step10 (at minimum) is customized, step 5 below decides which
customized subagent actually runs next -- step14 is never one of the names it can return; see step 7.

### 5. Dispatch -- decide which subagent runs next (optional, once at least step10 is customized)

```
loopr dispatch --state <target>/.loopr-state/state.json [--json] [--dry-run] [--remodernize]
                [--modernized-prd-path PATH] [--phase-1-spec-path PATH] [--build-complete-path PATH]
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

`loopr-step12` can be named here TWICE for the same phase before this controller moves on -- a REVIEW
sub-dispatch (approves, then stops) and, after you dispatch `loopr-step14` yourself in between, an
ADVANCEMENT-ONLY sub-dispatch (drafts the next spec). `decide()` cannot tell these apart; it only
sees `active_step=STEP_12` both times. Step 7's driver automates recognising which is which from each
sub-dispatch's own HANDOFF FORMAT and dispatching Step 14 between them -- if you are driving this
manually rather than via step 7, apply that same sequencing by hand: never call `dispatch-complete
--verdict clean/minor` until AFTER the ADVANCEMENT-ONLY sub-dispatch, with `loopr-step14` dispatched
and its own real output read in between.

`--modernized-prd-path` / `--phase-1-spec-path` (same override flags `customize --step 11/12` has):
a mature repo can legitimately carry more than one valid phase-spec artifact permanently (this
project's own repo does), and `dispatch`'s step10-artifact detection HALTs rather than guess which
one applies. If it does, point it at the right file directly with these flags instead of moving or
deleting the other one.

`--build-complete-path`: a repo can also host more than one loopr-managed build, each with its own
completion marker (this repo does: `BUILD_COMPLETE.md` for the base module,
`CUSTOMIZATION_BUILD_COMPLETE.md` for this series) -- `dispatch` otherwise checks the hardcoded
`BUILD_COMPLETE.md`, which may belong to a different project than the one `--state` tracks. Point
this at the marker your `--state` file's project actually uses; unlike the two flags above, a path
that does not exist yet is a normal answer here (the project is simply still mid-build), not an
error.

| Exit | Name | What you do |
|---|---|---|
| `0` | `OK` | A subagent was named and the state was updated. Dispatch the printed `Task(...)` line. |
| `50` | `COMPLETE` | `BUILD_COMPLETE.md` exists; nothing left to dispatch. |
| `40` | `HALT` | The state is incoherent, or step10's real artifacts are ambiguous on disk. Show the printed block to the user; if it's the artifact ambiguity, resolve with `--modernized-prd-path`/`--phase-1-spec-path`; otherwise do not dispatch anything, especially not `loopr-step10`. |
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

### 6. Escalate to the AUDITOR (optional, once step12 has flagged something)

Not part of `loopr dispatch`'s routing table -- `decide()` stays a deterministic, zero-LLM state
machine with exactly three targets (`loopr-step10`/`loopr-step11`/`loopr-step12`); the auditor is
never a fourth thing it can name, and neither is `loopr-step14` (step 7 below covers Step 14's own,
unrelated dispatch). This is a separate, architect-initiated act, only ever taken after
`loopr-step12` has already run and flagged a specific item as `UNCERTAIN` (confidence below
threshold) or as touching a correctness-critical path regardless of confidence.

Do not conflate the auditor with Step 14: the auditor adjudicates a single flagged item on the
architect's own initiative, optional, and only ever engaged mid-review; Step 14 is mandatory,
dispatched by the architect/driver after EVERY step12 APPROVED completion (never mid-review, never
optional), and produces `COMPREHENSION.md`, not a verdict on one item. Both are separate subagents
outside `decide()`'s three-target state machine, but for otherwise-unrelated reasons.

**You (the architect), not step12, decide to dispatch.** Never let step12 self-escalate -- a
confidently-wrong reviewer will not recognise it needs help, which is exactly when help is needed.
Extract the one flagged item's spec clause, file/line reference, and step12's written reason (never
just its confidence number), and dispatch `Task(subagent_type="loopr-auditor")` with exactly that --
never the full diff, never the rest of the review.

When the auditor returns its `VERDICT`/`REASON`/`GUIDANCE` block, append it to this project's
escalation log before relaying anything back to step12 -- the log is what makes the escalation a
real audit trail instead of an off-the-record exchange between subagents:

```python
import json
from datetime import UTC, datetime
from pathlib import Path

entry = {
    "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "item": "<the flagged item's spec clause / file:line>",
    "verdict": "<CONFIRMED_VIOLATION | FALSE_ALARM | GENUINELY_AMBIGUOUS>",
    "reason": "<the auditor's REASON>",
    "guidance": "<the auditor's GUIDANCE>",
}
log_path = Path("<target>/.loopr-state/auditor-log.jsonl")
log_path.parent.mkdir(parents=True, exist_ok=True)
with open(log_path, "a", encoding="utf-8", newline="\n") as handle:
    handle.write(json.dumps(entry, sort_keys=True) + "\n")
```

Same shape as `dispatch-log.jsonl` (one JSON object per line, `sort_keys=True`, append-only, never
rewritten) for the same reason: a diffable, greppable audit trail. A separate file, not the same
log -- this is an adjudication record, not a dispatch decision, and the two should not be conflated
in one grep. Then relay the auditor's `GUIDANCE` back to the reviewer so it can resume -- it resumes,
it does not restart; restarting would discard phase context already paid for.

### 7. Run the dispatch loop -- the mechanical wrapper around step 5/6 (optional, once at least step10 is customized)

`.claude/loopr-loop-driver/baby_prd.md` (confirmed via a real `/loopr` interrogation, 2026-08-06)
automates the mechanical round-trip you were otherwise running by hand for every single round: `loopr
dispatch` -> read its decision -> dispatch the named subagent via the Agent tool -> `loopr
dispatch-complete` -> repeat. **The one thing that cannot be automated out of this loop:** only a live
Claude Code session can invoke the Agent tool (`Task(subagent_type=...)`) -- a standalone script has
no way to do that itself. So `.claude/skills/loopr/scripts/driver.py` automates everything mechanical
and judgment-free (calling `loopr dispatch`/`dispatch-complete`, parsing exit codes, logging every
mechanical action to `driver-log.jsonl`, a THIRD log alongside `dispatch-log.jsonl` and
`auditor-log.jsonl` in the same state directory) and hands back to you, the session, exactly what to
do next. It makes zero LLM calls and contains zero judgment logic of its own -- grep it; the only
things it branches on are exit codes and the small set of already-structured `DispatchDecision`/log
fields its safety guards (a round cap, a same-decision-three-times-in-a-row no-progress check, and --
added 2026-08-11 for Step 14, see below -- a same-build-round `step14_ok` check) compare for exact
equality, never decision or subagent-output *text*.

**Step 14 and this loop (`.claude/loopr-step14-comprehension/baby_prd.md`, confirmed 2026-08-11):**
`loopr dispatch`'s own `decide()` is UNCHANGED and still knows nothing about Step 14 -- it is never a
fourth target. Instead, `loopr-step12` itself now runs in up to two separate sub-dispatches for the
same phase, both reported by `loopr dispatch` as the SAME decision (`S6_STEP12_IN_FLIGHT`, target
`loopr-step12`) because `state.dispatch.active_step` stays `STEP_12` across both:
  - **A REVIEW sub-dispatch** -- `.claude/agents/loopr-step12.md`'s own PHASE DISCOVERY finds an
    implementation with no review-approved commit yet. It runs CODE REVIEW through PHASE APPROVAL,
    commits the approval, and stops -- its HANDOFF FORMAT ends `Status: Ready for Step 14
    (comprehension pass)`, never reaching PHASE ADVANCEMENT.
  - **An ADVANCEMENT-ONLY sub-dispatch** -- PHASE DISCOVERY instead finds a review-approved commit
    with no next-phase spec yet, skips CODE REVIEW entirely, and goes straight to PHASE ADVANCEMENT
    (drafting `PHASE_(N+1)_SPEC.md` or `BUILD_COMPLETE.md`). Its HANDOFF FORMAT starts `Phase N
    advancement: done`.
Step 14 (`loopr-step14`) is dispatched by you, the architect/driver, strictly BETWEEN these two --
never by `loopr dispatch` itself, and never in the same `Task(...)` call as either step12 sub-dispatch.
`driver.py complete --verdict clean/minor` now structurally refuses (`guard_halt`) unless a
`step14-complete` call has already logged a `step14_ok` record for the CURRENT `dispatch_ok`'s
build_round -- this is what makes the sequencing load-bearing rather than merely documented here.

**The loop, one round at a time:**

1. Run `python .claude/skills/loopr/scripts/driver.py dispatch --state <path> [--modernized-prd-path
   PATH] [--phase-1-spec-path PATH] [--build-complete-path PATH] [--remodernize] [--max-rounds N]`
   (same override flags step 5's `loopr dispatch` takes, forwarded verbatim; `--max-rounds` defaults
   to 20 -- a structural circuit breaker against a driver bug repeating real subagent side effects, not
   a rework-cap policy, see the file's own docstring).
   - Exit `40` (HALT) -- from `loopr dispatch` itself, or from the driver's own safety guards. Read
     the printed block. **STOP.** Surface it to the human. Do not dispatch anything, especially not on
     your own initiative "to be safe."
   - Exit `50` (COMPLETE) -- the build is done. Stop; nothing left to run.
   - Exit `0` (OK) -- parse the printed decision's `target` field and dispatch it yourself:
     `Task(subagent_type="<target>")`. This is the one step only you can do.
2. Read the dispatched subagent's own output in full, the same way you already would without this
   driver. The things only you can judge (never the script, never a heuristic):
   - **A genuine gate/judge/question moment inside that subagent's own run** (it asks a real question,
     halts on an unrecoverable issue, needs a decision only a human can make). If so: run
     `python .claude/skills/loopr/scripts/driver.py log-stop --state <path> --kind subagent_gate
     --subagent <target> --reason "<why>"`, then **STOP** and surface it. Do not call `complete`.
   - **If the target was `loopr-step12` and its HANDOFF FORMAT is the REVIEW form** (`Status: Ready
     for Step 14 (comprehension pass)`): first, scan its PER-ITEM VERDICT TRACKING output for an
     escalation-eligible `UNCERTAIN` item, exactly as before (below). Then -- whether or not an
     escalation happened -- dispatch `Task(subagent_type="loopr-step14")` yourself, read its own
     output in full to confirm it produced a genuine HANDOFF (this is your judgment, never the
     script's), and run `python .claude/skills/loopr/scripts/driver.py step14-complete --state
     <path>`. Do **NOT** call `complete` for this round -- go back to step 1: `loopr dispatch` will
     report the SAME decision again (`loopr-step12`, still in flight), and this time
     `.claude/agents/loopr-step12.md`'s own PHASE DISCOVERY resumes as the ADVANCEMENT-ONLY
     sub-dispatch. Only once THAT sub-dispatch's HANDOFF FORMAT (`Phase N advancement: done`) has been
     read does this round reach step 3 below and call `complete`.
   - **If the target was `loopr-step12`'s escalation-eligible `UNCERTAIN` item check applies** (per
     `.claude/agents/loopr-step12.md`: low confidence, or Hard Invariant Preservation / Hard Boundary
     category regardless of confidence) -- on the REVIEW sub-dispatch only, never the
     ADVANCEMENT-ONLY one, which runs no code review at all. If found: escalate exactly per step 6
     above -- extract the item's spec clause, file/line, and step12's written reason (never the full
     diff, never a reimplemented extraction), dispatch `loopr-auditor`, append its verdict to
     `auditor-log.jsonl` (step 6's exact snippet), then run
     `python .claude/skills/loopr/scripts/driver.py log-stop --state <path> --kind step12_uncertain
     --subagent loopr-step12 --reason "<item + auditor verdict summary>"` before moving on to
     dispatching `loopr-step14` above. A genuine escalation is a human-awareness point even once the
     auditor has resolved it, not merely a delay until it resolves -- but it does not on its own stop
     the round the way a subagent_gate does; Step 14 and eventual advancement still follow.
3. Otherwise -- a clean completion (an ADVANCEMENT-ONLY step12 sub-dispatch, or a `loopr-step10`/
   `loopr-step11` completion), no gate, no escalation-eligible `UNCERTAIN` item pending -- run
   `python .claude/skills/loopr/scripts/driver.py complete --state <path> [--verdict
   clean|minor|spec_violating]` (verdict only when the completed step was `loopr-step12`; note this is
   the SAME `--verdict` value the REVIEW sub-dispatch already established -- carry it forward to this
   later `complete` call, do not re-derive it from the ADVANCEMENT-ONLY sub-dispatch, which makes no
   review verdict of its own), then go back to step 1 immediately. **No human-authored command in
   between** -- you (the session) chain this on your own initiative, the same discipline the rest of
   this skill already applies to `loopr step`'s `OK`/exit-`0` re-invoke loop. If `--verdict clean` or
   `minor` is given here without a matching `step14_ok` record already logged for this build round
   (the sequencing above skipped), `complete` structurally refuses (`guard_halt`) rather than silently
   letting the round close without its comprehension pass.

`driver-log.jsonl` is the full audit trail: every `dispatch_ok` / `dispatch_halt` /
`dispatch_complete_terminal` / `complete_ok` / `complete_error` / `stop_subagent_gate` /
`stop_step12_uncertain` / `guard_halt` entry, timestamped, so a third party can recount automated
rounds versus human interventions from the log alone, without asking you.

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
