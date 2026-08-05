# loopr — Modernization Log

Pinned external reality for loopr's **own** build. Canonical source for dependency versions and
model strings; `loopr-PRD.md` section 8a summarises it, this file carries the verification detail.

**Scope note:** everything here constrains loopr's own engine code only. loopr specs target projects
in any stack; none of these pins are written into a generated artifact or imposed on a user's repo.

**Update rule:** append a new dated section; never edit a prior one in place. Every row carries the
command or URL that verified it and the date it was verified — a pin without a verification method
is not a pin, it is a memory.

---

## 2026-07-28 — Step 10 (PRD modernization + Phase 1 blueprinting)

First entry. This file did not previously exist.

### Language and toolchain

| Component | Pin | Latest available | Verified by | Date |
|---|---|---|---|---|
| Python | `>=3.14` | 3.14.4 (confirmed on local toolchain) | `py --version` → `Python 3.14.4`; <https://www.python.org/downloads/> | 2026-07-28 |
| Pydantic | `>=2.13,<3` | 2.13.4 | `py -m pip index versions pydantic` → `LATEST: 2.13.4` | 2026-07-28 |
| mypy | `>=2.3,<3` | 2.3.0 | `py -m pip index versions mypy` → `LATEST: 2.3.0` | 2026-07-28 |

Local environment at time of pinning (recorded for reproducibility, not as a requirement):
Python 3.14.4, pydantic 2.13.3 installed, mypy 2.0.0 installed. **The installed pydantic and mypy
are both below the pins above** — the Phase 1 build must upgrade them, not silently satisfy itself
with what is already present.

### Why these floors, not exact `==` pins

Lower-bound-plus-major-ceiling rather than exact equality. loopr is distributed as a portable module
a stranger installs alongside whatever else is in their environment; exact pins on a library as
common as Pydantic cause resolver conflicts in a consumer's project for no benefit. The major-version
ceiling is the part that actually matters — Pydantic v1→v2 and mypy 1.x→2.x were both breaking.

### API-shape verification (no corrections were required)

- `model_config = ConfigDict(extra='forbid')` is the current, documented Pydantic v2 form —
  <https://docs.pydantic.dev/latest/api/config/>. loopr-PRD.md never committed to Pydantic syntax
  beyond `extra="forbid"`, so **no hallucinated or outdated API shape was found to correct.**
  Recorded explicitly because "nothing was wrong" is a finding, and its absence from a changelog is
  indistinguishable from not having checked.
- mypy 2.x **cannot run under Python 3.9** (it can still type-check 3.9 code via `--python-version 3.9`)
  — <https://mypy.readthedocs.io/en/stable/changelog.html>. Irrelevant at Python 3.14, recorded so the
  pin is not loosened carelessly later.

### Model strings

**None pinned, deliberately.** loopr's judge calls are answered by the invoking agent using that
session's own model (`loopr-PRD.md` section 15, resolved 2026-07-28; contract in `PHASE_1_SPEC.md`
§6). The module names no model, imports no vendor SDK, and requires no API key — a direct consequence
of the no-paid-dependency hard rule in `loopr-PRD.md` section 8. If a future phase ever introduces a
direct-API binding, its model strings belong in this section and the hard rule must be re-argued
first.

### Research-tooling status at time of this pass

Recorded because the citation discipline in `loopr-PRD.md`'s changelog depends on it.

| Tool | Status | Detail |
|---|---|---|
| `/arxiv` | Working | Verified across three distinct research-focus queries returning distinct, on-topic results. |
| `/paper-search` — arXiv source | **Patched during this pass** | Was returning newest-on-arXiv regardless of query (terms OR-joined). Patched to AND-join query terms under `all:` in `paper_search_mcp/academic_platforms/arxiv.py`; re-verified on two distinct queries before any citation was relied upon. |
| `/paper-search` — Google Scholar source | **Broken, unresolved** | Returns an empty list unconditionally. Very likely Google anti-scraping, not a code defect. Disclosed as a coverage gap: no non-arXiv venue sweep (ICSE/FSE/EMSE) in this pass. Re-check the A3a convention-vs-cruft null finding if access is restored. |

---

## 2026-08-04 — Step 10 (PRD re-modernization + customization Phase 3 blueprinting)

Second entry. Appended, not edited over the 2026-07-28 section above.

### Language and toolchain — re-verified, nothing moved

| Component | Pin | Latest available | Installed | Verified by | Date |
|---|---|---|---|---|---|
| Python | `>=3.14` (unchanged) | 3.14.4 | 3.14.4 | `python --version` → `Python 3.14.4` | 2026-08-04 |
| Pydantic | `>=2.13,<3` (unchanged) | 2.13.4 | 2.13.3 | `pip index versions pydantic` → `LATEST: 2.13.4`, `INSTALLED: 2.13.3` | 2026-08-04 |
| mypy | `>=2.3,<3` (unchanged) | 2.3.0 | **2.3.0** | `pip index versions mypy` → `LATEST: 2.3.0`, `INSTALLED: 2.3.0` | 2026-08-04 |
| pytest | **not pinned in the PRD** — dev-group floor `pytest>=8` in `pyproject.toml` only | 9.1.1 | 9.0.3 | `pip index versions pytest` | 2026-08-04 |

**The mypy gap the 2026-07-28 entry flagged is closed** — the installed mypy is now 2.3.0, at the pin.
Installed pydantic (2.13.3) still sits one patch below latest but **satisfies the `>=2.13` floor**, so
this is not a violation, only a note. No pin was moved; no API shape required correction.

### Model strings

**Still none pinned in loopr's engine code, and customization Phase 3 does not change that.** The
dispatch controller names *subagent names* (`loopr-step10` / `loopr-step11` / `loopr-step12`), never a
model. The per-subagent model and effort pins remain module-level constants in
`src/loopr/customization/customize.py` and use coarse tier keywords (`opus` / `sonnet`), matching what
real shipped Claude Code agent definitions use — verified in-repo at `6eebfe6`.

Current first-party model IDs were checked this pass (`claude-opus-5`, `claude-sonnet-5`,
`claude-haiku-4-5`) and **deliberately not written into any artifact**: a dated or versioned model ID
in subagent frontmatter would be a regression against the tier-keyword convention, not a
modernization. Recorded here so a future pass does not "helpfully" substitute one.

### Subagent frontmatter `effort` — open question closed

`CUSTOMIZATION_PHASE_1_SPEC.md` §6.1a flagged as unverified whether `effort` exists as a real
per-subagent frontmatter field. **It does.** It is supported frontmatter on a subagent definition and
overrides the session-level effort while that subagent is active; it shipped from feature request
#31536. Sources: web search 2026-08-04 —
<https://www.developersdigest.tech/guides/subagent-frontmatter>,
<https://www.tembo.io/blog/claude-code-subagents>. This corroborates the in-repo verification recorded
at commit `6eebfe6`; the flag is closed, not re-litigated.

### Research-tooling status at time of this pass

| Tool | Status | Detail |
|---|---|---|
| Native web search | **Working** | Carried this pass. Primary discovery path. |
| `WebFetch` against arxiv.org HTML | **Working** | Used to read paper *sections* (not abstracts) for the two load-bearing citations. The one PDF-only paper (2604.17025) was not extractable — cited abstract-level and tagged `[UNVERIFIED]`. |
| `/arxiv` | **Degraded — rate-limited** | One query succeeded; every subsequent call returned HTTP 429 for the remainder of the pass. Not a code defect; retry-after backoff, not investigated further. |
| `/paper-search` — arXiv source | **Broken, regressed** | Returns `{"result": []}` for every query, including the single-word control query `transformer`. This is a regression against the patched state recorded 2026-07-28. Re-patch or re-verify before relying on it. |
| `/paper-search` — Google Scholar source | **Broken, still unresolved** | Unchanged from 2026-07-28. No non-arXiv venue coverage this pass either. |
| GitHub MCP (read-only) | **Not available — skipped, not substituted** | Not configured in this session. Dependency reality was checked against the local package index (`pip index versions`) instead. That is adequate for version drift and inadequate for a *removed* package or a renamed API; disclosed rather than glossed. |
