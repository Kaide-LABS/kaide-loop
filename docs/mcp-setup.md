# MCP setup — paper-search-mcp, arXiv MCP, GitHub MCP (read-only)

This document is two things at once:

1. **A prompt.** Paste the whole file into Claude Code (or any agent with shell + MCP-config
   access) and say "follow this." The agent runs the commands, verifies each connection, and
   reports back per the REPORTING FORMAT at the end.
2. **Plain instructions.** Every command below is also something you can type yourself, by hand,
   with no agent involved.

These three servers are **optional** — `loopr` Step 10 (PRD modernization) works on native web
search alone if none of them are configured (see `loopr-PRD.md` §8, `prompts/Template_prompts/STEP_10`
§2 HALT CONDITIONS). This doc exists because the template assumes they're already reachable; it
does not tell you how to get there. Nothing here is required to use loopr.

**No vendoring.** Nothing below copies server code into this repo, and nothing adds a git
submodule. Each server stays an external process/package the agent reaches at runtime — this repo
only records how to point at it.

**Do not report success on partial completion.** If any step below fails, STOP at that step and
report exactly which server failed and what the error was (see REPORTING FORMAT). Do not continue
configuring the remaining servers silently and call the whole pass "done" — a partial setup that
reads as a complete one is the exact failure mode this doc exists to prevent.

---

## Prerequisites

- Claude Code CLI installed and authenticated (`claude --version` works).
- [`uv`](https://docs.astral.sh/uv/) installed (provides `uvx`) — both `paper-search-mcp` and
  `arxiv-mcp-server` are Python packages run via `uvx`. Check with `uvx --version`; if missing,
  install per uv's own docs before continuing.
- Docker installed and running, **only if** you want GitHub MCP (Task 3 below). Not needed for the
  other two servers.

If a prerequisite is missing, report that specifically — do not silently skip the server that
depends on it.

---

## 1. paper-search-mcp (academic paper search: arXiv, PubMed, bioRxiv, medRxiv, Semantic Scholar, more)

**Verified identity:** this is `openags/paper-search-mcp` — <https://github.com/openags/paper-search-mcp>,
MIT-licensed. This is the package `loopr-PRD.md` §8 names ("MIT, free-first, multi-source incl.
arXiv/PubMed/bioRxiv/Semantic Scholar"); its tool surface (`search_arxiv`, `search_pubmed`,
`search_biorxiv`, `search_medrxiv`, `search_google_scholar`, `download_arxiv`, `read_arxiv_paper`,
…) matches exactly what this project's own MCP tool list exposes under the `paper-search-mcp`
prefix — confirmed against the README, not assumed from the name alone.

Zero configuration required — no API key needed for the core sources. Install and register:

```bash
claude mcp add paper-search -- uvx paper-search-mcp
```

Verify:

```bash
claude mcp list
```

`paper-search` should show `✔ Connected`. If it shows `✘ Failed to connect`, run `uvx
paper-search-mcp` directly in a terminal to see the underlying error (most likely: `uv`/`uvx` not
on PATH, or first-run package download still in progress — retry `claude mcp list` after it
finishes).

**Source verified:** README at <https://github.com/openags/paper-search-mcp> (license, install
commands, tool list, "all keys are optional unless noted"), 2026-08-06.

---

## 2. arXiv MCP (preprints, citation graph, semantic search over arXiv)

**Verified identity:** this is `blazickjp/arxiv-mcp-server` — <https://github.com/blazickjp/arxiv-mcp-server>,
package name `arxiv-mcp-server` on PyPI. Its tool surface (`search_papers`, `get_abstract`,
`download_paper`, `list_papers`, `read_paper`, `citation_graph`, `watch_topic`, `check_alerts`,
`semantic_search`, `reindex`) matches this project's own MCP tool list under the `arxiv-mcp` prefix
exactly — confirmed against the README's tool list, not assumed.

**Correction to `loopr-PRD.md` §8:** the PRD currently describes this server as "MIT, free". The
actual license, verified directly against the repo's LICENSE file and license badge, is
**Apache License 2.0**, not MIT. Both are permissive, free, non-paid OSS licenses, so this does not
change the no-paid-dependency conclusion — but the license label itself was wrong and is corrected
here rather than repeated.

The citation-graph and semantic-search features `loopr-PRD.md` §8 relies on ("kept alongside
paper-search-mcp... arXiv MCP's citation-graph and semantic-search surface is not duplicated")
require the `[pro]` extra — the base install does not include it. Install with the extra and
register:

```bash
uv tool install "arxiv-mcp-server[pro]"
claude mcp add --scope user arxiv -- uvx --from "arxiv-mcp-server[pro]" arxiv-mcp-server
```

**Storage note:** downloaded papers default to `~/.arxiv-mcp-server/papers` (outside any repo). Do
not override `--storage-path` to point inside this repo — that would put downloaded papers under
git tracking, which is not what this server is for.

Verify:

```bash
claude mcp list
```

`arxiv` should show `✔ Connected`.

**Source verified:** README and LICENSE at <https://github.com/blazickjp/arxiv-mcp-server>, PyPI
page at <https://pypi.org/project/arxiv-mcp-server/>, 2026-08-06.

---

## 3. GitHub MCP — read-only (dependency source/packaging verification)

**Verified identity:** this is GitHub's own official server, `github/github-mcp-server` —
<https://github.com/github/github-mcp-server>, MIT-licensed.

### 3a. Create a read-only, fine-grained personal access token (about 2 minutes)

GitHub's unauthenticated API rate limit is **60 requests/hour** — enough to fail on the second or
third file read of a real dependency-verification pass. A token is not a blocker; it is a couple
of clicks:

1. Go to **github.com → your profile photo (top right) → Settings → Developer settings → Personal
   access tokens → Fine-grained tokens → Generate new token**.
2. **Resource owner:** yourself.
3. **Repository access:** choose **"Public Repositories (read-only)"**. This is the scope loopr
   Step 10 actually needs — verifying packaging/API-surface of open-source dependencies. Do not
   grant broader access than this by default.
4. **Permissions:** leave empty / default. GitHub grants read access to public repository contents
   under this scope with no extra permission checkboxes needed — do not add `Contents: Read and
   write` or any other write-capable permission. Step 10 has no legitimate reason to write issues,
   PRs, or comments, and this doc does not configure that capability even though it is technically
   available on a broader token.
5. Set an expiration (90 days is a reasonable default; GitHub will prompt you to regenerate).
6. Generate, then copy the token immediately — GitHub shows it once.

**If you later need private-repo access:** this is a token-scope change, not a rearchitecture.
Regenerate (or create a new) fine-grained token with **Repository access → Only select
repositories** (pick the private repos you need) and add the **Contents: Read-only** permission
explicitly. The server, the `--read-only` flag, and every instruction in
`prompts/Template_prompts/STEP_10` stay exactly as they are — only the token's own scope changes.
This is why the template's wording was fixed to say "real source" / "browse repositories" instead
of hardcoding "public" (see the disclosed fix in `loopr-PRD.md` §8).

### 3b. Register the server, enforced read-only

Read-only is enforced by the `--read-only` flag on the server itself (passed after the image name,
not a Docker flag) — the token's own scope is the second, independent layer of enforcement per
`prompts/Template_prompts/STEP_10` §2 ("the enforcement should come from the token's own scope, not
from this instruction alone").

```bash
claude mcp add --scope user github -e GITHUB_PERSONAL_ACCESS_TOKEN=<your-token> \
  -- docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server stdio --read-only
```

The server name (`github`) must come before the `-e` flag, not after — `claude mcp add`'s parser
otherwise misreads the name as part of the environment-variable value and fails with "Invalid
environment variable format." `--scope user` makes it available in every project, not just the one
you're standing in when you run this (default scope is `local`, project-only).

Replace `<your-token>` with the token from 3a. Verify:

```bash
claude mcp list
```

`github` should show `✔ Connected`. If it shows `! Needs authentication` or `✘ Failed to connect`,
run the `docker run` command directly (without the `claude mcp add` wrapper) to see the raw error —
most likely causes: Docker not running, token pasted with a trailing space/newline, or the token
already expired.

**Source verified:** README and LICENSE at <https://github.com/github/github-mcp-server>, 2026-08-06
— confirmed `GITHUB_PERSONAL_ACCESS_TOKEN` env var name and that `--read-only` is a server flag
(write tools are skipped even if explicitly requested via `--tools` when this flag is set).
**The Docker invocation itself was NOT actually run at doc-writing time — only read from the
README, and it was wrong** (missing the required `stdio` subcommand; running without it just prints
help text and exits). Found and fixed 2026-08-07 by actually running the container with a real
token and a real MCP handshake, not by re-reading the docs more carefully. The command above is the
one that was live-tested.

---

## `claude mcp add` syntax — what was actually verified

All three commands above follow the syntax confirmed against Claude Code's own docs
(<https://code.claude.com/docs/en/mcp-quickstart>, 2026-08-06): flags (`--transport`, `--env`,
`--scope`) precede the server name; everything after a bare `--` is the command Claude Code runs to
start the server. Default transport is `stdio`; default scope is `local` (this project only). Use
`--scope user` (as done for `arxiv` above) if you want a server available in every project instead
of just this one.

---

## REPORTING FORMAT (for the agent following this doc as a prompt)

After attempting all three servers, report exactly this shape — do not compress it into a single
"done" line:

```
paper-search-mcp: CONNECTED | FAILED (<reason>) | SKIPPED (<reason>)
arxiv-mcp:        CONNECTED | FAILED (<reason>) | SKIPPED (<reason>)
github-mcp:       CONNECTED | FAILED (<reason>) | SKIPPED (<reason>) — read-only token scope: <public-only | public+private>
```

A report that says "MCP setup complete" without this per-server breakdown is not an acceptable
handoff — it is exactly the silent-partial-completion failure this doc exists to prevent.
