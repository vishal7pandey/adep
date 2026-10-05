# ADE-39 — Plan: the engine loop

Status: plan-approved · Risk: high · Jira: ADE-39
Created: 2026-10-05 · Slug: engine-loop · Spec: spec.md

## Summary

One new module, `src/engine/agent.py`, wiring ADE-34 (skills), ADE-35 (budget), ADE-36 (validation),
ADE-37 (history, not directly wired — see spec Non-functional) and ADE-38 (tools) into a pydantic-ai
`Agent`. **Size: L** (the integration surface is five modules plus a new third-party dependency).

## Current state

- `src/engine/{skills,budget,validation,history,tools}.py` all exist, tested, inert — nothing imports
  them from outside their own test files yet.
- `src/documents/store.py::DocumentStore.get_document(doc_id)` returns `{document_id,
  original_filename, format, total_pages, page_dimensions: [{width,height},...], page_paths,
  thumbnail, created_at}` — ade's equivalent of ade2's `list_pages()`.
- `src/config.py::settings` has `azure_api_key`, `azure_chat_endpoint`, `azure_chat_deployment`
  (default `"gpt-5.4"`); `src/providers/vlm_azure.py::_get_client()` already builds an `AzureOpenAI`
  client from exactly these three settings, lazily, at `api_version="2024-02-15-preview"`.
- `src/tools/graph/serialization.py::_serialize_dexpi` exists but is a different, simplified XML shape
  for the old LangGraph graph's node/edge data — not real DEXPI/Proteus, not ade2's richer P&ID shape.
  Confirmed not reusable here (spec: Users and context).

## Dependency resolution (done as part of this story, before writing code)

`uv add --optional engine pydantic-ai` resolves to **pydantic-ai 1.22.0** — the newest 1.x release, and
the newest release compatible with ade's *existing* `langchain-openai>=0.2.0,<0.3.0` core dependency
(pydantic-ai's 2.x line requires `openai>=2.29.0`; `langchain-openai<0.3.0` requires `openai<2.0.0`; the
two are provably incompatible, confirmed via `uv add --optional engine "pydantic-ai>=2.0"`'s resolver
error). Upgrading `langchain-openai`/`openai` to unblock pydantic-ai 2.x would touch the old engine's own
dependencies — explicitly out of scope for a strangler migration story. **Decision: pydantic-ai 1.22.0,
not 2.x — revisit only alongside ADE-33 (retire LangGraph), when the old engine's `openai<2.0` pin no
longer has to coexist.**

pydantic-ai 1.22.0 itself transitively pulls `opentelemetry-api` unpinned; the resolver picked the
newest available (1.44.0 at resolution time), which no longer ships the `opentelemetry._events` module
pydantic-ai 1.22.0's `messages.py` imports at package-import time — a hard `ModuleNotFoundError` on
`import pydantic_ai`, confirmed by direct import and by downloading and inspecting the 1.33/1.36/1.39/
1.44/1.45 wheels (`_events` present through 1.39, absent by 1.44). Fix: pin `opentelemetry-api<1.41`
alongside `pydantic-ai` in the same `engine` extra (resolves to 1.40.0, confirmed importable end to end:
`Agent`, `RunContext`, `TestModel`, `FunctionModel`, `AzureProvider`, `OpenAIChatModel`). ade's own
`src/observability/tracing.py` already imports `opentelemetry.*` lazily and only when
`ADE_OTEL_ENDPOINT` is set (never in tests), so this pin changes nothing observable for existing code —
opentelemetry wasn't in `dependencies` before this story; it only arrived as pydantic-ai's own
transitive dependency.

## Approach

1. `ExtractionState` dataclass (deps): `document_id`, `skill_id`, `todo`, `validations`,
   `budget: BudgetTracker` (default-factory each).
2. `SYSTEM_PROMPT`: ported from ade2's, rewritten wherever it names a bbox to say pixel-space
   `(x1, y1, x2, y2)` instead of normalized `[ymin, xmin, ymax, xmax]`; keeps ade2's "how to work"
   sequence and budget-aware strategy verbatim in spirit (survey → budget check → re-survey dense
   regions → read → validate → serialize → validate again → return) since that reasoning doesn't depend
   on coordinate space. No skill `probe_order` anywhere in this prompt (AC2).
3. `build_agent(model=None)`: if `model` is `None`, lazily construct `AzureProvider` +
   `OpenAIChatModel(settings.azure_chat_deployment, provider=provider)` from `settings` (mirrors
   `vlm_azure.py`); otherwise use the given `model` directly (how tests and future eval harnesses inject
   a `TestModel`/`FunctionModel`). Constructs `Agent(model, system_prompt=SYSTEM_PROMPT,
   output_type=str, deps_type=ExtractionState, retries=2)`, registers every tool below, returns it.
4. Perception tools (`@agent.tool`, each calls `ctx.deps.budget.record_tool("<name>")` first, then
   delegates to the matching `src.engine.tools` function of the same name minus `_tool`):
   `list_document_pages` (→ `DocumentStore.get_document`, `FileNotFoundError` → `{"error": ...}`),
   `survey_layout_tool`, `survey_region_tool`, `crop_and_read_tool`, `ocr_page_tool`.
5. `budget_status` (`@agent.tool`, no `record_tool` call — free): `ctx.deps.budget.status()`.
6. `update_plan` (`@agent.tool`, records `"update_plan"` — 0 turns per `TOOL_TURNS`): sets
   `ctx.deps.todo`, returns `{"plan": tasks, "summary": "<n> completed, <n> in progress, <n> pending"}`.
7. `validate_extraction` (`@agent.tool`, records `"validate_extraction"` — 0 turns): loads the skill
   (`load_skill(ctx.deps.skill_id)` if set), runs `validate_output` (schema) and `validate_invariants`
   (ADE-36's structured checker — surfaces `checked`/`violated`/`could_not_check` to the agent verbatim,
   never collapsing `could_not_check` into a pass), then ade2's completeness check (any of
   `nodes`/`valves`/`instruments`/`edges`/`off_page_connectors` present-but-empty → error) and thinness
   check (valve/edge counts vs. equipment count → warning), then — only if `data.get("dexpi_xml")` is
   truthy — a well-formedness-only XML parse (`ET.fromstring`, catches `ET.ParseError`); no round-trip
   entity-count comparison (needs ADE-14's parser, not built here). Appends the result to
   `ctx.deps.validations`, returns it.
8. `to_dexpi_xml` / `to_spice_netlist` (`@agent.tool`, each records its own name): clean stub, each
   always returns `{"error": "DEXPI serialization is not available yet (ADE-14)", "dexpi_xml": None}`
   (spice: `"... (ADE-16)", "spice_netlist": None`) — never touches `src/tools/graph/serialization.py`.
9. `list_skills` / `load_skill` (`@agent.tool_plain`, no state, no `record_tool` call — matches ade2 and
   `TOOL_TURNS` not listing either): wrap ADE-34's functions; `load_skill` returns `{"error": "Skill
   '<id>' not found"}` instead of `None`.

**Alternatives rejected**
- Reusing `src/tools/graph/serialization.py::serialize_graph(..., format="dexpi_xml")` for
  `to_dexpi_xml`: different input shape (flat nodes/edges vs. P&ID's separate valves/instruments/
  off_page_connectors/nozzles), different output schema (home-grown tag names, not real DEXPI/Proteus).
  Bridging the two well would mean half-building ADE-14 inside ADE-39; spec's Non-goals rules this out.
- Porting ade2's `parse_dexpi_xml`-based round-trip check: there is no DEXPI XML to round-trip yet (the
  serializer is a stub), so the check would always be dead code until ADE-14 lands anyway.
- Pinning `pydantic-ai>=2.0` and bumping `openai`/`langchain-openai` to match: would touch the old
  engine's dependencies mid-strangler-migration, a bigger, separate decision (belongs with ADE-33).

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Resolve and pin the `engine` extra (`pydantic-ai`, `opentelemetry-api<1.41`) | `pyproject.toml`, `uv.lock` | AC6 | `uv sync --all-extras`; import probe script |
| T2 | Failing tests first (red): unit tests for each tool wrapper + one hermetic `FunctionModel` integration test | `src/tests/test_engine_agent.py` | AC1–AC5 | tests fail (no module yet) |
| T3 | `src/engine/agent.py`: `ExtractionState`, `SYSTEM_PROMPT`, `build_agent()`, all tools | `src/engine/agent.py` | AC1–AC5 | tests pass |

## Data, API and migration impact

None — new, inert module; nothing calls it (AC3). `pyproject.toml`/`uv.lock` gain a new optional
extra; the default install path (`uv sync` with no extras, and `--all-extras` which CI already uses)
both keep working — confirmed by running the full suite after T1 before touching any code.

## Security and failure modes

- No new attack surface: every tool either delegates to an already-hardened ADE-38 function
  (`document_id`/`page_num`/bbox only ever resolve through `DocumentStore`'s existing path logic) or
  operates purely on in-memory `data` the agent itself constructed.
- The real Azure model is built lazily (only inside `build_agent()`, only when `model=None`) so
  `import src.engine.agent` never requires `AZURE_API_KEY` to be set (AC3) and never makes a network
  call at import time.

## Rollout and rollback

Merge; revert to undo. No migration, no runtime behavior change — nothing outside `src/engine/` imports
this module yet.

## Risks and open points

- The pydantic-ai/opentelemetry version pin (above) is this story's main surprise; documented in both
  this plan and the PR so a future dependency bump (e.g. alongside ADE-33) knows why the pin exists and
  when it's safe to revisit (once `langchain-openai`/`openai` are no longer load-bearing for the old
  engine).
- Testing a pydantic-ai tool loop hermetically needs its own idiom (`FunctionModel` scripting a fixed
  sequence of tool calls by inspecting message history) rather than ADE-34–38's simple monkeypatch
  style; AC5's test is the first of its kind in this codebase and sets the pattern ADE-40 will reuse.
