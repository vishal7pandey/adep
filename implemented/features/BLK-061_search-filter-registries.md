---
id: BLK-061
type: feature
title: "Search & filter in registries — definitions, skills, templates, runs"
priority: medium
status: backlog
phase: 4
owner: unassigned
created: 2026-08-08T00:05:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-019, BLK-020, BLK-021, BLK-022]
tags: [frontend, backend, search, filter, registry, ui]
---

## Description

Add search and filter to the Agent Definitions, Skills, Templates, and
Runs registry pages. Users need to find existing assets quickly as the
library grows.

## Registry Pages

| Page | Search Fields | Filters |
|------|---------------|---------|
| `/definitions` | name, description | skill, template, status |
| `/skills` | name, description | tool used, semantic checks |
| `/templates` | name, description | field name, field type |
| `/runs` | run id, document name | status, definition, date range |

## API Additions

```
GET /api/v1/definitions?q={query}&skill={skill_id}&template={template_id}
GET /api/v1/skills?q={query}&tool={tool}&semantic={true|false}
GET /api/v1/templates?q={query}&field_type={type}
GET /api/v1/runs?q={query}&status={status}&definition_id={id}&from={date}&to={date}
```

## UI

- Search input at top of each registry
- Filter chips/dropdowns
- Clear all filters button
- Result count
- Empty state: "No matches for '...'"

## Acceptance Criteria

- [ ] Search by name and description
- [ ] Filter by relevant fields
- [ ] Combined search + filters
- [ ] Result count shown
- [ ] Clear filters button
- [ ] Empty state
- [ ] Backend filtering (not just frontend)
- [ ] Unit tests for query parsing
- [ ] Integration test for each registry endpoint

## Constraints

- File-based store — use simple filename/description matching, not
  full-text search engine [SF]
- Case-insensitive substring search
- v1: no pagination yet (deferred until needed)

## Dependencies

- BLK-019, BLK-020, BLK-021, BLK-022 (REST endpoints)
