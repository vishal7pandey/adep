---
id: BLK-103
type: feature
title: "End-to-end smoke test — upload → select agent → run → verify extraction"
priority: high
status: backlog
phase: 3
owner: backend
created: 2026-08-08T03:30:00+05:30
estimate: M
depends-on: [BLK-088, BLK-092, BLK-093]
tags: [backend, testing, e2e, smoke-test, stabilization]
---

## Description

Create an end-to-end test that proves the full extraction pipeline
works: upload a document, select a prebuilt agent definition, start a
run, and verify extracted fields match expected values.

## Motivation

We have 745 unit tests but no proof that the full pipeline works.
The stabilization fixes (BLK-088 to BLK-100) fixed individual bugs,
but we need to verify the pieces work together. Sample data is now
available in `sample-data/`.

## Design

### Test 1: Invoice extraction (simplest case)

```python
def test_e2e_invoice_extraction():
    """Upload invoice PDF → run invoice agent → verify fields."""
    # 1. Seed store
    seed_store()

    # 2. Start run with invoice definition
    result = run_engine.start_run(
        definition_id="def-invoice-v1",
        document_path="sample-data/invoices/sample-invoice-01.pdf",
    )

    # 3. Wait for completion
    run = run_engine.get_run(result.run_id)
    assert run["status"] in ["completed", "partial"]

    # 4. Verify extracted fields
    extraction = run["extraction"]
    assert "vendor_name" in extraction
    assert "invoice_number" in extraction
    assert "total_amount" in extraction
    # Verify invariant: subtotal + tax = total
    if "subtotal" in extraction and "tax_amount" in extraction:
        assert abs(
            extraction["subtotal"]["value"] + extraction["tax_amount"]["value"]
            - extraction["total_amount"]["value"]
        ) < 0.01
```

### Test 2: Utility bill extraction

```python
def test_e2e_utility_bill():
    result = run_engine.start_run(
        definition_id="def-utility-bill",
        document_path="sample-data/utility-bills/sample-utility-bill-01.pdf",
    )
    run = run_engine.get_run(result.run_id)
    assert run["status"] in ["completed", "partial"]
    assert "provider_name" in run["extraction"]
    assert "amount_due" in run["extraction"]
```

### Test 3: Medical claim (CMS-1500)

```python
def test_e2e_medical_claim():
    result = run_engine.start_run(
        definition_id="def-medical-claim",
        document_path="sample-data/medical-claims/sample-cms1500-01.pdf",
    )
    run = run_engine.get_run(result.run_id)
    assert run["status"] in ["completed", "partial"]
```

### Test 4: BOQ extraction

```python
def test_e2e_boq():
    result = run_engine.start_run(
        definition_id="def-boq-estimator",
        document_path="sample-data/boq/sample-boq-01.pdf",
    )
    run = run_engine.get_run(result.run_id)
    assert run["status"] in ["completed", "partial"]
```

## Acceptance Criteria

- [ ] `test_e2e_invoice_extraction` passes with sample-invoice-01.pdf
- [ ] `test_e2e_utility_bill` passes with sample-utility-bill-01.pdf
- [ ] `test_e2e_medical_claim` passes with sample-cms1500-01.pdf
- [ ] `test_e2e_boq` passes with sample-boq-01.pdf
- [ ] Tests use documents from `sample-data/` directory
- [ ] Tests verify at least 3 extracted fields per document
- [ ] Tests verify at least 1 invariant per document type
- [ ] All tests pass in CI

## Notes

- These tests require OCR providers (PaddleOCR/Tesseract) to be
  installed. Mark as `@pytest.mark.integration` so they can be
  skipped in environments without providers.
- If providers are not available, mock the OCR output but still test
  the full run engine → graph → validator → extraction flow.
- Sample data is in `sample-data/` (see README.md in that folder).
