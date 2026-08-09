---
id: BLK-098
type: bug
title: "Frontend: createDefinition sends skill_id/template_id but backend expects skill_ref/template_ref"
priority: high
status: backlog
phase: 3
owner: frontend
created: 2026-08-08T02:30:00+05:30
estimate: S
depends-on: [BLK-091]
tags: [frontend, bug, api-contract, stabilization]
---

## Bug

`frontend/app/definitions/page.tsx` lines 44-50:

```typescript
const created = await createDefinition({
  name: defName,
  skill_id: selectedSkillId,
  template_id: selectedTemplateId,
  system_prompt: systemPrompt,
  max_iterations: maxIterations,
});
```

The backend `CreateDefinitionRequest` expects `skill_ref`,
`template_ref`, `tool_names`, `agent_config`, `id`, and `version`.
The frontend sends `skill_id`, `template_id`, `max_iterations` — none
of which match the backend schema.

**Result:** The definition is created with empty skill and template
references. Any run using it fails.

## Fix

This is the frontend side of BLK-091. Once the naming convention is
agreed, update the frontend:

1. `AgentDefinition` interface — use agreed field names
2. `createDefinition` call — send correct fields
3. Add `id` field (currently the backend generates it, but the
   frontend should propose one or let the backend auto-generate)
4. Add `tool_names` from the wizard's tool selection step
5. Map `max_iterations` → `agent_config.max_cycles_per_document`

```typescript
const created = await createDefinition({
  id: `def-${Date.now()}`,
  name: defName,
  skill_ref: selectedSkillId,    // or skill_id per BLK-091
  template_ref: selectedTemplateId,
  tool_names: selectedTools,
  agent_config: {
    max_cycles_per_document: maxIterations,
  },
  system_prompt: systemPrompt,
});
```

## Acceptance Criteria

- [ ] Frontend sends fields matching the backend `CreateDefinitionRequest`
- [ ] `tool_names` from wizard step 4 included in the request
- [ ] `max_iterations` mapped to `agent_config.max_cycles_per_document`
- [ ] Created definition can be used to start a run
