---
id: BLK-121
type: bug
title: "Skills API drops skill data — CreateSkillRequest missing system_prompt, probe_order, invariants, failure_actions"
priority: high
status: done
started: 2026-08-08T14:35:00+05:30
completed: 2026-08-08T14:45:00+05:30
phase: 4
owner: backend
created: 2026-08-08T13:50:00+05:30
estimate: M
depends-on: [BLK-108]
tags: [backend, bug, api, skills, data-loss, asymmetry]
---

## Problem

`CreateSkillRequest` and `UpdateSkillRequest` in
`src/api/routes/skills.py` only accept 6 fields:

```python
class CreateSkillRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    semantic_checks_enabled: bool = False
    semantic_prompt: str | None = None
    tools: list[str] = Field(default_factory=list)
```

But BLK-108 made the store **serialize** the full skill data:
`system_prompt`, `tool_preferences`, `probe_order`, `invariants`,
`failure_actions`, `known_failures`, `confidence_overrides`.

**This is a read/write asymmetry.** `GET /api/v1/skills/{id}` returns
full skill data. `POST /api/v1/skills` and `PUT /api/v1/skills/{id}`
silently drop everything except the 6 fields above.

## Impact

The Skill Editor (frontend, BLK-101) has full UI sections for:
- System prompt
- Tool preferences
- Probe order
- Invariants
- Failure actions
- Known failures
- Confidence overrides

**None of these can be saved.** The user edits them, clicks Save, and
the data is silently discarded. On reload, their edits are gone.

This is worse than a 400 error — it's silent data loss.

## Fix

Extend both request models to accept the full skill schema:

```python
class ProbeStep(BaseModel):
    region: str
    intent: str

class InvariantSpec(BaseModel):
    name: str
    fields: list[str]
    description: str = ""

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

class UpdateSkillRequest(BaseModel):
    # All fields optional (same set as above, all `| None = None`)
```

## Note on Invariants

Invariant **functions** are not JSON-serializable. The API accepts
invariant *specs* (name + fields + description) which are declarative
metadata. Executable invariants remain code-defined in
`src/skills/*.py`.

For user-created skills via the API, invariants are declarative only —
they describe what should be checked but don't execute. A follow-up
item should address a safe declarative invariant DSL (e.g.,
`"subtotal + tax == total"` parsed and evaluated in a sandbox).
Create that as a separate backlog item if it's worth pursuing.

## Acceptance Criteria

- [x] `CreateSkillRequest` accepts all 10 skill fields
- [x] `UpdateSkillRequest` accepts all 10 fields as optional
- [x] `POST /api/v1/skills` round-trips full skill data
- [x] `PUT /api/v1/skills/{id}` preserves fields not in the request
- [x] `GET` after `POST` returns exactly what was sent
- [x] Tests: round-trip test for every field
- [x] Tests: partial update doesn't clobber unspecified fields
- [x] No regression in existing tests (788 total, 3 new)
- [x] Definitions API also checked — `task_type` added to Create/UpdateDefinitionRequest

## Notes

Verify the same asymmetry doesn't exist for definitions. Templates
were checked and are correct (`CreateTemplateRequest` accepts
`fields`).
