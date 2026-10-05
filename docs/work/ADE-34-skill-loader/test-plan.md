# ADE-34 — Test plan: skill loader

Status: implementing · Risk: low · Jira: ADE-34

Test framework and conventions found: pytest, `tmp_path` + `monkeypatch` for per-test isolation
(this module introduces that pattern for `src/engine/`; existing `src/tests/fixtures/` is for larger
committed fixtures, not needed here), markers in `pyproject.toml` (`integration`); command
`uv run pytest src/tests/ -v -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_engine_skills.py::test_list_skills_returns_metadata_for_valid_skills_only, ::test_list_skills_on_missing_or_empty_dir_returns_empty_list | two valid skills listed with all 5 metadata fields | SKILLS_DIR missing entirely -> [] | a dir with no SKILL.md is skipped, not listed | verified |
| AC2 | unit | ::test_load_skill_returns_full_skill_or_none | valid skill: hints + schema populated, probe_order parsed | n/a | nonexistent id returns None | verified |
| AC3 | unit | ::test_load_skill_without_schema_json_has_none_schema | SKILL.md present, no schema.json -> schema=None | n/a | n/a | verified |
| AC4 | unit | ::test_malformed_schema_json_logs_warning_and_degrades | n/a | n/a | malformed schema.json -> schema=None + warning record naming the skill id | verified |
| AC5 | unit | ::test_to_prompt_block_omits_probe_order | invariants/ruleset text present | n/a | probe_order step text absent even though the skill has probe_order entries | verified |
| AC6 | unit | ::test_bom_and_non_bom_skill_md_parse_identically, ::test_skill_md_with_no_frontmatter_loads_with_empty_metadata | BOM-prefixed SKILL.md parses identically to a non-BOM copy | file with no `---` block loads with empty metadata, full file as hints, name falls back to id | n/a | verified |
| AC7 | unit | (all above), plus ::test_skills_dir_resolves_to_repo_root_slash_skills | tmp_path-built fixtures per test, no network/LLM | SKILLS_DIR itself resolves to `<repo_root>/skills` (the plan's flagged risk) | n/a | verified |

## Regression risk

None — new module, nothing else imports it yet. No existing test should be affected.

## Untestable AC

None.

## Manual checks

None.

## Audit (after implementation)

Red first: all 9 tests failed at collection (`ModuleNotFoundError: No module named 'src.engine'`) before
`src/engine/skills.py` existed. After implementation: 9 passed (one test assertion bug on my part, fixed
once — expected `.strip()`-ed content where the loader correctly returns the file unchanged).

Four mutations applied to the real `src/engine/skills.py` (each confirmed to have changed the file via
`diff`), run, then restored (confirmed byte-identical with `diff -q`):

| Mutation | Test(s) run | Result |
|---|---|---|
| M1: `to_prompt_block` renders `probe_order` | `-k probe_order` | fails (asserts the rendered text does not contain probe_order step text) |
| M2: malformed `schema.json` raises instead of degrading to `schema=None` | `-k malformed` | fails with an uncaught `JSONDecodeError` |
| M3: `list_skills` includes directories with no `SKILL.md` | `-k list_skills` | fails (asserts exactly the two valid skill ids) |
| M4: BOM-stripping disabled (`if md.startswith("﻿")` replaced with `if False`) | `-k bom` | fails (`with_bom.name` stays `"with-bom"`, the directory name, instead of parsing to `"Valid Skill"`) |

Full suite after restoring: `src/tests/test_engine_skills.py` 9 passed; `pytest src/tests/ -m "not
integration"` 1793 passed, 9 failed (the pre-existing ADE-23/ADE-24 failures, unchanged by this diff),
19 deselected. `ruff check src/engine/` and `ruff format --check src/engine/`: clean.
