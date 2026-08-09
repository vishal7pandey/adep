---
id: BLK-048
type: feature
title: "Trust calibration UI — expectation setting, confidence communication, agent identity"
priority: medium
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T22:35:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-026, BLK-028]
tags: [frontend, ux, trust, onboarding, confidence, audit, heuristics]
---

## Description

Implement trust calibration UX patterns from the Agentic UX Audit
framework: set accurate expectations on first use, communicate
uncertainty clearly, and calibrate the agent's visual identity to its
functional role.

## Motivation

The UX audit framework states: trust is volatile in autonomous systems.
Over-trust leads to catastrophic delegation (user accepts wrong
extractions without checking). Under-trust renders the agent useless
(micromanagement). The UI must actively calibrate trust.

## Design

### 1. First-Run Onboarding (expectation calibration)
- Modal on first launch: "What ADEP can and cannot do"
  - Can: Extract structured data from documents with pixel grounding
  - Cannot: Guarantee 100% accuracy — always verify high-stakes extractions
  - Tip: Click any field in Pane 2 to see its source in Pane 3
- "Don't show again" checkbox (stored in localStorage)

### 2. Confidence Communication
- Pane 2 field cards: confidence as both color AND percentage
  - Green (S. Green `#4DB848`): ≥ 0.8 — "High confidence"
  - Yellow (Tech Yellow `#F2E500`): 0.5-0.79 — "Review recommended"
  - Red (Coral `#F47C6D`): < 0.5 — "Low confidence — verify"
- Tooltip on hover: "Confidence: 87% — extracted via VLM from region (page 1, bbox [120,450,310,480])"
- Pane 1: overall run confidence indicator (average of field confidences)

### 3. Agent Identity (anthropomorphism calibration)
- Agent is a "tool", not a "companion" — visual identity should reflect this
- Pane 1 header: "Extraction Agent" (not "Your AI Assistant" or human-like name)
- No human avatar — use a document/extraction icon (lucide `FileSearch`)
- Status indicators use machine metaphors: "Processing", "Analying", not "Thinking", "Reading"

### 4. Uncertainty Surfacing
- When agent is stuck (retrying same region): show "Agent is having difficulty with this region" banner
- When compaction occurs: show "Context compacted — agent summarized its progress to continue"
- When max iterations approached: show warning "Approaching iteration cap (12/15)"

## Acceptance Criteria

- [ ] First-run onboarding modal with capabilities/limitations
- [ ] "Don't show again" persists in localStorage
- [ ] Confidence badges show both color AND percentage number
- [ ] Confidence tooltip shows tool + region provenance
- [ ] Pane 1 header says "Extraction Agent" with `FileSearch` icon
- [ ] No human-like avatars or names anywhere in the UI
- [ ] Status indicators use machine metaphors
- [ ] "Agent having difficulty" banner after 2+ retries on same region
- [ ] "Approaching iteration cap" warning at 80% of max_iterations
- [ ] LTTS brand colors for all confidence indicators
- [ ] Both dark and light mode

## Constraints

- Onboarding modal is dismissable — don't force it on power users [SF]
- Confidence display is always visible (not hidden in tooltips) — it's critical for trust
- No anthropomorphism — agent is a tool, not a companion

## Dependencies

- BLK-026 (frontend scaffold — localStorage, layout)
- BLK-028 (Pane 1 — status indicators, header)

## Notes

- Agentic UX Audit: §Stage 1 (Initial Engagement), §Trust Calibration
- Microsoft HAI Guideline: "Set accurate expectations"
- Google PAIR: "Show confidence but don't overclaim"
