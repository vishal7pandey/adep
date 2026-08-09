# BLK-170: No guardrail for definition-document type mismatch

- **Priority:** P2 — Medium
- **Status:** backlog
- **Owner:** unassigned
- **Phase:** 5
- **Type:** bug
- **Reported:** 2026-08-08

## Problem

The platform allows running any agent definition on any document. A user ran an "Advertising Insertion Order" definition (`def-ad-buy`, task_type: extraction) on a P&ID diagram. The system offered no warning or prevention. The auto-classification/suggestion system (`suggestAgent`) should ideally steer the user to the correct definition, but there's no hard guardrail or warning when a mismatch is obvious.

## Root Cause

The auto-classification system (BLK-127) suggests definitions based on visual similarity, but:
1. If the user manually selects a definition, the system doesn't warn about mismatches
2. The `auto_route_threshold` (0.75) only auto-selects when confidence is high — it doesn't prevent wrong manual selections
3. There's no task_type compatibility check (e.g., running an extraction definition on a diagram that should use graph_extraction)

## Files Affected

- `frontend/components/workbench/Pane1AgentConsole.tsx` — definition selection logic
- `src/api/routes/documents.py` — `suggestAgent` endpoint

## Fix

1. When the user manually selects a definition that differs from the top suggestion, show a non-blocking warning ("Selected definition doesn't match the suggested agent. Continue?")
2. When a graph_extraction definition is selected for a non-diagram document (or vice versa), show a warning
3. Optionally: when the suggestion system returns a graph_extraction definition but the user selects an extraction definition, show a stronger warning

## Acceptance Criteria

- [ ] Warning shown when user selects a definition that differs from top suggestion
- [ ] Warning is non-blocking (user can proceed)
- [ ] Task_type mismatch (extraction vs graph_extraction) triggers a warning
- [ ] No false positives on correctly matched definitions
