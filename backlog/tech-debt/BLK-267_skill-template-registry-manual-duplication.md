---
id: BLK-267
type: tech-debt
title: "Skill/Template registries are hand-maintained in parallel (44 imports, 2 dicts, aliasing drift) — collapse into auto-discovery"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T10:15:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [skills, templates, registry, refactor, maintainability]
---

## Description

`src/skills/*.py` (22 files) and `src/templates/*.py` (22 files) mirror each other one-to-one by document type. The split itself is defensible — `Skill` describes *how* to extract (prompts, probe order, tool preferences), `Template` describes *what a valid result looks like* (Pydantic schema) — but the wiring to get from a string ID to a class is entirely manual and duplicated:

- `src/api/run_engine.py` hand-imports all 22 skill classes and all 22 template classes (44 import lines).
- Two parallel hand-maintained dicts, `_SKILL_REGISTRY` and `_TEMPLATE_REGISTRY`, map string IDs to classes. Several IDs are aliased twice for backward compatibility (`"invoice"` and `"sk-invoice-basic"` both map to `InvoiceSkill`; `"trade_finance_mt700"` and `"trade_finance"` both map to `TradeFinanceTemplate`; `"medical_claim_cms1500"` and `"medical_claim"` both map to `MedicalClaimTemplate`; etc.) — this alias drift is exactly the pattern that produced the duplicate-definition bug fixed in BLK-172.
- On top of the static registry there's a second, dynamic resolution path (`_build_dynamic_skill` / `_build_dynamic_template` in `run_engine.py`) that builds `Skill`/`Template` objects at runtime from user-authored data in `DefinitionStore`, for skills/templates created through the SkillEditor / AiTemplateComposer UI. `resolve_skill()` / `resolve_template()` check the static dict first, then fall through to the dynamic path.

## Problem Statement

Nothing here is functionally broken — both paths work — but adding or changing a built-in document type currently requires touching four places (skill file, template file, and two registry entries), plus understanding an entirely separate code path for user-created skills/templates. This raises the odds of the next alias-drift bug and makes `run_engine.py` harder to read than the abstraction requires.

## Acceptance Criteria

- [ ] Built-in skills and templates are discovered automatically (e.g. scan `src/skills/*.py` for `Skill` subclasses, same for `src/templates/*.py` for `Template` subclasses) instead of 44 hand-written imports
- [ ] A single source of truth per skill/template for its canonical ID and any aliases (e.g. a class attribute), so aliasing isn't split across a dict literal that's easy to drift
- [ ] `resolve_skill()` / `resolve_template()` keep the same external behavior (static registry first, dynamic `DefinitionStore` fallback second) — this is a refactor of wiring, not of the abstraction
- [ ] Existing alias IDs (`sk-invoice-basic`, `trade_finance_mt700`, `medical_claim_cms1500`, etc.) keep resolving to the same classes — no breaking change for saved definitions
- [ ] All existing skill/template resolution tests pass unchanged

## Constraints

- Do not change the `Skill`/`Template` abstraction itself — this is purely about how string IDs get resolved to classes
- Must not slow down cold start meaningfully (module-scan approach should be cheap — 22 files, done once)

## Dependencies

- `src/api/run_engine.py` (`_SKILL_REGISTRY`, `_TEMPLATE_REGISTRY`, `resolve_skill`, `resolve_template`, `_build_dynamic_skill`, `_build_dynamic_template`)
- `src/skills/*.py`, `src/templates/*.py`

## Notes

- Found via full-repo audit (`ADE_codebase_audit.md`, §6)
- Lower priority than BLK-178/179/180 — this is a maintainability improvement, not a correctness bug, but worth doing before the document-type count grows further (BLK-104 wants to expand sample data across categories, which will pressure this registry further)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T10:15 (mgmt)**: Logged after confirming the current registry still has 44 manual imports and duplicate-keyed aliases in both `_SKILL_REGISTRY` and `_TEMPLATE_REGISTRY`.
