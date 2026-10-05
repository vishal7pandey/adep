# ADE-39 — Test plan: the engine loop

Status: in-review · Risk: high · Jira: ADE-39

Test framework and conventions found: pytest, `monkeypatch` to replace the ADE-34–38 module functions
`src.engine.agent` imports through (same boundary-mocking style as ADE-38's tests), plus pydantic-ai's
own `FunctionModel` (a test-only `Model` that scripts a deterministic sequence of tool calls by
inspecting message history) for the one true integration test; command
`uv run pytest src/tests/ -v -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_engine_agent.py::test_build_agent_registers_every_tool | `build_agent(model=TestModel())` returns an `Agent` whose tool names cover all of ADE-34–38 | n/a | n/a | verified |
| AC2 | unit | ::test_system_prompt_documents_tools_but_omits_probe_order, ::test_to_prompt_block_output_never_appears_verbatim_in_system_prompt | prompt mentions every tool by name | n/a | a skill's `probe_order` string never appears in `SYSTEM_PROMPT` | verified |
| AC3 | unit + full suite | ::test_import_requires_no_azure_credentials, ::test_build_agent_with_no_model_arg_does_not_require_azure_env_until_called; full-suite run | `import src.engine.agent` with Azure env cleared | n/a | n/a | verified |
| AC4 | unit | ::test_crop_and_read_tool_wraps_errors_as_structured_not_exceptions, ::test_validate_extraction_never_raises_on_malformed_data, ::test_dexpi_stub_never_raises, ::test_spice_stub_never_raises | n/a | n/a | a mocked ADE-38 tool returns `{"error": ...}`; wrapper passes it through unchanged, no exception | verified |
| AC5 | integration (hermetic) | ::test_function_model_drives_tool_calls_through_validate_extraction_to_a_final_answer | a scripted `FunctionModel` calls survey_layout_tool, then validate_extraction, then returns final text | n/a | n/a | verified |
| AC6 | manual | `uv sync --all-extras` after `uv add --optional engine "pydantic-ai>=1.22.0,<2.0.0" "opentelemetry-api<1.41"`; `grep pydantic-ai pyproject.toml` only under `[project.optional-dependencies].engine` | n/a | n/a | verified |
| R3/R4/R5 | unit | ::test_budget_status_tool_is_free, ::test_update_plan_tool_records_cost_and_updates_state, ::test_perception_tools_record_one_turn_each | each tool's `ctx.deps.budget` reflects the expected recorded cost (or none, for the free tools) | n/a | n/a | verified |
| R6 | unit | ::test_validate_extraction_surfaces_could_not_check_never_as_passed, ::test_validate_extraction_completeness_and_thinness_checks, ::test_validate_extraction_dexpi_wellformedness_only | n/a | n/a | malformed `dexpi_xml` string → error, not a round-trip comparison | verified |
| R8 | unit | ::test_load_skill_tool_returns_structured_error_for_unknown_id, ::test_list_skills_tool_delegates_to_engine_skills | n/a | n/a | unknown skill id → `{"error": ...}`, never `None` | verified |

## Regression risk

New module; nothing else imports `src.engine.agent` yet. The only shared-state risk is the new
`pyproject.toml`/`uv.lock` dependency resolution — covered by AC3's full-suite run and AC6's manual
`uv sync --all-extras` check (both the default install and the all-extras install CI uses).

## Untestable AC

None. (AC5's "no live Azure/LLM credentials needed" is itself testable: the test asserts the run
completes without `AZURE_API_KEY` set.)

## Manual checks

- `uv sync --all-extras` completes cleanly (CI's own install command) after the dependency change —
  done, see Audit.

## Audit (after implementation)

18 new tests, all green. Full suite: 1846 passed (1828 pre-existing + 18 new), same 9 pre-existing
unrelated failures as the clean-checkout baseline (`AGENTS.md`), no regressions. `uv sync
--all-extras` completes cleanly with the new `engine` extra. `ruff check`/`ruff format` clean on both
new files.

Dependency resolution note: `pydantic-ai` resolves to the 1.x line (`>=1.22.0,<2.0.0`) rather than
the newer 2.x line — 2.x requires `openai>=2.29.0`, which conflicts with the old engine's
`langchain-openai<0.3.0` (needs `openai<2.0.0`); confirmed via the resolver's own conflict report.
`opentelemetry-api` is pinned `<1.41` — pydantic-ai 1.22.0's `messages.py` imports
`opentelemetry._events`, a module present through opentelemetry-api 1.39 and absent by 1.44/1.45
(confirmed by downloading and inspecting the wheels directly); resolves to 1.40.0, confirmed
importable end to end (`Agent`, `RunContext`, `TestModel`, `FunctionModel`, `AzureProvider`,
`OpenAIChatModel`). Full detail in `plan.md`'s "Dependency resolution" section.

Mutation testing (6 mutations against `src/engine/agent.py`, each applied, tested, then reverted and
confirmed byte-identical via `diff -q` against a backup):

| # | Mutation | Result |
|---|----------|--------|
| M1 | `survey_layout_tool` skips recording its budget cost | Caught |
| M2 | `budget_status` wrongly records a cost (should be free) | Caught |
| M3 | `validate_extraction` folds `could_not_check` invariants into `invariants_passed` | Caught |
| M4 | `load_skill` tool returns `None` for an unknown skill id instead of a structured error | Caught |
| M5 | `validate_extraction` skips the `dexpi_xml` well-formedness parse check entirely | Caught |
| M6 | `SYSTEM_PROMPT` leaks the literal string `probe_order` | Caught |

All 6 mutations caught on the first attempt — no coverage gaps found this time.
