---
id: BLK-052
type: feature
title: "Admin panel — consumption dashboard, budget monitoring, run history"
priority: medium
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T23:30:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-050, BLK-051, BLK-026]
tags: [frontend, admin, dashboard, consumption, budget, monitoring, observability]
---

## Description

Build an Admin Panel in the frontend that surfaces token consumption,
cost data, budget status, and run history. This is the human-facing
observability layer for the platform's LLM usage.

## Motivation

The workbench (3-pane) is for running extractions. The admin panel is
for understanding what they cost. Without visibility into consumption,
platform operators can't manage budgets, identify expensive runs, or
spot anomalies.

## Design

### Route

`/admin` — separate from the workbench (`/workbench`). Accessible from
sidebar footer ("Admin" link). No separate auth in v1 (single-tenant).

### Layout

```
┌──────────────────────────────────────────────────────────┐
│ ADEP Admin                          [Dark/Light] [← Back] │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │ Tokens  │  │  Cost   │  │  Runs   │  │ Avg     │    │
│  │ Today   │  │  Today  │  │  Today  │  │ Cost/Run│    │
│  │ 2.1M    │  │ $14.20  │  │   18    │  │ $0.79   │    │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Token Consumption (Last 7 Days)                   │   │
│  │                                                    │   │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │   │
│  │  Mon  Tue  Wed  Thu  Fri  Sat  Sun                │   │
│  │                                                    │   │
│  │  ▓ = input tokens  ▒ = output tokens              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Budget Status                                     │   │
│  │                                                    │   │
│  │  Global Daily:  ████████░░░░  68%  $14.20 / $100  │   │
│  │  Per-Def Daily:  ██████░░░░░░  52%  $5.20 / $10   │   │
│  │  Per-Run:        ███░░░░░░░░░  25%  $0.25 / $1.0  │   │
│  │                                                    │   │
│  │  ⚠  Warning at 80%   ✕  Block at 100%             │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Recent Runs                                       │   │
│  │                                                    │   │
│  │  Run ID    Definition     Status   Tokens  Cost   │   │
│  │  run-001   Invoice Agent  ✅ Done  8.5K   $0.05  │   │
│  │  run-002   Invoice Agent  ✅ Done  12K    $0.08  │   │
│  │  run-003   Invoice Agent  ⚠ Partial 15K   $0.09  │   │
│  │  run-004   BOQ Agent      🔄 Running 3.2K  $0.02 │   │
│  │  ...                                              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Top Expensive Runs (Last 30 Days)                 │   │
│  │                                                    │   │
│  │  Run ID    Definition     Cost     Reason          │   │
│  │  run-087   Lease Agent    $0.95   45 cycles        │   │
│  │  run-042   Audit Agent    $0.82   3 compactions    │   │
│  │  run-019   Invoice Agent  $0.71   12 retries       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Components

**1. Stat Cards (top row)**
- Tokens Today: total input + output tokens across all runs today
- Cost Today: total USD cost today
- Runs Today: count of runs started today
- Avg Cost/Run: average cost per run today

**2. Consumption Chart (7-day bar chart)**
- Stacked bars: input tokens (bottom) + output tokens (top)
- X-axis: days (Mon–Sun)
- Y-axis: token count (formatted: 1.2K, 3.5M)
- Hover tooltip: exact tokens + cost for that day
- Uses a lightweight chart library (recharts — already common with shadcn/ui)

**3. Budget Status Panel**
- Three progress bars: Global Daily, Per-Definition Daily (selected), Per-Run (current/last)
- Color: green <60%, yellow 60-80%, red >80%
- Shows consumed / limit in tokens and USD
- Warning icon (⚠) when >80%, block icon (✕) when >100%

**4. Recent Runs Table**
- Columns: Run ID, Definition name, Status (icon), Tokens, Cost, Duration, Timestamp
- Sortable by any column
- Click row → navigate to `/workbench?run={id}` (loads run in workbench)
- Pagination (20 per page)
- Status icons: ✅ complete, ⚠ partial, ❌ error, 🔄 running

**5. Top Expensive Runs**
- Sorted by cost descending (last 30 days)
- Shows run ID, definition, cost, and reason (why it was expensive)
- Reasons: "N cycles", "N compactions", "N retries", "large document"
- Click row → navigate to run in workbench

### API Endpoints Needed

```
GET /api/v1/admin/stats          — stat cards (today's aggregates)
GET /api/v1/admin/consumption    — 7-day chart data (daily breakdown)
GET /api/v1/admin/budget         — budget status (all levels)
GET /api/v1/admin/runs           — recent runs (paginated, sortable)
GET /api/v1/admin/runs/expensive — top expensive runs (last 30 days)
```

### Settings Panel (within admin)

```
┌──────────────────────────────────────────────────┐
│ Budget Settings                                   │
│                                                    │
│ Per-Run Token Limit:     [100000    ]             │
│ Per-Run Cost Limit ($):  [1.00      ]             │
│ Per-Def Daily Tokens:    [1000000   ]             │
│ Per-Def Daily Cost ($):  [10.00     ]             │
│ Global Daily Tokens:     [10000000  ]             │
│ Global Daily Cost ($):   [100.00    ]             │
│ Warning Threshold (%):   [80        ]             │
│                                                    │
│ LLM Pricing                                        │
│ Input $/1K tokens:       [0.005     ]             │
│ Output $/1K tokens:      [0.015     ]             │
│ VLM Input $/1K tokens:   [0.01      ]             │
│ VLM Output $/1K tokens:  [0.03      ]             │
│                                                    │
│              [Cancel]  [Save Settings]            │
└──────────────────────────────────────────────────┘
```

- `GET /api/v1/admin/settings` — returns current budget + pricing config
- `PUT /api/v1/admin/settings` — updates config (writes to `.env` or config store)

## Acceptance Criteria

- [ ] `/admin` route in Next.js App Router
- [ ] Sidebar footer "Admin" link navigates to `/admin`
- [ ] Stat cards: Tokens Today, Cost Today, Runs Today, Avg Cost/Run
- [ ] 7-day consumption chart (stackacked bar, input + output tokens)
- [ ] Budget status panel with 3 progress bars (color-coded)
- [ ] Recent runs table (sortable, paginated, click-through to workbench)
- [ ] Top expensive runs panel (last 30 days, with reason)
- [ ] Budget settings form (edit limits + pricing)
- [ ] "Back" button navigates to `/workbench`
- [ ] Dark/light mode supported
- [ ] ADEP brand colors (Mobility Blue for progress bars, Coral for over-budget)
- [ ] Chart uses recharts (compatible with shadcn/ui)
- [ ] All data fetched from admin API endpoints
- [ ] Loading states (skeletons) for all panels
- [ ] Empty states when no runs exist yet
- [ ] Responsive (works on tablet — admin may be used on iPad)

## Constraints

- No separate auth in v1 (single-tenant) — auth is BLK-037 (v2) [SF]
- Admin panel is read-heavy, write-light — only settings form writes [SF]
- Chart library: recharts (not custom canvas — maintainability) [RP]
- All monetary values in USD (v1 — multi-currency is v2)
- Token counts formatted with K/M suffixes for readability

## Dependencies

- BLK-050 (Token tracking — provides the data)
- BLK-051 (Budget enforcement — provides budget status)
- BLK-026 (Frontend scaffold — Next.js, TailwindCSS, shadcn/ui)

## Notes

- This is the observability layer for [TM] rules
- Admin API endpoints are part of BLK-050/051 backend work
- Future: add per-definition breakdown, per-skill comparison, anomaly alerts
