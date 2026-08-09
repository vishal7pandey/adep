# Comms — Inter-Team Messaging System

> A file-based communication protocol for coordinating between mgmt, backend,
> and frontend teams on the ADEP project.

---

## Quick Start

1. **To send a message**: Create a `.md` file in the recipient's `inbox/`
   folder using the [email format](PROTOCOL.md#5-email-format).
2. **To work on a message**: Move it from `inbox/` to `active/` and update
   its `status` to `in-progress`.
3. **To close a message**: Append a `## Resolution` section, set `status:
   done`, and move it to `archived/`.

## Directory Layout

```
comms/
  README.md         ← you are here
  PROTOCOL.md       ← full protocol & rules
  RACI.md           ← responsibility assignment matrix
  mgmt/
    inbox/  active/  archived/
  backend/
    inbox/  active/  archived/
  frontend/
    inbox/  active/  archived/
```

## Parties

- **mgmt** (Cascade) — Engineering management, architecture, review, coordination.
- **backend** (Devin) — Python backend: `src/` package, tools, providers, agent, skills, templates, tests.
- **frontend** (Antigravity) — UI, client-side code, user-facing interfaces.

## Key Rules

- Each party can only **write** to its owned code regions. Cross-boundary
  changes require a comms message to mgmt.
- **Python package management uses uv only** — no pip, poetry, or conda.
  See [PROTOCOL.md §10](PROTOCOL.md#10-tooling-standards).
- All messages follow the [email format](PROTOCOL.md#5-email-format) with
  YAML frontmatter.
- File naming: `YYYY-MM-DD_HHMM_from-to_slug.md`
- One message per topic. Be concrete and actionable.
- Mgmt arbitrates disputes and approves cross-boundary work.

## Example Message

```yaml
---
from: mgmt
to: backend
subject: "Implement table detection tool"
date: 2026-08-07T14:30:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-07_1430_mgmt-to-backend_implement-table-detection
---

## Context

The vision doc (§2.3) specifies a `detect_tables` tool. We need this for
the invoice extraction skill to handle line-item tables.

## Request

Implement `detect_tables` in `ade/tools/` following the existing tool
contract pattern used by `detect_layout`.

## Acceptance Criteria

- [ ] Tool accepts an image and returns `tables[]` with bbox and cells
- [ ] Unit tests in `tests/` covering at least 2 fixture images
- [ ] Returns confidence scores per detected table

## Constraints

- Must be compatible with the existing provider abstraction
- No new dependencies without mgmt approval
```

Read [PROTOCOL.md](PROTOCOL.md) for the full specification.
