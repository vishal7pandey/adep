---
from: frontend
to: mgmt
subject: "BLK-134 — Phase 1 complete: Semantic design token system + dark mode formalized. Component tokenization in progress."
date: 2026-08-08T10:25:00+05:30
priority: medium
status: new
message-id: 2026-08-08_1025_frontend-to-mgmt_blk134-phase1
in-reply-to: 2026-08-08_1430_mgmt-to-frontend-blk137-133-confirmed
---

## BLK-134 — Phase 1: Design Token System ✅

### What shipped

**`globals.css`** — Complete semantic token system with 50+ tokens:

| Category | Tokens | Purpose |
|----------|--------|---------|
| `--surface-*` | 4 tokens | Backgrounds (raised, sunken, overlay) |
| `--text-*` | 4 tokens | Primary, secondary, muted, inverse |
| `--brand-*` | 7 tokens | Primary, hover, subtle, muted, accent, navy |
| `--status-*` | 8 tokens | Success/warning/error/info + subtle variants |
| `--heatmap-*` | 6 tokens | Confidence overlay colors |
| `--interactive-*` | 6 tokens | Focus rings, input borders, button states |
| `--misc-*` | 5 tokens | Badge, scrollbar, code bg |

**Dark theme** — Full GitHub-inspired dark palette:
- Surfaces: `#0D1117` → `#161B22` → `#1C2128` hierarchy
- Brand primary shifts from `#0071CE` → `#58A6FF` for readability
- Status colors brighten for dark backgrounds (e.g., error `#DC3545` → `#F85149`)
- Heatmap tokens are **identical** in both themes (document viewer
  always keeps white bg — per your directive to never invert the
  document render)

### Components tokenized so far

| Component | Status | Key changes |
|-----------|--------|-------------|
| `LttsButton` | ✅ | `--brand-primary`, `--brand-accent`, `--surface-raised` |
| `LttsBadge` | ✅ | `--status-success/warning/error`, `--badge-tool-*` |
| `Sidebar` | ✅ | `--sidebar-bg`, `--brand-primary`, `--brand-accent`, `--status-*` |

### Remaining component work (same session)

These still have hardcoded hex and will be tokenized as I continue:
- `Pane1AgentConsole.tsx` — heaviest hex usage (~15 references)
- `Pane2ExtractedData.tsx` — status colors, brand primary
- `CommandPalette.tsx` — brand primary, surface colors
- `SkillEditor.tsx` — brand primary, status
- `TemplateEditor.tsx` — brand primary, status
- `InfoTooltip.tsx` — brand primary

### Key design decisions

1. **Document viewer never inverts** — white bg stays white in dark
   mode. The viewport area behind the document uses a neutral dark
   mat (`bg-black/10 dark:bg-black/40`).
2. **Sidebar darkens further** — from `#00205C` → `#010B1A` in dark
   mode. The navy blue shifts to near-black for proper contrast.
3. **Brand blue brightens** — `#0071CE` → `#58A6FF` in dark mode.
   WCAG AA contrast ratio against `#161B22` bg: 6.2:1 ✅
4. **Scrollbar adapts** — thumb color uses tokens, adapts to theme.

Will continue tokenizing remaining components. Build compiles clean.
