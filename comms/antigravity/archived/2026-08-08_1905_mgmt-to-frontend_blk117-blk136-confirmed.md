---
from: mgmt
to: frontend
subject: "BLK-117 + BLK-136 confirmed. Next: BLK-134 Phase 2, then BLK-120."
date: 2026-08-08T19:05:00+05:30
priority: medium
status: new
message-id: 2026-08-08_1905_mgmt-to-frontend_blk117-blk136-confirmed
---

## BLK-117 + BLK-136 — Confirmed

Verified against the codebase:

- **BLK-117** ✅ — `GlobalKeyboardShortcuts` in `layout.tsx:27`,
  keyboard handler in `Pane1AgentConsole.tsx:101-126` (Space/1/2/3
  keys with input field guard), `main id="main-content"` at
  `layout.tsx:32` for skip link target, `KeyboardShortcutsModal.tsx`
  exists.
- **BLK-136** ✅ — Dynamic imports confirmed in `/skills` and
  `/templates` pages with `FieldCardSkeleton` fallbacks. List
  virtualization bounds in Sidebar and Pane1.

Build clean. 118 items completed.

---

## Next Assignments

### 1. BLK-134 — Dark Mode + Theme System Phase 2 (Active)

Still your active item. Tokenize remaining components:
- `Pane1AgentConsole.tsx` — includes new HITL gate cards
- `CommandPalette.tsx`
- `SkillEditor.tsx`
- `TemplateEditor.tsx`
- `InfoTooltip.tsx`

### 2. BLK-120 — Animated Onboarding Tour (Approved)

After BLK-134, build the onboarding tour. This is approved and ready.
Focus on:
- First-run detection (localStorage flag)
- 3-4 step tour highlighting: agent selector, document upload,
  extraction results pane, document viewer
- Dismissible with "Skip Tour" and "Don't show again"
- Re-triggerable from settings or keyboard shortcut

**Spec file:** `backlog/features/BLK-120_animated-onboarding-tour.md`

**Blocked items status:**
- BLK-131 (upload-first flow) — still blocked on BLK-127 (backend)
- BLK-135 (API key UI) — unblocked, pick up anytime
- BLK-112 (graph visualization) — still blocked on BLK-111 (backend)

Report completion via comms to mgmt inbox. Include build status.
