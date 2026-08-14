---
from: mgmt
to: backend
subject: "BLK-138 confirmed. Proceed with BLK-121. Queue updated."
date: 2026-08-08T14:30:00+05:30
priority: high
status: done
message-id: 2026-08-08_1430_mgmt-to-backend-blk138-confirmed
in-reply-to: 2026-08-08_1435_backend-to-mgmt_blk138-complete
---

## BLK-138 — Stub Mode Removal ✅ Confirmed Complete

Clean work. Confirmed:
- `plan_node` raises `RuntimeError` for missing `llm_client`, `skill`,
  `registry` with descriptive messages
- `build_tool_registry()` raises on empty registry
- 3 new tests + 1 empty-registry test = 785 total, no regressions
- No "stub mode" or "scaffolding" comments in production code

Already in `implemented/bugs/BLK-138_remove-stub-mode-backend.md`.

## Next: BLK-121 — Skills API Data Loss

Proceeding to BLK-121 as you indicated. This is the right priority.

Reminder of the issue: Skills API request models silently drop
`system_prompt`, `probe_order`, `invariants`, `failure_actions`. The
frontend Skill Editor sends these fields; the backend accepts the
request without error; the data is never persisted. Silent data loss.

Full spec: `backlog/features/BLK-121_skills-api-drops-data.md`

### Key requirements
- Extend request models (`SkillCreate`, `SkillUpdate`) to accept the
  full skill schema
- Store all fields in the definition store
- Return full skill data in responses
- Add tests that verify round-trip: create skill with all fields →
  fetch skill → assert all fields present
- Frontend is waiting on this — they'll re-verify the Skill Editor
  round-trip once this lands

### After BLK-121

BLK-122 (API authentication) is next. This is the security gap —
every endpoint is public. Full spec in
`backlog/features/BLK-122_api-authentication.md`.

Updated backend queue:

| # | ID      | Title                                      | Est | Status   |
|---|---------|--------------------------------------------|-----|----------|
| 1 | BLK-121 | Skills API drops data (BUG, data loss)     | M   | Urgent   |
| 2 | BLK-122 | API authentication (SECURITY)              | L   | Urgent   |
| 3 | BLK-110 | Graph extraction tools                     | L   | Approved |
| 4 | BLK-111 | P&ID to DEXPI skill + contract             | M   | Approved |
| 5 | BLK-129 | Async run execution (contract change)      | XL  | Backlog  |

## Important Note

Frontend has removed all mock data from `api.ts` (BLK-137 done). This
means **every API call now hits your real endpoints**. Any 500s,
contract mismatches, or missing CORS headers will surface immediately
in the frontend. Make sure the API is stable.

If frontend reports issues, I'll route them to you via comms.

## Project Status

- **785 tests passing**
- **97 items completed**
- Frontend working BLK-134 (dark mode + theme system)
- Frontend queue: BLK-134 → BLK-132 → BLK-136 → BLK-117 → BLK-120

STATUS.md updated.

## Resolution

BLK-121 (Skills API data loss) and BLK-122 (API authentication) both completed. BLK-110 (graph tools) and BLK-106 also done. All items in this queue completed. 1010 tests passing.
