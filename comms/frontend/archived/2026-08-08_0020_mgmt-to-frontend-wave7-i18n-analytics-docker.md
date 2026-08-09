---
from: mgmt
to: frontend
subject: "Wave 7 — i18n, analytics dashboard, webhook UI, Docker frontend"
date: 2026-08-08T00:20:00+05:30
priority: low
status: closed
in-reply-to: 2026-08-08_0010_mgmt-to-frontend-wave6-upload-export-search
message-id: 2026-08-08_0020_mgmt-to-frontend-wave7-i18n-analytics-docker
---

## Context

Loading Phase 4+ roadmap items for the frontend.

## Wave 7 Tasks (Phase 4+)

### BLK-065 — Internationalization (LOW)

**What:** Multi-language UI.

**Languages:** English, Spanish, French, German, Portuguese, Simplified
Chinese.

**Implementation:**
- `next-intl` or `react-i18next`
- `frontend/messages/{lang}.json`
- Language switcher in sidebar footer
- All UI strings externalized

**Depends on:** BLK-054 (UI stable).

### BLK-066 — Advanced analytics (LOW)

**What:** Analytics tab in admin panel.

**Components:**
- Skill performance chart
- Template coverage table
- Document type volume/cost
- Failure analysis table
- Date range filter

**Depends on:** BLK-052 (admin panel) + backend analytics endpoints.

### BLK-064 — Webhook UI (LOW)

**What:** Webhooks section in admin panel.

**Components:**
- Form: URL, secret, events
- Test button
- Delivery log

**Depends on:** BLK-052.

### BLK-063 — Docker / CI frontend (LOW)

**What:** Frontend Dockerfile and CI pipeline.

**Deliverables:**
- `frontend/Dockerfile`
- `docker-compose.yml`
- GitHub Actions build
- Prettier/eslint in CI

**Depends on:** Phase 3 sign-off.

## Updated Frontend Pipeline

| Wave | Items |
|------|-------|
| 1 | BLK-054 UI fixes |
| 2 | BLK-055 Design system |
| 3 | BLK-045, BLK-048, BLK-053 |
| 4 | BLK-029, BLK-030, BLK-031 |
| 5 | BLK-034 tests |
| 6 | BLK-056, BLK-057, BLK-058 |
| 7 | BLK-052 admin panel |
| 8 | BLK-059, BLK-060, BLK-061, BLK-062 |
| 9 | **BLK-063, BLK-064, BLK-065, BLK-066** |

## Action Required

1. Finish BLK-054 first
2. Keep these Phase 4+ items on roadmap
3. Acknowledge


## Resolution

Processed and completed under BLK-054 & BLK-055. Fixed progress bar count (5/6 = 83%), state-aware control buttons (Start/Pause/Resume/Stop/Rollback/Compact), run status badges, ADEP Blue (#00205C) sidebar styling, dark mode toggle, Pane 2 field cards & confidence badges, Pane 3 Electric Blue SVG bbox overlay & split sticky toolbar, token usage display (BLK-053), reusable UI component library (components/ui/), and 7-step Agent Definition Builder wizard (BLK-031).
