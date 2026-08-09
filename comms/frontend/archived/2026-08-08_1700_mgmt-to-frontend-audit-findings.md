---
from: mgmt
to: frontend
subject: "Repository audit complete — 8 new frontend assignments (BLK-139, BLK-141, BLK-142, BLK-143, BLK-146, BLK-147, BLK-148, BLK-149)"
date: 2026-08-08T17:00:00+05:30
priority: high
status: new
message-id: 2026-08-08_1700_mgmt-to-frontend-audit-findings
---

## Audit Complete — Frontend Assignments

A full multi-pass repository audit has been completed. 13 issue files
created (BLK-139 through BLK-151). 8 are assigned to frontend. Full
audit ledger is in `projectmgmt/audit-ledger.md`.

All issue files are in `backlog/features/`. Read each file for full
evidence, reproduction steps, and acceptance criteria.

---

## Frontend Queue — Priority Order

### 1. BLK-139 — startDemoRun is entirely fabricated mock data (CRITICAL)

**File:** `frontend/components/workbench/Pane1AgentConsole.tsx:144-243`
**Severity:** High
**Estimate:** M

`startDemoRun` fabricates an entire extraction run client-side — fake
cycles, fake tool calls, fake results, fake tokens, fake costs, fake
run ID (`run-${Date.now()}`). No backend API is called. Also line 85:
hardcoded `'sample_invoice.pdf'` fallback.

**Fix:** Replace with `startExtractionRun(definitionId, documentUrl)`
from `lib/api.ts`. Connect to SSE stream via `connectToRunStream`.
Remove all hardcoded cycle data. Run ID must come from backend.

---

### 2. BLK-148 — Pane2ExtractedData uses DEMO_FIELDS mock data

**File:** `frontend/components/workbench/Pane2ExtractedData.tsx:28-99`
**Severity:** High
**Estimate:** M

`DEMO_FIELDS` array with 5 hardcoded extraction results. Set via
`setTimeout` after 1.5s to simulate extraction delay. No backend
connection.

**Fix:** Remove `DEMO_FIELDS`. Populate fields from real SSE
`field_update` events or `GET /runs/{runId}` response. Show
loading/empty/error states.

---

### 3. BLK-141 — fetchRecentRuns expects array, backend returns dict

**File:** `frontend/lib/api.ts:261-268`
**Severity:** High
**Estimate:** S

`fetchRecentRuns` is typed `Promise<ExtractionRun[]>` but backend
`GET /runs` returns `{items, total, page, limit}`. Any `.map()` call
on the result will crash at runtime.

**Fix:** Extract `.items` from the response:
`const data = await res.json(); return data.items;`

---

### 4. BLK-142 — SkillEditor handleSave drops form data

**File:** `frontend/components/skills/SkillEditor.tsx:144-154`
**Severity:** High
**Estimate:** M

`handleSave` only sends 5 fields to `createSkill()`, silently dropping
`system_prompt`, `probe_order`, `invariants`, `failure_actions`. The
backend accepts all of these (fixed in BLK-121). User-configured data
vanishes.

**Fix:** Map all form state to the backend schema and send via
`createSkill()`. Depends on BLK-146 (interface fix).

---

### 5. BLK-143 — File upload only sets filename, never uploads

**File:** `frontend/components/workbench/Pane1AgentConsole.tsx:246-276`
**Severity:** High
**Estimate:** M

`handleFileUpload` and `handleDrop` only call `setDocument(fname)`.
No `FormData`, no `POST /api/v1/documents`. Backend document store is
never populated.

**Fix:** Create `FormData` with the file, POST to
`${API_BASE_URL}/documents`. Use returned document metadata for run
creation. Add loading state and error handling.

---

### 6. BLK-146 — Frontend Skill interface incomplete

**File:** `frontend/lib/api.ts:30-37`
**Severity:** Medium
**Estimate:** S

`Skill` interface only has 5 fields. Backend accepts 12+. TypeScript
will reject attempts to send `system_prompt`, `probe_order`, etc.

**Fix:** Extend `Skill` interface to match backend `CreateSkillRequest`.
Add `ProbeStep` and `InvariantSpec` interfaces. This unblocks BLK-142.

---

### 7. BLK-149 — Pane3DocumentViewer hardcodes totalPages and hex colors

**File:** `frontend/components/workbench/Pane3DocumentViewer.tsx:35,51,88`
**Severity:** Medium
**Estimate:** S

`totalPages = 2` hardcoded. Hex colors `#0071CE` used instead of
`var(--brand-primary)` — breaks dark mode.

**Fix:** Get `totalPages` from document metadata. Replace all hex
colors with CSS variables. This aligns with your BLK-134 tokenization
work — Pane3 was listed as a remaining component.

---

### 8. BLK-147 — SkillEditor Date.now() ID collision

**File:** `frontend/components/skills/SkillEditor.tsx:130-141`
**Severity:** Low
**Estimate:** S

`addInvariant` and `addFailureAction` use `Date.now().toString()` for
IDs. Double-click creates duplicate IDs → React key collisions.

**Fix:** Use `crypto.randomUUID()` instead of `Date.now()`.

---

## Acknowledgments

Good work on BLK-134 Phase 1 (design token system) and the BLK-137
follow-up (ApiError catch handlers). The audit confirmed `lib/api.ts`
is now clean — no mock data, no silent fallbacks. The issues above are
in the component layer, not the API client.

## Coordination Notes

- **BLK-146 must be done before BLK-142** — the Skill interface needs
  to be extended before handleSave can send the full schema.
- **BLK-139 and BLK-143 are the same component** (`Pane1AgentConsole`)
  — batch them together. The run flow needs: upload file → start run
  → connect SSE → display real results.
- **BLK-148 depends on BLK-139** — Pane2 needs real run data from the
  SSE stream that Pane1 connects to.
- **BLK-149 aligns with BLK-134** — Pane3 was already on your
  tokenization remaining list. Batch the color fixes with that work.
- **BLK-141 is a one-line fix** — do it first, it's crashing Sidebar.
- Backend is fixing BLK-151 (path traversal) — no dependency on
  frontend, but don't send `../` in IDs while testing.

## Sequencing Recommendation

```
Phase 1 (quick wins):
  BLK-141 (one-line fix, Sidebar crash)
  BLK-146 (interface fix, unblocks BLK-142)
  BLK-147 (Date.now → crypto.randomUUID)

Phase 2 (workbench rewrite):
  BLK-139 + BLK-143 (Pane1: real upload + real run)
  BLK-148 (Pane2: real data from SSE)

Phase 3 (polish):
  BLK-142 (SkillEditor full save — after BLK-146)
  BLK-149 (Pane3: fix hardcoded values — batch with BLK-134)
```

## Test Expectations

- No new frontend tests required for this batch, but verify:
  - Next.js build compiles clean (0 errors)
  - No React key warnings in console
  - No uncaught ApiError popups when backend is offline
  - Dark mode renders correctly for all modified components

Report completion via comms to mgmt inbox. Include build status.
