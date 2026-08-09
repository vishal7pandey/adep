---
from: mgmt
to: frontend
subject: "BLK-162 (urgent): Agent Definition Registry — rename labels + add edit/delete card actions"
date: 2026-08-08T23:15:00+05:30
priority: high
status: new
message-id: 2026-08-08_2315_mgmt-to-frontend_blk162-agent-definition-registry
---

## BLK-162 — Agent Definition Registry: Rename + Edit/Delete

**Priority:** Urgent (can be done alongside BLK-058)
**Estimate:** M
**Spec file:** `backlog/features/BLK-162_agent-definition-registry-edit-delete.md`

### Design rationale

The Agent Definitions page is a **registry** — where users view,
create, edit, and delete definitions. The "choosing" happens in the
workbench when starting a session. Current labels say "Choose Agent
Definition" which is misleading. Cards are display-only with no
edit/delete capability.

### Required changes

**1. Sidebar** (`Sidebar.tsx`):
- "Choose Agent Definition" → **"Agent Definitions"**
- Matches "Skills" and "Templates" (plural nouns)

**2. Page title** (`app/definitions/page.tsx`):
- Heading: "Choose Agent Definition" → **"Agent Definitions"**
- Subtitle: → **"View, create, and manage agent definitions"**
- Create button: "Build New Agent Definition" → **"Create Agent
  Definition"**

**3. Card interactions** (`app/definitions/page.tsx`):
- Click card → opens wizard in **edit mode** (pre-populated with
  definition's current values)
- Delete button (trash icon) on card → confirmation dialog → calls
  `deleteDefinition(id)` → removes from list
- Buttons must be discoverable (hover or always visible — your call)

**4. Wizard edit mode**:
- Reuse existing 7-step wizard for both create and edit
- Create mode: title "Create Agent Definition", button "Create Agent
  Definition", calls `createDefinition()`
- Edit mode: title "Edit Agent Definition", pre-populate all fields,
  button "Save Changes", calls `updateDefinition(id, data)`

**5. API client** (`lib/api.ts`):
- Add `updateDefinition(id, data)` → `PUT /definitions/{id}`
- Add `deleteDefinition(id)` → `DELETE /definitions/{id}` (204)
- Backend endpoints already exist — no backend work needed

**6. OnboardingTour** (`OnboardingTour.tsx`):
- "Agent Definition Library" → **"Agent Definitions"**

### No backend changes needed

Backend already has `PUT /definitions/{id}` and `DELETE
/definitions/{id}`. This is a frontend-only task.

### Note on deleting prebuilt definitions

Prebuilt definitions come from code (not disk). If a user deletes a
prebuilt definition, the store's `delete()` method will try to delete
from disk — which may not exist. The definition will still appear in
`list_definitions()` because the prebuilt merge includes it. This is
a known limitation — if the user wants to "hide" a prebuilt
definition, that's a separate feature. For now, just let the API
call succeed or fail naturally and show the error if one occurs.

Report completion via comms to mgmt inbox. Include build status.
