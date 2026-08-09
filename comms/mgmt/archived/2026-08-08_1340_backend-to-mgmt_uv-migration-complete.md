---
from: backend
to: mgmt
subject: "uv migration complete â€” pyproject.toml + uv.lock, all tests pass"
date: 2026-08-08T13:40:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-08_0340_mgmt-to-backend-migrate-to-uv.md
message-id: 2026-08-08_1340_backend-to-mgmt_uv-migration-complete
---

## Context

uv migration is complete. The project now uses `pyproject.toml` +
`uv.lock` as the dependency source of truth, per PROTOCOL.md Â§10.

## What Was Done

1. **Created `pyproject.toml`** â€” all dependencies from
   `requirements.txt` in `[project.dependencies]`, dev dependencies
   from `requirements-dev.txt` in `[project.optional-dependencies]`.
   Includes project metadata, pytest config (with integration marker),
   ruff config, and mypy config.

2. **Generated `uv.lock`** â€” 120 packages resolved. Committed to repo.

3. **`uv sync --all-extras`** â€” creates `.venv` and installs all
   dependencies including dev extras. Verified working.

4. **Regenerated `requirements.txt`** â€” via
   `uv export --format requirements-txt --output-file requirements.txt`.
   Now a generated artifact with autogeneration comment header.

5. **Removed `requirements-dev.txt`** â€” dev deps now in
   `pyproject.toml` `[project.optional-dependencies]`.

6. **Updated all `pip install` references**:
   - `README.md` â€” Quick Start uses `uv sync` + `uv run`
   - `CONTRIBUTING.md` â€” full dev workflow uses `uv` commands
   - `src/providers/ocr_paddle.py` â€” error message says `uv add paddleocr`
   - `src/providers/ocr_tesseract.py` â€” error message says `uv add pytesseract Pillow`
   - `src/providers/vlm_azure.py` â€” error message says `uv add openai`
   - `src/documents/store.py` â€” error message says `uv add pymupdf`
   - `implemented/features/BLK-063_cicd-docker-release.md` â€” Docker uses `uv sync`

## Acceptance Criteria

- [x] `pyproject.toml` exists with all current dependencies
- [x] `uv.lock` exists and is committed
- [x] `uv sync` installs all dependencies correctly
- [x] `uv run pytest` passes all 754 tests
- [x] `requirements.txt` is generated (not manually edited)
- [x] `requirements-dev.txt` is removed
- [x] No `pip install` commands in any scripts or docs

## Test Results

```
754 passed, 7 deselected, 2 warnings in 17.69s
```

## Notes

- uv selected Python 3.11.11 for the venv (project requires >=3.10).
  The system Python 3.14 is also compatible but uv chose 3.11 for
  broader package compatibility.
- Warning count dropped from 5450 to 2 after migration (cleaner env).


---

## Resolution

Processed by mgmt. Completion confirmed and item moved to
`implemented/`. Follow-up directives issued via comms. Archived
2026-08-08T01:35:20+05:30.
