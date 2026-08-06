# loopr V2 -- Agent Archetype Orchestration

> **STATUS: FORWARD SPEC. NOT CURRENT SCOPE. DO NOT BUILD ANY OF THIS NOW.**
>
> loopr V1 ships first, current scope unchanged. This is the next major arc *after* V1 is complete.
> Filed 2026-08-03; **extended the same day with the Escalation Tier (Step 12.5 Auditor)** -- see the
> extension section at the foot of this document, which also REVERSES one decision made at original
> filing. Nothing in this document alters V1's confirmed boundary, its phase specs, or any in-flight
> build.
>
> First real application will be the **Sand Technologies FDE artifact build**, not loopr itself.

---

## Three archetypes

**ARCHITECT -- persistent.** The main session. Never retires. Owns the spec chain (baby PRD ->
ultimate PRD -> phase specs), owns the scratch file, adjudicates disputes. Goes quiet during phased
execution but returns at the end to verify `BUILD_COMPLETE` against the PRD across all phases.

**EXECUTOR -- subagent.** Writes code against whatever spec it is given. Present in both
orchestration modes.

**REVIEWER -- subagent, phase-scoped.** Exists ONLY in primary/phased orchestration. Verifies phase
output against phase spec and generates the next phase spec. Effectively a per-phase architect
stand-in. Does not exist in secondary mode.

> **A fourth archetype -- AUDITOR -- was added in the 2026-08-03 extension below**, along with a
> dedicated Step 10 subagent. Three was the count at original filing; read the extension before
> treating this list as complete.

---

## Two orchestration modes

**PRIMARY** (new feature, significant version): baby PRD -> ultimate PRD -> phased Step 11 build /
Step 12 review loop. All three archetypes. **FRESH executor and FRESH reviewer per phase** -- this is
deliberate: if a phase can only be built by an executor that remembers the previous phase, that phase
spec was underspecified. Freshness is a free correctness check on spec self-sufficiency.

**SECONDARY** (small feature, debug, taste-driven change): architect directs, ONE long-lived executor
across directives, no reviewer, no phase specs. Long-lived because debug work is serially dependent --
directive 3 references what surfaced in directive 1, and re-deriving that trail each time is slower
and more error-prone than keeping it in the window. **[AMENDED 2026-08-06]** "Long-lived" no longer
implies a separate manual session/tab -- native subagent dispatch (`Task(...)`) achieves the same
cumulative-context property by continuing the *same* dispatched subagent via `SendMessage` across
directives, instead of spawning a fresh one per directive. The design intent (context lives in one
place across a serially-dependent trail, not re-derived each time) is unchanged; only the mechanism
moved from a manual tab to a resumable subagent. See `.claude/skills/loopr/SKILL.md`'s "Primary vs
secondary work" section for the operational rule this produces.

**The governing rule:** fresh context when the spec should be self-sufficient, persistent context when
the investigation is cumulative.

---

## Reviewer isolation

The reviewer receives the phase spec and the diff. It does NOT receive the executor's conversation,
reasoning, or justifications. It verifies the artifact against the spec, not against the executor's
account of the artifact. A reviewer that inherits the executor's context inherits its
rationalizations -- it has already been convinced.

The reviewer **FLAGS. It does not overrule.** The architect adjudicates. Otherwise the last word has
just moved to a different model instead of living in the spec.

---

## Two-layer state (RAM / SSD)

**Layer 1** -- the architect's running summary. Working memory, in-context.
**Layer 2** -- a scratch file on disk under `.claude/`. Durable storage.

The **ARCHITECT** writes and maintains the scratch file, not the executor. Two reasons:

1. The architect is the only agent that reads the file across sessions, so it should own the
   structure. An executor appending handoffs produces a chronological log -- written to be written,
   not to be read.
2. A maintained document can be revised. Stale entries get marked dead, three entries collapse into
   one established fact, a suspicion gets promoted to confirmed. An append-only log cannot do this,
   so after fifteen entries most of it is stale but still looks authoritative.

**FIDELITY RULE: summarize the reasoning, never paraphrase the facts.** Error strings, file paths,
line numbers, function names, config values, version numbers go in VERBATIM. The narrative around
them ("we suspected the parser, ruled it out because X") gets compressed. Rule of thumb: if you would
grep for it, it goes in exactly as it appeared.

The scratch file has a fixed section shape so retrieval is predictable across sessions -- current
hypothesis / established findings / ruled out (with why) / open threads / verbatim artifacts. A fresh
executor handed this file orients in one read.

---

## Executor retirement (secondary mode)

**Do NOT build a context-size or context-pressure detector.** Size does not tell you whether carried
context is helping or hurting. Because state is durable on disk, retiring early is cheap and retiring
late is expensive (anchoring on a wrong hypothesis, throttling). Asymmetric costs, so bias toward
early.

Four triggers, in expected order of frequency:

1. **Task complete** -- bug fixed, feature shipped. Unambiguous.
2. **Operator ends the session** -- architect writes the summary to the scratch file, executor
   retires.
3. **Direction change** -- the architect issues a directive that does not build on prior findings.
   Architect's judgment call, not automated.
4. **Stall** -- roughly 3 directives with no change in the failing symptom. This is the anchoring case
   and the only one worth a hard rule, because a confidently-stuck executor will not notice. A fresh
   executor with the scratch file and no memory of three failed attempts is a genuinely different
   reader.

---

## Not in scope

**Traycer is NOT used for this.** Native Claude Code subagents already provide separate context
windows -- that is their defining property, not a workaround. Traycer solves cross-provider
orchestration, which is multi-loopr's problem, later. Adding it here would introduce a runtime
dependency to solve something the host already does natively.

---

## Sequencing

loopr V1 ships first, current scope unchanged. This archetype orchestration is V2. The first real
application of it will be the Sand Technologies FDE artifact build, not loopr itself.

---

## Filing notes (added at archive time; not part of the spec as given)

Two relationships to existing project documents, recorded so a future reader does not mistake them
for contradictions:

1. **On Traycer.** `loopr-MIGRATION.md` §5 records Traycer as the locked adaptation target for the
   *harness* (sequencing step 3, still unassessed against the three invariants). This document rules
   Traycer out for *archetype orchestration* specifically. These are different layers and do not
   conflict -- Traycer remains the named target for cross-provider work (multi-loopr), and is simply
   not the mechanism for context isolation, which native subagents already provide.

2. **On native subagents.** `loopr-MIGRATION.md` §5 recorded native Claude Code subagents as "a lean,
   NOT a locked decision," demoted in favour of Traycer for the harness. This document deliberately
   revives them for a *different* purpose -- context isolation between archetypes, not cross-provider
   orchestration. That is a genuine change of position for this layer, made knowingly.

3. **[SUPERSEDED 2026-08-03, same day -- see "Correction: Step 10 keeps a dedicated subagent" in the
   extension below.]**

   ~~On Step 10 and the model floor -- SETTLED, do not reopen. The architect always handles Step 10;
   it is never delegated to a subagent. Because the architect is the main session, its model floor is
   enforced manually -- the operator types `/model` before running Step 10. That is the documented
   manual mechanism, it works, and it is accepted here rather than engineered around. Do not build a
   pinned Step-10 subagent to "fix" this; doing so would sever the continuity that makes the
   architect the architect.~~

   **Reversed by the operator on evidence.** Step 10 KEEPS a dedicated subagent with an Opus-class
   model declared in its config. Reasoning is in the extension below. Preserved here rather than
   deleted, per this project's own continuity rule (`loopr-PRD.md` §7 -- mark superseded with a
   pointer, never delete). Worth preserving specifically because the losing argument ("the architect
   can just run it; the operator switches models first") is intuitively reasonable and will be
   re-proposed by someone unless the counter-evidence stays on the record.

---

# EXTENSION, 2026-08-03 -- Escalation Tier (Step 12.5 Auditor)

> Still forward spec. Still **DO NOT BUILD NOW**. loopr V1 ships first, unchanged.

## Correction: Step 10 keeps a dedicated subagent

**This reverses filing note 3 above. Treat this as the current position and disregard the earlier
one.**

Step 10 (PRD modernization + Phase 1 spec) KEEPS a dedicated subagent, with an **Opus-class model
declared in its config**.

Two reasons:

1. It does a specific, bounded job -- run the Step 10 pass with web search, the Nia MCP server, the
   arXiv skill and the paper-search skill. That is a clean subagent boundary, not something that
   needs to live in the persistent session.
2. The architect could run it, but only if the operator remembers to switch models first. **That
   failed in practice recently and cost a full rerun:** a Sonnet-low Step 10 pass pinned a dependency
   that cannot install on the dev platform, then declared the pass complete and explicitly stated no
   escalation was needed. Opus-high caught it on a second self-verification pass. A config-declared
   model floor makes this structural instead of a discipline the operator has to hold every time.

## Fourth archetype

**AUDITOR -- subagent, on-demand only.** Permanently set to an Opus-class model in config. Exists
only in primary/phased orchestration. Never runs by default; only when the architect dispatches it.

The auditor is a **SEPARATE subagent, not the architect wearing a second hat.** This is a cost
decision. The architect is persistent and usually runs on Sonnet (medium or high), because most of
what it does is directing secondary orchestration, which Sonnet handles well. If the architect had to
BE the auditor, the entire persistent session would have to run on Opus just to cover rare
escalations. Keeping them separate means Opus is paid for only at the moments that need it.

Default to **Opus 5**. Reserve **Fable 5** for genuinely harder cases -- Opus 5 covers the majority of
Fable's ground at lower cost.

### Model tiering across archetypes

| Archetype | Model / effort | Rationale |
|---|---|---|
| Executor | Sonnet, low effort | Most output volume; work is checked immediately downstream |
| Reviewer | Sonnet, high effort | Judgment work, scoped to one phase against one spec |
| Auditor | Opus 5 (Fable 5 only when warranted) | Rare, small context, high-leverage adjudication |
| Architect | Usually Sonnet, medium or high | Operator-controlled |
| Step 10 subagent | Opus-class, declared in config | See the correction above |

## Escalation chain -- architect routes, does not adjudicate

Anthropic's advisor tool (server-side mid-generation escalation) is API-only, both seats must be
Anthropic models, and it is unavailable on Vertex. It cannot be invoked from inside a Claude Code
session. **Do not design around it.** Replicate the PATTERN, not the tool.

The full chain:

```
reviewer hits a problem
  -> reviewer HALTS (the review prompts are already structured to halt on problems)
  -> escalates to architect
  -> architect dispatches the auditor subagent with scoped context only
  -> auditor returns verdict plus guidance
  -> architect receives it
  -> architect passes it to the reviewer
  -> reviewer RESUMES
```

**The reviewer RESUMES, it does not restart.** Restarting discards the phase context that produced
the halt and re-pays for derivation already done.

The architect sits in the middle deliberately, so the entire escalation is captured in **one audit
trail** rather than happening agent-to-agent off the record.

**The reviewer does NOT self-escalate to the auditor.** Escalation is an architect dispatch. This is a
forced checkpoint rather than self-triggered escalation, which is the correct shape regardless: a
confidently-wrong reviewer will not recognise that it needs help, which is exactly when help is
needed.

## Reviewer output contract

The reviewer emits a **STRUCTURED verdict, not prose**:

- **PASS** items -- verified against spec.
- **FAIL** items -- verified violations, with spec clause and location.
- **UNCERTAIN** items -- each carrying: the spec clause at issue, the file and line reference, and a
  written reason it could not be resolved.
- A **confidence score** per item.

The **written reason is mandatory** and is what the auditor acts on. The numeric score is only a
dispatch trigger. LLM confidence scores are poorly calibrated -- **never let the number alone carry
the decision.**

## Auditor context scoping -- this is what keeps it cheap

The auditor **NEVER** receives the whole project, the full diff, or the reviewer's conversation. It
receives only:

- The specific flagged items.
- The spec clauses those items reference.
- The code snippets those items reference.

It returns a verdict per item plus guidance on how to proceed. Small context in, small output out.
This mirrors why the advisor pattern is economical: the expensive model supplies judgment at one
moment, it does not redo the work.

## Dispatch triggers -- severity AND confidence, not confidence alone

Scoping the auditor to uncertain items makes it **structurally blind to FALSE NEGATIVES**: something
the reviewer confidently passed but got wrong. That is the more dangerous failure, and confidence
alone will never surface it.

Therefore dispatch on **either** condition:

1. Reviewer confidence below threshold on any item, **OR**
2. The item touches a **correctness-critical path** -- regardless of reviewer confidence.

**Consequence severity sets the ceiling; confidence is the gate.** Anything in a deterministic or
correctness-critical layer gets audited even at high reviewer confidence. This is Accountable
Autonomy applied to loopr's own loop.

*Optional hardening for later:* a full unscoped audit at the final phase, to catch accumulated false
negatives the scoped audits could not see.

## Auditor authority

The auditor **adjudicates the flagged items and advises**. It does not silently rewrite the spec or
overrule locked architecture. If it finds that a locked architectural decision is wrong, it escalates
to the human -- same escalate-don't-overrule rule as Step 10.

## Scratch files -- split by ORCHESTRATION MODE, not by agent class

Two files, both written and maintained by the architect:

- `.claude/primary_context.md` -- the phased build. Executor halts, reviewer verdicts, audit
  adjudications and the escalation log all live here, in one timeline.
- `.claude/secondary_context.md` -- the debug and small-feature loop. Separate because it is a
  genuinely different workstream.

**Do NOT create a separate file per agent class** (primary executor, secondary executor, reviewer,
auditor). A halt is a single causal chain spanning executor state, reviewer reasoning and audit
verdict. Splitting it across four files fragments the story and forces the architect to reassemble
the narrative from four places every time -- which is the work the scratch file exists to avoid.

The escalation log within `primary_context.md` records: what halted, why, what the auditor ruled, and
how it resolved. That is the audit trail.

If a single phase's escalation history ever becomes genuinely unwieldy, split **then**, per-phase,
with evidence. Not pre-emptively.

## Portability note -- do not weld the roles to the mechanism

Subagents are a Claude Code primitive. Codex and other hosts will not have the same feature.
Everything above the mechanism -- the archetype roles, the escalation chain, the reviewer output
contract, the dispatch gating, the file contract -- is **host-agnostic**.

Keep the archetype logic separable from the subagent implementation so a future port to Codex or
multi-loopr is a **mechanism swap rather than a redesign**. This costs nothing now and is only
expensive to retrofit later.
