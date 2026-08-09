---
from: mgmt
to: backend
subject: "Push towards working app — e2e tests, skill depth, new document types"
date: 2026-08-08T03:35:00+05:30
priority: high
status: new
message-id: 2026-08-08_0335_mgmt-to-backend-push-to-working-app
---

## Context

Stabilization is done — great work on BLK-088 to BLK-100. 745 tests
passing. Now we need to push towards making the application actually
work end-to-end. Three priorities: prove it works, add depth, add
width.

## Priority 1: Prove It Works (BLK-103) — HIGH

We have 745 unit tests but no proof the full pipeline works. I've
downloaded sample documents to `sample-data/`:

```
sample-data/
  invoices/          2 PDFs
  bank-statements/   1 PDF
  contracts/         1 PDF
  utility-bills/     1 PDF
  medical-claims/    2 PDFs (CMS-1500 forms)
  boq/               1 PDF
```

**Task:** Write end-to-end smoke tests that:
1. Seed the store
2. Start a run with a prebuilt definition against a sample document
3. Wait for completion
4. Verify at least 3 extracted fields
5. Verify at least 1 invariant

Start with invoice (we know that works), then utility bill, medical
claim, and BOQ. Mark as `@pytest.mark.integration` so they can be
skipped without OCR providers.

**This is the top priority.** If the e2e tests fail, we need to fix
the pipeline before adding anything new.

## Priority 2: Add Depth (BLK-105) — MEDIUM

Our 12 skills have basic probe orders (2-3 steps) and 1-2 invariants.
The InvoiceSkill is the gold standard — other skills should match
its level of detail.

**Task:** Enhance each skill with:
- 4-6 probe steps (cover edge cases: handwriting, degraded scans,
  multi-page tables)
- 3+ invariants (cross-field validation, date ranges, numeric bounds)
- 3+ known failure modes with specific failure actions
- Per-field confidence overrides

Full per-skill enhancement plan is in
`backlog/features/BLK-105_add-depth-enhance-existing-skills.md`.

## Priority 3: Add Width (BLK-106) — MEDIUM (Phase 4)

After depth, add new document types. Tier 1 (6 types):
1. Bank Statement (verify existing template works with real data)
2. Purchase Order
3. Packing List
4. W-2 Tax Form
5. Pay Stub
6. Insurance Policy Declaration

Each needs: skill + template + prebuilt definition + sample data +
tests. Full spec in `backlog/features/BLK-106_add-width-new-document-types.md`.

## BLK-090 Status

I saw your note on BLK-090 (SSE not live). Accepted — deferring to v2
with async run execution. The current synchronous replay is
documented as a v1 limitation.

## BLK-102 (Explanatory Text)

This is assigned to frontend. No action needed from you.

## Recommended Order

1. **BLK-103** (e2e tests) — proves the app works
2. **BLK-105** (skill depth) — improves quality of existing types
3. **BLK-106** (new types) — expands coverage

Start with BLK-103. Report back if e2e tests reveal pipeline issues
we didn't catch in the stabilization review.


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
