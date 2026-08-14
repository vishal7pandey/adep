---
from: mgmt
to: frontend
subject: "FOCUSED: Sidebar Session Manager implemented; Phase 3 priorities"
date: 2026-08-08T00:55:00+05:30
priority: high
status: closed
message-id: 2026-08-08_0055_mgmt-to-frontend-focused-priorities
---

## What changed

The sidebar has been redesigned into a Session Manager and implemented
in `components/layout/Sidebar.tsx`.

### New sidebar structure

- **New Session** — starts a blank workbench
- **Recent Sessions** — last 3 runs, with `more...` to expand all
- Each session shows: status icon, name, status, extraction progress %
- `...` per session: Rename, Duplicate, Export, Delete
- Divider
- **Library**: Agents, Skills, Templates

### API additions

`lib/api.ts` now has:
- `fetchRecentRuns`
- `deleteRun`
- `duplicateRun`
- `renameRun`

### What you need to do

1. **Review and test BLK-077** — pull the branch, verify sidebar renders
   in both dark and light mode, collapsed and expanded.
2. **Continue BLK-054** — UI bugfix sweep is still the top priority and
   blocks Phase 3 sign-off.
3. **Hook up session loading** — when a session is clicked, the
   workbench should load that run ID via `?run={id}`. Pane 1 must display
   the correct run state.
4. **Add `name` field to `ExtractionRun`** (optional, v2) — right now
   sessions display `document_url` or `run.id`.

### Current Phase 3 priorities (do not deviate)

1. BLK-054 — UI Polish & Bugfix Sweep (highest, blocking)
2. BLK-077 — Sidebar Session Manager (just implemented, review + test)
3. BLK-028 / BLK-033 / BLK-038 — finish the 3 panes
4. BLK-046 — agent control integration
5. BLK-045, BLK-048, BLK-053 — progressive disclosure, trust, token display
6. BLK-055 — design system (after BLK-054)
7. BLK-029, BLK-030, BLK-031 — editors

No new Phase 4/5 work until Phase 3 is signed off.


## Resolution

Processed and implemented under BLK-077. Redesigned components/layout/Sidebar.tsx into a Session Manager with New Session CTA, Recent Sessions list (last 3, expandable), session status icons & progress %, session action dropdowns (Rename, Duplicate, Export, Delete), and Library section (Agents, Skills, Templates). Connected session selection to ?run={id} URL parameters.
