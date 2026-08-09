---
id: BLK-031
type: feature
title: "Agent Definition Builder — wizard for composing definitions"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-027]
tags: [frontend, definition-builder, ui, wizard]
---

## Description

Build the Agent Definition Builder — a wizard UI for composing agent
definitions by selecting a skill, a template, a tool set, and an agent
runtime. Essentially a step-by-step wizard that snaps the bricks together.

**Key UX principle: no bare dropdowns.** Users cannot evaluate a skill or
template by name alone — they need to see what it does, what fields it
extracts, what tools it uses. Use **card-based selectors** with rich
previews, similar to Instagram filter thumbnails or VS Code extension
picker. Each card shows a visual summary so the user can compare options
at a glance.

### Card-Based Selector Design

**Skill cards** (horizontal scroll or grid):
```
┌─────────────────────────────────────┐
│ 🧠 Invoice Processing Skill         │
│ ReAct reasoning skill for extracting │
│ invoice metadata                     │
│                                     │
│ Tools: ocr · vlm · crop             │
│ Semantic checks: OFF                │
│                          [SELECT]   │
└─────────────────────────────────────┘
```

**Template cards** (horizontal scroll or grid):
```
┌─────────────────────────────────────┐
│ 📋 Standard Invoice Schema          │
│ Extracts vendor, total, tax, line   │
│ items                               │
│                                     │
│ Fields: 7 (5 required)              │
│ invoice_number · total · tax · ...  │
│                          [SELECT]   │
└─────────────────────────────────────┘
```

**Tool chips** (multi-select, inline):
```
┌──────────┐ ┌──────────┐ ┌──────────┐
│ ✓ OCR    │ │ ✓ VLM    │ │   Crop   │
│ Extracts │ │ Visual   │ │ Region   │
│ text     │ │ reasoning│ │ crop     │
└──────────┘ └──────────┘ └──────────┘
```

## Acceptance Criteria

- [ ] Step 1: Name + description input
- [ ] Step 2: Skill selector — card grid (not dropdown) showing:
  - Skill name + icon
  - Short description
  - Tool list as chips/badges
  - Semantic checks on/off badge
  - Selected card highlighted with Mobility Blue border
  - "Create new skill" card → links to Skill Editor (BLK-029)
- [ ] Step 3: Template selector — card grid (not dropdown) showing:
  - Template name + icon
  - Short description
  - Field count + required count (e.g. "7 fields, 5 required")
  - First 3-4 field names as preview chips
  - Selected card highlighted with Mobility Blue border
  - "Create new template" card → links to Template Editor (BLK-030)
- [ ] Step 4: Tool selector — toggleable chips with name + 1-line description
  - Pre-selected based on chosen skill's tool list
  - User can override (add/remove tools)
  - Each chip shows tool name + short description on hover/expand
- [ ] Step 5: System prompt override (optional textarea with placeholder)
- [ ] Step 6: Max iterations cap (number input, default from skill/config)
- [ ] Step 7: Review summary — shows all selections in a read-only summary card before saving
- [ ] Save → POST /api/v1/definitions
- [ ] Edit existing definitions (loads wizard with pre-selected cards)
- [ ] Clone existing definitions (loads wizard with pre-selected cards, new name)
- [ ] Cards animate in on mount (stagger fade-in)
- [ ] Hover state on cards: subtle elevation/shadow
- [ ] Selected state: Mobility Blue `#0071CE` border + light blue background
- [ ] ADEP brand color scheme applied throughout
- [ ] Both dark and light mode supported

## Dependencies

- BLK-027 (API client)

## Notes

- vision.md §0.2 (Agent Definition Builder), §7.2 criterion 8
