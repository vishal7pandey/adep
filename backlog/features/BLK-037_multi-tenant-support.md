---
id: BLK-037
type: feature
title: "Multi-tenant support (v3, if warranted)"
priority: low
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: XL
depends-on: [BLK-036]
tags: [multi-tenant, v3, scaling, architecture]
---

## Description

Multi-tenant support if the platform proves out and multi-user access is
needed. Each tenant has their own definitions, skills, templates, and runs.

## Acceptance Criteria

- [ ] Tenant isolation model
- [ ] Authentication + authorization
- [ ] Per-tenant definition store
- [ ] Per-tenant run isolation

## Constraints

- Only build if the platform proves out (vision.md §6 non-goal for v1)
- Architecture decision required from mgmt

## Dependencies

- BLK-036 (database-backed store)

## Notes

- vision.md §6 (Non-Goals: not multi-tenant SaaS in v1)
