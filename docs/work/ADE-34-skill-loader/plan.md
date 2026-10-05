# ADE-34 — Plan: skill loader

Status: plan-approved · Risk: low · Jira: ADE-34
Created: 2026-10-05 · Slug: skill-loader · Spec: spec.md

## Summary

One new module, `src/engine/skills.py`, ported closely from ade2's `src/ade2/skills.py` (read in full),
adjusted only for ade's package layout and logging convention. **Size:** S.

## Current state

- No `src/engine/` package exists yet — this story creates it (`src/engine/__init__.py`,
  `src/engine/skills.py`).
- No top-level `skills/` directory exists yet; this story's tests build their own skill directories on
  the fly under pytest's `tmp_path`, monkeypatching `SKILLS_DIR` per test — avoids cross-test collisions
  between scenarios (a "list two valid skills" test and a "load one skill with a malformed schema" test
  must not share one fixture tree).
- `pyyaml` is not a direct dependency in `pyproject.toml` but is already present in `uv.lock` (pulled in
  transitively) and importable in the environment — confirmed by checking `uv.lock` directly. No
  dependency change needed; `import yaml` just works. If a future `uv sync --frozen --no-dev`-only
  environment ever drops it, that surfaces as an import error here and is a one-line fix then, not now.
- Commands: `uv run pytest src/tests/ -v -m "not integration"`, `uv run ruff check src/`,
  `uv run ruff format src/` (pre-commit hook already installed, ADE-5).

## Approach

Direct, careful port of `skills.py`'s four pieces:
1. `Skill` dataclass — same fields as ade2's, plus `to_prompt_block()` and `to_dict()`.
2. `_parse_frontmatter(md)` — BOM strip, `---`-delimited YAML block, body is everything after the second
   `---`; no frontmatter at all returns `({}, md)` unchanged.
3. `list_skills()` — iterate `SKILLS_DIR`, one dict per valid skill directory.
4. `load_skill(skill_id)` — full `Skill`, `schema=None` on missing/malformed `schema.json` with a logged
   warning (not raised).

`SKILLS_DIR` resolves the same way ade2's does (three parents up from the module file, i.e. repo root /
`skills`), via `Path(__file__).resolve().parent.parent.parent / "skills"` — `src/engine/skills.py`'s
parents are `src/engine/` → `src/` → repo root, so this needs verifying against the actual depth once the
file exists (ade2's module was one level shallower, `src/ade2/skills.py`, so its "three parents up" lands
differently — don't copy the literal parent count, derive it fresh for `src/engine/skills.py`'s real
depth and add a test that asserts `SKILLS_DIR` resolves to `<repo_root>/skills`).

**Alternatives rejected**
- Nesting skills under `src/skills_data/` or similar: rejected in favor of matching ade2's own
  repo-root-sibling layout (ADE-30's Assumptions), so a future diff against ade2 skill content stays easy
  to read.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Failing tests first (red): test module building its own tmp_path fixtures | `src/tests/test_engine_skills.py` | AC1-AC7 | tests fail (no `src/engine/skills.py` yet) |
| T2 | `src/engine/__init__.py`, `src/engine/skills.py` | `src/engine/__init__.py`, `src/engine/skills.py` | AC1-AC6 | tests pass |

## Data, API and migration impact

None — new, inert module. Nothing imports it yet.

## Security and failure modes

Reads local files only, from a path derived from `__file__` (not user input). A malformed `schema.json`
degrades to `schema=None` with a warning rather than raising, per R3/AC4.

## Rollout and rollback

Merge; revert to undo. No migration, no runtime behavior change (nothing calls this module yet).

## Risks and open points

- The exact `SKILLS_DIR` parent-count must be verified against `src/engine/skills.py`'s real path depth,
  not assumed from ade2's. T2 includes a test for this specifically.
