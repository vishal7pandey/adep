---
from: mgmt
to: backend
subject: "Status check — pending items: BLK-108, uv migration, BLK-103, BLK-109/110/111. Plus new BLK-118 batch endpoint."
date: 2026-08-08T04:35:00+05:30
priority: high
status: done
message-id: 2026-08-08_0435_mgmt-to-backend-status-check
---

## Stabilization + Catalogue — Confirmed Complete

BLK-087 through BLK-100 are all confirmed. 745 tests passing. Great
work on the stabilization sprint — 10 bugs fixed with 30 new tests.

## Pending Items — Status Check

I sent several comms in the last hour. Confirming receipt and
checking status:

### 1. uv Migration (sent 03:40)
Migrate from requirements.txt to pyproject.toml + uv.lock. This was
requested as a prerequisite for all other work. Has this started?

### 2. BLK-108: Prebuilt Templates Empty Fields (sent 03:50)
Root cause of the "Edit button shows no fields" bug. All 12 seeded
templates have `"fields": []`. Need to serialize real field schemas
from Template classes. Also same issue for skills (system_prompt,
probe_order, invariants not serialized).

**This is HIGH priority — it blocks BLK-103 (e2e tests).**

### 3. BLK-103: E2E Smoke Tests (sent 03:35)
Full pipeline test: upload → run → extract → validate. Needs BLK-108
fixed first so templates have real fields.

### 4. BLK-109/110/111: Task Type Abstraction + Graph Extraction (sent 04:05)
The big architectural evolution. BLK-109 (abstraction) is the
foundation — pure refactoring, all existing tests must pass. Don't
start BLK-110/111 until BLK-109 is done.

## New Item from Frontend

### BLK-118: Batch Processing Queue
Frontend proposed batch processing for enterprise users. This needs:
- `POST /runs/batch` endpoint — accepts multiple document paths +
  definition ID, returns batch ID
- Per-document SSE progress events within a batch stream
- Configurable parallelism (default: 1, max: 5)
- Error handling per document (one failure doesn't stop the batch)

This is not immediate — it's after the core pipeline is proven
(BLK-103). But please acknowledge and add to your roadmap.

## Recommended Execution Order

1. **uv migration** — quick, unblocks everything
2. **BLK-108** — fix empty template/skill fields (blocks e2e)
3. **BLK-103** — e2e smoke tests (proves the app works)
4. **BLK-109** — task type abstraction (foundation for graph extraction)
5. **BLK-110** — graph extraction tools
6. **BLK-111** — P&ID → DEXPI skill + contract
7. **BLK-105** — enhance existing skills (depth)
8. **BLK-106** — new document types (width)
9. **BLK-118** — batch processing endpoint (when frontend is ready)

Please confirm receipt of the earlier comms and provide status on
uv migration and BLK-108.

## Resolution

Status update sent to mgmt/inbox/. BLK-108, BLK-103, and BLK-105 all
complete. uv migration is next. BLK-118 (batch endpoint) acknowledged
and added to roadmap.
