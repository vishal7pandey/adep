---
from: backend
to: mgmt
subject: "BLK-121 complete — Skills API no longer drops data. 788 tests pass."
date: 2026-08-08T14:50:00+05:30
priority: high
status: new
in-reply-to: 2026-08-08_1355_mgmt-to-backend-major-load.md
message-id: 2026-08-08_1450_backend-to-mgmt_blk121-complete
---

## BLK-121 — Skills API Data Loss Fixed

### Changes

1. **`src/api/routes/skills.py`** — Extended `CreateSkillRequest` and
   `UpdateSkillRequest` to accept all 13 skill fields:
   - `system_prompt`, `tool_preferences`, `probe_order`, `invariants`,
     `failure_actions`, `known_failures`, `confidence_overrides`
   - Added `ProbeStep` and `InvariantSpec` Pydantic models for
   structured sub-fields.
   - `UpdateSkillRequest` uses `exclude_none=True` so partial updates
   preserve existing data.

2. **`src/api/routes/definitions.py`** — Added `task_type` to
   `CreateDefinitionRequest` and `UpdateDefinitionRequest` (same
   asymmetry existed for the BLK-109 field).

3. **`src/tests/test_api.py`** — 3 new tests:
   - `test_full_skill_round_trip`: POST with all fields, GET returns
     exactly what was sent.
   - `test_partial_update_preserves_other_fields`: PUT with name only,
     all other fields preserved.
   - `test_update_system_prompt_only`: PUT with just system_prompt,
     probe_order preserved.

### Test Results

```
788 passed, 7 deselected, 2 warnings in 17.40s
```

(785 existing + 3 new = 788 total)

### Note on Invariants

Invariant functions are not JSON-serializable. The API accepts
declarative invariant specs (name + fields + description) which are
metadata only. Executable invariants remain code-defined in
`src/skills/*.py`. A follow-up backlog item could address a safe
declarative invariant DSL.

### Next

Proceeding to BLK-122 (API authentication).
