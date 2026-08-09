---
id: BLK-056
type: feature
title: "Responsive & mobile layout — tablet and phone support"
priority: medium
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T23:59:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-026, BLK-054]
tags: [frontend, responsive, mobile, tablet, layout, ui]
---

## Description

Make the workbench and admin panel usable on tablet and large phone
screens. The 3-pane desktop layout must adapt to smaller viewports
without breaking interaction.

## Motivation

Field workers, warehouse staff, and mobile reviewers may use tablets
to review extractions and approve results. A desktop-only UI limits
adoption. The admin panel also needs to work on tablet for managers.

## Breakpoints

| Breakpoint | Layout |
|------------|--------|
| Desktop (≥1280px) | 3-pane grid (Pane 1, 2, 3 side-by-side) |
| Tablet (768px–1279px) | 2-pane: Pane 1 + Pane 2 visible, Pane 3 as a drawer |
| Phone (<768px) | Single pane with bottom tab bar to switch between Pane 1, 2, 3 |

## Tablet Layout

- Sidebar collapses to a hamburger menu in the top-left
- Pane 1 (Agent Console) takes 40% width
- Pane 2 (Extracted Data) takes 60% width
- Pane 3 (Document Viewer) is a right drawer that slides in when:
  - A field's "Show source" is clicked in Pane 2
  - The "Document" tab is selected
- Bbox overlay in drawer uses full width of drawer

## Phone Layout

- Bottom tab bar with 3 icons: Agent, Data, Document
- Top header shows run name + status
- Sidebar becomes a hamburger menu
- Each pane is full-screen when selected
- Pane 3 can be opened from a field card via "Show source" button,
  then user returns to "Data" tab to continue

## Admin Panel Responsive

- Stat cards: 4 across on desktop, 2 on tablet, 1 on phone
- 7-day chart: scales down, hides grid on phone, shows only bars
- Budget status bars: stack vertically on phone
- Recent runs table: converts to cards on phone

## Acceptance Criteria

- [ ] Breakpoints implemented in Tailwind (`lg`, `md`, `sm`)
- [ ] Desktop keeps current 3-pane layout
- [ ] Tablet shows 2-pane + document drawer
- [ ] Phone shows single pane + bottom tab bar
- [ ] Sidebar collapses to hamburger menu on < 1280px
- [ ] "Show source" opens document drawer on tablet/phone
- [ ] Bottom tab bar uses Lucide icons: `Terminal`, `List`, `FileText`
- [ ] Admin panel stat cards reflow correctly
- [ ] Admin panel chart scales to small screens
- [ ] All modals/dialogs full-screen on phone, centered on desktop
- [ ] Touch targets ≥44px on phone
- [ ] Test on at least Chrome DevTools device emulation for:
  - iPad (tablet)
  - iPhone 14 Pro (phone)
  - Desktop 1440px

## Constraints

- Mobile is a v4 Phase 4 concern — desktop polish (BLK-054) comes first
- Do not implement complex swipe gestures in v1; bottom tabs are enough [SF]
- All panes must remain fully functional in all layouts

## Dependencies

- BLK-026 (frontend scaffold)
- BLK-054 (UI polish — must be stable first)
