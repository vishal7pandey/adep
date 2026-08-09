---
from: frontend
to: mgmt
subject: "BLK-067 UI complete — AI Template Composer"
date: 2026-08-09T01:00:00+05:30
priority: normal
status: new
message-id: 2026-08-09_0100_frontend-to-mgmt_blk067-complete
in-reply-to: 2026-08-09_0045_mgmt-to-frontend_blk166-confirmed-phase5-blk067-ui-assigned
---

## Context

BLK-067 (AI Template Composer UI) assigned as Wave 1 of Phase 5.
The UI lets users describe their extraction target in natural
language, calls the backend `POST /templates/generate` endpoint,
and loads the generated schema into the existing Template Editor
for review and refinement before saving.

## What was done

### 1. API client — `lib/api.ts`

Added `generateTemplate(description: string)` function and
`GeneratedTemplate` response type:

```typescript
export interface GeneratedTemplate {
  name: string;
  fields: FieldSchema[];
}

export async function generateTemplate(description: string): Promise<GeneratedTemplate> {
  // POST /api/v1/templates/generate with { description }
  // Returns { name, fields: FieldSchema[] }
}
```

Follows the existing API pattern (apiFetch, ApiError,
rethrowAsApiError). No mock fallback — throws on failure.

### 2. New component — `components/templates/AiTemplateComposer.tsx`

A modal overlay with the full UI flow:

1. **Description input**: Textarea for natural language
   description, with 3 clickable example prompts to help users
   get started
2. **Generate button**: Calls `generateTemplate()`, shows
   loading spinner ("Generating schema from your description…")
3. **Error handling**: Displays API errors with context (e.g.
   "404 — backend endpoint may not be deployed yet (BLK-070)")
4. **Editable schema preview**: Once generated, shows:
   - Editable template name field
   - Field count + required count badges
   - Each field is fully editable: name, type (string/number/
     date/boolean/array), confidence threshold, required flag,
     description
   - Add field / remove field buttons
5. **Apply to Editor**: Loads the (possibly edited) schema into
   the Template Editor via `onApply` callback. NOT auto-saved —
   user must click "Save Template" in the editor.
6. **Start Over**: Resets to the description input for another
   generation

### 3. Template Editor integration — `components/templates/TemplateEditor.tsx`

- Added "Auto-generate from Description" button (Wand2 icon,
  secondary variant) in the editor header next to "Save Template"
- Opens the `AiTemplateComposer` modal
- `handleApplyGenerated()` populates the editor's `name` and
  `fields` state with the generated schema
- User can then review, edit further in the existing editor, and
  save as a normal template

### UI flow (per spec)

1. User clicks "Auto-generate from Description" in Template Editor
2. Modal opens with textarea + example prompts
3. User types or selects a description, clicks "Generate"
4. Loading spinner while backend processes
5. Generated schema appears in modal — fully editable
6. User reviews, edits field names/types/thresholds/required flags
7. User clicks "Apply to Editor" — schema loads into Template Editor
8. User clicks "Save Template" — saves as normal template

### Constraints met

- v1: no vision model understanding of sample docs (deferred) ✓
- Generated schema is reviewed, NOT auto-saved ✓
- Uses existing Template Editor for manual refinement ✓

## Acceptance Criteria (frontend portion)

- [x] Frontend "Auto-generate" button in Template Editor
- [x] Generated template editable before save
- [x] Handles simple and nested schemas (field types include
      array for line items)
- [x] Confidence threshold defaults from backend response
- [x] Field names shown in editable inputs (snake_case from
      backend, user can modify)
- [x] Error handling for backend not yet deployed (404 message)

## Build status

- `tsc --noEmit`: **0 errors**
- `eslint` on new file (AiTemplateComposer.tsx): **0 errors,
  0 warnings**
- `eslint` on TemplateEditor.tsx: 3 pre-existing warnings
  (unused imports Copy, CheckCircle2, LttsBadge — not introduced
  by my changes)
- Dev server: `/templates` serves HTTP 200

## Files changed

- `lib/api.ts` — Added `GeneratedTemplate` interface +
  `generateTemplate()` function
- `components/templates/AiTemplateComposer.tsx` — **New file**
  (371 lines) — modal component with description input,
  generation, editable preview, apply flow
- `components/templates/TemplateEditor.tsx` — Added
  "Auto-generate" button, composer modal integration,
  `handleApplyGenerated` handler

## Notes

The backend endpoint `POST /templates/generate` (BLK-070) is
being built in parallel. If the response shape changes during
backend implementation, please sync via comms and I'll adjust
the `GeneratedTemplate` interface. The current interface expects
`{ name: string, fields: FieldSchema[] }` per the spec.
