---
id: BLK-055
type: feature
title: "Frontend design system / component library — ADEP-branded reusable components"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T23:59:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-026]
tags: [frontend, design-system, components, adep, ui, consistency]
---

## Description

Create a small, reusable component library enforcing the ADEP design
system. This prevents the visual inconsistency seen in the UI audit
(BLK-054). It is a dependency for cleaning up the workbench and editors.

## Motivation

The UI audit revealed wrong colors, inconsistent buttons, mismatched
tabs, and broken focus states across screens. A shared component
library is the upstream fix — every screen uses the same components,
so brand and interaction patterns stay consistent.

## Components to Build

| Component | Path | Purpose |
|-----------|------|---------|
| `AdeButton` | `components/ui/AdeButton.tsx` | All buttons: primary, secondary, destructive, tertiary, ghost, icon |
| `AdeCard` | `components/ui/AdeCard.tsx` | Consistent card: padding, border, shadow, hover, selected state |
| `AdeBadge` | `components/ui/AdeBadge.tsx` | Confidence, status, tool chips, risk tiers |
| `AdePillTabs` | `components/ui/AdePillTabs.tsx` | Tab groups used everywhere |
| `AdeProgressBar` | `components/ui/AdeProgressBar.tsx` | Field completion, budget consumption |
| `AdeEmptyState` | `components/ui/AdeEmptyState.tsx` | Idle/empty pane states |
| `AdeTooltip` | `components/ui/AdeTooltip.tsx` | Hover tooltips (grounding, confidence, token info) |
| `AdeDialog` | `components/ui/AdeDialog.tsx` | Modals (onboarding, critical gate, settings) |
| `AdeInput` | `components/ui/AdeInput.tsx` | Text inputs, textareas, number inputs |
| `AdeSelect` | `components/ui/AdeSelect.tsx` | Dropdowns (fallback, not default) |
| `AdeToggle` | `components/ui/AdeToggle.tsx` | Boolean toggles (required, semantic checks, dark mode) |
| `AdeSlider` | `components/ui/AdeSlider.tsx` | Confidence threshold slider |
| `AdeAccordion` | `components/ui/AdeAccordion.tsx` | Expandable cycle cards, field cards |
| `AdeScrollArea` | `components/ui/AdeScrollArea.tsx` | Styled scrollable pane with sticky header support |

## Design Tokens

```css
:root {
  --adep-blue: #00205C;
  --mobility-blue: #0071CE;
  --s-green: #4DB848;
  --tech-yellow: #F2E500;
  --coral: #F47C6D;
  --electric-blue: #00B5E2;
  --adep-purple: #A27CC9;
  --neutral-dark: #101820;
  --neutral-light: #E1E1E1;
  --success: #4DB848;
  --warning: #F2E500;
  --error: #F47C6D;
  --info: #0071CE;
}
```

## AdeButton Variants

- **primary**: solid `mobility-blue`, white text
- **secondary**: outline `mobility-blue`, `mobility-blue` text
- **destructive**: solid `coral`, white text
- **tertiary**: ghost, `mobility-blue` text
- **icon**: square button with icon only, subtle hover

All buttons: 8px horizontal padding, 6px vertical, 6px border-radius,
`electric-blue` focus ring.

## AdeBadge Variants

- **verified**: `s-green` background, white text
- **medium**: `tech-yellow` background, dark text
- **failed**: `coral` background, white text
- **info**: `mobility-blue` background, white text
- **tool**: `adep-purple` background, white text
- **neutral**: light gray background, dark text

## Acceptance Criteria

- [ ] All components in `components/ui/` with Storybook or simple
      demo page at `/ui-demo`
- [ ] AdeButton used in all CTAs across app
- [ ] AdeCard used for field cards, skill/template/definition cards
- [ ] AdeBadge used for confidence, status, tool chips
- [ ] AdePillTabs replaces all tab implementations
- [ ] AdeProgressBar used for field completion and budget bars
- [ ] AdeEmptyState used for all idle/empty panes
- [ ] AdeTooltip used for confidence and grounding hints
- [ ] All components support dark mode via `dark:` Tailwind classes
- [ ] Focus states visible and consistent
- [ ] Unit tests for all components (render + variants)
- [ ] `/ui-demo` page shows all components in light and dark mode

## Constraints

- Use TailwindCSS + shadcn/ui primitives where possible, but wrap
  them to enforce ADEP colors [SF]
- No third-party component libraries beyond shadcn/ui [FP]
- Components must be typed with TypeScript and use `forwardRef` where
  appropriate

## Dependencies

- BLK-026 (frontend scaffold)

## Notes

- Do **not** start this before BLK-054 critical bugs are fixed.
- This is the upstream fix for visual consistency. Future frontend
  work must use these components.
