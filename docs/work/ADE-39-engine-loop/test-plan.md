# ADE-39 — Test plan: the engine loop

Status: implementing · Risk: high · Jira: ADE-39

Test framework and conventions found: pytest, `monkeypatch` to replace the ADE-34–38 module functions
`src.engine.agent` imports through (same boundary-mocking style as ADE-38's tests), plus pydantic-ai's
own `FunctionModel` (a test-only `Model` that scripts a deterministic sequence of tool calls by
inspecting message history) for the one true integration test; command
`uv run pytest src/tests/ -v -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_engine_agent.py::test_build_agent_registers_every_tool | `build_agent(model=TestModel())` returns an `Agent` whose tool names cover all of ADE-34–38 | n/a | n/a | planned |
| AC2 | unit | ::test_system_prompt_documents_tools_but_omits_probe_order | prompt mentions every tool by name | n/a | a skill's `probe_order` string never appears in `SYSTEM_PROMPT` | planned |
| AC3 | unit | ::test_import_requires_no_azure_credentials, ::test_existing_suite_untouched (full-suite run, not a single test) | `import src.engine.agent` with env cleared | n/a | n/a | planned |
| AC4 | unit | ::test_crop_and_read_tool_wraps_errors_as_structured_not_exceptions, ::test_validate_extraction_never_raises_on_malformed_data, ::test_dexpi_stub_never_raises | n/a | n/a | a mocked ADE-38 tool returns `{"error": ...}`; wrapper passes it through unchanged, no exception | planned |
| AC5 | integration (hermetic) | ::test_function_model_drives_tool_calls_through_validate_extraction_to_a_final_answer | a scripted `FunctionModel` calls survey_layout_tool, then validate_extraction, then returns final text | n/a | n/a | planned |
| AC6 | manual | `uv sync --all-extras` after `uv add --optional engine pydantic-ai "opentelemetry-api<1.41"`; `grep pydantic-ai pyproject.toml` only under `[project.optional-dependencies].engine` | n/a | n/a | planned |
| R3/R4/R5 | unit | ::test_budget_status_tool_is_free, ::test_update_plan_tool_records_cost_and_updates_state | each tool's `ctx.deps.budget` reflects the expected recorded cost (or none, for the free tools) | n/a | n/a | planned |
| R6 | unit | ::test_validate_extraction_surfaces_could_not_check_never_as_passed, ::test_validate_extraction_completeness_and_thinness_checks, ::test_validate_extraction_dexpi_wellformedness_only | n/a | n/a | malformed `dexpi_xml` string → error, not a round-trip comparison | planned |
| R8 | unit | ::test_load_skill_tool_returns_structured_error_for_unknown_id | n/a | n/a | unknown skill id → `{"error": ...}`, never `None` | planned |

## Regression risk

New module; nothing else imports `src.engine.agent` yet. The only shared-state risk is the new
`pyproject.toml`/`uv.lock` dependency resolution — covered by AC3's full-suite run and AC6's manual
`uv sync --all-extras` check (both the default install and the all-extras install CI uses).

## Untestable AC

None. (AC5's "no live Azure/LLM credentials needed" is itself testable: the test asserts the run
completes without `AZURE_API_KEY` set.)

## Manual checks

- `uv sync --all-extras` completes cleanly (CI's own install command) after the dependency change,
  confirmed once, result recorded in the Audit section below.

## Audit (after implementation)

<!-- Filled after implementation. -->
