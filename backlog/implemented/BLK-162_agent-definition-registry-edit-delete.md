---
id: BLK-162
title: "Agent Definition Registry — rename labels, add edit/delete card actions"
status: assigned
priority: high
estimate: M
assigned_to: frontend
created: 2026-08-08T23:15:00+05:30
by: mgmt
---

## Problem

The Agent Definitions page is labeled as a "chooser" ("Choose Agent
Definition") but it's actually a **registry** — the place where users
view, create, edit, and delete definitions. The actual "choosing"
happens in the workbench when starting a session.

Currently:
- Sidebar says "Choose Agent Definition" (action verb, inconsistent
  with "Skills" and "Templates" which are nouns)
- Page title says "Choose Agent Definition"
- Cards are display-only — no edit, no delete, no click handler
- Frontend API client has `createDefinition` but **missing**
  `updateDefinition` and `deleteDefinition` (backend endpoints exist)

## Design Decision

Rename to **"Agent Definitions"** everywhere in navigation and page
title. The page is a registry, not a chooser. Add edit and delete
capabilities to cards.

## Required Changes

### 1. Sidebar (`components/layout/Sidebar.tsx`)

Change nav label from "Choose Agent Definition" to **"Agent
Definitions"** (plural noun, matches "Skills" and "Templates").

### 2. Page Title (`app/definitions/page.tsx`)

- Page heading: **"Agent Definitions"** (not "Choose Agent
  Definition")
- Subtitle: **"View, create, and manage agent definitions"**
- Create button: **"Create Agent Definition"** (not "Build New Agent
  Definition")

### 3. Card Interactions (`app/definitions/page.tsx`)

Each definition card needs:

- **Click card** → opens wizard in **edit mode** (pre-populated with
  the definition's current values: name, skill, template, tools,
  system prompt, max iterations)
- **Delete button** (trash icon, top-right of card) → confirmation
  dialog → calls `deleteDefinition(id)` → removes from list
- **Edit/Delete buttons** should be visible on hover or always
  visible (designer's choice, but must be discoverable)

### 4. Wizard Edit Mode (`app/definitions/page.tsx`)

The existing 7-step wizard should support both create and edit:

- **Create mode** (current behavior):
  - Title: "Create Agent Definition"
  - Final button: "Create Agent Definition"
  - Calls `createDefinition()`

- **Edit mode** (new):
  - Title: "Edit Agent Definition"
  - Pre-populate all fields from the selected definition
  - Final button: "Save Changes"
  - Calls `updateDefinition(id, data)` instead of `createDefinition()`
  - On save, update the definition in the local list (don't refetch
    all)

### 5. Frontend API Client (`lib/api.ts`)

Add two missing functions:

```typescript
export async function updateDefinition(
  id: string,
  data: Partial<AgentDefinition>
): Promise<AgentDefinition> {
  const res = await apiFetch(`${API_BASE_URL}/definitions/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new ApiError(
    `Failed to update definition: ${res.statusText}`, res.status
  );
  return res.json();
}

export async function deleteDefinition(id: string): Promise<void> {
  const res = await apiFetch(`${API_BASE_URL}/definitions/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok && res.status !== 204) throw new ApiError(
    `Failed to delete definition: ${res.statusText}`, res.status
  );
}
```

### 6. OnboardingTour (`components/ui/OnboardingTour.tsx`)

Update the tour text that references "Agent Definition Library" to
say **"Agent Definitions"** for consistency.

### 7. Pane1AgentConsole (`components/workbench/Pane1AgentConsole.tsx`)

No changes needed — the workbench is where "choosing" happens. The
selector label "Agent Definition:" is correct. The suggestion card
"Suggested Agent Definition:" is correct.

## Backend

**No changes needed.** Backend already has:
- `PUT /api/v1/definitions/{id}` — update
- `DELETE /api/v1/definitions/{id}` — delete (204 No Content)

## Tests

- Create a new definition → appears in grid
- Click existing definition card → wizard opens in edit mode with
  pre-populated fields
- Edit and save → definition updates in grid
- Delete with confirmation → definition removed from grid
- Delete prebuilt definition → should work (it gets deleted from
  disk, prebuilt still shows if no disk override — verify behavior
  with backend)
- Build still compiles with 0 TypeScript errors

## Out of Scope

- Skills and Templates pages also lack edit/delete — this will be
  filed separately if needed
- Bulk operations (multi-select delete)
- Drag-and-drop reordering
