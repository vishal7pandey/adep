---
id: BLK-075
type: feature
title: "Provider comparison & dynamic selection — OCR/VLM provider registry with cost/accuracy metadata"
priority: low
status: backlog
phase: 5
owner: unassigned
created: 2026-08-08T00:35:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-001, BLK-050]
tags: [provider, registry, cost, accuracy, selection, ocr, vlm]
---

## Description

Maintain a provider registry with cost, accuracy, and capability
metadata for each OCR/VLM provider. The agent can dynamically select
the best provider for a region or document type.

## Motivation

From `agentic agent builder.md`: the meta-agent must be aware of OCR
and VLM provider pricing and capabilities (LandingAI, LlamaParse,
Parseur, Reducto, Mistral OCR 3, AWS Textract). A provider registry
enables ADE to make informed tool choices.

## Design

**Provider registry:**
```json
{
  "providers": [
    {
      "name": "paddle_ocr",
      "type": "ocr",
      "cost_per_page_usd": 0.0,
      "cost_per_1k_chars_usd": 0.0,
      "strengths": ["structured forms", "Chinese"],
      "weaknesses": ["handwriting", "poor scans"],
      "accuracy_score": 0.82
    },
    {
      "name": "mistral_ocr",
      "type": "ocr",
      "cost_per_1k_pages_usd": 2.0,
      "strengths": ["multilingual", "high volume"],
      "weaknesses": ["no grounding", "flat markdown output"]
    }
  ]
}
```

**Dynamic selection:**
- Skill can specify `provider_preferences`
- Plan node selects provider based on:
  - Document type
  - Region characteristics (text density, language, quality)
  - Cost budget
  - Historical accuracy

**Fallback chain:**
- Try preferred provider
- If confidence < threshold, try next
- If all OCRs fail, escalate to VLM

## Acceptance Criteria

- [ ] Provider registry with metadata
- [ ] `provider_metadata` available in plan node
- [ ] Skill can specify provider preferences
- [ ] Dynamic provider selection based on cost/accuracy
- [ ] Fallback chain implementation
- [ ] Provider comparison table in admin panel
- [ ] Test: degraded scan → VLM fallback works
- [ ] Test: high-volume run → cheaper provider chosen

## Constraints

- v1: only providers already in ADE (PaddleOCR, Tesseract, Azure VLM)
- External provider costs are estimates
- No actual billing integration

## Dependencies

- BLK-001 (tool interfaces)
- BLK-050 (token cost data)
