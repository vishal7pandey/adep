---
id: BLK-127
type: feature
title: "classify_document tool + auto-routing to the best agent definition"
priority: high
status: done
phase: 4
owner: backend
created: 2026-08-08T13:50:00+05:30
estimate: L
depends-on: []
tags: [backend, tools, classification, routing, ux]
---

## Problem

The user must know which agent definition to pick before uploading.
With 11 prebuilt agents across 11 GICS sectors, that is a real burden
— and it gets worse as the catalogue grows.

Worse, picking wrong produces a confusing failure: the invoice agent
run against a medical claim will return mostly empty fields with low
confidence and no clear explanation that the *agent choice* was the
problem.

## Requirements

### Tool Contract

```python
classify_document(image, candidates: list[str] | None = None) -> ClassificationResult
```

Returns:

```python
{
  "predictions": [
    {
      "document_type": str,        # e.g. "invoice", "medical_claim"
      "confidence": float,
      "reasoning": str,            # short, for the trace
      "suggested_definition_id": str | None,
    }
  ],
  "page_count": int,
  "is_multi_type": bool,           # true if pages differ in type
}
```

Ranked, highest confidence first. `candidates` optionally restricts
the label set; default is all registered template ids.

### Implementation

1. Rasterize page 1 (plus a sample of later pages for multi-page docs)
2. VLM pass with a compact prompt listing the candidate types and
   their distinguishing features, derived from each Template's
   description
3. Return ranked predictions with short reasoning

Keep the prompt in `src/prompts/` per the prompt-engineering rule —
not inline.

### Auto-Routing Endpoint

```
POST /api/v1/documents/{document_id}/suggest-agent
```

Returns the ranked predictions plus the matching agent definition for
each. The frontend can then present "This looks like an **Invoice**.
Use *Invoice Extractor*?" with alternatives.

### Optional Auto-Route on Run Start

Allow `POST /api/v1/runs` with `definition_id: "auto"`. The engine
classifies first, picks the top prediction above a confidence
threshold (default 0.75), and records the routing decision as the
first trace entry.

If no prediction clears the threshold, fail fast with a clear error
listing the top candidates — **do not** silently guess. Guessing wrong
burns budget and produces confusing partial results.

### Multi-Type Documents

If pages classify differently, set `is_multi_type: true` and return
per-page predictions. Full multi-document orchestration is BLK-035
(deferred) — this item only needs to *detect and report* the
condition, not handle it.

## Acceptance Criteria

- [ ] `classify_document` registered with a ToolSpec
- [ ] Prompt lives in `src/prompts/`, not inline
- [ ] Ranked predictions with confidence and short reasoning
- [ ] `suggested_definition_id` resolved from the definition store
- [ ] `POST /api/v1/documents/{id}/suggest-agent` endpoint
- [ ] `definition_id: "auto"` supported on run start
- [ ] Auto-route threshold configurable (default 0.75)
- [ ] Below-threshold auto-route fails fast with candidate list —
      never silently guesses
- [ ] Routing decision recorded as a trace entry
- [ ] `is_multi_type` detection with per-page predictions
- [ ] Marked `cacheable=True` for BLK-124
- [ ] Tests: correct classification for all 12 shipped types,
      ambiguous document, unknown type, multi-type document,
      auto-route success, auto-route below-threshold failure
- [ ] New GapType `DOCUMENT_TYPE_UNKNOWN`

## Notes

Coordinate with frontend (BLK-131) — the upload flow should offer the
suggestion rather than forcing an upfront agent choice. This is a
significant UX improvement: upload first, confirm the agent second.
