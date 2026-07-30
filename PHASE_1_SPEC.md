# PHASE_1_SPEC.md — loopr standalone spec-discipline module

> Built 2026-07-28 from the **modernised** `loopr-PRD.md` (MODERNIZATION CHANGELOG Entry 2), not the
> pre-modernization version. Implements `docs/stopping-test-spec.md` (confirmed) and
> `docs/conformance-classification-spec.md` (confirmed, as amended 2026-07-28).
>
> **This document is a blueprint. It contains no application code.** Signatures, schemas, and
> contracts are specified so a literal-minded execution agent cannot guess; the agent writes the
> bodies.

---

## §0 Phase Plan Header

**Phase 1 of 1.**

Phase 1 is sequencing step 1 in full (`loopr-MIGRATION.md` §2): the standalone, portable
spec-discipline module — greenfield **and** brownfield — proven on one real project of each kind.

**Why PHASE_COUNT = 1, stated honestly.** The Step 10 instruction to derive PHASE_COUNT from a
breakdown of the module's build pulls against its own §8, which binds *both* real-project proofs to
Phase 1's acceptance gate. §8 is the binding constraint — it is what the review agent checks — so the
module's build does not decompose into multiple phases here: all of it, plus both proofs, is Phase 1.
Sequencing steps 2–4 (skill packaging, harness/Traycer, meeting bot) are separate later programmes
and explicit non-goals (§9), not phases of this build.

Because one phase this size still needs commit ordering, §6.9 gives a **work-package sequence
(WP-A … WP-G)** with a green-bar checkpoint at each boundary. Work packages are commit-sequencing
guidance, **not** phases: there is one acceptance gate (§8), at the end.

> **⚑ FLAGGED SUGGESTION — not applied, for human decision.**
> A single phase carrying the whole engine plus two real-project proofs is large for one
> build/review cycle, and the two proofs are calibration exercises whose findings will change code
> written earlier in the same phase. A cleaner shape would be **Phase 1 of 4**: (1) core greenfield
> engine through Gate 1; (2) brownfield conformance through Gate 3; (3) greenfield proof +
> calibration; (4) brownfield proof + calibration. That would let the round-cap and structural
> heuristics — which `docs/stopping-test-spec.md` §Decisions 1 and 4 explicitly defer to the real
> project test — be tuned in a phase of their own rather than retrofitted.
> **This is flagged, not baked in.** The spec below is the faithful single-phase fill. Splitting it
> is a structural change to the loop's phase plan, which is the human's call, not mine.

**Preconditions.** loopr has no engine code. Phase 1 is the first code this project has; assume no
existing module layout. The repo currently holds design documents, the abandoned Docker harness
(untouched, not resurrected), and prompt templates.

---

## §1 Files Added or Modified

All new code lives under `src/loopr/`. **No file at repo root is modified except as listed.**

### 1.1 Added — packaging and configuration

| Path | Purpose |
|---|---|
| `pyproject.toml` | PEP 621 metadata, dependency pins (§2), `[tool.mypy]` strict config, `[tool.pytest.ini_options]`, console-script entry point `loopr = "loopr.cli:main"`. Build backend: `hatchling`. |
| `src/loopr/py.typed` | PEP 561 marker (empty file). Without it, consumers get no types from an installed loopr. |
| `.gitignore` | **Modified** — append `.loopr-state/`, `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `*.egg-info/`, `dist/`. Do not remove existing entries. |

### 1.2 Added — models (`src/loopr/models/`)

| Path | Contents |
|---|---|
| `__init__.py` | Re-exports every public model. Calls `model_rebuild()` on the two models with forward references (§3.9). |
| `common.py` | `LooprBase`; enums `Mode`, `ConditionId`, `JudgeCallType`, `QuestionStatus`, `QuestionOrigin`, `ScopeEdgeKind`, `NoteSource`, `Verdict`, `Centrality`, `GateId`. |
| `interrogation.py` | `AcceptanceCriterion`, `ScopeEdge`, `Boundary`, `ContextNote`, `OpenQuestion`, `Assumption`, `ConditionResult`, `InterrogationState`. |
| `brownfield.py` | `EvidenceBundle`, `PatternClassification`, `BrownfieldState`. |
| `judge.py` | `JudgeRequest`, `JudgeResponse`, `JudgeExchange`, `ALLOWED_INPUTS`. |
| `gates.py` | `GateRecord`, `GatePayload`. |

### 1.3 Added — judge port (`src/loopr/judge/`)

| Path | Contents |
|---|---|
| `__init__.py` | Re-exports `JudgeClient`, `AgentJudgeClient`, `ScriptedJudgeClient`. |
| `port.py` | `JudgeClient` `Protocol` (§6.2). |
| `envelope.py` | `write_request`, `read_response`, `digest` — envelope (de)serialisation and SHA-256. |
| `agent_client.py` | `AgentJudgeClient` — the default emit-and-exit binding. |
| `scripted_client.py` | `ScriptedJudgeClient` — fixture replay; the only binding used in tests. |

### 1.4 Added — deterministic checks and rubrics

| Path | Contents |
|---|---|
| `src/loopr/rubrics/__init__.py` | Re-exports `RUBRICS`. |
| `src/loopr/rubrics/texts.py` | Frozen mapping `RUBRICS: Mapping[JudgeCallType, RubricSpec]`. Rubric text is **data, not f-strings** — §7 G-4. |
| `src/loopr/checks/__init__.py` | Re-exports `evaluate_all`. |
| `src/loopr/checks/structural.py` | The six pure structural pre-checks, plus shared heuristics. |
| `src/loopr/checks/conditions.py` | `evaluate_all` — the two-layer evaluator and lowest-false-first selection. |

### 1.5 Added — interrogation, gates, brownfield, artifacts, state, CLI

| Path | Contents |
|---|---|
| `src/loopr/interrogation/__init__.py` | Re-exports `step`. |
| `src/loopr/interrogation/loop.py` | `step()` — the one-shot state advance (§6.4). |
| `src/loopr/interrogation/questions.py` | `build_followup` — targeted question construction (§6.5). |
| `src/loopr/gates/__init__.py` | Re-exports gate helpers. |
| `src/loopr/gates/gates.py` | Gate 1/2/3 request, confirmation, and hash invalidation (§6.6). |
| `src/loopr/brownfield/__init__.py` | Re-exports the brownfield entry points. |
| `src/loopr/brownfield/discovery.py` | Two-stage touched-surface discovery (§6.7.1). |
| `src/loopr/brownfield/evidence.py` | `EvidenceBundle` construction from git/grep/import-graph (§6.7.2). |
| `src/loopr/brownfield/classify.py` | Classification call construction and verdict routing (§6.7.3). |
| `src/loopr/artifacts/__init__.py` | Re-exports the three emitters. |
| `src/loopr/artifacts/baby_prd.py` | Baby PRD renderer, TL;DR-first. |
| `src/loopr/artifacts/context_md.py` | `context.md` renderer, layered per PRD §7. |
| `src/loopr/artifacts/conformance_ledger.py` | `conformance-ledger.md` renderer (brownfield only). |
| `src/loopr/state/__init__.py` | Re-exports `StateStore`. |
| `src/loopr/state/store.py` | Atomic load/save, schema-version guard (§6.3). |
| `src/loopr/cli.py` | Argument parsing, command dispatch, exit-code contract (§6.1). |
| `src/loopr/__init__.py` | `__version__`; re-exports the library-facing API. |

### 1.6 Added — tests (`tests/`)

`test_structural_checks.py`, `test_conditions.py`, `test_judge_scope.py`, `test_judge_envelope.py`,
`test_round_cap.py`, `test_gates.py`, `test_state_store.py`, `test_brownfield_discovery.py`,
`test_brownfield_evidence.py`, `test_brownfield_classify.py`, `test_artifacts.py`, `test_cli.py`,
`test_no_hardcoded_domain.py`, `test_no_paid_dependency.py`, plus `tests/fixtures/` holding scripted
judge transcripts and two throwaway git repos built by fixture (`tests/conftest.py`).

`test_no_hardcoded_domain.py` and `test_no_paid_dependency.py` are **boundary tests** — they encode
the §7 G-11/G-12 hard-boundary greps as failing tests so the boundary is enforced by CI, not only by
review.

### 1.7 Added — proof artifacts (§8)

`proofs/greenfield/` and `proofs/brownfield/`, each holding the run's emitted artifacts, the full
judge-exchange log, and a `FINDINGS.md`. These are evidence for the acceptance gate, not code.

### 1.8 Explicitly NOT modified

`kaide-loop.sh`, `Dockerfile`, `docker-compose.yml`, `entrypoint.sh`, `loop.gates.sh`,
`scripts/preflight.sh`, `prompts/**`, `README.md`. The Docker harness is abandoned
(`loopr-MIGRATION.md` §1); Phase 1 neither uses nor deletes it. `README.md` still describes the
abandoned harness — **rewriting it is Phase 2 work**, and touching it here is scope creep.

---

## §2 Dependencies

### 2.1 Runtime — exactly one

```toml
requires-python = ">=3.14"
dependencies = ["pydantic>=2.13,<3"]
```

**That is the entire runtime dependency list.** One package. Everything else — CLI parsing, JSON,
hashing, subprocess, file walking — is standard library (`argparse`, `json`, `hashlib`, `subprocess`,
`pathlib`, `re`, `difflib`, `dataclasses`, `enum`, `typing`).

If this list grows during the build, that is a **defect in this spec or in the implementation**, not
a discovery. Per Step 10 §5's instruction to flag it: the list is short and free-tier-only, as the
hard boundary in `loopr-PRD.md` §8 requires. Any added runtime dependency must be justified against
that rule before it is added, and it must be free, permissively licensed, and not require an account.

### 2.2 Development — pinned, not shipped

```toml
[dependency-groups]
dev = ["mypy>=2.3,<3", "pytest>=8", "pytest-cov>=5"]
```

### 2.3 Version provenance

Verified 2026-07-28; full method and dates in `docs/modernization_log.md`, summarised in
`loopr-PRD.md` §8a.

| Pin | Latest at pin time | Verified by |
|---|---|---|
| `>=3.14` | Python 3.14.4 | `py --version`; <https://www.python.org/downloads/> |
| `pydantic>=2.13,<3` | 2.13.4 | `pip index versions pydantic` |
| `mypy>=2.3,<3` | 2.3.0 | `pip index versions mypy` |

**Local environment is behind both pins** (pydantic 2.13.3, mypy 2.0.0 installed). The build must
upgrade; satisfying itself with what is already installed is a gate failure.

### 2.4 Forbidden dependencies — enforced by test

`test_no_paid_dependency.py` asserts that the runtime dependency set is exactly `{"pydantic"}` and
that no module under `src/loopr/` contains a top-level import of: `nia`, `nia_sdk`, `context7`,
`anthropic`, `openai`, `google.generativeai`, `vertexai`, `langchain`, `httpx`, `requests`,
`aiohttp`. **The network-client bans are deliberate and are not incidental** — loopr Phase 1 makes no
outbound network call of any kind, and the absence of an HTTP client is the mechanical proof.

### 2.5 mypy configuration

```toml
[tool.mypy]
python_version = "3.14"
strict = true
warn_unreachable = true
disallow_any_explicit = true
plugins = []
```

`disallow_any_explicit = true` is deliberate and stricter than `--strict`. The one place `Any` is
genuinely needed — judge-envelope input values — uses a constrained `JsonValue` recursive alias
(§3.6), not `Any`. **No `# type: ignore` may be added without an adjacent comment naming the
upstream issue it works around.** `strict = true` already implies `disallow_untyped_defs`, so every
signature carries hints (`loopr-MIGRATION.md` §8).

---

## §3 Pydantic Schemas

Every model below inherits `LooprBase`. **Every model therefore carries
`model_config = ConfigDict(extra="forbid")`** — set once on the base and inherited, not repeated
per class. Verified current v2 syntax: <https://docs.pydantic.dev/latest/api/config/>.

### 3.1 `LooprBase` and enums — `models/common.py`

```python
class LooprBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        frozen=False,
    )
```

`validate_assignment=True` matters: the interrogation loop mutates state between steps, and without
it a bad assignment would only surface at the next serialise.

| Enum | Members |
|---|---|
| `Mode` | `GREENFIELD`, `BROWNFIELD` |
| `ConditionId` | `C1_OUTCOME`, `C2_ACCEPTANCE`, `C3_SCOPE_EDGES`, `C4_BOUNDARY`, `C5_SOFT_CONTEXT`, `C6_NO_UNKNOWNS` |
| `JudgeCallType` | `C1_OUTCOME`, `C2_ACCEPTANCE`, `C3_SCOPE_EDGES`, `C5_SOFT_CONTEXT`, `C6_LOAD_BEARING`, `BF_RELEVANCE`, `BF_CLASSIFY` |
| `QuestionStatus` | `OPEN`, `RESOLVED`, `DEFERRED_NON_LOAD_BEARING` |
| `QuestionOrigin` | `MODULE`, `USER`, `PATTERN_AMBIGUITY` |
| `ScopeEdgeKind` | `OUT`, `DEFERRED` |
| `NoteSource` | `STATED`, `INFERRED` |
| `Verdict` | `CONFORM`, `DO_NOT_REPLICATE`, `CONFLICT`, `AMBIGUOUS` |
| `Centrality` | `CORE`, `PERIPHERAL` |
| `GateId` | `GATE_1_BABY_PRD`, `GATE_2_BOUNDARY`, `GATE_3_CONFLICTS` |

**Note there is no `C4_BOUNDARY` in `JudgeCallType`.** Condition 4 is a pure state-machine check with
no judge rubric (`docs/stopping-test-spec.md` §Condition 4). The enum asymmetry is intentional and
load-bearing — it makes "condition 4 must never make a judge call" a type-level fact. A reviewer
seeing `C4` added to `JudgeCallType` should treat it as a defect.

### 3.2 `models/interrogation.py`

**`AcceptanceCriterion`**

| Field | Type | Constraint |
|---|---|---|
| `text` | `str` | `min_length=1` |
| `judge_confirmed_testable` | `bool` | default `False`. Set only by the C2 judge; never by user input. |

**`ScopeEdge`**

| Field | Type | Constraint |
|---|---|---|
| `item` | `str` | `min_length=1` |
| `kind` | `ScopeEdgeKind` | — |
| `reason` | `str` | `min_length=1`. An edge with an empty reason fails structurally (`docs/stopping-test-spec.md` §Condition 3). |

**`Boundary`**

| Field | Type | Constraint |
|---|---|---|
| `text` | `str` | `min_length=1` |
| `confirmed` | `bool` | default `False` |
| `confirmed_hash` | `str \| None` | default `None`. SHA-256 of `text` at the moment of confirmation. |
| `declined` | `bool` | default `False`. The PRD A3 escape hatch — a distinct recorded user action, never inferred from silence. |

Model validator `check_confirmation_coherent`: if `confirmed` is `True` then `confirmed_hash` must be
non-`None`; `confirmed` and `declined` may not both be `True`. **There is no separate dirty flag** —
staleness is derived by comparing `confirmed_hash` against a fresh hash of `text` (§6.6.2), so it
cannot be forgotten.

**`ContextNote`** — `text: str` (`min_length=1`), `source: NoteSource`.

**`OpenQuestion`**

| Field | Type | Constraint |
|---|---|---|
| `id` | `str` | `min_length=1`; stable, assigned at creation |
| `text` | `str` | `min_length=1` |
| `origin` | `QuestionOrigin` | `PATTERN_AMBIGUITY` is how a brownfield AMBIGUOUS verdict enters the condition-6 ledger without a seventh condition (`loopr-MIGRATION.md` §1a) |
| `status` | `QuestionStatus` | default `OPEN` |
| `load_bearing` | `bool \| None` | default `None`; set by the C6 judge at logging time |
| `resolution` | `str \| None` | default `None` |
| `force_resolved` | `bool` | default `False`; set only by the round cap |

Model validator: `status == RESOLVED` requires non-`None` `resolution`; `force_resolved` implies
`status == DEFERRED_NON_LOAD_BEARING`.

**`Assumption`** — `text: str`, `source_question_id: str`, `created_round: int` (`ge=1`). These are
what the round cap emits, and they are rendered into the baby PRD's "Assumptions" section where the
user sees them at Gate 1.

**`ConditionResult`**

| Field | Type |
|---|---|
| `condition` | `ConditionId` |
| `structural_pass` | `bool` |
| `judge_pass` | `bool \| None` (`None` = judge not reached, either gated off by the structural layer or not applicable, as for C4) |
| `overall` | `bool` |
| `detail` | `str` |

Model validator `check_two_layer_invariant` — **this is loopr's central invariant, expressed as a
schema rule**: `overall` may be `True` only if `structural_pass` is `True`, **and** (`judge_pass` is
`True` **or** the condition is `C4_BOUNDARY`). A judge pass can never carry a condition on its own.
Constructing a `ConditionResult` that violates this raises, rather than producing a wrong stop.

**`InterrogationState`** — the root persisted object.

| Field | Type | Default |
|---|---|---|
| `schema_version` | `int` | `1` |
| `mode` | `Mode` | — |
| `repo_root` | `str` | — |
| `problem_statement` | `str \| None` | `None` |
| `problem_statement_prefilter_flagged` | `bool` | `False` — advisory only; §6.5.1 |
| `acceptance_criteria` | `list[AcceptanceCriterion]` | `[]` |
| `scope_edges` | `list[ScopeEdge]` | `[]` |
| `boundary` | `Boundary \| None` | `None` |
| `context_notes` | `list[ContextNote]` | `[]` |
| `open_questions` | `list[OpenQuestion]` | `[]` |
| `assumptions` | `list[Assumption]` | `[]` |
| `condition_results` | `list[ConditionResult]` | `[]` |
| `consecutive_judge_failures` | `dict[ConditionId, int]` | `{}` — drives the C1 anti-loop guard |
| `round` | `int` | `1` (`ge=1`) |
| `max_rounds` | `int` | `8` (`ge=1`, `le=50`) |
| `gates` | `dict[GateId, GateRecord]` | `{}` |
| `brownfield` | `"BrownfieldState \| None"` | `None` — forward reference; §3.9 |
| `judge_log` | `list["JudgeExchange"]` | `[]` — forward reference; §3.9 |

Model validator `check_mode_coherent`: `mode == BROWNFIELD` iff `brownfield is not None`. A
greenfield run carrying brownfield state, or the reverse, is a corrupt state and must raise.

### 3.3 `models/brownfield.py`

**`EvidenceBundle`** — as amended 2026-07-28 (`loopr-PRD.md` §5 A3a; amendment note in
`docs/conformance-classification-spec.md` §3).

| Field | Type | Constraint / note |
|---|---|---|
| `pattern_id` | `str` | `min_length=1` |
| `description` | `str` | `min_length=1`; plain language |
| `locations` | `list[str]` | `min_length=1`; `file:line`, representative |
| `occurrence_count` | `int` | `ge=1` |
| `centrality` | `Centrality` | import-graph heuristic |
| `git_last_touched_days_ago` | `int \| None` | `ge=0` |
| `git_top_author_commit_share` | `float \| None` | `ge=0.0, le=1.0` — **replaces** `git_distinct_authors`; `OWN_COMMIT` per [arXiv:2408.12807](https://arxiv.org/abs/2408.12807) RQ4 |
| `git_major_author_count` | `int \| None` | `ge=0` — developers above 5% ownership (`MAJOR_COMMIT`) |
| `deprecation_markers` | `list[str]` | default `[]` |
| `naming_flags` | `bool` | default `False` |
| `signal_qualifiers` | `list[str]` | default `[]`. **Populated by code, sent to the judge, never empty when a weak signal is present.** §6.7.2 / §7 G-13. |

**`PatternClassification`** — `pattern_id: str`, `verdict: Verdict`, `reason: str` (`min_length=1`).
No confidence field: `AMBIGUOUS` already carries "not confident enough to call it"
(`docs/conformance-classification-spec.md` §4).

**`BrownfieldState`**

| Field | Type | Default |
|---|---|---|
| `touched_surface` | `list[str]` | `[]` |
| `touched_surface_confirmed_hash` | `str \| None` | `None` |
| `pattern_candidates` | `list[EvidenceBundle]` | `[]` |
| `classifications` | `list[PatternClassification]` | `[]` |
| `gate_3_confirmed` | `bool` | `False` |

`gate_3_required` is a **`@property`, not a field** — it recomputes
`any(c.verdict is Verdict.CONFLICT for c in self.classifications)`. A stored flag could go stale;
`docs/conformance-classification-spec.md` §7 requires it be computed. A reviewer finding
`gate_3_required` as a settable field should treat it as a defect.

### 3.4 `models/judge.py` — the scope-enforcement mechanism

This is where the "judge sees exactly its documented scope, never more" invariant stops being a
review convention and becomes a runtime error.

```python
JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]

ALLOWED_INPUTS: Mapping[JudgeCallType, frozenset[str]] = {
    JudgeCallType.C1_OUTCOME:     frozenset({"problem_statement", "prefilter_flagged"}),
    JudgeCallType.C2_ACCEPTANCE:  frozenset({"acceptance_criteria"}),
    JudgeCallType.C3_SCOPE_EDGES: frozenset({"scope_edges"}),
    JudgeCallType.C5_SOFT_CONTEXT: frozenset({"context_note", "acceptance_criteria"}),
    JudgeCallType.C6_LOAD_BEARING: frozenset({"question_text", "acceptance_criteria",
                                              "scope_edges", "boundary"}),
    JudgeCallType.BF_RELEVANCE:   frozenset({"candidate_files", "problem_statement",
                                             "acceptance_criteria", "scope_edges"}),
    JudgeCallType.BF_CLASSIFY:    frozenset({"evidence_bundle", "problem_statement",
                                             "acceptance_criteria", "scope_edges", "boundary"}),
}
```

`ALLOWED_INPUTS` is the machine-readable transcription of the Shape 1 / Shape 2 discipline:
C1/C2/C3 are Shape 1 (single field, plus C1's advisory flag); C5/C6/BF_* are Shape 2 (field plus the
specific fields their rubric names). It must match `docs/stopping-test-spec.md` §Design approach and
`docs/conformance-classification-spec.md` §1/§4 exactly.

**`JudgeRequest`** — `model_config` adds `frozen=True`; this is an immutable audit record.

| Field | Type |
|---|---|
| `call_id` | `str` — deterministic (§6.2.3), never random |
| `call_type` | `JudgeCallType` |
| `rubric_id` | `str` |
| `rubric_text` | `str` |
| `inputs` | `dict[str, JsonValue]` |
| `created_round` | `int` (`ge=1`) |
| `envelope_version` | `int` = `1` |

Model validator `check_scope`: **`set(inputs.keys()) == ALLOWED_INPUTS[call_type]`** — exact set
equality, not subset. Over-scoping raises `JudgeScopeError`; *under*-scoping raises too, because a
missing input silently changes what the rubric is answering. This is the single most important
validator in the codebase.

**`JudgeResponse`**

| Field | Type | Note |
|---|---|---|
| `call_id` | `str` | must match the request |
| `passed` | `bool \| None` | condition calls (C1/C2/C3/C5/C6) |
| `verdict` | `Verdict \| None` | `BF_CLASSIFY` only |
| `selected_files` | `list[str] \| None` | `BF_RELEVANCE` only |
| `reason` | `str` | `min_length=1` — always required |
| `missing` | `str \| None` | what to ask for next |
| `misplaced` | `bool` | default `False`; C5 only (`docs/stopping-test-spec.md` §Condition 5) |

Model validator `check_response_shape`: exactly the response field matching the call type may be
non-`None`. A `BF_CLASSIFY` response carrying `passed` is malformed.

**`JudgeExchange`** — `request: JudgeRequest`, `response: JudgeResponse`,
`request_sha256: str`, `response_sha256: str`, `answered_at_round: int`. Appended to
`InterrogationState.judge_log` and **never mutated or removed**. This log is what makes the judge
audit-able after the fact (§7 G-1) and what `loopr replay` replays.

### 3.5 `models/gates.py`

**`GatePayload`** — `gate: GateId`, `title: str`, `body_markdown: str`, `digest: str` (SHA-256 of
`body_markdown`).

**`GateRecord`** — `gate: GateId`, `requested_round: int`, `payload_digest: str`,
`confirmed: bool` (default `False`), `confirmed_payload_digest: str | None`,
`user_amendment: str | None`. A confirmation is bound to the exact payload digest confirmed; if the
payload changes, the confirmation no longer matches and the gate re-fires (§6.6.2).

### 3.6 `JsonValue`, not `Any`

`disallow_any_explicit = true` (§2.5) forbids `Any`. `JudgeRequest.inputs` uses the recursive
`JsonValue` alias above. Under Python 3.14 the recursive alias needs `model_rebuild()` — see §3.9.

### 3.7 Every model is `extra="forbid"`

Inherited from `LooprBase`. `test_judge_scope.py` includes a reflective test that walks every
`BaseModel` subclass exported from `loopr.models` and asserts
`model.model_config.get("extra") == "forbid"`, so a future model added without inheriting the base
fails CI rather than review.

### 3.8 What is deliberately NOT a model

Rubric text (frozen module-level data, §1.4), file-path strings, and git command output. Judge
*responses* are always models; judge-adjacent plumbing is not.

### 3.9 Forward-reference discipline

Three forward references exist:

1. `InterrogationState.brownfield: "BrownfieldState | None"` — `brownfield.py` imports nothing from
   `interrogation.py`, so this is a one-directional string annotation.
2. `InterrogationState.judge_log: list["JudgeExchange"]`.
3. `JsonValue`'s self-reference.

`models/__init__.py` must, after importing all modules, call `InterrogationState.model_rebuild()` and
`JudgeRequest.model_rebuild()`. Per `loopr-MIGRATION.md` §8, **no unresolved forward reference may
remain**: `test_state_store.py` asserts `InterrogationState.__pydantic_complete__ is True` and
round-trips a fully-populated state through `model_dump_json()` / `model_validate_json()`.

---

## §4 API Route Signatures

**N/A — stated explicitly, not left blank.**

loopr Phase 1 is a CLI and importable library. It exposes **no HTTP routes, no server, no listening
socket, and makes no outbound network request.** The LLM-routing decision in §6.2 is what makes this
so: because the module never calls a model API, it needs no HTTP client, no base URL, no auth header,
and no retry/backoff policy.

The nearest analogue to a route table is the CLI command surface and its exit-code contract, which is
specified in §6.1. The nearest analogue to a request/response schema is `JudgeRequest` /
`JudgeResponse` (§3.4), which cross a **process boundary, not a network boundary**.

If any phase introduces an HTTP surface, it must first re-argue `loopr-PRD.md` §8's no-paid-dependency
rule, because the only reason to add one is to call a paid model API.

---

## §5 Migrations

**N/A — stated explicitly, not left blank.**

loopr has no database. Nothing in the PRD implies one, and none is introduced here. All state is a
single JSON file (`.loopr-state/state.json`, §6.3), and all output is Markdown under
`.claude/loopr/` in the target repo.

The one migration-shaped concern is **state-file schema evolution**, handled without a migration
framework: `InterrogationState.schema_version` is an `int`, currently `1`. `StateStore.load()` raises
`StateVersionError` on any value it does not recognise rather than attempting a silent upgrade
(§6.3.3). Phase 1 ships version 1 only and therefore ships no migration code. A future version bump
adds an explicit upgrade function; guessing at one now would be speculative.

---

## §6 Implementation Logic Flow

### 6.1 CLI surface and the exit-code contract — `cli.py`

```python
def main(argv: Sequence[str] | None = None) -> int: ...
```

`main` returns the exit code; the console script wraps it in `sys.exit`. `main` never raises to the
caller — it catches `LooprError` and maps to code 40.

| Command | Signature | Purpose |
|---|---|---|
| `loopr init` | `--repo PATH --mode {greenfield,brownfield} [--state PATH] [--max-rounds N]` | Create the state file. Fails if one exists (no silent overwrite). |
| `loopr step` | `--state PATH [--judge-response FILE] [--gate-response FILE] [--answer FILE]` | Advance the machine by one step. The workhorse. |
| `loopr status` | `--state PATH [--json]` | Print condition results, round, pending gate. Read-only, never mutates. |
| `loopr emit` | `--state PATH [--out DIR]` | Render artifacts. Refuses unless all six conditions pass. |
| `loopr replay` | `--state PATH --fixtures DIR` | Re-run every logged judge call against a scripted client; report divergence. |

**Exit codes — the machine-readable contract the invoking agent drives on:**

| Code | Name | Meaning | Agent's next action |
|---|---|---|---|
| `0` | `OK` | Step completed; state advanced; nothing pending | Re-invoke `step` |
| `10` | `JUDGE_REQUIRED` | One `JudgeRequest` written to `<state-dir>/pending_judge.json` | Answer it; re-invoke with `--judge-response` |
| `20` | `GATE_REQUIRED` | A `GatePayload` written to `<state-dir>/pending_gate.md` | Show the human; re-invoke with `--gate-response` |
| `30` | `QUESTION_REQUIRED` | A targeted follow-up written to `<state-dir>/pending_question.md` | Ask the user; re-invoke with `--answer` |
| `40` | `HALT` | Invariant violation, corrupt state, scope error, a supplied `--judge-response` that never matched the call actually pending (FIX 3), or a state file that failed to load -- corrupt JSON, schema validation failure, or unrecognised `schema_version` (`StateLoadError`; see `docs/stopping-test-spec.md`) | Stop; surface to human. **Never retried automatically.** |
| `50` | `COMPLETE` | All six conditions pass; artifacts emitted | Stop; spec phase done |
| `2` | `USAGE` | Bad arguments | Fix invocation |

Codes are module-level named constants, not literals. `40` is terminal by design — a lesson carried
directly from the abandoned harness, which retried deterministic failures because it could only
distinguish "clean status vs not" (`loopr-MIGRATION.md` §7). **Exactly one** of the three pending
files may exist at a time; `step` asserts this on entry and HALTs otherwise.

### 6.2 THE LLM-ROUTING DECISION

> **This is the decision Step 10 §3 required be resolved explicitly here rather than assumed.**

#### 6.2.1 The decision

**loopr's module never calls an LLM API.** It is a pure, resumable state machine over a persisted
state file. When a judge call is needed, it serialises exactly one `JudgeRequest`, writes it to
`pending_judge.json`, and exits `10`. The **invoking agent** — Claude Code by default, using that
session's own model — reads the envelope, produces a `JudgeResponse`, and re-invokes `step
--judge-response`. The module resumes from persisted state.

#### 6.2.2 Why, in order of force

1. **The hard boundary decides it.** `loopr-PRD.md` §8: no paid dependency, ever, for core
   functionality; §3 of the Step 10 instruction: never a required API key for the six-condition test
   to run. A direct-API binding needs a vendor SDK and a key. Both are excluded. This is a
   consequence, not a preference.
2. **Zero setup is a success metric.** `loopr-PRD.md` §13 requires loopr work with zero setup. An
   agent-answered judge inherits the session's existing auth — no key, no config, no signup.
3. **It makes the scoping invariant mechanically checkable.** Because the envelope is the *complete*
   input and it is on disk, "the judge saw only its documented scope" is greppable by the review
   agent and assertable in tests. An in-process API call would bury the same property in a prompt
   string. The invariant loopr most needs to prove becomes an artifact.
4. **It is crash-safe and resumable** — kill it mid-run, re-invoke, it re-derives from the state
   file. Same instinct as git-marker discovery (`loopr-PRD.md` §B2): the disk is the ground truth.
5. **It makes the whole engine testable headlessly** with `ScriptedJudgeClient` and zero tokens.

#### 6.2.3 The port

```python
class JudgeClient(Protocol):
    def ask(self, request: JudgeRequest) -> JudgeResponse | None: ...
```

Returning `None` means "cannot answer in-process — caller must suspend." Two Phase 1 implementations:

- **`AgentJudgeClient`** (default). `ask` writes the envelope, returns `None`. The CLI translates
  that to exit `10`. On re-invocation with `--judge-response`, the CLI loads and validates the
  response, matches `call_id`, appends a `JudgeExchange`, deletes `pending_judge.json`, continues.
- **`ScriptedJudgeClient`** (tests, `replay`). Constructed from a fixture mapping `call_id →
  JudgeResponse`; `ask` returns the fixture or raises `MissingFixtureError`. **Never falls back to a
  live call** — a missing fixture is a test failure, not a network request.

`call_id` is **deterministic**: `sha256(f"{call_type}|{round}|{canonical_json(inputs)}")`, truncated
to 16 hex chars. Never `uuid4`, never `Date.now()`. This is what makes `replay` a real reproducibility
check: identical inputs produce an identical `call_id`, so a fixture keyed on it matches only if the
inputs genuinely did not change.

#### 6.2.4 What is explicitly NOT built

`ApiJudgeClient` — a direct vendor-SDK binding. Named here so its absence is visibly deliberate. It
would require a key and a paid dependency; it is a **non-goal** (§9). If a later phase argues for it,
it must be strictly optional, absent from `dependencies`, imported lazily inside the function that
uses it, and the six-condition test must run fully without it.

### 6.3 State persistence — `state/store.py`

```python
class StateStore:
    def __init__(self, path: Path) -> None: ...
    def load(self) -> InterrogationState: ...
    def save(self, state: InterrogationState) -> None: ...
    @property
    def dir(self) -> Path: ...
```

1. **Atomic writes.** `save` writes to `state.json.tmp` in the same directory, `flush()` +
   `os.fsync()`, then `os.replace()`. A crash mid-write must never leave a truncated state file.
2. **Canonical serialisation.** `model_dump_json(indent=2)` with sorted keys, trailing newline. The
   state file is diffable and reviewable — it is evidence, not an opaque blob.
3. **Version guard.** `load` reads `schema_version` *before* full validation; unrecognised → raise
   `StateVersionError` (exit 40). Never silently upgrade (§5).
4. Default location `<repo_root>/.loopr-state/`, overridable by `--state`. **Distinct from
   `.claude/loopr/`**, which holds user-facing artifacts. Working state is gitignored; artifacts are
   committed. Conflating them would put churn in the user's repo — the failure `loopr-PRD.md` §9
   forbids.

### 6.4 `step()` — the single state advance — `interrogation/loop.py`

```python
def step(
    state: InterrogationState,
    judge: JudgeClient,
    inbound: InboundPayload | None = None,
) -> StepOutcome: ...
```

`InboundPayload` is a tagged union of `JudgeResponse`, `GateResponse`, `UserAnswer`.
`StepOutcome` carries the new state, an exit code, and an optional pending payload. **`step` is
pure with respect to the filesystem** — it does not read or write files; the CLI does. That is what
makes it testable.

**Ordered algorithm. The order is load-bearing; do not reorder.**

1. **Apply inbound**, if any. Judge response → validate `call_id`, append `JudgeExchange`, apply the
   verdict to the target field. Gate response → §6.6. User answer → merge into state fields.
2. **Brownfield precondition.** If `mode == BROWNFIELD` and the boundary is confirmed but the
   touched surface is not, run discovery (§6.7.1) and request Gate 2's touched-surface section.
   *This runs before condition evaluation* because classification can create `OpenQuestion`s that
   condition 6 must then see in the same pass.
3. **Evaluate all six conditions** via `checks.conditions.evaluate_all`. Every round, all six — not
   gated in strict 1→6 order, because a later answer can opportunistically close an earlier gap
   (`docs/stopping-test-spec.md` §Cross-condition sequencing). Structural checks are pure and run
   first, always. If a condition needs a judge call and its structural check passed, `evaluate_all`
   returns a *pending call*; `step` issues **exactly one** judge call per invocation and returns.
4. **Round-cap check.** If `state.round >= state.max_rounds`, run force-resolution (§6.8) *before*
   deciding to continue.
5. **All six true?** → Gate 3 if required and unconfirmed (§6.6.3), else Gate 1 (§6.6.4), else emit
   artifacts and return `COMPLETE`.
6. **Not all true?** → select the **lowest-numbered false condition**, build a targeted follow-up
   (§6.5), increment `round`, return `QUESTION_REQUIRED`.

**Exactly one judge call, one question, or one gate per invocation.** No batching. This is not a
performance compromise — it is the design property the literature supports: batching fourteen
criteria into one call left only 1/30 outputs clean, while single-criterion targeting hit 84.3%
([arXiv:2507.02858](https://arxiv.org/abs/2507.02858) §IV-C, §V-D). Batching judge calls is a
**defect**, not an optimisation.

### 6.5 Deterministic anchors — `checks/structural.py`

Every function here is **pure**: no I/O, no model call, no randomness, deterministic on its inputs.
This module is the anchor the entire design rests on ([arXiv:2603.05399](https://arxiv.org/abs/2603.05399)
measured 37.50% stochastic stability on identical repeated judge input — the judge cannot be the only
thing standing between a fuzzy answer and a stop).

```python
def check_c1_outcome(state) -> StructuralResult: ...
def check_c2_acceptance(state) -> StructuralResult: ...
def check_c3_scope_edges(state) -> StructuralResult: ...
def check_c4_boundary(state) -> StructuralResult: ...
def check_c5_soft_context(state) -> StructuralResult: ...
def check_c6_no_unknowns(state) -> StructuralResult: ...
```

`StructuralResult` = `passed: bool`, `detail: str`, `advisory_flags: list[str]`.

**C1.** Hard gate: `problem_statement` non-empty. Additionally runs the solution-shape pre-filter and
sets `problem_statement_prefilter_flagged`. **The pre-filter may only downgrade, never block** — it
is passed to the judge as the advisory `prefilter_flagged` input and never gates the call
(`docs/stopping-test-spec.md` §Condition 1). *An implementation where the pre-filter can fail C1 on
its own is a defect* (§7 G-5).

**C2.** `>=1` criterion, each non-empty, at least one containing an observable predicate (comparator
or observable verb). Heuristic and illustrative, untuned pending the §8 proof runs
(`docs/stopping-test-spec.md` §Decisions 4).

**C3.** `>=1` edge; each `kind ∈ {OUT, DEFERRED}`; `item` and `reason` both non-empty. Empty reason
auto-fails.

**C4.** Pure state machine, **no judge**. Passes iff `boundary is not None` and
(`boundary.declined` or (`boundary.confirmed` and
`boundary.confirmed_hash == sha256(boundary.text)`)). The hash comparison is what makes a post-confirm
tweak automatically invalidate the confirmation.

**C5.** `>=1` `ContextNote`, each with non-empty `text` and a `source`. The explicit-"none" case is a
**pass**, recorded as `ContextNote(text="user confirmed no soft context", source=STATED)` — but only
after the module has explicitly asked (§6.5.1). Never inferred from silence.

**C6.** Passes iff no `OpenQuestion` has `status == OPEN and load_bearing is True`. A question with
`load_bearing is None` is *unjudged*, not passing — it triggers a C6 judge call.

#### 6.5.1 Targeted follow-ups — `interrogation/questions.py`

```python
def build_followup(state: InterrogationState, target: ConditionId) -> str: ...
```

Produces a question aimed at exactly one failing condition. **Never emits a generic "anything else?"**
(`docs/stopping-test-spec.md` §Design approach). Question templates are frozen module data.

- **C1 anti-loop guard.** After 2 consecutive C1 judge failures
  (`consecutive_judge_failures[C1_OUTCOME] >= 2`), stop asking open-endedly: surface the judge's last
  two `reason` strings **verbatim** and ask the user to restate the outcome directly.
  `consecutive_judge_failures` resets to 0 on any pass.
- **C5 must ask before it may accept "none."** The C5 follow-up explicitly offers the null option
  ("any boss-said / political / watch-out constraints, or is this a clean slate?"). Only an explicit
  "none" answer may write the sentinel note.

### 6.6 Gates — `gates/gates.py`

#### 6.6.1 Chronology

Written-up order is Gate 1, 2, 3; **chronological firing order is Gate 2 → Gate 3 → Gate 1**
(`loopr-PRD.md` §4; `docs/conformance-classification-spec.md` §6). Condition 4 requires a confirmed
boundary before interrogation can stop, so Gate 2 necessarily fires *during* interrogation. Gate 3
follows it (classification runs over the confirmed touched surface). Gate 1 is the final confirm on
an already-settled spec. **An implementation that fires Gate 1 first is a defect** (§7 G-8).

#### 6.6.2 Confirmation binding

```python
def request_gate(state, gate: GateId, payload: GatePayload) -> StepOutcome: ...
def apply_gate_response(state, response: GateResponse) -> InterrogationState: ...
def gate_is_satisfied(state, gate: GateId) -> bool: ...
```

`gate_is_satisfied` returns `True` only if a `GateRecord` exists, `confirmed` is `True`, **and**
`confirmed_payload_digest` equals a freshly-computed digest of the current payload. Any edit to the
underlying content re-fires the gate automatically. No dirty flag anyone can forget to set.

#### 6.6.3 Gate 2 — boundary (+ touched surface, brownfield)

One confirm moment, not two. Payload carries the proposed boundary text and, for brownfield, the
proposed touched-surface file list as an added section
(`docs/conformance-classification-spec.md` §1). The user may confirm, tweak, or decline the boundary
(setting `declined`), and may add/remove files. Tweaking the boundary text clears `confirmed` and
`confirmed_hash` via §6.5's C4 hash comparison.

#### 6.6.4 Gate 3 — CONFLICTs only, batched

Fires **iff** `brownfield.gate_3_required` and not `gate_3_confirmed`. Payload contains **only
CONFLICT verdicts**, all in one confirmation. CONFORM and DO_NOT_REPLICATE never reach the user —
they go straight to the ledger. This scoping is the mitigation for conflict-gate fatigue
(`loopr-PRD.md` §10); *a Gate 3 payload containing a non-CONFLICT verdict is a defect* (§7 G-9).

#### 6.6.5 Gate 1 — baby PRD via TL;DR

Payload leads with the TL;DR and includes the "Assumptions" section listing every force-resolved
question (§6.8), so the user sees them at the moment they can still object. Chronologically last.

### 6.7 Brownfield — `brownfield/`

#### 6.7.1 Touched-surface discovery, two stages

```python
def prefilter_candidates(repo_root: Path, state: InterrogationState) -> list[str]: ...
def build_relevance_request(candidates, state) -> JudgeRequest: ...
def apply_relevance_response(state, response) -> InterrogationState: ...
```

Stage 1 is deterministic and free: keyword search seeded from `problem_statement`,
`acceptance_criteria`, and `scope_edges`, plus a one-hop import-graph expansion. **Cast wide
deliberately — this stage optimises recall, not precision**, and is the primary mitigation for
touched-surface miss (`loopr-PRD.md` §10). Respects `.gitignore`; skips binaries and vendored
directories.

Stage 2 is one `BF_RELEVANCE` judge call over **file paths plus short summaries, never full file
contents** (`docs/conformance-classification-spec.md` §1). The result is proposed to the user at
Gate 2, never silently trusted.

#### 6.7.2 Evidence bundles

```python
def discover_patterns(repo_root: Path, touched_surface: Sequence[str]) -> list[EvidenceBundle]: ...
```

A candidate qualifies as a pattern if `occurrence_count >= 3` **or** it is a structural touchpoint
the new work must interact with regardless (`docs/conformance-classification-spec.md` §2). Signals
are gathered by pure code: `git log` for recency and ownership, `grep` for deprecation markers,
import-graph for centrality.

**Ownership must be commit-based.** Compute `git_top_author_commit_share` and
`git_major_author_count` from `git log --format=%ae -- <path>`, **not** from `git blame`. The two
approaches identify only 0–40% of the same developers, and only the commit-based one is associated
with defect-proneness ([arXiv:2408.12807](https://arxiv.org/abs/2408.12807) RQ1, RQ4, §V Rec. 1).
*An implementation using `git blame` for ownership is a defect* (§7 G-14).

**`signal_qualifiers` must be populated whenever a weak signal is present.** This is not
decoration — it is how the judge is told what not to over-trust (§7 G-13):

| Condition | Qualifier text (verbatim) |
|---|---|
| `git_last_touched_days_ago` is high | `"staleness alone is not sufficient for DO_NOT_REPLICATE; stable mature code is also old"` |
| `deprecation_markers` non-empty | `"a deprecation marker may indicate on-hold debt (correct code blocked on an external event), not cruft"` |
| `occurrence_count == 3` | `"at the minimum recurrence threshold; weak evidence of intentionality"` |
| `naming_flags` is `True` | `"naming heuristic only; no validated basis"` |

#### 6.7.3 Classification and routing

```python
def build_classify_request(bundle, state) -> JudgeRequest: ...
def route_verdict(state, classification) -> InterrogationState: ...
```

One `BF_CLASSIFY` call per bundle — never batched. Routing
(`docs/conformance-classification-spec.md` §5):

- **CONFORM / DO_NOT_REPLICATE** → appended to `classifications`; written to `conformance-ledger.md`;
  no gate.
- **CONFLICT** → appended; `gate_3_required` becomes `True` by recomputation.
- **AMBIGUOUS** → appended **and** an `OpenQuestion` is created with
  `origin=QuestionOrigin.PATTERN_AMBIGUITY`, `text` encoding the pattern description, the evidence
  summary, and why it is ambiguous. From there it is indistinguishable from any other open question:
  condition 6's existing Shape 2 call judges it load-bearing, and the round cap can force-resolve it.
  **No seventh condition, no parallel gate** (`loopr-MIGRATION.md` §1a).

### 6.8 Round-cap force-resolution

Triggered at the start of round `max_rounds` (default 8), *before* the continue/stop decision.

For every `OpenQuestion` with `status == OPEN`, **load-bearing or not**:

1. Draft a best-guess answer and write it to `resolution`.
2. Append an `Assumption` naming the question, the guess, and the round.
3. Set `status = DEFERRED_NON_LOAD_BEARING` and `force_resolved = True`.

Termination is then guaranteed in bounded time regardless of judge behaviour. The cost is paid
visibly: every forced assumption appears in the baby PRD's "Assumptions" section and is surfaced at
Gate 1, where the user can kick any of them back into a real question
(`docs/stopping-test-spec.md` §Condition 6B).

**Silent force-resolution is the single worst failure this module can have** — it would convert
"loop forever" into "quietly ship a guess," which is strictly worse. `test_round_cap.py` asserts that
the count of forced assumptions in state equals the count rendered into the baby PRD (§7 G-6).

`max_rounds = 8` is a **calibratable default, not an empirical optimum** — see the honest framing and
its two caveats in `loopr-PRD.md` §5 A1. The §8 proof runs calibrate it
(`docs/stopping-test-spec.md` §Decisions 1).

### 6.9 Work-package sequence

Commit ordering within the single phase. Each boundary is a green-bar checkpoint: `mypy --strict`
clean, tests passing.

| WP | Contents | Checkpoint |
|---|---|---|
| **A** | `pyproject.toml`, `models/`, `py.typed` | Models round-trip; `__pydantic_complete__` true; every model `extra="forbid"` |
| **B** | `judge/`, `rubrics/` | `JudgeRequest` scope validator rejects over- and under-scoped inputs |
| **C** | `checks/`, `state/` | Six structural checks pass unit tests; two-layer invariant enforced |
| **D** | `interrogation/`, `gates/`, `cli.py` | Full greenfield run to `COMPLETE` under `ScriptedJudgeClient` |
| **E** | `brownfield/` | Full brownfield run incl. Gate 3, against a fixture git repo |
| **F** | `artifacts/` | All three artifacts render; assumption-count parity holds |
| **G** | Proof runs (§8) | Both real projects; `proofs/**` populated |

**Commits carry no AI attribution** — no `Co-Authored-By`, no "Generated with" trailer, no emoji
(`loopr-MIGRATION.md` §8). Commit plainly as the author.

---

## §7 Failure-Mode Guards

Every entry in `loopr-PRD.md` §10, including the three brownfield entries and the three added
2026-07-28, mapped to a Phase 1 guard and a concrete review-agent check.

| # | Failure mode (PRD §10) | Guard in Phase 1 | What the review agent checks |
|---|---|---|---|
| **G-1** | **Premature draft** — baby PRD drafted before the six conditions hold | `emit` refuses unless all six `ConditionResult.overall` are `True`; `step` reaches Gate 1 only via §6.4 branch 5 | Grep `artifacts/` for any render path not behind the six-condition guard. Confirm `ConditionResult.check_two_layer_invariant` exists and that no code constructs `ConditionResult` with `model_construct` (which skips validation) |
| **G-2** | **Unread gate** — user rubber-stamps the baby PRD | Gate 1 payload is TL;DR-first; assumptions listed at the top of the body | Confirm the Gate 1 payload builder emits TL;DR before body, and that forced assumptions are in the payload, not only in the file |
| **G-3** | **Boundary over-fit to examples** — proposal flavoured by the author's context | Boundary proposal reads only from this user's `context_notes`; no example catalogue ships in the engine | Grep `src/loopr/` for domain nouns: `shariah`, `kaide`, `mizan`, `halal`, `gcp`, `vertex`, `bigquery`. **Must return zero.** `test_no_hardcoded_domain.py` enforces it |
| **G-4** | (Rubric drift) | Rubric text is frozen module data, not f-strings; `rubric_id` recorded in every `JudgeRequest` | Confirm no rubric string is built by interpolation. Variable content belongs in `inputs`, never in `rubric_text` |
| **G-5** | (C1 pre-filter over-reach) | Pre-filter sets an advisory flag only; never gates the judge call | Confirm `check_c1_outcome` returns `passed=True` on a non-empty statement even when flagged, and that `prefilter_flagged` appears in `ALLOWED_INPUTS[C1_OUTCOME]` as an input, not a gate |
| **G-6** | **Silent assumption** — round cap resolves questions invisibly | Every force-resolution writes an `Assumption`, rendered in the baby PRD and surfaced at Gate 1 | Assert parity: `len(state.assumptions)` == count of assumptions rendered. Confirm no code path sets `status = DEFERRED_NON_LOAD_BEARING` without appending an `Assumption` |
| **G-7** | **Context.md rot** — blind appends | `context_md.py` renders a current-state header, a sectioned body, and supersession pointers (`loopr-PRD.md` §7) | Confirm the renderer is not an append-only writer and that a superseded note retains a pointer rather than being deleted |
| **G-8** | (Gate chronology inversion) | Gate order enforced in `step` branch 5: Gate 3 before Gate 1; Gate 2 during interrogation | Trace `step`; confirm Gate 1 is unreachable while `gate_3_required and not gate_3_confirmed` |
| **G-9** | **Conflict-gate fatigue (brownfield)** | Gate 3 payload contains CONFLICT verdicts only, batched into one confirmation | Assert the Gate 3 payload builder filters on `Verdict.CONFLICT`. A CONFORM entry in a Gate 3 payload is a defect |
| **G-10** | **Silent cruft inheritance (brownfield)** | Every qualifying pattern gets an explicit verdict; no pattern is applied without one | Confirm no code path writes to the ledger without a `PatternClassification`. Confirm the `>=3`-or-structural-touchpoint bar is applied, not skipped |
| **G-11** | **Touched-surface miss (brownfield)** | Two-stage discovery with a deliberately wide stage 1; user adjusts at Gate 2 | Confirm stage 1 is not narrowed by a relevance threshold, and that the Gate 2 payload includes the file list as an editable section |
| **G-12** | **Google/Kaide leakage** — author-specific content in the generic engine | No domain catalogue anywhere in `src/loopr/` | Same grep as G-3, plus: no required env var. Grep for `os.environ` / `getenv` — **any read of `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY` is an immediate HALT**. Confirm `dependencies == ["pydantic>=2.13,<3"]` |
| **G-13** | **Signal laundering (added 2026-07-28)** | `signal_qualifiers` populated for every weak signal; rubric names each signal's known weakness | Confirm each §6.7.2 qualifier condition is implemented and that `BF_CLASSIFY` rubric text contains the staleness and on-hold-debt caveats |
| **G-14** | (Ownership signal regression) | Commit-based ownership only | Grep `brownfield/evidence.py` for `blame` — **must return zero**. Confirm `git_distinct_authors` does not reappear as a field |
| **G-15** | **Judge nondeterminism read as signal (added 2026-07-28)** | Structural layer gates every judge call; every exchange logged with digests; round cap bounds flip cost | Confirm `judge_log` is append-only (no code removes or mutates entries) and that `call_id` is derived by hash, never `uuid4` or a timestamp |
| **G-16** | **Overclaimed brownfield validation (added 2026-07-28)** | Novelty stated in PRD §5 A3a, here in §8, and in the ledger's own header | Confirm `conformance_ledger.py` renders a header stating the classification is unvalidated and human-escalation-backed |
| **G-17** | **Judge over-scoping** | `JudgeRequest.check_scope` exact set equality | Confirm every judge-call construction goes through a `build_*_request` helper. **Any direct `JudgeRequest(...)` construction outside `judge/` or `brownfield/` is a defect.** Confirm `ALLOWED_INPUTS` matches the two operationalization specs exactly |
| **G-18** | **Harness lied about why it stopped** (`loopr-MIGRATION.md` §7) | Distinct exit codes per condition; `40` terminal and never auto-retried | Confirm no retry loop wraps a `40`, and that codes are named constants |

**Not applicable in Phase 1**, stated so their absence is not read as an oversight: *silent two-tier*
and *checker writes approval* (`loopr-PRD.md` §10) belong to the parked Phase B harness — Phase 1
builds no tiers and no reviewer. They are non-goals (§9), not gaps.

---

## §8 Phase Acceptance Criteria

All must pass. The review agent verifies each; any failure blocks approval.

### 8.1 Gates (deterministic, machine-checkable)

| # | Criterion |
|---|---|
| **A-1** | `mypy --strict src/loopr tests` exits 0. Zero errors. Any `# type: ignore` carries an adjacent comment naming the upstream issue |
| **A-2** | `pytest` exits 0. Line coverage of `src/loopr/` ≥ 85%; `checks/`, `judge/`, and `gates/` ≥ 95% — these three carry the invariants |
| **A-3** | Runtime dependency set is exactly `{"pydantic"}`; `test_no_paid_dependency.py` passes |
| **A-4** | `test_no_hardcoded_domain.py` passes — zero domain-specific nouns in `src/loopr/` |
| **A-5** | Every `BaseModel` exported from `loopr.models` has `extra="forbid"`; `InterrogationState.__pydantic_complete__` is `True` |
| **A-6** | `JudgeRequest` rejects both over-scoped and under-scoped `inputs` for all seven call types (14 test cases minimum) |
| **A-7** | `loopr replay` on both proof runs reports zero divergence — identical inputs reproduce identical `call_id`s |
| **A-8** | No outbound network call: no HTTP client in `dependencies`, no `os.environ` read of any `*_API_KEY` |
| **A-9** | Commits contain no AI attribution — no `Co-Authored-By`, no "Generated with", no emoji |

### 8.2 Behavioural (scripted, no tokens)

| # | Criterion |
|---|---|
| **B-1** | A full greenfield run reaches `COMPLETE` under `ScriptedJudgeClient`, emitting baby PRD + `context.md` under `.claude/loopr/` |
| **B-2** | A full brownfield run against a fixture git repo reaches `COMPLETE`, additionally emitting `conformance-ledger.md`, with Gate 3 firing on a seeded CONFLICT |
| **B-3** | A brownfield run with **zero** CONFLICTs never fires Gate 3 — graceful degradation, matching Gate 2's behaviour when no boundary exists |
| **B-4** | Round-cap test: a run seeded with a permanently-unresolvable question terminates at round 8 with a visible `Assumption`, and assumption-count parity (G-6) holds |
| **B-5** | Crash-safety: killing the process between any two `step` invocations and re-invoking resumes at the identical state; the state file is never truncated |
| **B-6** | Boundary-tweak test: editing `boundary.text` after confirmation automatically invalidates it and re-fires Gate 2 |
| **B-7** | C1 anti-loop: two consecutive C1 judge failures produce a restate-directly prompt quoting both judge reasons verbatim, not a third open-ended question |

### 8.3 The three acceptance signals, on two real projects

Per `loopr-PRD.md` §3 and `loopr-MIGRATION.md` §9 step 4. **One real greenfield project AND one real
brownfield project** — real, not fixtures. Evidence in `proofs/{greenfield,brownfield}/FINDINGS.md`.

| # | Signal | Evidence required |
|---|---|---|
| **C-1** | **TL;DR moment** — "this understood my problem better than I did" | The Gate 1 TL;DR as presented, plus the human's recorded reaction. Honest record: if it did not fire, that is a finding, not a failure to hide |
| **C-2** | **Scope-creep catch** — the boundary visibly flags something out-of-scope the user would otherwise have built | The specific item, the round it surfaced, and the user's confirmation that they would have built it |
| **C-3** | **No-rework readiness** — remaining gaps are net-new, never spec-captured-then-dropped | Enumerate every gap found after speccing; classify each as net-new or spec-dropped. **Any spec-dropped gap fails this criterion** — that is the whole promise |
| **C-4** | Both runs complete without a HALT that is not a genuine escalation | Full judge-exchange logs committed |

### 8.4 Brownfield classification quality — measured, not assumed

**This criterion exists because the research pass found no prior art, no labelled dataset, and no
published baseline for convention-vs-cruft discrimination** (`loopr-PRD.md` §5 A3a). Phase 1 may not
assert the classifier works; it must show what it did.

| # | Criterion |
|---|---|
| **D-1** | On the real brownfield project, a human independently classifies the same pattern candidates **blind to the module's verdicts**. Agreement is reported as a confusion matrix over the four verdicts |
| **D-2** | Every disagreement is enumerated with the evidence bundle that produced it. **No agreement threshold gates this phase** — there is no baseline to set one against. The requirement is that the number is *measured and published*, not that it is high |
| **D-3** | `FINDINGS.md` states plainly which of the six evidence signals actually carried the verdicts, and which proved inert. This is the calibration input for a later phase |
| **D-4** | `conformance-ledger.md` renders a header stating the classification is a novel, unvalidated mechanism backed by human escalation (G-16) |

### 8.5 Calibration outputs

`docs/stopping-test-spec.md` §Decisions 1 and 4 defer the round cap and the C1–C3 structural
heuristics to these proof runs. `proofs/*/FINDINGS.md` must report: rounds actually used per run;
whether the cap was hit; every structural-check false positive and false negative observed; and a
recommendation — keep 8, or change it, with the observed reason. **A run that reports no calibration
findings has not been examined properly.**

---

## §9 Explicit NON-GOALS

Not built in Phase 1. Each names where it belongs. **An execution agent that builds any of these has
exceeded the phase boundary, and the review agent should HALT.**

### 9.1 Later sequencing steps

| Non-goal | Belongs to |
|---|---|
| **Claude Code skill packaging** — `.claude/skills/loopr/`, `SKILL.md`, `references/`, `assets/`, progressive disclosure | Sequencing step 2 (`loopr-MIGRATION.md` §2). Only after step 1 is proven |
| **Any harness or loop** — build/review/audit tiers, git-marker phase discovery, gates-as-ground-truth, supervised-first-run, `BUILD_COMPLETE.md` | Sequencing step 3, parked (`loopr-PRD.md` §6) |
| **Traycer** — adaptation, or even evaluation against the three invariants | Sequencing step 3. First task *when that step begins*, not now |
| **Meeting bot** | Sequencing step 4 |
| **Anything Docker** — the abandoned harness is not resurrected, ported, fixed, or deleted | Nothing. Abandoned (`loopr-MIGRATION.md` §1) |
| **Subagent generation** — `.claude/agents/loopr-*.md`, per-tier model pins, read-only tool scoping | A5 outputs, after the module exists |

### 9.2 Within Phase A, but not Phase 1

| Non-goal | Note |
|---|---|
| **A4 research-grounded ultimate-PRD expansion** | Phase 1 stops at the baby PRD + `context.md` (+ ledger). The expansion is a distinct capability |
| **A5 gate generation** (`loop.gates.sh` per stack) | Coupled to the parked harness |
| **`PHASE_1_SPEC.md` generation for target projects** | loopr generating a phase spec for a *user's* project is an A5 output. **Not to be confused with this document**, which is loopr's own build spec |
| **Failure-mode catalogue generation** | Coupled to the parked audit tier |

### 9.3 Implementation non-goals

| Non-goal | Why |
|---|---|
| **`ApiJudgeClient`** — any direct vendor-SDK LLM binding | §6.2.4. Would require a key and a paid dependency |
| **Any network call, HTTP client, or `*_API_KEY` read** | §2.4, G-12. Mechanically enforced |
| **Embeddings, vector search, or a semantic index** | Researched and rejected; two-stage discovery replaces it (`loopr-PRD.md` §8) |
| **Nia or Context7 as a dependency** | Same. Not optional-with-fallback in Phase 1 — simply absent |
| **A database, ORM, or migration framework** | §5 |
| **An HTTP server or listening socket** | §4 |
| **A TUI, web UI, or interactive REPL** | The invoking agent is the interface |
| **Tuning the C1–C3 structural heuristics before the proof runs** | `docs/stopping-test-spec.md` §Decisions 4 defers tuning to real data. Hand-tuning blind is forbidden |
| **Changing `max_rounds` from 8 pre-proof** | §Decisions 1. Configurable, not re-defaulted on a hunch |
| **Rewriting `README.md`** | Still describes the abandoned harness. Phase 2 work |
| **Question-generation/grouping logic beyond targeted follow-ups** | Open in `loopr-PRD.md` §15. Phase 1 builds only the targeted-at-the-failing-condition follow-up |
| **A `context.md`-vs-baby-PRD split classifier** | Open in §15. Phase 1 uses C5's judge to detect *misplacement*, which is narrower |

---

## §10 Traceability

| This spec | Source |
|---|---|
| §3 schemas | `docs/stopping-test-spec.md` §State model; `docs/conformance-classification-spec.md` §3, §7 (as amended 2026-07-28) |
| §6.5 structural checks | `docs/stopping-test-spec.md` §Conditions 1–6 |
| §6.2 LLM routing | `loopr-PRD.md` §8 (hard rule), §15 (resolved 2026-07-28) |
| §6.6 gate chronology | `loopr-PRD.md` §4; `docs/conformance-classification-spec.md` §6 |
| §6.7 brownfield | `docs/conformance-classification-spec.md` §1–§5, §7 |
| §6.8 round cap | `docs/stopping-test-spec.md` §Condition 6B |
| §7 guards | `loopr-PRD.md` §10 (all entries, incl. 2026-07-27 brownfield and 2026-07-28 research additions) |
| §8 acceptance | `loopr-PRD.md` §3; `loopr-MIGRATION.md` §9 step 4 |
| §9 non-goals | `loopr-MIGRATION.md` §2, §9 ("Do NOT") |
| §2 pins | `docs/modernization_log.md` (2026-07-28) |
