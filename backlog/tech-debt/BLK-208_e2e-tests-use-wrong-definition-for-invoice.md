---
id: BLK-208
type: tech-debt
title: "E2E tests use def-trade-finance-scrutiny definition for invoice tests — wrong definition for the document type"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T12:15:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [testing, e2e, correctness, test-quality, fixtures]
---

## Description

In `src/tests/test_e2e.py`, multiple tests that claim to test invoice extraction actually use the `def-trade-finance-scrutiny` definition:

- `test_invoice_e2e_mocked` (line 255): `execute_run("def-trade-finance-scrutiny", str(sample_pdf))`
- `test_invoice_run_produces_result` (line 289): `execute_run("def-trade-finance-scrutiny", str(sample_pdf))`
- `test_result_has_required_keys` (line 377): `execute_run("def-trade-finance-scrutiny", str(sample_pdf))`
- `test_invoice_sample_01` (line 470): `execute_run("def-trade-finance-scrutiny", str(pdf))`
- `test_invoice_sample_02` (line 480): `execute_run("def-trade-finance-scrutiny", str(pdf))`
- `test_invoice_invariant_checked` (line 532): `execute_run("def-trade-finance-scrutiny", str(pdf))`

There is a `def-invoice` definition in the prebuilt catalogue. The tests set up `InvoiceSkill`, `InvoiceTemplate`, and invoice mock values, but then run them through the trade finance scrutiny definition, which uses `TradeFinanceScrutinySkill` and `TradeFinanceTemplate`.

## Problem Statement

- Tests named `test_invoice_*` are not actually testing invoice extraction — they're testing trade finance scrutiny extraction with invoice mock data
- The test assertions check `result["definition_id"] == "def-trade-finance-scrutiny"` (line 258), confirming the wrong definition is intentional, but the test class names and mock data are all invoice-themed
- If the invoice definition has a bug, these tests would not catch it
- If the trade finance scrutiny definition has a bug that happens to be masked by invoice mock values, these tests give false confidence
- The integration tests (`test_invoice_sample_01`, `test_invoice_sample_02`) use sample invoice PDFs but run them through the trade finance definition — any accuracy claims for invoices based on these tests are measuring the wrong skill

## Acceptance Criteria

- [ ] Change all `test_invoice_*` tests to use `def-invoice` instead of `def-trade-finance-scrutiny`
- [ ] Verify that `def-invoice` exists in the prebuilt catalogue and maps to `InvoiceSkill` / `InvoiceTemplate`
- [ ] Update assertions to check `result["definition_id"] == "def-invoice"`
- [ ] Add separate tests for trade finance scrutiny if they don't already exist
- [ ] Re-run all e2e tests to confirm they pass with the correct definition

## Constraints

- Don't change the mock values or test structure — only fix the definition ID
- If `def-invoice` doesn't exist in the prebuilt catalogue, that's a separate bug to file

## Dependencies

- `src/tests/test_e2e.py`
- `src/definitions/prebuilt.py` (verify `def-invoice` exists)

## Notes

- Found during full-repo audit; this may be a copy-paste error from when the test was first written using trade finance as a proxy, or the invoice definition may not have existed at the time

## Implementation Log

- **2026-08-09T16:00 (mgmt)**: Reassigned from `cline` (mandate suspended, see projectmgmt/STATUS.md 2026-08-09 16:00 note) to `devin`. Test-code ownership for this file's domain reverts to the implementing team; independent verification now happens via cross-team review (devin<->antigravity) instead of a dedicated gate.

- **2026-08-09 (mgmt)**: Assigned to `cline` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
