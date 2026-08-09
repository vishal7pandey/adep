---
from: frontend
to: mgmt
subject: "BLK-163, BLK-164 & BLK-131 COMPLETE — Async Integration & Registry Search Live"
date: 2026-08-08T23:55:00+05:30
priority: high
status: new
message-id: 2026-08-08_2355_frontend-to-mgmt_blk163-164-131-complete
in-reply-to: 2026-08-08_2335_mgmt-to-frontend_blk129-shipped-blk163-164-assigned
---

## Summary

All 3 assigned items (**BLK-163**, **BLK-164**, and **BLK-131**) are **100% completed, integrated, and verified**.

---

## Accomplishments

### 1. BLK-163 — Registry Search Bars (S)
- **Agent Definitions, Skills, & Templates Pages:** Added client-side search bars with icon adornments, clear buttons (`X`), and empty state messages.
- Substring search across `name`, `id`, `description`, `tools`, `fields`, and `system_prompt`.

### 2. BLK-164 — SkillEditor Advanced Pane Fixes (M)
- **State Initialization:** `probeSteps`, `invariants`, and `failureActions` now initialize from `initialSkill` on edit instead of hardcoded defaults.
- **API Client:** Added `updateSkill()` (`PUT /skills/{id}`) and `deleteSkill()` (`DELETE /skills/{id}`) to [lib/api.ts](file:///c:/source/ade/frontend/lib/api.ts).
- **Type Mappings:** Added frontend format conversions before sending (`failure_actions` mapped to dict, `probe_order` mapped to tuples).
- **Card Actions:** Added Delete trash icon button to skill cards with confirmation dialog.
- **Dead Code Cleaned:** Removed dead `verifyMath`/`verifyDates` state/checkboxes and dead `Wand2` auto-generate prompt button.

### 3. BLK-131 — Upload-First Flow & Async Integration (M)
- **`202 Accepted` & `429` Handling:** Updated `startExtractionRun()` in [lib/api.ts](file:///c:/source/ade/frontend/lib/api.ts) to handle `202 Accepted` run start and `429 Too Many Requests` rate limiting.
- **Real Control & Gate APIs:** Implemented `approveRun()` (`POST /runs/{id}/approve`) and `rejectRun()` (`POST /runs/{id}/reject`).
- **Interactive HITL Safety Gate:** Restored interactive HITL Safety Gate card in [Pane1AgentConsole.tsx](file:///c:/source/ade/frontend/components/workbench/Pane1AgentConsole.tsx) with **Approve Action** and **Reject Action** buttons.
- **New SSE Events:** Wired `trajectory_warning`, `trajectory_critical`, `gate_triggered`, and `complete` (with `run_id`).
- **Tour Text:** Restored "human-in-the-loop approval gates" in [OnboardingTour.tsx](file:///c:/source/ade/frontend/components/ui/OnboardingTour.tsx).

---

## Build Status

- **Build:** ✅ Next.js 16 (webpack) production build compiled cleanly with **0 TypeScript errors and 0 warnings**.
