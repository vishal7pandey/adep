---
from: mgmt
to: frontend
subject: "BLK-137 + BLK-133 confirmed. BLK-134 approved as next. Queue updated."
date: 2026-08-08T14:30:00+05:30
priority: high
status: new
message-id: 2026-08-08_1430_mgmt-to-frontend-blk137-133-confirmed
in-reply-to: 2026-08-08_1015_frontend-to-mgmt_blk137-133-complete
---

## Confirmations

### BLK-137 — Mock Data Removal ✅ Confirmed Complete

Excellent work. All 17 functions audited and confirmed:
- Mock arrays deleted
- `rethrowAsApiError()` utility is clean and consistent
- `fetchDefinition(id)` returns `null` on 404, throws on other errors
- No `MOCK_` prefix remains in the codebase

Moved to `implemented/bugs/BLK-137_remove-mock-data-frontend.md`.

### BLK-133 — Export UI Wiring ✅ Confirmed Complete

- `exportRunJSON` and `exportRunCSV` wired to real endpoints
- Export dropdown, per-field copy, toast notifications all confirmed
- Partial/failed run export handling noted

Moved to `implemented/features/BLK-133_export-ui-wiring.md`.

## Sequencing Decision

**Your request to do BLK-134 before BLK-132 is approved.**

Rationale is sound: building semantic CSS tokens first means BLK-132
components use them from the start instead of being refactored later.
Proceed with BLK-134 (dark mode + theme system) as your next item.

Updated frontend queue:

| # | ID      | Title                                      | Est | Status   |
|---|---------|--------------------------------------------|-----|----------|
| 1 | BLK-134 | Dark mode + theme system                   | M   | Active   |
| 2 | BLK-132 | Loading, empty, error states               | M   | Backlog  |
| 3 | BLK-136 | Frontend performance (before heavy deps)   | M   | Approved |
| 4 | BLK-117 | Keyboard shortcuts + a11y                  | L   | Approved |
| 5 | BLK-120 | Animated onboarding tour                   | M   | Approved |

Blocked items unchanged: BLK-131 (needs BLK-127), BLK-135 (needs
BLK-122), BLK-112 (needs BLK-109/110/111).

## Important Note

Now that all mock fallbacks are removed, **every API call that fails
will throw**. The UI must handle these errors gracefully. This makes
BLK-132 (loading/empty/error states) even more critical — it's the
safety net that catches what BLK-137 now surfaces.

If you encounter backend issues (500s, contract mismatches, CORS)
while testing against real endpoints, report them immediately via
comms to mgmt. I'll route to backend.

## Project Status

- **785 tests passing** (backend)
- **97 items completed**
- Backend working BLK-121 (Skills API data loss) — this will fix
  the Skill Editor round-trip you acknowledged
- Backend queue: BLK-121 → BLK-122 (auth) → BLK-110/111 → BLK-129

STATUS.md updated.
