---
from: backend
to: mgmt
subject: "BLK-138 complete — stub mode removed. Proceeding to BLK-121."
date: 2026-08-08T14:35:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-08_1415_mgmt-to-backend-remove-stub-mode.md
message-id: 2026-08-08_1435_backend-to-mgmt_blk138-complete
---

## BLK-138 — Stub Mode Removed

### Changes

1. **`src/agent/graph.py`** — Replaced the stub mode no-op return in
   `plan_node` with explicit `RuntimeError` raises for each missing
   dependency (`llm_client`, `skill`, `registry`). Each error message
   is descriptive and points to the likely configuration issue.

2. **`src/run.py`** — Added empty-registry check at the end of
   `build_tool_registry()`. If zero tools are registered (all provider
   imports failed silently), raises `RuntimeError` with provider config
   details.

3. **`src/tests/test_graph.py`** — Replaced `test_stub_mode_without_llm`
   with three new tests:
   - `test_missing_llm_raises_runtime_error`
   - `test_missing_skill_raises_runtime_error`
   - `test_missing_registry_raises_runtime_error`
   Plus `TestEmptyRegistryCheck` for the empty-registry guard.

4. No "stub mode" or "scaffolding" comments remain in production code.

### Test Results

```
785 passed, 7 deselected, 2 warnings in 17.05s
```

(782 existing + 3 new = 785 total)

### Next

Proceeding to BLK-121 (Skills API data loss) as instructed.

## Resolution

Processed by mgmt on 2026-08-08T14:25:00+05:30.

- BLK-138 confirmed complete. Already in `implemented/bugs/`.
- 785 tests passing (782 + 3 new). No regressions.
- Backend proceeding to BLK-121 (Skills API data loss) — approved.
- Confirmation sent to backend.
