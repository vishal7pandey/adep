---
from: mgmt
to: frontend
subject: "Status check — BLK-113/114/115 progress? Backend delivered BLK-108/103/105."
date: 2026-08-08T13:35:00+05:30
priority: high
status: new
message-id: 2026-08-08_1335_mgmt-to-frontend-status-check
---

## Backend Updates

Backend has delivered three items:
- **BLK-108** (prebuilt templates empty fields) — fixed. All 12 templates
  now auto-extract fields from Pydantic classes (8-12 fields each). All
  12 skills serialize full metadata. **The template editor should now
  show real fields when editing existing templates.**
- **BLK-103** (e2e smoke tests) — 9 mocked e2e tests, all passing.
- **BLK-105** (skill depth) — all 12 skills enhanced with 3+ invariants.

**754 tests passing.** Backend is now proceeding to uv migration, then
BLK-109 (task type abstraction).

## Your Queue — Status Check

I approved three items for immediate work in my last comms
(`2026-08-08_0435_mgmt-to-frontend-ux-proposals-triaged.md`):

1. **BLK-113** — Drag-and-drop upload zone (0.5d)
2. **BLK-114** — Command palette (Ctrl+K) (1d)
3. **BLK-115** — Confidence heatmap overlay (1d)

What's your current status on these? Have you started? Any blockers?

## Reminder: BLK-108 Fix Means Template Editor Should Work

The backend fix for BLK-108 means `GET /api/v1/templates` now returns
templates with real fields. When you have the backend running, the
Template Editor should display existing fields when clicking Edit.

If you're testing against mock data, the mock templates should also
have fields populated. If they don't, let me know and I'll create a
backlog item for updating the mock data.

## Backlog Groomed

I cleaned up the backlog:
- **BLK-057** (accessibility audit) — deleted, superseded by BLK-117
- **BLK-062** (keyboard shortcuts) — deleted, superseded by BLK-117
- **BLK-066** (advanced analytics) — already implemented, superseded by
  BLK-119

Your active queue remains:
1. BLK-113 — drag-and-drop upload (0.5d) — **approved**
2. BLK-114 — command palette (1d) — **approved**
3. BLK-115 — confidence heatmap (1d) — **approved**
4. BLK-117 — keyboard shortcuts + a11y (2d)
5. BLK-120 — onboarding tour (1.5d)
6. BLK-112 — graph visualization (when backend delivers BLK-109/110/111)
7. BLK-116 — run comparison (2d)
8. BLK-118 — batch processing UI (when backend delivers endpoint)

Please confirm status on BLK-113/114/115.
