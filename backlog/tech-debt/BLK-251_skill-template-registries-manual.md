---
id: BLK-251
type: tech-debt
title: "Definition/Skill/Template resolution depends on manual registries and duplicated alias mappings"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T12:55:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-217]
tags: [backend, skills, templates, registry, architecture, tech-debt, drift]
---

## Description

`src/api/run_engine.py` hand-imports 22 skill classes + 22 template classes (44 import lines) and maintains two parallel static registries (`_SKILL_REGISTRY`, `_TEMPLATE_REGISTRY`) with duplicate backward-compat aliases (`"invoice"` and `"sk-invoice-basic"` → same class; `"trade_finance_mt700"` and `"trade_finance"` → same template). A second, dynamic resolution path (`_build_dynamic_skill` / `_build_dynamic_template`) exists for user-created definitions from the DefinitionStore.

## Problem Statement

Adding or changing a document type touches up to four manual places (skill file, template file, two registry dicts), and the aliases are exactly the kind of hand-maintained coupling that produced the BLK-172 duplicate-definition bug. The two paths (static registry vs dynamic store) can drift — a user-created skill with the same ID as a built-in aliases unpredictably, and there is no test that guarantees every `src/skills/*.py` class is registered (or vice-versa).

This overlaps BLK-217 (tool contract drift); the registry duplication is the mechanism that makes contract drift invisible.

## Acceptance Criteria

- [ ] Built-in skills/templates are discovered by scanning `src/skills/*.py` / `src/templates/*.py` for `Skill`/`Template` subclasses (auto-registration) instead of two hand-written dicts
- [ ] Alias handling is centralized and documented (single canonical ID + explicit alias map), with a test that all aliases resolve to the same class
- [ ] A registry-consistency test asserts: every built-in skill has exactly one template pairing, and vice-versa; no duplicate canonical IDs
- [ ] Resolution order (static → dynamic) is explicit and tested for the ID-overlap case
- [ ] BLK-172-style duplicate IDs fail loudly at import/test time

## Constraints

- Preserve backward-compatible aliases for existing persisted definitions (e.g. old definitions referencing `sk-invoice-basic` must still resolve)
- Do not force a database migration for the static path

## Dependencies

- `src/api/run_engine.py` (registries + dynamic builders)
- `src/skills/*.py`, `src/templates/*.py`
- `src/definitions/store.py` (dynamic path)
- Related BLK-217 (tool/skill contract drift)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T12:55 (mgmt)**: Filed from audit of the two-registry + two-path resolution design.
