# ADE Codebase Audit — Full Report

**Scope reviewed:** `src/` (~38,000 lines Python), `frontend/` (~8,100 lines TypeScript/React), `backlog/`, `comms/`, `requirements.txt`, `notebooks/` (original DeepLearning.AI baseline, 5 files, ~150KB).

**Method:** Static reading of the core agent loop (`src/agent/graph.py`), the run engine (`src/api/run_engine.py`, `src/api/run_executor.py`), the PDF fallback path (`src/fallback/pdf_runtime.py`), the frontend workbench components, and an automated cross-reference of every production module against every other file in the repo to find code that is written and tested but never actually called from a real execution path. Timestamps inside the zip were used to establish ordering between backlog tickets and the code that (in some cases) already fixes them.

This is organized by severity: architectural bugs in the agent loop first, then dead/decorative code, then process and bookkeeping problems, then scale/complexity issues, then a corrected account of the frontend (which is in better shape than I first reported).

---

## 1. CRITICAL — The ReAct agent is silently bypassed for 9 of ~22 document types on PDFs, including exactly the fixtures used to claim accuracy

This is the most important finding in the whole review, and it wasn't in your backlog.

**`src/api/run_engine.py`, inside `_execute_run_inner`:**

```python
if not settings.azure_api_key and not settings.azure_chat_endpoint:
    fallback_result = run_pdf_fallback(document_path, template_cls=template_cls,
                                        skill=skill, validator_config=validator_config)
    if fallback_result is None:
        raise RuntimeError("No LLM provider configured. Set AZURE_API_KEY and AZURE_CHAT_ENDPOINT...")
else:
    fallback_result = run_pdf_fallback(document_path, template_cls=template_cls,
                                        skill=skill, validator_config=validator_config)
if fallback_result is not None:
    serialized = serialize_extraction_result(run_id, definition_id, document_path, fallback_result, ...)
    ...
    return serialized   # <-- returns here. build_react_graph() / graph.invoke() never happens.
```

`run_pdf_fallback` (`src/fallback/pdf_runtime.py`) is a regex/PyMuPDF text-extraction script. It looks at two things only — file extension and skill name — **not whether an LLM is configured**:

```python
def run_pdf_fallback(document_path, *, template_cls, skill, validator_config):
    if Path(document_path).suffix.lower() != ".pdf":
        return None
    parser = _PARSERS.get(skill.name)
    if parser is None:
        return None
    ...
```

`_PARSERS` covers 9 skills: `bank_statement`, `utility_bill`, `commercial_lease`, `trade_finance_scrutiny`, `commodity_trade`, `purchase_order`, `packing_list`, `purchase_order_sf1449`, `packing_list_travel`.

**What this means in practice:** upload a PDF bank statement, utility bill, commercial lease, trade-finance doc, commodity-trade doc, purchase order, or packing list — with Azure fully configured, API key present, everything wired correctly — and the system never builds the LangGraph, never calls the LLM planner, never calls a tool, never runs the circuit breaker, never runs trajectory-cascade detection, never runs the outcome validator's iterative gap-filling. It runs a hand-written regex parser once and returns. The entire "ReAct: plan → act → observe → reflect" loop this project is built around does not execute for these cases.

**And this is exactly what your accuracy numbers are built on.** The evaluation fixtures your team calls "high value" (`src/tests/fixtures/high_value/`) are: `bank_statement`, `commercial_lease`, `commodity_trade`, `packing_list_travel`, `purchase_order_sf1449`, `trade_finance`, `utility_bill` — 7 of the 9 fallback-covered skills. I confirmed one directly:

```json
// src/tests/fixtures/high_value/bank_statement/ground_truth.json
{
  "definition_id": "def-bank-statement",
  "document_path": "../../../../../sample-data/bank-statements/sample-bank-statement-01.pdf",
  ...
}
```

And `src/tests/test_integration_real.py` runs these fixtures through `execute_run(fixture.definition_id, fixture.document_path)` — the exact function that contains the bypass above.

**Consequence:** whatever "integration real" / accuracy results exist for these 7 document types measure a deterministic regex parser, not the agent. If the agent's planning, tool selection, or gap-filling logic has bugs, this test suite structurally cannot catch them for the majority of your "high value" categories, because it never reaches that code. Conversely, if someone points to these eval numbers as evidence the *agent* works, that claim isn't supported by what actually ran.

**This is also inconsistent with the module's own docstring**, which frames the fallback as an emergency path ("gives the runtime a deterministic execution path *when no planner LLM or OCR provider is configured*") — but the code doesn't check that condition before using it. The `if/else` in `run_engine.py` looks like it's trying to preserve that intent (only raise an error in the no-LLM branch) but both branches call the fallback unconditionally, so the guard is cosmetic. This is a one-line fix (only call `run_pdf_fallback` when the provider truly isn't configured) but as written it silently overrides the "agentic" path for a meaningful fraction of your document taxonomy.

**Recommendation:** Gate `run_pdf_fallback` behind the actual "no LLM configured" condition, or explicitly make it an opt-in "fast path" definition setting rather than an automatic, silent override — and re-run/re-label your accuracy numbers once real agent runs are what's being measured for these 7 types.

---

## 2. CRITICAL (confirmed, unchanged from last review) — The guardrails subsystem is dead code

`src/agent/guardrails/` — 8 files, ~2,140 lines: `audit_logging.py`, `exfiltration_prevention.py`, `hallucination_detection.py`, `loop_detection.py`, `output_validation.py`, `pii_redaction.py`, `retry_circuit_breaker.py`, `tool_guardrails.py`.

I re-ran an automated cross-reference (every production module vs. every other file, excluding self and excluding test files) across the entire `src/` tree. Result: **all 8 guardrail modules are imported by nothing except their own tests.** `graph.py`, `run_engine.py`, `run_executor.py`, `main.py`, and every route file have zero references to `src.agent.guardrails`. The package docstring claims:

> *"No single guardrail is the last line of defense... Every output is validated, sanitized, and audited before it reaches tool execution or state mutation."*

That claim is false for the running system. It's true only inside the guardrails package's own unit tests, which exercise the functions directly without going through the pipeline. Whoever wrote or reads that docstring would reasonably believe protections exist that don't.

**Same automated scan also flagged, at lower severity:**
- `src/eval/accuracy.py` (confidence-calibration reporting) — imported only by its own test. It does correctly depend on `eval/harness.py` (so it's not itself an island), but nothing calls *it* — no script, no route, no CLI entrypoint.
- `src/eval/benchmarks.py` (the `BENCHMARK_TARGETS` / `BenchmarkResult` machinery referenced in the earlier review) — same pattern. There is no `scripts/run_benchmarks.py` or equivalent; it was built to spec (`[BLK-128]`) and tested in isolation, then never wired to anything runnable.

These two are lower stakes than the guardrails (they're reporting tools, not safety mechanisms), but they're the same underlying pattern: a ticket gets "implemented" in the sense that code exists and tests pass, without the last step of actually connecting it to something a person or CI job would run.

**Recommendation:** For guardrails specifically, this needs a decision, not a cleanup: either wire the modules into `act_node`/`observe_node`/`plan_node` for real, or delete the package and its docstring's claims. Leaving it as-is is worse than having nothing, because it will pass a code review that greps for "do we have PII redaction / loop detection / audit logging" and finds a confident yes.

---

## 3. HIGH — Two separate, non-communicating circuit breakers

- `CircuitBreaker` in `src/agent/graph.py` (lines ~58–70) — the real one, instantiated in `run_engine.py` with `threshold=3`, wired into `act_node`.
- `GlobalCircuitBreaker` in `src/agent/guardrails/retry_circuit_breaker.py` (344 lines) — dead per §2 above.

Notable detail I hadn't checked last time: the live `CircuitBreaker.is_tripped(tool_name)` / `record_failure(tool_name)` is keyed by **tool name**, even though the class docstring calls it a "per-provider" breaker. If two tools front the same underlying provider (e.g. an OCR tool and a table-detection tool both hitting the same Azure OCR endpoint), a failure storm on one won't trip the breaker for the other, and the resilience story is weaker than the docstring implies. Minor on its own, but worth fixing while someone's in this file for the fallback bug in §1.

---

## 4. HIGH — Redundant branching (the exact "vibe-coded" pattern you asked about)

Also in `_execute_run_inner`, same block as §1:

```python
if not settings.azure_api_key and not settings.azure_chat_endpoint:
    fallback_result = run_pdf_fallback(document_path, ...)   # <- identical call
    if fallback_result is None:
        raise RuntimeError(...)
else:
    fallback_result = run_pdf_fallback(document_path, ...)   # <- identical call
```

Both branches of the `if/else` call `run_pdf_fallback` with **identical arguments**. The only difference between the branches is whether a `RuntimeError` is raised afterward. This is textbook incremental-patch residue: the `if/else` structure was almost certainly added by an AI pass fixing BLK-171 ("fail fast if no LLM provider"), which needed to add the `raise` but didn't need to duplicate the call — a single `fallback_result = run_pdf_fallback(...)` followed by one guarded `raise` would do the same thing with no branching at all. It's not a functional bug, but it's a direct, concrete example of the "over-complication instead of simplification" pattern you described.

---

## 5. MEDIUM — Your backlog is not reliable evidence of what's broken (self-correction from my last message)

In my previous message I reported `BLK-167` through `BLK-172` as your open, unfixed priority list. That was wrong, and I want to be direct about it: I took the backlog markdown files at face value instead of checking the code they described. Having now read `GraphVisualizationView.tsx`, `Pane2ExtractedData.tsx`, `graph.py`'s `terminate_node`, `run_engine.py`'s skill/tool registries, and `prebuilt.py`, here's what's actually true, with the zip's internal timestamps as evidence:

| Ticket | Backlog claims | Code shows | Bug filed | Code fixed |
|---|---|---|---|---|
| BLK-167 | `GraphVisualizationView.tsx` renders hardcoded `SAMPLE_*` constants, accepts no props | Component takes `nodes`, `edges`, `topologyRules`, `serializedOutput` as props; has a real empty state; no `SAMPLE_*` constants anywhere in the file | 12:17 | 12:23 |
| BLK-168 | Graph tab shown unconditionally; fallback checks definition ID strings | `Pane2ExtractedData.tsx` computes `isGraphTask = runMeta?.taskType === 'graph_extraction'` and gates the tab and the fallback on that, sourced from the fetched run's real `task_type` | 12:17 | 12:24 |
| BLK-169 | Run engine has no graph-extraction code path; tools/skill not registered | `PnIDSkill` is in `_SKILL_REGISTRY`, graph tools (`detect_symbols`, `build_graph`, `validate_topology`, `serialize_graph`, etc.) are registered in `build_tool_registry()`, `terminate_node` dispatches to `_build_graph_result()` for `task_type == "graph_extraction"`, and `serialize_extraction_result` handles `GraphExtractionResult` | 12:18 | 12:25–12:29 |
| BLK-171 | Zero-token, zero-field runs report "completed" | `terminate_node` explicitly checks `total_tokens == 0 and not extraction` and forces `RunStatus.ERROR` with an explanatory message | 12:18 | 12:28 |
| BLK-172 | Duplicate `def-pid-to-dexpi` / `def-pnid-to-dexpi` definitions | Only `def-pnid-to-dexpi` exists in `prebuilt.py` now | 12:18 | 12:25 |

All five tickets were filed at 12:17–12:18 and the corresponding fix landed in the code between 12:23 and 12:29 — but every one of these files is still sitting in `backlog/bugs/` with `Status: backlog` and `Owner: unassigned`, not moved to `backlog/implemented/` the way `BLK-156` through `BLK-166` were.

**Why this matters more than the individual bugs did:** you've built a fairly elaborate process around this backlog — 229 files in `comms/` simulating a mgmt/backend/frontend organization, a `PROTOCOL.md`, RACI docs, "contract proposals," ticket confirmations. That apparatus exists specifically to track ground truth about what's done. If tickets don't get closed even when the fix is verifiably in the code minutes later, the backlog can't be trusted as a source of truth — by you, or by a future AI session picking up this project, which will read `BLK-169` marked `P0 / backlog / unassigned` and either waste time re-implementing something that already works, or (worse) tell you with confidence that something is broken when it isn't, the way I did in my last message.

**Recommendation:** Before trusting *any* backlog file in this repo, including the ones I haven't spot-checked, diff its claim against the actual code. I'd treat the whole `backlog/bugs/` directory as unverified until someone does that pass and moves confirmed-fixed items to `implemented/`.

---

## 6. MEDIUM — Skill/Template split: 22 hand-maintained pairs, two resolution paths

`src/skills/*.py` (22 files) and `src/templates/*.py` (22 files) mirror each other one-to-one by document type (`invoice`, `bank_statement`, `pid_diagram`, etc.). The conceptual split is defensible — `Skill` describes *how* to extract (prompts, probe order, tool preferences), `Template` describes *what a valid result looks like* (Pydantic schema) — but the wiring is entirely manual:

- `run_engine.py` hand-imports all 22 skill classes and all 22 template classes (44 import lines).
- Two parallel hand-maintained dicts, `_SKILL_REGISTRY` and `_TEMPLATE_REGISTRY`, map string IDs to classes — and several IDs are aliased twice for backward compatibility (`"invoice"` and `"sk-invoice-basic"` both point to `InvoiceSkill`, `"trade_finance_mt700"` and `"trade_finance"` both point to `TradeFinanceTemplate`, etc.), which is exactly the kind of drift that produced the BLK-172 duplicate-definition bug in the first place.
- On top of the static registry, there's a **second, dynamic** resolution path (`_build_dynamic_skill` / `_build_dynamic_template`) that builds `Skill`/`Template` objects at runtime from user-authored data in the `DefinitionStore`, for skills/templates created through the `SkillEditor` / `AiTemplateComposer` UI. `resolve_skill()` and `resolve_template()` check the static dict first, then fall through to the dynamic path.

This isn't broken — both paths work — but it means "how do I add or change a document type" has four places to touch (skill file, template file, two registry entries) for built-ins, plus an entirely separate code path for user-created ones. An auto-discovering registry (scan `src/skills/*.py` for `Skill` subclasses, same for templates) would remove the hand-maintenance and the class of bug BLK-172 represents, without changing the actual Skill/Template abstraction.

---

## 7. MEDIUM — Scope creep, quantified

The original DeepLearning.AI course material is `notebooks/L2.ipynb` through `L9.ipynb` — 5 notebooks, ~150KB combined. What's grown from it:

- **37,846 lines of Python** across `src/` (excluding tests, excluding `__pycache__`).
- **8,120 lines of TypeScript/React** in `frontend/`.
- **22 document-type skills**, spanning invoices, bank statements, medical claims (CMS-1500), government purchase orders (SF1449), P&ID engineering diagrams, metallurgical assays, commodity trade docs, and more — described in `prebuilt.py` as covering "all 11 GICS sectors."
- **2,990-line `requirements.txt`**, pulling in PaddleOCR, Tesseract, an Azure VLM client, three separate OpenCV builds (`opencv-python`, `opencv-contrib-python`, `opencv-python-headless` — these largely overlap; you almost never need all three simultaneously), scikit-image, the full `transformers`/`tokenizers`/`safetensors` stack, SQLAlchemy, and the complete LangChain/LangGraph ecosystem.
- **229 files in `comms/`** — a simulated mgmt/backend/frontend organization exchanging memos, directives, and "contract proposals" per a `PROTOCOL.md`, plus a `projectmgmt/` folder with `RACI.md`, `STATUS.md`, and an `audit-ledger.md`.

None of this is inherently wrong for a real product, but it's worth being honest that it's a different project than "build a ReAct extraction agent," and every one of the concrete bugs in this report (the fallback bypass, the dead guardrails, the stale backlog) lives somewhere in that expansion, not in the original course code.

---

## 8. Frontend — corrected assessment

Contrary to what the backlog implied, the frontend is in reasonably good shape where I looked:

- `GraphVisualizationView.tsx` — real props interface, real empty state, no mock constants (see §5).
- `Pane2ExtractedData.tsx` — fetches real run data via `fetchRun(runId)`, subscribes to live SSE `field_update` events, gates the graph tab on the real `task_type` from the backend, exports JSON/CSV via real API calls with a client-side fallback only for partial/failed runs (a reasonable design, not a mock).
- `WorkbenchLayout.tsx` — clean phase-based layout (`chat` / `document` / `extraction`), wraps every pane in an `ErrorBoundary`, no issues.
- `frontend/lib/api.ts` — every exported function hits a real endpoint; no hardcoded response data.
- A targeted grep for `SAMPLE_`, `MOCK_`, `DUMMY_`, `TODO`, `FIXME` across every `.tsx`/`.ts` file in `frontend/components` and `frontend/lib` returned zero hits.

I did not do a full line-by-line read of `Pane1AgentConsole.tsx` (843 lines) or `Pane3DocumentViewer.tsx` (264 lines) beyond confirming their state is backed by real `useEffect`/`fetch` calls rather than static data — if you want that same level of scrutiny applied there, say so and I'll do it.

---

## 9. Smaller notes

- `map_status_to_frontend()` in `run_engine.py` maps `RunStatus.PARTIAL → "completed"`. This looks alarming out of context (it's literally what BLK-171 was about) but on inspection it's correct: the zero-signal failure case is diverted to `RunStatus.ERROR` *before* reaching this function (in `terminate_node`), and `ERROR` isn't matched by any branch here, so it falls through to the final `return "failed"`. A genuine partial-with-some-fields run correctly shows as "completed." No action needed, but worth documenting so a future pass doesn't "fix" this and break it.
- `_contains_instruction_patterns()` in `graph.py` is a 16-phrase keyword list (`"ignore previous instructions"`, `"treat as compliant"`, etc.) used to *log a warning* when an LLM response looks like it contains injected instructions. It does not block, sanitize, or otherwise act on a match — which is fine as documented ("a detection/logging function, not a blocking function... the architecture itself prevents injection"), but it's trivially bypassed by paraphrase, translation, or Unicode tricks, and it duplicates ground that `guardrails/exfiltration_prevention.py` and `guardrails/output_validation.py` were presumably meant to cover more robustly — except those are dead (§2). If prompt-injection resistance matters to you, this keyword list is not it.

---

## Priority order for fixing

1. **Fix the PDF-fallback bypass (§1).** This is the one that actually changes what your system does in production and what your accuracy claims mean. One-line condition fix in `run_engine.py`.
2. **Decide on guardrails (§2): wire or delete.** Currently actively misleading.
3. **Re-verify the rest of `backlog/bugs/`** against actual code before trusting or acting on any of it (§5); update `backlog/implemented/` for the 5 confirmed-fixed tickets.
4. **Clean up the redundant if/else (§4)** and the tool-keyed-not-provider-keyed circuit breaker (§3) — quick, low-risk.
5. **Collapse the Skill/Template registry (§6)** into an auto-discovering pattern if you're going to keep adding document types.
6. Everything in §7 (scope/dependencies/process) is a judgment call about what kind of project you want this to be — not a bug, but worth a deliberate decision rather than continued organic growth.
