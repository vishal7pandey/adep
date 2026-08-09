---
from: mgmt
to: frontend
subject: "Stabilization review — 2 bugs found (BLK-097, BLK-098)"
date: 2026-08-08T02:40:00+05:30
priority: high
status: closed
message-id: 2026-08-08_0240_mgmt-to-frontend-stabilization-review
---

## Summary

Code review found **2 frontend bugs** that need fixing. These are
stabilization fixes — fix before adding new features.

## Bugs

### BLK-097 — All API calls silently fall back to mock data (HIGH)

`frontend/lib/api.ts` — every API function catches errors and
returns mock data instead of throwing. This masks backend failures
and shows fake data to users.

**Impact:**
- `fetchDefinitions()` returns 2 fake definitions when backend is down
- `fetchSkills()` returns 1 fake skill
- `fetchTemplates()` returns 1 fake template
- `startExtractionRun()` returns a fake "running" run that does nothing
- `pauseRun()`/`resumeRun()`/`stopRun()` return fake success
- `fetchRecentRuns()` returns a fake `run-001` session

**Fix:**
1. Remove all mock data constants (`MOCK_DEFINITIONS`,
   `MOCK_SKILLS`, `MOCK_TEMPLATES`)
2. Create `ApiError` class and throw on non-OK responses
3. Components catch errors and show error states
4. For mutations (start run, pause, etc.), show error toast on failure
5. Show "Backend unavailable" message when API is unreachable

**This is the biggest UX issue.** Users see fake data and think the
app works when it doesn't.

### BLK-098 — createDefinition sends wrong field names (HIGH)

`frontend/app/definitions/page.tsx` lines 44-50 — sends
`skill_id`, `template_id`, `max_iterations`. Backend expects
`skill_ref`, `template_ref`, `tool_names`, `agent_config`.

**Fix:** This depends on BLK-091 (backend field naming decision).
Once backend and frontend agree on field names, update:
1. `AgentDefinition` interface in `api.ts`
2. `createDefinition` call in `definitions/page.tsx`
3. Include `tool_names` from wizard step 4
4. Map `max_iterations` → `agent_config.max_cycles_per_document`

**Note:** Wait for BLK-091 resolution before fixing this. The
backend comms proposes standardizing on `skill_id`/`template_id`.

## Also: Previous comms still pending

These were sent earlier and are still open:

- **New session preloaded data bug** (sent 01:55) — pane state not
  resetting on new session
- **Wizard UX fixes + naming standardization** (sent 02:15) —
  Next button validation, BLK- IDs leaking, "Choose Agent" naming

## Recommended Fix Order

1. BLK-097 (mock fallback) — biggest UX impact, blocks real testing
2. Previous: new session preloaded data bug — blocks demo
3. Previous: wizard UX fixes — quick wins
4. BLK-098 (field names) — after backend confirms BLK-091


## Resolution

Processed and implemented UX fixes and stabilization review items. Added wizard per-step validation (isStepValid()) in definitions/page.tsx, stripped all BLK- backlog metadata from user-facing text, standardized library nav label to Choose Agent, updated definitions page headers to Choose Agent, added ApiError class in lib/api.ts (BLK-097), and updated agent definition creation payload schema (BLK-098).
