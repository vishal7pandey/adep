# ADE-31 — Head-to-head P&ID evaluation: old LangGraph engine vs new engine

Status: approved · Risk: medium · Jira: ADE-31
Created: 2026-10-05 · Slug: pid-head-to-head · Spec: spec.md

## Summary

Add three small modules under `src/eval/`: a client-level usage meter with hard caps, a pure comparison runner (records, summary, table, results file), and the two engine adapters plus the old engine's graph-to-categories mapping. A thin CLI (`python -m src.eval.pid_compare`) wires them to the real engines. The runner and meter are tested hermetically with stub engines and a fake completions function; the adapters are tested only where pure (the mapping) and exercised for real in the manual run.

**Size:** M

## Current state

- `src/eval/pid_scoring.py` (ADE-15): `score_extraction(extraction, truth) -> PidScore`, `.to_dict()`; categories `nodes, valves, instruments, off_page_connectors, edges`; tags read from `item["tag"]` in `nodes, valves, instruments`.
- `src/eval/pid_ground_truth.py`: `discover_references(dir)`, `load_ground_truth(xml, svg)`, `svg_to_png`, `reference_dir()` (env `ADE_DEXPI_REF_DIR`).
- New engine: `src/engine/agent.py` `build_agent()`, `ExtractionState`; run with `agent.run_sync(prompt, deps=ExtractionState(document_id, skill_id), usage_limits=UsageLimits(request_limit=30))`; documents imported with `get_document_store().import_document(png)`. First real run (ADE-41) used exactly this.
- Old engine P&ID path (mirrors `src/api/run_engine.py::_execute_run_inner`): `build_initial_state(path, PnIDContract, PnIDSkill, task_type="graph_extraction")`, `build_tool_registry(tool_names=...)` with the tool list of `def-pnid-to-dexpi` in `src/definitions/prebuilt.py`, `build_react_graph(registry, skill, validator_config, llm_client=_build_planner_client(), breaker=CircuitBreaker(3))`, `graph.invoke(state, config={"recursion_limit": 60})`, then `_build_graph_result(...)` whose `.graph` is `{"nodes": [{id, type, tag, bbox...}], "edges": [...]}` (see `src/tools/graph/graph_building.py`).
- `settings.ocr_provider` selects the old engine's OCR/layout tools (`src/run.py::build_tool_registry`): `paddle` registers `detect_layout`, `detect_text`, `ocr`; anything else registers none, and the old P&ID skill then fails (smoke run). R8 is met by passing the provider per run (`--old-ocr`, default `paddle`).
- Both engines call OpenAI through the `openai` SDK's `Completions.create` / `AsyncCompletions.create` (old: `src/providers/vlm_azure.py`, `llm.py`; new: perception tools via the same client, the agent via pydantic-ai's `OpenAIChatModel`).
- Tests: `.venv/Scripts/python.exe -m pytest src/tests/<file> -q`; lint `ruff check` and `ruff format --check`. `.adep/` is git-ignored.

## Approach

- `usage_meter.py`: `UsageMeter(max_calls, max_tokens)` context manager that wraps `openai.resources.chat.completions.Completions.create` and `AsyncCompletions.create` at class level, adds each response's `usage` to its totals, and raises `SpendCapReached` before forwarding a call once a cap is reached. Class-level patching measures every client instance without touching either engine, so agent and tool calls are counted the same way. Restores originals in `__exit__`.
- `pid_compare.py` (pure): `RunOutcome`, `Engine` protocol, `run_comparison(engines, drawings, runs, score_fn, clock, meter_tokens)` -> records; `summarize(records)`; `format_table(summary, meta)`; `write_results(path, meta, records, summary)`; error handling stores `type(exc).__name__` only; each record has `status` in `ok | failed | skipped_budget`. Loop order: for drawing, for repetition, for engine (alternation). A `SpendCapReached` marks the current and all remaining runs `skipped_budget`.
- `pid_engines.py`: `graph_to_extraction(graph)` (rules: `valve` in type -> valves; `instrument`, `sensor`, `controller`, `indicator`, `transmitter` -> instruments; `off_page`/`offpage` -> off_page_connectors; `pipe` and `fitting` ignored; everything else -> nodes; edges -> edges; tags carried), `NewEngineAdapter`, `OldEngineAdapter(ocr_provider)` (sets `settings.ocr_provider` for the run, restores after), JSON-from-text parsing shared with the new engine (`UnparseableOutput`).
- CLI in `pid_compare.py::main`: args `--refs`, `--runs`, `--engines`, `--old-ocr`, `--model`, `--max-calls`, `--max-tokens`, `--timeout`, `--out`, optional `--price-in/--price-out` (per million tokens); reads the key from the environment, refuses to start without it or without the references; prints the table.

**Alternatives rejected**
- Use each engine's own token accounting: the new engine's reads 0 (ADE-42) and the two are not defined alike; measuring at the client is the same yardstick for both.
- Run the old engine through the HTTP API and run store: needs a server, definitions and the run store; the in-process graph call is the same code path minus the HTTP.
- Force VLM-only perception on both engines: tried in the smoke run; the old engine produces nothing without its layout tool, so the number would measure a missing tool, not the engine.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Usage meter with caps | `src/eval/usage_meter.py`, `src/tests/test_usage_meter.py` | AC5 | pytest file passes; breaking the cap check or the restore makes a test fail |
| T2 | Runner: records, alternation, failure isolation | `src/eval/pid_compare.py`, `src/tests/test_pid_compare.py` | AC1, AC3 | pytest |
| T3 | Summary and table | same | AC2, AC6 | pytest |
| T4 | Budget skip handling | same | AC7 | pytest |
| T5 | Results file, secret and path rules | same | AC3, AC6 | pytest with a fake key in the environment |
| T6 | Graph mapping | `src/eval/pid_engines.py`, `src/tests/test_pid_engines.py` | AC4 | pytest |
| T7 | Engine adapters and CLI | `src/eval/pid_engines.py`, `src/eval/pid_compare.py` | AC8 | one capped real run per engine (smoke), then the full run |
| T8 | Real comparison and write-up | results file (git-ignored), Jira, Confluence | AC8 | table and verdict posted |

## Data, API and migration impact

None to product behaviour. New CLI `python -m src.eval.pid_compare`; no new settings. Results go to `.adep/eval/` (ignored).

## Security and failure modes

The key comes from the environment only and is never printed; provider error messages are discarded (type only). The meter caps calls and tokens; the run has a per-run timeout. A failing engine is recorded, not fatal. Nothing writes outside `.adep/`.

## Rollout and rollback

Dev tooling only; revert the PR. No deploy.

## Risks and open points

- The old engine may not run at all without OCR tools (all runs fail). That is itself a finding (the engine depends on providers not installed) and the report says so; it is not hidden by retries.
- Per-run timeout via a thread cannot kill a hung provider call; the meter's caps are the backstop.
