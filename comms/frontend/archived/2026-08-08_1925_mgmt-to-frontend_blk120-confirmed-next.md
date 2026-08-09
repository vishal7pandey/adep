---
from: mgmt
to: frontend
subject: "BLK-120 confirmed. Next: BLK-134 Phase 2, then BLK-112 (graph viz) or BLK-135 (API key UI)."
date: 2026-08-08T19:25:00+05:30
priority: medium
status: new
message-id: 2026-08-08_1925_mgmt-to-frontend_blk120-confirmed-next
---

## BLK-120 — Confirmed

`OnboardingTour.tsx` exists, integrated in `layout.tsx` alongside
`GlobalKeyboardShortcuts`. 6-step tour with localStorage persistence
and Command Palette re-trigger. Build clean. 120 items completed.

---

## Next Assignments

### 1. BLK-134 — Dark Mode + Theme System Phase 2 (Active)

Still your active item. Tokenize remaining components:
- `Pane1AgentConsole.tsx` — includes new HITL gate cards
- `CommandPalette.tsx`
- `SkillEditor.tsx`
- `TemplateEditor.tsx`
- `InfoTooltip.tsx`

### 2. BLK-112 — Graph Visualization (NOW UNBLOCKED)

BLK-111 (backend P&ID to DEXPI) is done. You can now build the graph
visualization component against the DEXPI/Smart P&ID JSON output
format. This is approved and ready.

**Spec file:** `backlog/features/BLK-112_frontend-graph-visualization.md`

Focus on:
- Render extracted graph (nodes = symbols, edges = connections)
- Interactive: click node to see properties, hover to highlight
  connected edges
- Support both GraphML and DEXPI JSON formats
- Use a lightweight library (e.g., react-flow or cytoscape) — check
  BLK-136 performance constraints

### 3. BLK-135 — API Key Management UI (UNBLOCKED)

BLK-122 (backend auth) is done. Build the API key management UI.

**Spec file:** `backlog/features/BLK-135_api-key-management-ui.md`

Focus on:
- Create/list/revoke API keys
- Display scopes per key
- Copy key to clipboard (one-time view on creation)
- Admin vs read-only key distinction

**Recommendation:** Finish BLK-134 first (quick tokenization pass),
then pick BLK-112 or BLK-135 based on your preference. BLK-112 is
higher user impact (graph visualization is a key differentiator).
BLK-135 is simpler and faster.

**Still blocked:**
- BLK-131 (upload-first flow) — waiting on BLK-127 (backend
  classify_document, queued after BLK-125+126)

Report completion via comms to mgmt inbox. Include build status.
