---
id: BLK-159
title: Store should always include prebuilt content — no seeding mechanism
status: done
priority: high
estimate: M
assigned_to: backend
created: 2026-08-08T22:40:00+05:30
tags: [bug, backend, store, architecture]
---

## Problem

The `.adep/definitions/`, `.adep/skills/`, and `.adep/templates/`
directories are empty when the server starts. Users see no agent
definitions, skills, or templates in the UI despite 18 definitions,
19 skills, and 19 templates existing in `src/definitions/prebuilt.py`.

Root cause: `seed_store()` exists in `prebuilt.py` but is **never
called**. `main.py:create_app()` does not invoke it. There is also
`scripts/seed.py` which seeds only 1 definition — also not called
automatically.

## Design Decision

**No seeding mechanism.** There should be no distinction between
"prebuilt" and "user-created" content. The store should always
include all content — prebuilt definitions from code merged with
any user-created or user-edited content on disk.

## Required Fix

Modify the store's read methods to **merge** prebuilt content from
`prebuilt.py` with on-disk content:

### `src/definitions/store.py`

1. **`list_definitions()`** — Return prebuilt definitions from
   `PREBUILT_DEFINITIONS` merged with `.adep/definitions/*.json`.
   If a definition exists on disk with the same ID, the disk version
   takes precedence (user may have edited it).

2. **`list_skills()`** — Return `PREBUILT_SKILLS` merged with
   `.adep/skills/*.json`. Same precedence rule.

3. **`list_templates()`** — Return `PREBUILT_TEMPLATES` merged with
   `.adep/templates/*.json`. Same precedence rule.

4. **`get_definition(id)`** — Check disk first, fall back to prebuilt.

5. **`get_skill(id)`** — Check disk first, fall back to prebuilt.

6. **`get_template(id)`** — Check disk first, fall back to prebuilt.

### What stays the same

- `create_definition()`, `update_definition()`, `delete_definition()`
  still write to disk only. User-created content is persisted.
- User edits to prebuilt definitions get written to disk and take
  precedence on next read.
- `PREBUILT_DEFINITIONS`, `PREBUILT_SKILLS`, `PREBUILT_TEMPLATES`
  in `prebuilt.py` remain as the canonical baseline.

### What to remove

- `seed_store()` function — no longer needed
- `register_prebuilt_definitions()` function — no longer needed
- `scripts/seed.py` — no longer needed
- Any startup/seeding hooks

### Cleanup

- Remove `scripts/seed.py` (dead code)
- Remove `seed_store()` and `register_prebuilt_definitions()` from
  `prebuilt.py`
- Keep `PREBUILT_DEFINITIONS`, `PREBUILT_SKILLS`, `PREBUILT_TEMPLATES`
  as data — these are read by the store

## Tests

- Fresh `.adep/` directory (no disk files) → `list_definitions()`
  returns 18 definitions from prebuilt
- Fresh `.adep/` → `list_skills()` returns 19 skills from prebuilt
- Fresh `.adep/` → `list_templates()` returns 19 templates from prebuilt
- Create a new definition via API → appears in `list_definitions()`
  alongside prebuilt ones
- Edit a prebuilt definition → disk version takes precedence
- Delete a prebuilt definition → should it be deletable? (design
  decision — recommend: write a tombstone file to disk so it stays
  deleted across restarts)
- `get_definition("def-trade-finance-scrutiny")` returns the prebuilt
  definition even with empty disk

## Immediate Workaround

Until this is fixed, populate the store manually:

```bash
uv run python -c "from src.definitions.prebuilt import seed_store; seed_store()"
```

This writes all prebuilt content to `.adep/` on disk. Not a permanent
fix — just makes the UI functional now.
