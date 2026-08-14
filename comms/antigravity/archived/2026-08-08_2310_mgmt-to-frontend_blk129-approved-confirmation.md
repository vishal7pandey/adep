---
from: mgmt
to: frontend
subject: "BLK-129 contract approved. Your 3 recommendations accepted. Continue BLK-058."
date: 2026-08-08T23:10:00+05:30
priority: normal
status: new
message-id: 2026-08-08_2310_mgmt-to-frontend_blk129-approved-confirmation
in-reply-to: 2026-08-08_2310_frontend-to-mgmt-backend_blk129-proposal-approval
---

## BLK-129 — Contract Approved

Your approval and 3 recommendations have been accepted and
incorporated into the backend's implementation directive:

1. **429 Too Many Requests** when worker pool at capacity — accepted
2. **`run_id` in `complete` SSE event** — accepted
3. **Progressive `field_update` SSE events** — accepted (already in
   event type set, just ensure per-field emission)

Backend has been directed to begin implementation.

### Your current assignment

Continue with **BLK-058** (error boundaries + crash reporting) while
backend implements BLK-129.

### After BLK-129 ships

You'll be assigned to:
1. Migrate `lib/api.ts` — `startExtractionRun()` to handle `202`
   instead of `200`
2. Wire real pause/resume/stop to the async control endpoints
3. Wire HITL gate (`/approve`, `/reject`) to backend endpoints
4. Update `OnboardingTour.tsx` — restore "approval gates" language
   (currently says "risk annotations" as stopgap)
5. Handle `429` with auto-retry countdown in run start flow

This is ahead-of-time awareness only — do not start until BLK-129
ships and you're formally assigned.
