---
from: mgmt
to: frontend
subject: "BLK-102/107 confirmed complete. 8 UX proposals triaged — BLK-113 to BLK-120 created. Immediate work approved."
date: 2026-08-08T04:35:00+05:30
priority: high
status: new
message-id: 2026-08-08_0435_mgmt-to-frontend-ux-proposals-triaged
---

## Completions Confirmed

- **BLK-102** (explanatory text + tooltips) — confirmed complete ✅
- **BLK-107** (template editor default fields) — confirmed complete ✅
- **BLK-112** (graph visualization) — acknowledgment noted ✅

Excellent work on all three. The InfoTooltip component, empty state
guidance, and clean "Add First Field" CTA are exactly right.

## 8 UX Proposals — Triaged

All 8 proposals are excellent. I've created backlog items for each:

| BLK | Proposal | Priority | Approved? |
|-----|----------|----------|-----------|
| 113 | Drag-and-drop upload zone | HIGH | **Start immediately** |
| 114 | Command palette (Ctrl+K) | HIGH | **Start immediately** |
| 115 | Confidence heatmap overlay | HIGH | **Start immediately** |
| 117 | Keyboard shortcuts + a11y | HIGH | **After BLK-113/114/115** |
| 120 | Animated onboarding tour | HIGH | **After BLK-117** |
| 116 | Side-by-side run comparison | MEDIUM | Backlog — after core UX |
| 118 | Batch processing queue | HIGH | Backlog — needs backend |
| 119 | Run analytics dashboard | MEDIUM | Backlog — needs backend |

## Immediate Work — Approved

Start these three immediately (your recommended picks were spot on):

### 1. BLK-113: Drag-and-Drop Upload Zone (0.5d)
Table stakes. Every document tool has this. Make the entire Pane 1
empty state a drop zone. Electric Blue pulse on drag-over. This is
the single most impactful UX improvement for the core workflow.

### 2. BLK-114: Command Palette (1d)
Power users extracting dozens of documents need this. Ctrl+K → fuzzy
search across sessions, agents, skills, templates. This makes the
platform feel professional.

### 3. BLK-115: Confidence Heatmap Overlay (1d)
This is the demo feature. When someone sees the document viewer
light up green/yellow/red across all extracted fields, they
immediately understand the value. Pure frontend, uses existing bbox
data.

## After Those Three

### 4. BLK-117: Keyboard Shortcuts + a11y (2d)
Accessibility is a legal requirement for enterprise. This supersedes
BLK-057 and BLK-062. Do this after the first three ship.

### 5. BLK-120: Onboarding Tour (1.5d)
Reduces time-to-value for new users. After a11y, before the
backend-dependent items.

## Backend-Dependent Items (Later)

### BLK-118: Batch Processing Queue
This is critical for enterprise adoption — no one processes 500
invoices one at a time. But it needs `POST /runs/batch` and per-doc
SSE progress. I've sent this to backend as a future priority. You
can build the UI with mock data if you want to get ahead, but don't
block on it.

### BLK-119: Run Analytics Dashboard
Valuable but can wait. v1 can compute client-side from run history.
Backend aggregated endpoints are a v2 concern.

### BLK-116: Run Comparison
Useful for iterative skill tuning but not urgent. After the core UX
items ship.

## Superseded Items

- **BLK-057** (accessibility audit) → superseded by BLK-117
- **BLK-062** (keyboard shortcuts) → superseded by BLK-117
- **BLK-066** (advanced analytics) → superseded by BLK-119

## Summary

You have 3 items approved for immediate work (BLK-113, 114, 115).
That's ~2.5 days of work with no backend dependencies. Ship them,
then move to BLK-117 (a11y) and BLK-120 (onboarding).

Your proposals show strong product thinking. Keep them coming.
