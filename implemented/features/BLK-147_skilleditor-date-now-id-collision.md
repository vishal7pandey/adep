---
id: BLK-147
type: bug
title: "SkillEditor addInvariant and addFailureAction use Date.now() for IDs — collision-prone"
priority: low
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T14:45:00+05:30
estimate: S
tags: [frontend, bug, skills, id-generation]
---

## Problem

`addInvariant` and `addFailureAction` in
`frontend/components/skills/SkillEditor.tsx` use `Date.now().toString()`
for client-side ID generation. If a user clicks "add" twice within the
same millisecond (e.g., double-click), both items get the same ID,
causing React key collisions and potential state corruption.

## Evidence

`frontend/components/skills/SkillEditor.tsx:130-141`:
```typescript
const addInvariant = () => {
    setInvariants((prev) => [
      ...prev,
      { id: Date.now().toString(), fieldName: 'invoice_date', type: 'date_compare', params: 'date <= today' },
    ]);
  };

  const addFailureAction = () => {
    setFailureActions((prev) => [
      ...prev,
      { id: Date.now().toString(), condition: 'ocr_error', action: 'deskew' },
    ]);
  };
```

Also, the default items use hardcoded IDs `'inv-1'`, `'fa-1'`, `'1'`,
`'2'` (lines 86-97) — if a user adds a new item that collides with
these, the same problem occurs.

## Impact

- React key warnings in console
- Potential state corruption if two items with the same ID are
  deleted/edited — React may update the wrong item
- Double-clicking "add" creates two items with the same ID

## Reproduction or reasoning

1. Open Skill Editor.
2. Double-click "Add Invariant" quickly.
3. Both new invariants have the same `Date.now()` ID (if within same
   millisecond).
4. React key warning appears in console.

## Proposed resolution

Use `crypto.randomUUID()` or a counter-based approach:

```typescript
const addInvariant = () => {
    setInvariants((prev) => [
      ...prev,
      { id: crypto.randomUUID(), fieldName: 'invoice_date', type: 'date_compare', params: 'date <= today' },
    ]);
  };
```

## Acceptance criteria

- [ ] No `Date.now()` used for ID generation
- [ ] IDs are unique even on rapid double-click
- [ ] No React key warnings

## Validation plan

- Double-click "Add Invariant" and "Add Failure Action" rapidly
- Verify each new item has a unique ID
- Verify no React key warnings in console

## Related issues

BLK-142 (SkillEditor drops form data — same component)
