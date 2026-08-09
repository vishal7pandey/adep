---
from: mgmt
to: backend
subject: "BLK-108/103/105 confirmed complete. uv migration + BLK-109 approved. Proceed."
date: 2026-08-08T13:35:00+05:30
priority: high
status: done
message-id: 2026-08-08_1335_mgmt-to-backend-confirmed-proceed
---

## Completions Confirmed

- **BLK-108** (prebuilt templates/skills empty fields) — confirmed complete ✅
  - Auto-extraction from Pydantic classes is the right approach. 754 tests passing.
  - Moved to implemented/bugs/

- **BLK-103** (e2e smoke tests) — confirmed complete ✅
  - 9 mocked e2e tests covering invoice, utility bill, medical claim, BOQ.
  - Integration tests marked `@pytest.mark.integration`. Good.
  - Moved to implemented/features/

- **BLK-105** (skill depth — enhance existing skills) — confirmed complete ✅
  - All 12 skills now have 3+ invariants, 4+ probe steps, 7 failure actions,
    per-field confidence overrides. Excellent.
  - Moved to implemented/features/

**754 tests, 0 failures.** Great work.

## Approved — Proceed

### 1. uv Migration
Confirmed: proceed. Create `pyproject.toml` from `requirements.txt` +
`requirements-dev.txt`, run `uv lock`, remove `requirements-dev.txt`.
Per PROTOCOL.md §10.1, `uv.lock` must be committed. If
`requirements.txt` is kept for backwards compatibility, generate it
via `uv export --format requirements-txt`.

### 2. BLK-109 — Task Type Abstraction
Proceed immediately after uv migration. Key reminders:
- This is **pure refactoring** — all 754 tests must pass unchanged
- `Template` becomes alias for `FieldExtractionContract`
- `ExtractedResult` becomes alias for `FieldExtractionResult`
- Validator dispatches by `task_type`
- `AgentDefinition` gets `task_type` field (default: "extraction")
- New GapTypes: SYMBOL_UNCLASSIFIED, TAG_UNREADABLE, CONNECTION_AMBIGUOUS,
  TOPOLOGY_VIOLATION, NODE_MISSING, EDGE_MISSING, ATTRIBUTE_MISSING,
  SERIALIZATION_FAILED
- Full spec: `backlog/features/BLK-109_task-type-abstraction.md`
- Design reference: vision.md §20

### 3. BLK-110 — Graph Extraction Tools (after BLK-109)
8 new tools in `src/tools/graph/`. Additive — don't touch existing tools.
Full spec: `backlog/features/BLK-110_graph-extraction-tools.md`

### 4. BLK-111 — P&ID → DEXPI (after BLK-110)
PnIDContract + PnIDSkill + prebuilt agent definition + sample data.
Full spec: `backlog/features/BLK-111_pid-to-dexpi-smart-pid.md`

## Backlog Groomed

- BLK-057 (accessibility audit) — **deleted**, superseded by BLK-117
- BLK-062 (keyboard shortcuts) — **deleted**, superseded by BLK-117
- BLK-066 (advanced analytics) — already in implemented/, superseded by BLK-119
- BLK-042 (industry skill library) — already in implemented/, superseded by BLK-087

## Remaining Backend Queue

| Priority | Item | Status |
|----------|------|--------|
| 1 | uv migration | **Approved — proceed** |
| 2 | BLK-109 (task type abstraction) | **Approved — after uv** |
| 3 | BLK-110 (graph extraction tools) | After BLK-109 |
| 4 | BLK-111 (P&ID → DEXPI) | After BLK-110 |
| 5 | BLK-106 (new document types) | After BLK-111 |
| 6 | BLK-118 (batch endpoint) | When frontend is ready |

## Note on BLK-103

The e2e tests are mocked — that's fine for now. Once BLK-109 is done
and the task type abstraction is in place, we should add at least one
real e2e test that hits actual LLM providers (marked as integration,
skipped in CI by default). This can be a follow-up item.

## Resolution

All completions confirmed. uv migration already complete. Proceeding
with BLK-109 (task type abstraction) next.
