---
id: BLK-142
type: bug
title: "SkillEditor handleSave drops system_prompt, probe_order, invariants, failure_actions"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T14:45:00+05:30
estimate: M
tags: [frontend, bug, skills, data-loss, shallow-impl]
---

## Problem

`handleSave` in `frontend/components/skills/SkillEditor.tsx` only sends
5 fields to the backend (`name, description, semantic_checks_enabled,
semantic_prompt, tools`), silently dropping `system_prompt`,
`probe_order`, `invariants`, `failure_actions`, `known_failures`,
`confidence_overrides`, and `tool_preferences` — all of which the user
configured in the editor UI and the backend `CreateSkillRequest` now
accepts (fixed in BLK-121).

## Evidence

`frontend/components/skills/SkillEditor.tsx:144-154`:
```typescript
const handleSave = async () => {
    if (!name || !documentType) return;
    await createSkill({
      name,
      description,
      semantic_checks_enabled: verifyAi,
      semantic_prompt: semanticPrompt,
      tools: selectedTools,
    });
    if (onSaveComplete) onSaveComplete();
  };
```

The form state includes `systemPrompt` (line 76), `probeSteps`
(line 86), `invariants` (line 91), and `failureActions` (line 95) —
none are sent.

Backend `CreateSkillRequest` (`src/api/routes/skills.py:29-42`)
accepts:
```python
class CreateSkillRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    system_prompt: str = ""
    tool_preferences: dict[str, str] = Field(default_factory=dict)
    probe_order: list[ProbeStep] = Field(default_factory=list)
    invariants: list[InvariantSpec] = Field(default_factory=list)
    failure_actions: dict[str, str] = Field(default_factory=dict)
    known_failures: str = ""
    confidence_overrides: dict[str, float] = Field(default_factory=dict)
    semantic_checks_enabled: bool = False
    semantic_prompt: str | None = None
    tools: list[str] = Field(default_factory=list)
```

Also, `createSkill` in `api.ts` sends `Omit<Skill, 'id'>` but the
`Skill` interface (line 30-37) only has 5 fields — missing
`system_prompt`, `probe_order`, `invariants`, `failure_actions`, etc.

## Impact

Users configure a full skill in the editor — system prompt, probe
order, invariants, failure actions — but only 5 fields are persisted.
The rest silently vanish. This is the same class of bug as BLK-121
(data loss through incomplete form submission), but on the frontend
side.

## Reproduction or reasoning

1. Open Skill Editor in the frontend.
2. Fill in system prompt, add probe steps, add invariants, add failure
   actions.
3. Click Save.
4. Fetch the skill from the backend — only name, description,
   semantic_checks_enabled, semantic_prompt, tools are present.
5. All other fields are empty/default.

## Proposed resolution

1. Extend the `Skill` interface in `api.ts` to include all fields the
   backend accepts.
2. Update `handleSave` to send the full form state: `systemPrompt`,
   `probeSteps` (mapped to `probe_order` schema), `invariants`
   (mapped), `failureActions` (mapped).
3. Map the frontend's internal types (`ProbeOrderStep`,
   `InvariantRule`, `FailureActionRule`) to the backend's
   `ProbeStep`, `InvariantSpec`, and `failure_actions` dict schema.

## Acceptance criteria

- [ ] `Skill` interface in `api.ts` includes all backend-accepted fields
- [ ] `handleSave` sends `system_prompt`, `probe_order`, `invariants`,
      `failure_actions`, `tool_preferences`
- [ ] Round-trip: create skill → fetch skill → all fields present
- [ ] Probe steps map to `{region_type, rationale}` schema
- [ ] Invariants map to `{name, fields, description}` schema

## Validation plan

- Create a skill with all fields populated via the editor
- Fetch the skill from `GET /skills/{id}`
- Verify all fields are present and correct
- Verify existing skills still load without errors

## Related issues

BLK-121 (backend Skills API drops data — fixed on backend side,
this is the frontend counterpart)
