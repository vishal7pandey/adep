---
id: BLK-164
title: "SkillEditor advanced pane — dead state, no edit mode, type mismatches, dead buttons"
status: assigned
priority: high
estimate: M
assigned_to: frontend
created: 2026-08-08T23:35:00+05:30
by: mgmt
---

## Problem

The SkillEditor's "Advanced Mode" pane has multiple issues that make
it non-functional or misleading:

### 1. Advanced fields not initialized from existing skill on edit

When `initialSkill` is provided (editing an existing skill), the
advanced state is initialized with **hardcoded defaults**, not from
the skill's actual data:

```tsx
// Line 86-97 — always uses defaults, ignores initialSkill
const [probeSteps, setProbeSteps] = useState<ProbeOrderStep[]>([
  { id: '1', rationale: 'Initial full page text scan', action: 'Run OCR on page 1' },
  { id: '2', rationale: 'Inspect low confidence regions', action: 'Crop bbox and validate values' },
]);
const [invariants, setInvariants] = useState<InvariantRule[]>([
  { id: 'inv-1', fieldName: 'total_amount', type: 'sum_check', params: 'subtotal + tax == total_amount' },
]);
const [failureActions, setFailureActions] = useState<FailureActionRule[]>([
  { id: 'fa-1', condition: 'confidence < 0.6', action: 'vlm_escalation' },
]);
```

**Fix:** Initialize from `initialSkill?.probe_order`, `initialSkill?.invariants`,
`initialSkill?.failure_actions` when available.

### 2. `verifyMath` and `verifyDates` are dead state

Lines 80-81 declare `verifyMath` and `verifyDates` state with
checkboxes in the UI (section 4. Validation Options), but these
values are **never sent** in `handleSave()`. They're not in the
`Skill` interface, not in the backend model, and not used anywhere.

**Fix:** Either remove the checkboxes entirely, or wire them to
invariant rules (e.g., `verifyMath` → add a `sum_check` invariant,
`verifyDates` → add a `date_compare` invariant). Simplest fix: remove
them and let users add invariants manually in advanced mode.

### 3. "Auto-generate Prompt" button does nothing

Line 259-261: The `<Wand2>` "Auto-generate Prompt" button has no
`onClick` handler.

**Fix:** Remove the button entirely. AI prompt generation is a
Phase 5 feature (BLK-068 AI Skill Composer), not something to stub
out with a dead button.

### 4. `handleClone` doesn't actually clone

Line 160-162: `handleClone` just changes the name to `${name} (Copy)`.
It doesn't create a new skill or reset the ID. If the user then saves,
it either creates a duplicate or updates the original (depending on
whether `initialSkill` was set).

**Fix:** `handleClone` should:
- Clear `initialSkill` reference (so save creates a new skill)
- Append " (Copy)" to the name
- Clear the `id` field
- Keep all other fields

### 5. No update path — always calls `createSkill()`

`handleSave()` (line 144-158) always calls `createSkill()`, even when
editing an existing skill. This creates a duplicate instead of
updating.

**Fix:** Add `updateSkill()` to `lib/api.ts` (backend `PUT /skills/{id}`
already exists). In `handleSave`, check if `initialSkill?.id` exists:
- If yes → `updateSkill(initialSkill.id, data)`
- If no → `createSkill(data)`

### 6. Type mismatch: `failure_actions`

- **Frontend sends:** `FailureActionSpec[]` — array of `{condition, action}`
- **Backend expects:** `dict[str, str]` — mapping of GapType → action hint

This mismatch means the API call will either fail or silently lose
data.

**Fix:** Convert the frontend array to a dict before sending:
```tsx
const failureActionsDict = Object.fromEntries(
  failureActions.map(fa => [fa.condition, fa.action])
);
```
Or change the backend to accept the array format. **Recommended:**
convert on frontend side — less backend churn.

### 7. Type mismatch: `probe_order`

- **Frontend sends:** `ProbeOrderStep[]` — array of `{id, rationale, action}`
- **Backend expects:** `list[tuple[str, str]]` — list of `(region_type, rationale)`

**Fix:** Convert frontend array to list of tuples before sending:
```tsx
const probeOrderTuples = probeSteps.map(s => [s.action, s.rationale]);
```
Or update backend to accept the richer object format. **Recommended:**
update backend `ProbeStep` model to accept `{rationale, action}` and
map internally — the frontend format is more user-friendly.

### 8. Delete button missing on skill cards

The Skills registry page (`app/skills/page.tsx`) has Edit buttons but
no Delete. Backend `DELETE /skills/{id}` exists. Frontend
`deleteSkill()` is missing from `api.ts`.

**Fix:** Add `deleteSkill()` to `api.ts`, add delete button to skill
cards with confirmation dialog (same pattern as BLK-162 definition
cards).

## Required Changes

### Frontend API client (`lib/api.ts`)
- Add `updateSkill(id, data)` → `PUT /skills/{id}`
- Add `deleteSkill(id)` → `DELETE /skills/{id}` (204)

### SkillEditor (`components/skills/SkillEditor.tsx`)
- Initialize advanced fields from `initialSkill` when editing
- Remove `verifyMath`/`verifyDates` dead state and their checkboxes
- Remove "Auto-generate Prompt" dead button
- Fix `handleClone` to properly reset for new skill creation
- Fix `handleSave` to call `updateSkill` when editing
- Fix `failure_actions` type conversion before sending
- Fix `probe_order` type conversion before sending

### Skills page (`app/skills/page.tsx`)
- Add delete button to skill cards with confirmation

### Backend (`src/api/routes/skills.py`, `src/skills/base.py`)
- Update `ProbeStep` model to accept `{rationale, action}` object
  format instead of tuple — OR keep tuple and let frontend convert
- Update `failure_actions` if needed — OR keep dict and let frontend
  convert

**Recommended approach:** Frontend converts to backend types. No
backend changes needed. This keeps the backend stable.

## Tests

- Create new skill with advanced fields → verify persisted
- Edit existing skill → advanced fields pre-populated
- Edit and save → updates instead of creating duplicate
- Delete skill from registry → removed from list
- Clone skill → creates new skill with copied fields
- Build compiles with 0 TypeScript errors
