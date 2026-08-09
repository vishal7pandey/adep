---
id: BLK-026
type: feature
title: "Frontend project scaffold (Next.js + TailwindCSS + shadcn/ui + 3-pane layout)"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [frontend, scaffold, nextjs, tailwind, shadcn, 3-pane]
---

## Description

Scaffold the frontend project with Next.js (App Router), TailwindCSS,
shadcn/ui, lucide-react, and the 3-pane workbench layout per vision.md §11.
Set up routing, API client base, SSE client, and the CSS Grid layout for
the 3-pane workbench (Sidebar | Agent Console | Extracted Data | Document Viewer).

The 3-pane layout:
```
+------------------------------------------------------------------+
| Sidebar | Pane 1: Agent Console | Pane 2: Extracted | Pane 3: Doc |
| (nav)   | (reasoning trace)     | Data (cards/JSON) | (bbox overlay) |
+------------------------------------------------------------------+
```

## Acceptance Criteria

- [ ] `frontend/` directory with Next.js (App Router) + TypeScript
- [ ] TailwindCSS configured with LTTS brand color scheme (§9)
- [ ] shadcn/ui initialized with base components, themed to LTTS palette
- [ ] lucide-react for icons
- [ ] Dark mode and light mode support via `dark:` variants
- [ ] 3-pane CSS Grid layout: Sidebar | Pane 1 | Pane 2 | Pane 3
- [ ] Each pane has independent vertical scrollbar (overflow-y-auto)
- [ ] Pane headers are sticky (do not scroll with content)
- [ ] Pane 3 has horizontal scrollbar for zoomed/oversized documents
- [ ] Collapsible sidebar with nav: definitions, skills, templates
- [ ] Next.js App Router routes: /, /definitions/[id], /skills/[id], /templates/[id]
- [ ] API client base (`lib/api.ts`) and SSE client base (`lib/sse.ts`)
- [ ] Shared `ActiveHighlightContext` for Pane 2 ↔ Pane 3 bbox linking
- [ ] Dev server runs with `npm run dev`
- [ ] Build works with `npm run build`

## Constraints

- Next.js + TailwindCSS + shadcn/ui (locked decision §9)
- TypeScript
- 3-pane layout is the primary UI — not a separate chat page
- LTTS brand color scheme with dark + light mode (locked decision §9)

## Dependencies

None (can start in parallel with Phase 2 if API contracts are agreed)

## Notes

- vision.md §0.2 (3-Pane Workbench), §9 (Frontend: Next.js), §11 (package layout)
- backend is Consulted on API client shape (RACI §4)
