---
id: BLK-163
title: "Registry search bars — lightweight client-side filter for all 3 registry pages"
status: assigned
priority: high
estimate: S
assigned_to: frontend
created: 2026-08-08T23:35:00+05:30
by: mgmt
---

## Problem

All three registry pages (Agent Definitions, Skills, Templates) render
a flat grid of cards with no search or filter capability. As the
number of definitions/skills/templates grows, finding a specific item
requires visual scanning.

## Design Decision

**Lightweight client-side filter** — no backend search endpoint
needed. All items are already fetched on page mount and held in React
state. A simple `useMemo` + `filter` on the existing array is
sufficient.

### Search algorithm

Use **case-insensitive substring match** across multiple fields per
registry:

- **Agent Definitions**: match against `name`, `id`, `skill_id`,
  `template_id`, `system_prompt`
- **Skills**: match against `name`, `description`, `id`, `tools[]`
- **Templates**: match against `name`, `description`, `id`,
  `fields[].name`

This is O(n) per keystroke with n < 100 typically. No debouncing
needed — React state update is fast enough for this scale. No need
for fuzzy search libraries (Fuse.js, etc.) — substring match is
sufficient for a registry of this size.

### UI design

- Search input placed between the page header and the card grid
- `Search` icon from lucide-react as left adornment
- Placeholder text: "Search agent definitions...", "Search skills...",
  "Search templates..."
- Clear button (X) when text is non-empty
- Width: full-width within the page padding, max-w-2xl centered
- When no results match, show empty state: "No matches found for
  '{query}'"
- Standard `text-sm` font size, matching the page's existing scale

### Implementation pattern

```tsx
const [searchQuery, setSearchQuery] = useState('');
const filtered = useMemo(() => {
  if (!searchQuery.trim()) return items;
  const q = searchQuery.toLowerCase();
  return items.filter(item =>
    item.name.toLowerCase().includes(q) ||
    item.id.toLowerCase().includes(q) ||
    // ... other fields
  );
}, [items, searchQuery]);
```

Then render `filtered` instead of `items` in the grid.

### Files to modify

1. `app/definitions/page.tsx` — add search bar + filter
2. `app/skills/page.tsx` — add search bar + filter
3. `app/templates/page.tsx` — add search bar + filter

### Out of scope

- Backend search endpoints (not needed at this scale)
- Saved searches / search history
- Sort/ordering controls
- Faceted filtering (by tool, by document type, etc.)
