---
id: BLK-126
type: feature
title: "detect_signatures tool — signature, stamp, and seal detection"
priority: medium
status: done
started: 2026-08-08T17:20:00+05:30
completed: 2026-08-08T17:50:00+05:30
phase: 4
owner: backend
created: 2026-08-08T13:50:00+05:30
estimate: M
depends-on: []
tags: [backend, tools, signatures, stamps, trade-finance, compliance]
---

## Problem

Several shipped skills depend on verifying that a document is signed,
stamped, or sealed — but there is no tool to detect these:

- `TradeFinanceScrutinySkill` — MT700 presentations require signed
  and stamped documents; an unsigned bill of lading is a discrepancy
- `CommercialLeaseSkill` — executed lease requires both parties'
  signatures
- `ComplianceAuditSkill` — auditor sign-off
- `MedicalClaimSkill` — provider signature

The vision doc (§ on markdown being lossy) explicitly calls out that
"signatures, stamps, and infographics" are silently dropped by
markdown pipelines. This tool closes that gap.

## Requirements

### Tool Contract

```python
detect_signatures(image, region: BBox | None = None) -> SignaturesResult
```

Returns:

```python
{
  "marks": [
    {
      "bbox": BBox,
      "kind": "signature" | "stamp" | "seal" | "initials" | "checkmark",
      "confidence": float,
      "is_handwritten": bool,
      "nearby_label": str | None,   # e.g. "Authorized Signatory"
      "ink_coverage": float,        # fraction of bbox with ink
    }
  ]
}
```

### Implementation Strategy

1. **Candidate regions**: connected-component analysis for dense
   non-text ink clusters; circular/rectangular Hough detection for
   stamps and seals.
2. **Classification**: VLM pass on each candidate crop to assign
   `kind` and `is_handwritten`.
3. **Label association**: find the nearest text line below/left of the
   mark (typical signature-block layout) via `ocr` and report it as
   `nearby_label`.

### Important: Detection, Not Verification

This tool answers *"is there a signature here?"* — **not** *"is this
signature authentic?"* or *"whose signature is this?"*

Signature **verification** (identity matching, forgery detection) is
explicitly out of scope. It requires reference specimens, has serious
legal and liability implications, and is a fundamentally different
problem. Do not implement it under this item. If it is ever needed it
must be a separate, carefully scoped initiative with legal review.

Document this boundary clearly in the tool docstring so downstream
users don't over-trust the output.

## Acceptance Criteria

- [x] `detect_signatures` registered with a ToolSpec
- [x] Connected-component + Hough candidate detection
- [x] VLM classification into the 5 `kind` values
- [x] `is_handwritten` distinguishes ink from printed/digital marks
- [x] `nearby_label` associates marks with signature-block labels
- [x] `ink_coverage` computed deterministically
- [x] Docstring states detection-only scope, no authenticity claims
- [ ] Marked `cacheable=True` for BLK-124 (deferred to BLK-124)
- [x] Tests: signature present, absent, stamp, seal, checkbox,
      printed-vs-handwritten, label association
- [x] New GapType `SIGNATURE_MISSING` added
- [ ] Integration: `TradeFinanceScrutinySkill` gains a
      `required_documents_signed` invariant using this tool (follow-up)

## Constraints

- No authenticity, identity, or forgery claims in the output schema
- No biometric processing
