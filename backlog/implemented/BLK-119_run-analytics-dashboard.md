---
id: BLK-119
type: feature
title: "Run analytics dashboard"
priority: medium
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T04:30:00+05:30
estimate: XL
depends-on: []
tags: [frontend, backend, ux, analytics, dashboard, metrics]
---

## Description

A `/analytics` page providing visibility into extraction performance
over time.

## Requirements

- **Extraction success rate** over time (line chart)
- **Average confidence** per field per agent (bar chart)
- **Cost per document** trend (line chart with token/$ breakdown)
- **Processing time** distribution (histogram)
- **Failure heatmap** — which fields fail most across all runs
- **Agent leaderboard** — compare performance across agent definitions
- Date range picker, agent filter, document type filter

## Acceptance Criteria

- [ ] `/analytics` route with all charts
- [ ] Date range and agent filters functional
- [ ] Data computed from run history (client-side for v1)
- [ ] Charts render correctly with 50+ runs of data
- [ ] Export analytics as PDF/CSV

## Source

Frontend proposal #7 in `2026-08-08_0425_frontend-to-mgmt_engineering-proposals.md`

## Notes

v1 can compute metrics client-side from `/runs` history. Backend
aggregated endpoints can follow. Overlaps with existing BLK-066
(advanced analytics) — this item supersedes it with more detail.
