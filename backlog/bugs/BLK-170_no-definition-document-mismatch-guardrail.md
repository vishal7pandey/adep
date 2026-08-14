---
id: BLK-170
type: bug
title: "No guardrail for definition-document type mismatch"
priority: medium
status: backlog
phase: 5
owner: antigravity
created: 2026-08-08T00:00:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [ux, guardrail, definition-selection, cross-team]
---

## Description

The platform allows running any agent definition on any document. A user ran an "Advertising Insertion Order" definition (`def-ad-buy`, task_type: extraction) on a P&ID diagram. The system offered no warning or prevention. The auto-classification/suggestion system (`suggestAgent`) should ideally steer the user to the correct definition, but there's no hard guardrail or warning when a mismatch is obvious.

## Root Cause

The auto-classification system (BLK-127) suggests definitions based on visual similarity, but:
1. If the user manually selects a definition, the system doesn't warn about mismatches
2. The `auto_route_threshold` (0.75) only auto-selects when confidence is high — it doesn't prevent wrong manual selections
3. There's no task_type compatibility check (e.g., running an extraction definition on a diagram that should use graph_extraction)

## Acceptance Criteria

- [ ] Warning shown when user selects a definition that differs from top suggestion
- [ ] Warning is non-blocking (user can proceed)
- [ ] Task_type mismatch (extraction vs graph_extraction) triggers a warning
- [ ] No false positives on correctly matched definitions

## Constraints

- Primary fix is UI-side (warning banner/dialog); if the `suggestAgent` endpoint needs a `task_type` field added to its response, that touches `src/api/routes/documents.py` and requires a contract note to devin — do not edit backend files directly.

## Dependencies

- Related to BLK-127 (auto-classification, implemented)

## Notes

- Files implicated: `frontend/components/workbench/Pane1AgentConsole.tsx` (definition selection logic), `src/api/routes/documents.py` (`suggestAgent` endpoint, read-only reference for antigravity).
- Reformatted from legacy non-YAML backlog format during the 2026-08-09 mgmt reorg (see BLK-292 parallel-audit collision cleanup).

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09 (mgmt)**: Converted to standard YAML frontmatter; assigned to antigravity.
