---
id: BLK-146
type: bug
title: "Frontend Skill interface missing fields backend accepts — type mismatch"
priority: medium
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T14:45:00+05:30
estimate: S
tags: [frontend, bug, types, skills, contract-mismatch]
---

## Problem

The `Skill` interface in `frontend/lib/api.ts` only declares 5 fields
(`id, name, description, semantic_checks_enabled, semantic_prompt,
tools`) but the backend `CreateSkillRequest` and `UpdateSkillRequest`
accept 12+ fields. The frontend cannot send or receive the full skill
schema through the typed API client.

## Evidence

`frontend/lib/api.ts:30-37`:
```typescript
export interface Skill {
  id: string;
  name: string;
  description: string;
  semantic_checks_enabled?: boolean;
  semantic_prompt?: string;
  tools?: string[];
}
```

Backend `CreateSkillRequest` (`src/api/routes/skills.py:29-42`) accepts:
`id, name, description, system_prompt, tool_preferences, probe_order,
invariants, failure_actions, known_failures, confidence_overrides,
semantic_checks_enabled, semantic_prompt, tools`.

## Impact

- `createSkill(data: Omit<Skill, 'id'>)` in `api.ts` only allows
  sending 4 fields — TypeScript will reject attempts to send
  `system_prompt`, `probe_order`, etc.
- When fetching skills, the extra backend fields are present at runtime
  but invisible to TypeScript — components that try to access them
  will get type errors or need `any` casts.
- This is the root cause of BLK-142 (SkillEditor drops form data).

## Reproduction or reasoning

1. In the frontend, try to call `createSkill` with a `system_prompt`
   field.
2. TypeScript error: `system_prompt` does not exist on type
   `Omit<Skill, 'id'>`.

## Proposed resolution

Extend the `Skill` interface to match the backend schema:

```typescript
export interface ProbeStep {
  region_type: string;
  rationale: string;
}

export interface InvariantSpec {
  name: string;
  fields: string[];
  description: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  system_prompt?: string;
  tool_preferences?: Record<string, string>;
  probe_order?: ProbeStep[];
  invariants?: InvariantSpec[];
  failure_actions?: Record<string, string>;
  known_failures?: string;
  confidence_overrides?: Record<string, number>;
  semantic_checks_enabled?: boolean;
  semantic_prompt?: string;
  tools?: string[];
}
```

## Acceptance criteria

- [ ] `Skill` interface includes all backend-accepted fields
- [ ] `ProbeStep` and `InvariantSpec` interfaces defined
- [ ] `createSkill` accepts the full skill schema
- [ ] No TypeScript errors when sending/receiving full skill data

## Validation plan

- Verify TypeScript compilation succeeds
- Verify skill creation with all fields works end-to-end
- Verify skill fetch returns all typed fields

## Related issues

BLK-142 (SkillEditor drops form data — depends on this fix),
BLK-121 (backend Skills API — already fixed)
