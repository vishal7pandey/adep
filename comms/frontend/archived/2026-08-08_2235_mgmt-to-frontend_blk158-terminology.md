---
from: mgmt
to: frontend
subject: "BLK-158: Terminology standardization — 'Agent Definition' in all UI labels. Urgent."
date: 2026-08-08T22:35:00+05:30
priority: high
status: new
message-id: 2026-08-08_2235_mgmt-to-frontend_blk158-terminology
---

## BLK-158 — Terminology Standardization — Urgent

A full audit of "Agent" vs "Definition" terminology across the codebase
reveals a significant inconsistency. The backend is consistent (always
uses "definition" in code, "agent definition" in docstrings). The
frontend code variables are also consistent (`definitions`,
`fetchDefinitions`, `AgentDefinition` interface). But **all user-facing
UI labels say "Agent"** when they should say **"Agent Definition"**.

### Why this matters

Per `vision.md`:
- **Agent** = the runtime loop (ReAct + LLM + state model) — an
  implementation detail users never interact with directly
- **Agent Definition** = the user-composed blueprint (skill + template
  + tools + config) — what users actually choose, build, and run

Using "Agent" as shorthand for "Agent Definition" creates ambiguity.
We're standardizing on the full term **"Agent Definition"** in all
user-facing labels.

### What needs to change

**Spec file:** `backlog/features/BLK-158_terminology-agent-definition.md`

The spec contains a complete table of every label that needs updating,
with line numbers. Here's the summary:

#### `definitions/page.tsx` (12 labels)
- "Choose Agent" → "Choose Agent Definition"
- "Build New Agent" → "Build New Agent Definition"
- "Agent Name *" → "Agent Definition Name *"
- "Create Agent" → "Create Agent Definition"
- "Failed to load agents:" → "Failed to load agent definitions:"
- "Available Agents Grid" → "Available Agent Definitions"
- "Review & Create Agent" → "Review & Create Agent Definition"
- "Untitled Agent" → "Untitled Agent Definition"
- All placeholder/description text: "agent" → "agent definition"

#### `Sidebar.tsx` (1 label)
- "Choose Agent" → "Choose Agent Definition"

#### `Pane1AgentConsole.tsx` (8 labels)
- "Extraction Agent" → "Extraction Agent Definition"
- "Agent:" → "Agent Definition:"
- "Suggested Agent:" → "Suggested Agent Definition:"
- "Start Run with Suggested Agent" → "Start Run with Suggested Agent Definition"
- All descriptive text: "extraction agent" → "extraction agent definition"

#### `RunComparisonView.tsx` and `OnboardingTour.tsx`
- Check for any "agent" references in user-facing labels and update
  to "agent definition"

### What does NOT change
- Variable names (`definitions`, `selectedDefId`, etc.) — already correct
- API function names (`fetchDefinitions`, `createDefinition`) — already correct
- TypeScript interface (`AgentDefinition`) — already correct
- API endpoint paths (`/definitions`, `/documents/{id}/suggest-agent`) —
  these are API contracts, not user-facing labels
- Code comments that use "agent" in technical context (e.g. "agent
  reasoning trace" referring to the ReAct loop) — these are correct
  usage of "agent"

### Priority

This is urgent alongside BLK-156 and BLK-157. All three should be
completed in the same batch — they're all frontend-only changes.

Report completion via comms to mgmt inbox. Include build status.
