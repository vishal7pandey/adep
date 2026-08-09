---
id: BLK-066
type: feature
title: "Advanced analytics — per-skill, per-template, per-document-type insights"
priority: low
status: backlog
phase: 4
owner: unassigned
created: 2026-08-08T00:15:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-050, BLK-052]
tags: [frontend, backend, analytics, insights, reporting]
---

## Description

Extend the admin panel with analytics that help operators understand
which skills, templates, and document types are performing well and
which need improvement.

## Analytics Dashboard

### 1. Skill Performance
- Extraction success rate per skill
- Average confidence per skill
- Average tokens/cost per run
- Top failing fields per skill
- Chart: success rate over time

### 2. Template Performance
- Required vs optional field coverage
- Average confidence per field
- Most common missing fields
- Time to complete per template

### 3. Document Type Insights
- Volume by document type (from definition usage)
- Average extraction time
- Error rate by document type
- Cost per document type

### 4. Failure Analysis
- Most common `GapType` across runs
- Fields that fail most often
- Retry-loop frequency
- Most expensive failed runs

### 5. User-Level Activity (v2)
- Deferred until multi-tenant (BLK-037)

## API Endpoints

```
GET /api/v1/admin/analytics/skills
GET /api/v1/admin/analytics/templates
GET /api/v1/admin/analytics/documents
GET /api/v1/admin/analytics/failures
```

## Frontend

- New "Analytics" tab in admin panel
- Bar charts, line charts, tables
- Date range filter
- Export chart as PNG

## Acceptance Criteria

- [ ] Backend aggregates per-skill, per-template, per-doc-type metrics
- [ ] 4 analytics endpoints
- [ ] Admin panel analytics tab
- [ ] Charts for success rate, confidence, cost
- [ ] Failure analysis table
- [ ] Date range filter
- [ ] Tests for aggregation logic
- [ ] Integration test: complete 3 runs → analytics correct

## Constraints

- v1: aggregate from `.adep/runs/` files. No external analytics DB.
- Charts use recharts (same as admin consumption chart).

## Dependencies

- BLK-050 (token usage data)
- BLK-052 (admin panel)
