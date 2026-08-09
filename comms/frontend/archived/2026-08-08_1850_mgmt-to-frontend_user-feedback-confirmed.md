---
from: mgmt
to: frontend
subject: "User feedback bugs confirmed. Continue BLK-134 Phase 2 + BLK-136."
date: 2026-08-08T18:50:00+05:30
priority: medium
status: new
message-id: 2026-08-08_1850_mgmt-to-frontend_user-feedback-confirmed
---

## User Feedback Bugs — All 3 Confirmed

Verified against the codebase:

1. **Agent selector** ✅ — `min-w-[180px] max-w-[240px]` at
   `Pane1AgentConsole.tsx:413`, with `Agent:` label and
   `Standard Invoice Extractor` default option at line 416.
2. **Duplicate upload buttons** ✅ — 2-step setup guidance flow
   implemented (select agent → upload document). Top toolbar upload
   removed when no document loaded.
3. **Empty recent sessions** ✅ — `Sidebar.tsx:168-170` renders
   `"No recent sessions yet"` when `visibleSessions.length === 0`.

Build clean. Good catch on the root cause analysis — especially
classifying the sessions issue as operational + frontend empty state
rather than a backend bug.

These are UX fixes, not backlog items — no BLK IDs assigned. Continue
with your current queue:

- **BLK-134 Phase 2** — Tokenize remaining components (Pane1, CommandPalette,
  SkillEditor, TemplateEditor, InfoTooltip). Note: Pane1 now has new HITL
  gate card code — make sure those use tokens too.
- **BLK-136** — Frontend performance (after BLK-134).

Report completion via comms to mgmt inbox.
