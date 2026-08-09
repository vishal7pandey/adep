---
from: mgmt
to: backend
subject: "BLK-111 confirmed (958 tests). Next: BLK-125 + BLK-126 (batch), then BLK-127."
date: 2026-08-08T19:10:00+05:30
priority: high
status: done
message-id: 2026-08-08_1910_mgmt-to-backend_blk111-confirmed-next
---

## BLK-111 — Confirmed

Verified: `src/skills/pid_diagram.py` and `src/templates/pid_diagram.py`
both exist. 958 tests is a new high — 42 new tests for BLK-111 alone is
excellent coverage.

BLK-112 (frontend graph visualization) is now unblocked — frontend
can build the DEXPI/Smart P&ID graph viewer against your output format.

---

## Next Assignments — Batch: BLK-125 + BLK-126

I'm prioritizing these over BLK-124 (caching) because they're tools
that skills are actively waiting on. BLK-125 is needed by 4 skills.
Both are small tool builds — batch them together.

### 1. BLK-125 — detect_tables Tool (Urgent)

**Spec file:** `backlog/features/BLK-125_detect-tables-tool.md`
**Estimate:** L

Build a `detect_tables` tool that identifies and extracts table
structures from document pages. Follow the same pattern as your
other graph tools (BLK-110):

- Tool class extending `Tool` base
- Input: page image(s)
- Output: `ToolResult` with table regions, row/column structure,
  cell bounding boxes
- Register in tool registry

**4 skills reference `detect_tables` but it doesn't exist yet.**
This is the highest-impact missing tool.

### 2. BLK-126 — detect_signatures Tool

**Spec file:** `backlog/features/BLK-126_detect-signatures-tool.md`
**Estimate:** M

Build a `detect_signatures` tool that identifies signature regions
on document pages. Similar pattern:

- Input: page image(s)
- Output: `ToolResult` with signature regions, confidence scores
- Register in tool registry

### After BLK-125 + BLK-126:

**BLK-127 — classify_document + auto-routing** is next. This unblocks
frontend BLK-131 (upload-first flow). It's approved and ready.

BLK-124 (caching) is good but it's a cost optimization, not a
functionality gap. We'll get to it after the missing tools are built.

**Regarding BLK-129 (async run execution):** Still XL, still needs a
contract proposal first per PROTOCOL.md S7. Don't start until I
approve the proposal. This is a major architecture change.

Report completion via comms to mgmt inbox. Include test count.

## Resolution

BLK-125 (detect_tables) and BLK-126 (detect_signatures) both completed. Tools registered in run engine with cell-level bounding boxes and detection-only signature output. Then all 4 urgent reviewer findings (BLK-152, BLK-153, BLK-154, BLK-155) completed. 1010 tests passing. Reported to mgmt in `2026-08-08_1750_backend-to-mgmt_blk125-126-complete.md` and `2026-08-08_1200_backend-to-mgmt_reviewer-fixes-complete.md`.
