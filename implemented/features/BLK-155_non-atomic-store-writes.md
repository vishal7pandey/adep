# BLK-155: Non-atomic store writes with TOCTOU race in create()

**ID:** BLK-155
**Source:** REV-005 (independent reviewer)
**Severity:** Medium
**Category:** Reliability / Data integrity
**Status:** Done
**Assigned to:** Backend
**Estimate:** M

## Problem

All file-based stores (definitions, skills, templates, runs, documents,
webhooks, API keys) write JSON with direct `path.write_text(...)` and no
file locking. This is vulnerable to:

1. **Partial-write corruption:** process killed/crashes mid-write leaves
   a truncated, unparseable JSON file.
2. **TOCTOU race in `create()`:** two concurrent requests for the same
   new entity ID can both pass `path.exists()` before either writes,
   silently defeating the "fails if it already exists" guarantee.

This is not limited to multi-user scenarios — a single user's browser
can race via double-submit, multiple tabs, or client retry after a slow
response.

## Evidence

- `src/definitions/store.py:87-90` — `if path.exists(): raise
  FileExistsError(...)` then `path.write_text(...)` in a separate step.
  No atomic create (e.g. `os.open` with `O_CREAT | O_EXCL`).
- Same `path.write_text` direct-to-final-name pattern in
  `src/documents/store.py` and `src/agent/webhooks.py WebhookStore`.
- No write-to-temp-then-`os.replace()` pattern anywhere.

## Resolution

1. **Atomic writes:** Write to a temp file in the same directory, then
   `os.replace()` into place. This is atomic on POSIX and Windows.
2. **Atomic create:** Use `os.open(path, O_CREAT | O_EXCL | O_WRONLY)`
   to atomically create the file, or use a lock file.
3. Apply to all stores: `DefinitionStore`, `DocumentStore`,
   `WebhookStore`, and any other file-based store.

## Tests

- Kill/interrupt a write mid-flight → prior file content preserved.
- Two concurrent `create()` calls for same entity ID → exactly one
  succeeds, one receives `FileExistsError`.
- Read after interrupted write → valid JSON, not truncated.
