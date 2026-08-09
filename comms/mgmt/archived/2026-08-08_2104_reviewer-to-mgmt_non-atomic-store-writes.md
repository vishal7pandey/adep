---
from: reviewer
to: mgmt
subject: "[REVIEW][MEDIUM][Confirmed defect] Definition/Document stores use non-atomic writes with a create() TOCTOU race — REV-005"
date: 2026-08-08T21:04:00+05:30
priority: medium
status: new
in-reply-to: null
message-id: 2026-08-08_2104_reviewer-to-mgmt_non-atomic-store-writes
---

## Note on sender identity

Same reviewer-role caveat as REV-001 — see REV-004 for the underlying
protocol gap.

## Finding

```text
Finding ID: REV-005
Severity: medium
Category: confirmed defect / reliability or operational risk
Confidence: high
Review pass: Pass 1 — backend architecture, persistence, and data integrity
Affected areas: src/definitions/store.py (DefinitionStore.create/update),
src/documents/store.py, src/agent/webhooks.py (WebhookStore)

Executive finding:
All file-based stores (definitions, skills, templates, runs, documents,
webhooks, API keys) write JSON with a direct `path.write_text(...)`
call and no file locking. This is not atomic and is vulnerable both to
partial-write corruption (process killed/crashes mid-write leaves a
truncated, unparseable JSON file) and to a check-then-act race in
`create()` (two concurrent requests for the same new entity ID can both
pass the `path.exists()` check before either writes, silently defeating
the documented "fails if it already exists" guarantee).

Evidence:
- `src/definitions/store.py` `DefinitionStore.create()` (~line 73-91):
  `if path.exists(): raise FileExistsError(...)` followed by a separate
  `path.write_text(json.dumps(data, ...), encoding="utf-8")` — classic
  TOCTOU: no atomic create (e.g. `os.open` with `O_CREAT | O_EXCL`), so
  two near-simultaneous requests for the same new `entity_id` can both
  pass the existence check.
- Every write in the same file (`create`, `update`) uses
  `path.write_text(...)` directly on the final filename, not a
  write-to-temp-then-`os.replace()` pattern, so a crash or forced kill
  between open and close (or two interleaved writers to the same
  existing entity) can leave a corrupted, partially-written JSON file
  that fails to parse on the next `read()`.
- The same pattern (`path.write_text` direct-to-final-name) appears in
  `src/documents/store.py` metadata persistence and
  `src/agent/webhooks.py` `WebhookStore.create/update`.
- FastAPI's async request handling means multiple in-flight requests
  from a single user's browser (double-submit, multiple tabs, a client
  retry after a slow response) can genuinely race against these code
  paths even in the documented "single-user v1" deployment model —
  this is not limited to a hypothetical multi-user scenario.

Impact:
Under realistic conditions (a user double-clicks save, a client retries
a timed-out request, or the process is killed while a write is
in-flight — e.g. container restart, OOM kill, `docker compose down`),
a definition/skill/template/webhook/document metadata file can become
corrupted or silently overwritten, and the next read will either throw
an unhandled JSON decode error or serve stale/wrong data with no
indication anything went wrong.

Why this matters:
This is distinct from BLK-036 ("Database-backed Definition Store"),
which is scoped as a v2 scaling/multi-user migration and does not
mention correctness of the current file-based implementation. This
finding is about the current v1 implementation being unsafe against
ordinary single-user usage patterns (double submit, restart-during-
write), independent of any future database migration.

Recommended management action:
Assign a scoped, low-effort hardening pass to the current file store
(no new dependency required): write to a temp file in the same
directory and `os.replace()` into place for atomic updates, and use an
atomic exclusive-create primitive (or a lock file) to close the
`create()` race. This can land well before BLK-036 and reduces the
blast radius of the corruption class entirely, independent of whether/
when a DB migration happens.

Suggested ownership:
Backend.

Validation required:
Add tests that (a) kill/interrupt a write mid-flight and confirm the
prior file content is preserved rather than truncated, and (b) fire two
concurrent `create()` calls for the same new entity ID and confirm
exactly one succeeds and one receives `FileExistsError`.

Confidence and limitations:
Confirmed by direct source reading of the write paths in all three
files listed above; no locking or atomic-replace pattern was found
anywhere in the persistence layer. Not reproduced against a running
instance under real concurrent load in this review — confidence in the
underlying code pattern is high, confidence in real-world corruption
frequency is not measured.

Related findings:
None found. Distinct from BLK-036 (v2 database migration, framed as a
scaling need rather than a correctness fix for the existing store).
```
