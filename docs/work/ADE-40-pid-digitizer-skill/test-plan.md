# ADE-40 — Test plan: P&ID digitizer skill content + end-to-end proof

Status: implementing · Risk: medium · Jira: ADE-40

Test framework and conventions found: pytest, the real `DocumentStore` pointed at `tmp_path` (never
`.adep/`), the real `skills/` directory (the one intentional exception to monkeypatching
`engine_skills.load_skill` — this test exists to prove the real file parses), `vlm_azure.vlm`
monkeypatched at the `src.engine.tools` boundary (ADE-38's own convention), pydantic-ai's
`FunctionModel` to script the tool-call sequence (ADE-39's own convention); command
`uv run pytest src/tests/ -v -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_pid_skill_e2e.py::test_skill_loads_with_schema_and_invariants | real `load_skill("pid-dexpi-digitizer")` returns a `Skill` with 4 invariants and a non-None schema | n/a | n/a | planned |
| AC2 | unit | ::test_schema_matches_pid_graph_shape | `schema.json` has `nodes`/`valves`/`instruments`/`off_page_connectors`/`edges`/`header`/`dexpi_xml` keys, `nodes`/`edges` required fields match ADE-39's completeness-check names | n/a | n/a | planned |
| AC3 | integration (hermetic) | ::test_engine_runs_end_to_end_against_a_real_pid_sample | a scripted `FunctionModel` drives `build_agent()` through survey → validate_extraction (clean) → to_dexpi_xml (stub) → final answer, against a real imported `sample-pid-01.jpg` | n/a | n/a | planned |
| AC4 | manual | PR description names the exact `pytest` node id | n/a | n/a | n/a | planned |

## Regression risk

None — new skill directory (nothing reads `skills/` except ADE-34's loader, already tested) and one
new test file; no existing code changed.

## Untestable AC

None.

## Manual checks

- Confirm the PR body's "Run standalone" command actually matches the test's real node id (copy-paste
  check before opening the PR).

## Audit (after implementation)

<!-- Filled after implementation. -->
