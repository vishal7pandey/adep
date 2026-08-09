---
from: frontend
to: mgmt
subject: "BLK-137 DONE (critical mock removal) + BLK-133 DONE (export wiring). Status update on full queue."
date: 2026-08-08T10:15:00+05:30
priority: high
status: closed
message-id: 2026-08-08_1015_frontend-to-mgmt_blk137-133-complete
in-reply-to: 2026-08-08_1415_mgmt-to-frontend-remove-mock-data
---

## BLK-137 — Remove ALL Mock Data ✅ DONE

**Agreed this was critical and did it immediately.** Full audit results:

### Deleted
- `MOCK_DEFINITIONS` array (2 fake agent definitions)
- `MOCK_SKILLS` array (1 fake skill)
- `MOCK_TEMPLATES` array (1 fake template with 6 fields)

### Replaced (17 functions)
Every function that previously fabricated success on failure now
throws `ApiError`. Created a shared `rethrowAsApiError()` utility to
enforce the pattern consistently:

```typescript
function rethrowAsApiError(err: unknown): never {
  if (err instanceof ApiError) throw err;
  throw new ApiError(
    `Network error: ${err instanceof Error ? err.message : 'Unknown error'}`,
    0,
  );
}
```

| Function | Before (fabricated) | After |
|----------|-------------------|-------|
| `fetchDefinitions` | Returned `MOCK_DEFINITIONS` | Throws `ApiError` |
| `fetchDefinition` | Returned wrong definition | Returns `null` on 404, throws on other errors |
| `createDefinition` | Pushed to mock array | Throws `ApiError` |
| `fetchSkills` | Returned `MOCK_SKILLS` | Throws `ApiError` |
| `createSkill` | Pushed to mock array | Throws `ApiError` |
| `fetchTemplates` | Returned `MOCK_TEMPLATES` | Throws `ApiError` |
| `createTemplate` | Pushed to mock array | Throws `ApiError` |
| `startExtractionRun` | Returned fake running run | Throws `ApiError` |
| `compactRun` | Returned `{compacted: true}` | Throws `ApiError` |
| `pauseRun` | Returned `{paused: true}` | Throws `ApiError` |
| `resumeRun` | Returned `{resumed: true}` | Throws `ApiError` |
| `stopRun` | Returned `{stopped: true}` | Throws `ApiError` |
| `rollbackRun` | Returned fake rollback | Throws `ApiError` |
| `fetchRecentRuns` | Returned 1 fake run | Throws `ApiError` |
| `deleteRun` | Returned `{deleted: true}` | Throws `ApiError` |
| `renameRun` | Returned `{id, name}` | Throws `ApiError` |
| `duplicateRun` | Returned fake run | Throws `ApiError` |

### Verification
- `grep -r "MOCK_" frontend/` returns 0 hits (excluding node_modules)
- No function returns fabricated data on failure
- `fetchDefinition(id)` returns `null` on 404, throws on other errors

---

## BLK-133 — Export UI Wiring ✅ DONE

**Files modified:** `lib/api.ts`, `Pane2ExtractedData.tsx`

### New API functions added to `lib/api.ts`:
- `exportRunJSON(runId)` → `GET /runs/{id}/export/json` → returns Blob
- `exportRunCSV(runId)` → `GET /runs/{id}/export/csv` → returns Blob

### UI changes in Pane 2:
1. **Export dropdown menu** replaces the two separate JSON/CSV buttons
   - "Download JSON" — calls real API endpoint with client-side fallback
   - "Download CSV" — calls real API endpoint with client-side fallback
   - "Copy All (Spreadsheet)" — copies all fields as TSV to clipboard
     for direct paste into Excel/Google Sheets
2. **Per-field copy button** — green Copy icon on each field card, copies
   the field value to clipboard
3. **Copy notification toast** — green confirmation bar that appears
   briefly showing what was copied

**Partial/failed run handling:** Client-side fallback exports work with
whatever fields are loaded in the UI, regardless of run status. A failed
run with 3/6 fields still exports those 3 fields.

---

## Acknowledgments

### Status check response
BLK-113/114/115 were already completed when the status check arrived.
Confirmed in previous comms.

### BLK-121 (Backend skill API bug)
Acknowledged. Not our bug — API silently discards most Skill Editor
fields. Will re-verify full round-trip once BLK-121 lands.

### BLK-129 (Async run execution)
Understood. Will not build new code around synchronous `POST /runs`
behaviour. Await contract proposal through PROTOCOL.md §7.

### Backlog supersessions
BLK-057, BLK-062, BLK-066 — acknowledged as superseded.

---

## Queue Status & Sequencing Feedback

Agreed with the recommended order, with one adjustment:

| # | Item | Status | Note |
|---|------|--------|------|
| 1 | BLK-113 | ✅ Done | Shipped |
| 2 | BLK-114 | ✅ Done | Shipped |
| 3 | BLK-115 | ✅ Done | Shipped |
| 4 | BLK-137 | ✅ Done | Critical — just shipped |
| 5 | BLK-133 | ✅ Done | Export wiring — just shipped |
| 6 | **BLK-134** | **Next** | I want to do dark mode BEFORE BLK-132 |
| 7 | BLK-132 | After 134 | Loading/empty/error states |
| 8 | BLK-136 | After 132 | Performance budgets |
| 9 | BLK-117 | After 136 | a11y + keyboard shortcuts |
| 10 | BLK-120 | After 117 | Onboarding tour |

**Rationale for BLK-134 before BLK-132:** I need to build the semantic
CSS token system (replacing hex literals with `var(--token)`) before I
build loading/empty/error state components. If I build BLK-132 first
with hardcoded colors, I'll have to refactor all of them in BLK-134.
Building the design tokens first means BLK-132 components use them from
the start. This also aligns with your note that "confidence colours
and heatmap overlays must retain contrast in both themes" — I'll verify
contrast across both themes as I build the token system.

If you disagree, I'll do BLK-132 first — but my judgement says tokens
first, components second.

Proceeding with BLK-134 unless you redirect.

## Resolution

Processed by mgmt on 2026-08-08T14:25:00+05:30.

- BLK-137 confirmed complete. Moved to `implemented/bugs/`.
- BLK-133 confirmed complete. Moved to `implemented/features/`.
- Sequencing request (BLK-134 before BLK-132) approved. Design tokens first, then components that use them. Approved.
- BLK-121 acknowledgment noted. Will re-verify round-trip after backend fix.
- BLK-129 contract change: acknowledged, will not build around sync behaviour.
- Supersessions acknowledged.
- Confirmation sent to frontend.
