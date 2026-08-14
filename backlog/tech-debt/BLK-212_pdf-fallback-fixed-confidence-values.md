---
id: BLK-212
type: tech-debt
title: "PDF fallback assigns fixed confidence values (0.88–0.90) — not calibrated, not earned"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T12:35:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [fallback, confidence, correctness, eval-integrity]
---

## Description

In `src/fallback/pdf_runtime.py`, the regex-based parsers assign fixed confidence values to extracted fields:

- `bank_statement`: 0.90 for most fields
- `utility_bill`: 0.90 for most fields
- `commercial_lease`: 0.88 for most fields
- `trade_finance_scrutiny`: 0.90
- `commodity_trade`: 0.90
- `purchase_order`: 0.90
- `packing_list`: 0.90

These values are hardcoded constants, not computed from any calibration process. A regex match on a PDF text layer gets the same confidence as a VLM-backed extraction with verified grounding.

## Problem Statement

- Confidence scores are supposed to represent the probability that an extracted value is correct — a fixed 0.90 for regex matches is not calibrated
- The HITL gate (`src/agent/hitl.py`, BLK-204) uses confidence thresholds to decide gating: 0.90 is "LOW risk, auto-execute, no gate" — so fallback extractions bypass human review entirely
- Budget enforcement and partial termination logic use confidence to decide whether to continue cycling — inflated confidence means the agent gives up sooner
- Any analytics or accuracy reporting that aggregates confidence values will be skewed by these fixed values
- The values are high enough (0.88–0.90) to pass most validation thresholds, meaning regex-extracted fields are treated as virtually certain

## Acceptance Criteria

- [ ] Replace fixed confidence values with a more conservative default (e.g., 0.70) or a configurable setting
- [ ] Add a `fallback_confidence` setting to `src/config.py` so it can be tuned without code changes
- [ ] Document that fallback confidence is not calibrated and should not be compared directly to agent confidence
- [ ] Consider adding a `extraction_method` field to `FieldValue` or run metadata to distinguish fallback from agent extraction

## Constraints

- Don't break existing tests that assert on confidence values — update them to use the new default
- If lowering confidence causes HITL gates to fire (once HITL is wired in), that's correct behavior

## Dependencies

- `src/fallback/pdf_runtime.py`
- `src/config.py`
- Related to BLK-178 (PDF fallback bypasses agent) and BLK-204 (HITL unwired)

## Notes

- Found during full-repo audit; the fixed confidence values compound the BLK-178 problem — not only does the fallback bypass the agent, but it also reports high confidence that suppresses downstream review

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
