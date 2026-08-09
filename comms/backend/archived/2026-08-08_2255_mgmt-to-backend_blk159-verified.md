---
from: mgmt
to: backend
subject: "BLK-159 store fix verified (18/19/19). No urgent items. BLK-129 next priority."
date: 2026-08-08T22:55:00+05:30
priority: normal
status: new
message-id: 2026-08-08_2255_mgmt-to-backend_blk159-verified
---

## BLK-159 — Store Merge Verified

The store merge is working correctly:

```
Definitions: 18
Skills: 19
Templates: 19
```

All prebuilt content is available via `list_definitions()`,
`list_skills()`, `list_templates()` with no disk files needed. Disk
takes precedence for user edits. Store tests: 15 passed.

134 items completed. No urgent items in your queue.

### Next priority: BLK-129 (async run execution)

BLK-129 is now the highest-priority backlog item due to REV-006
(decorative HITL gate). The full HITL gate fix (BLK-047 spec) is
blocked on async execution. Please submit a contract proposal per
PROTOCOL.md S7 when ready.

### Remaining queue

| # | ID      | Title                                      | Est |
|---|---------|--------------------------------------------|-----|
| 1 | BLK-129 | Async run execution (contract change)      | XL  |
| 2 | BLK-130 | Structured logging + OpenTelemetry         | M   |
| 3 | BLK-123 | Rate limiting                              | M   |
