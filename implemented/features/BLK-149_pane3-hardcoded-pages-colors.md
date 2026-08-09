---
id: BLK-149
type: bug
title: "Pane3DocumentViewer hardcodes totalPages=2 and uses hardcoded hex colors"
priority: medium
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T14:50:00+05:30
estimate: S
tags: [frontend, bug, document-viewer, hardcoded, theming]
---

## Problem

`Pane3DocumentViewer` in
`frontend/components/workbench/Pane3DocumentViewer.tsx` hardcodes
`totalPages = 2` instead of getting the page count from the uploaded
document metadata. It also uses hardcoded hex colors (`#0071CE`)
instead of CSS variables (`var(--brand-primary)`) in several places,
inconsistent with the BLK-134 theming work.

## Evidence

`frontend/components/workbench/Pane3DocumentViewer.tsx:35`:
```typescript
const totalPages = 2;
```

Line 51:
```typescript
<FileText className="w-12 h-12 mx-auto opacity-30 text-[#0071CE]" />
```

Line 88:
```typescript
'bg-[#0071CE]/15 border-[#0071CE] text-[#0071CE] shadow-xs shadow-[#0071CE]/20'
```

The rest of the codebase is migrating to `var(--brand-primary)` etc.
(see Sidebar.tsx changes in BLK-134).

## Impact

- `totalPages = 2` means the page navigator always shows "Page 1 of 2"
  regardless of the actual document. A 10-page PDF shows 2 pages; a
  1-page image shows a non-existent page 2.
- Hardcoded hex colors break dark mode — `#0071CE` is the light-theme
  brand color and won't adapt to the dark theme's `--brand-primary:
  #58A6FF`.

## Reproduction or reasoning

1. Upload a 5-page PDF.
2. Open Pane 3 — page navigator shows "Page 1 of 2".
3. Navigate to page 2 — there's no page 2 image to display (or it's
   blank).
4. Toggle dark mode — the heatmap toggle button and empty-state icon
   still show light-theme blue.

## Proposed resolution

1. Get `totalPages` from document metadata (returned by
   `POST /api/v1/documents` or `GET /api/v1/documents/{id}`).
2. Replace all `text-[#0071CE]` with `text-[var(--brand-primary)]`.
3. Replace `bg-[#0071CE]/15` with `bg-[var(--brand-primary-muted)]`.
4. Replace `border-[#0071CE]` with `border-[var(--brand-primary)]`.
5. Replace `shadow-[#0071CE]/20` with an equivalent CSS variable.

## Acceptance criteria

- [ ] `totalPages` comes from document metadata, not hardcoded
- [ ] No hardcoded hex colors — all use CSS variables
- [ ] Dark mode renders correctly for all elements in Pane 3
- [ ] Page navigation respects actual document page count

## Validation plan

- Upload documents with different page counts (1, 5, 10)
- Verify page navigator shows correct total
- Toggle dark mode and verify all colors adapt

## Related issues

BLK-134 (dark mode + theme system),
BLK-143 (file upload not uploaded — document metadata not available)
