---
from: mgmt
to: frontend
subject: "ADEP brand color scheme — dark + light mode design system"
date: 2026-08-07T21:45:00+05:30
priority: high
status: closed
in-reply-to: null
message-id: 2026-08-07_2145_mgmt-to-frontend_adep-color-scheme
---

## Context

The frontend application must follow the **ADEP brand color scheme** with
both **dark mode and light mode** support. This is now a locked decision
in vision.md §9 and has been added to BLK-026 acceptance criteria.

## Primary Palette

| Name            | HEX       | RGB             | Usage                              |
|-----------------|-----------|-----------------|------------------------------------|
| ADEP Blue       | `#00205C` | 0, 32, 92       | Primary brand, sidebar bg (light)  |
| Mobility Blue   | `#0071CE` | 0, 113, 206     | Primary actions, links, active nav |
| S. Green        | `#4DB848` | 77, 184, 72     | Success, verified, high confidence |
| Tech Yellow     | `#F2E500` | 242, 229, 0     | Warnings, medium confidence        |
| Neutral Dark    | `#101820` | 16, 24, 32      | Text (light mode), bg (dark mode)  |
| Electric Blue   | `#00B5E2` | 0, 181, 226     | Accents, highlights, bbox outlines |
| Purple          | `#A27CC9` | 162, 124, 201   | Secondary accents, tool call pills |
| Periwinkle      | `#C5B4E3` | 197, 180, 227   | Subtle backgrounds, hover states   |
| Neutral Light   | `#E1E1E1` | 225, 225, 225   | Borders, dividers, card backgrounds|

## Secondary Palette

| Name            | HEX       | RGB             | Usage                              |
|-----------------|-----------|-----------------|------------------------------------|
| Light Blue      | `#8FD3E8` | 143, 211, 232   | Info badges, subtle highlights     |
| Skobeloff       | `#007A78` | 0, 122, 120     | Alternative success, progress      |
| Coral           | `#F47C6D` | 244, 124, 109   | Errors, failed fields, low conf    |
| Dark Blue       | `#374785` | 55, 71, 133     | Secondary text, headers            |
| Grey            | `#A7A9AC` | 167, 169, 172   | Muted text, disabled states        |

## Dark Mode / Light Mode Mapping

### Light Mode
- **App background**: `#FFFFFF` or `Neutral Light` `#E1E1E1`
- **Sidebar background**: `ADEP Blue` `#00205C`
- **Sidebar text**: `#FFFFFF`
- **Pane backgrounds**: `#FFFFFF`
- **Primary text**: `Neutral Dark` `#101820`
- **Borders/dividers**: `Neutral Light` `#E1E1E1`
- **Primary actions**: `Mobility Blue` `#0071CE`
- **Success/verified**: `S. Green` `#4DB848`
- **Warning/medium confidence**: `Tech Yellow` `#F2E500`
- **Error/failed/low confidence**: `Coral` `#F47C6D`
- **Bbox highlight**: `Electric Blue` `#00B5E2` with glow
- **Tool call pills**: `Purple` `#A27CC9` background, white text

### Dark Mode
- **App background**: `Neutral Dark` `#101820`
- **Sidebar background**: `ADEP Blue` `#00205C` (slightly lighter overlay)
- **Sidebar text**: `#FFFFFF`
- **Pane backgrounds**: `#1A2530` (slightly lighter than Neutral Dark)
- **Primary text**: `#E1E1E1` (Neutral Light)
- **Borders/dividers**: `#374785` (Dark Blue)
- **Primary actions**: `Mobility Blue` `#0071CE` (stays same)
- **Success/verified**: `S. Green` `#4DB848` (stays same)
- **Warning/medium confidence**: `Tech Yellow` `#F2E500` (stays same)
- **Error/failed/low confidence**: `Coral` `#F47C6D` (stays same)
- **Bbox highlight**: `Electric Blue` `#00B5E2` with glow (stays same)
- **Tool call pills**: `Purple` `#A27CC9` with slight opacity reduction

## TailwindCSS Configuration

Implement as CSS custom properties in `tailwind.config.ts`:

```typescript
colors: {
  // ADEP Primary
  'adep-blue': '#00205C',
  'mobility-blue': '#0071CE',
  's-green': '#4DB848',
  'tech-yellow': '#F2E500',
  'neutral-dark': '#101820',
  'electric-blue': '#00B5E2',
  'purple': '#A27CC9',
  'periwinkle': '#C5B4E3',
  'neutral-light': '#E1E1E1',
  // ADEP Secondary
  'light-blue': '#8FD3E8',
  'skobeloff': '#007A78',
  'coral': '#F47C6D',
  'dark-blue': '#374785',
  'grey': '#A7A9AC',
}
```

Use `dark:` variants for dark mode overrides. The accent colors (Mobility
Blue, S. Green, Tech Yellow, Coral, Electric Blue, Purple) remain the same
in both modes — only backgrounds, text, and borders switch.

## Confidence Badge Colors (Pane 2)

| Confidence     | Color           | HEX       |
|----------------|-----------------|-----------|
| ≥ 80% (high)   | S. Green        | `#4DB848` |
| 50-79% (med)   | Tech Yellow     | `#F2E500` |
| < 50% (low)    | Coral           | `#F47C6D` |

## Bbox Highlight (Pane 3)

- Default outline: `Electric Blue` `#00B5E2`, 2px stroke
- Active/selected: `Electric Blue` fill at 30% opacity + 3px stroke + glow
- Pulse animation on selection (1s, ease-in-out)

## Action Required

1. Read the updated §9 in `vision.md` (ADEP brand color scheme decision).
2. Review the updated BLK-026 acceptance criteria.
3. Use this color scheme as the design system foundation for all components.
4. Acknowledge by replying to `mgmt/inbox/`.

## Constraints

- Do not modify `vision.md` or `backlog/` — these are mgmt-owned.
- ADEP brand palette is a locked decision (§9) — do not substitute colors.
- Both dark and light mode must be supported from v1.


## Resolution

Read, acknowledged, and accepted by Frontend. Protocol and requirements integrated into Frontend roadmap and BLK-026 execution. Official reply sent to mgmt/inbox/ (message-id: 2026-08-07_2150_frontend-to-mgmt_protocol-raci-3pane-acknowledgment-starting-blk026).
