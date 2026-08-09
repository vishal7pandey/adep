---
id: BLK-091
type: bug
title: "Backend: API field name mismatch — definitions use skill_ref/template_ref, frontend sends skill_id/template_id"
priority: high
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: S
depends-on: []
tags: [backend, frontend, bug, api-contract, stabilization]
---

## Bug

The backend and frontend use **different field names** for the same
concept:

| Concept | Backend (API) | Frontend (TypeScript) |
|---------|---------------|----------------------|
| Skill reference | `skill_ref` | `skill_id` |
| Template reference | `template_ref` | `template_id` |

### Backend

`src/api/routes/definitions.py` line 20-21:
```python
class CreateDefinitionRequest(BaseModel):
    skill_ref: str
    template_ref: str
```

`src/api/run_engine.py` line 158-159:
```python
skill = resolve_skill(def_data.get("skill_ref", ""))
template_cls = resolve_template(def_data.get("template_ref", ""))
```

### Frontend

`frontend/lib/api.ts` line 42-48:
```typescript
export interface AgentDefinition {
  skill_id: string;
  template_id: string;
}
```

`frontend/app/definitions/page.tsx` line 44-49:
```typescript
const created = await createDefinition({
  name: defName,
  skill_id: selectedSkillId,
  template_id: selectedTemplateId,
  ...
});
```

## Impact

- When the frontend creates a definition, it sends `skill_id` and
  `template_id` — the backend ignores them (Pydantic drops unknown
  fields) and `skill_ref`/`template_ref` are empty strings.
- When `execute_run` tries to resolve the skill, it gets an empty
  string → `ValueError: Unknown skill: `.
- When the frontend reads definitions from the API, the response has
  `skill_ref` but the TypeScript interface expects `skill_id` — the
  skill name shows as undefined in the UI.

## Fix

**Pick one naming convention and apply it everywhere.**

Recommended: use `skill_id` and `template_id` (more intuitive, matches
the frontend convention).

### Backend changes:

1. `src/api/routes/definitions.py` — rename `skill_ref` → `skill_id`,
   `template_ref` → `template_id` in `CreateDefinitionRequest` and
   `UpdateDefinitionRequest`
2. `src/api/run_engine.py` — change `def_data.get("skill_ref")` →
   `def_data.get("skill_id")`, same for template
3. `src/definitions/base.py` — rename `AgentDefinition` fields
4. Any existing `.adep/definitions/*.json` files need migration

### OR: Frontend changes:

1. `frontend/lib/api.ts` — rename `skill_id` → `skill_ref`,
   `template_id` → `template_ref` in `AgentDefinition` interface
2. `frontend/app/definitions/page.tsx` — update `createDefinition`
   call and card display

## Acceptance Criteria

- [ ] Single naming convention used across backend and frontend
- [ ] Creating a definition from the frontend works end-to-end
- [ ] Running a definition resolves the skill and template correctly
- [ ] No `ValueError: Unknown skill` errors
