# Continuity model

Condensed from `loopr-PRD.md` §7. Covers how a project accumulates loopr runs over time without
`context.md` rotting into unreadable noise.

## Immutable charter

The founding baby PRD and original `context.md` are committed once and re-read on every later
iteration as grounding. git preserves them permanently -- loopr's job is to never overwrite them.
Later work is a new, additive phase-spec series building on the committed foundation, never a
rewrite of the originals (the same principle this skill's own build followed: `SKILL_PHASE_1_SPEC.md`
is additive to `PHASE_1_SPEC.md`, not a revision of it).

## Layered `context.md`, never a blind append

As new asks arrive, `context.md` grows in structured layers, not a blind append blob:

- A **current-state header** loopr maintains as the single source of "what's true now," so any
  fresh session orients in seconds without reading the whole history.
- A **sectioned body** (original intent, stakeholder constraints, watch-outs).
- A **supersession rule**: a changed constraint is marked superseded with a pointer to its
  replacement, **never deleted**. This preserves the audit trail while keeping the header always
  accurate, so the file stays readable at iteration ten instead of rotting into noise.

## Additive phase specs

New work is always a new, additive phase-spec series building on the committed foundation. The
mechanism this mirrors: the build reveals what an earlier interrogation missed, and what's missed
flows into `context.md` and the next phase spec, rather than reopening or rewriting the original.

## The failure mode this guards against

**"context.md rot"** (`loopr-PRD.md` §10): blind appends make the file unreadable by iteration ten.
Mitigation is exactly the structure above -- layered sections, a maintained current-state header, and
supersession pointers instead of deletion.
