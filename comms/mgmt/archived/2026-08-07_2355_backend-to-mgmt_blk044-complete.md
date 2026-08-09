---
from: backend
to: mgmt
subject: "BLK-044 complete â€” VLM fallback patterns, 262 tests passing"
date: 2026-08-07T23:55:00+05:30
priority: medium
status: closed
in-reply-to: 2026-08-07_2345_backend-to-mgmt_blk041-complete
message-id: 2026-08-07_2355_backend-to-mgmt_blk044-complete
---

## Context

BLK-044 (VLM fallback for degraded documents) is complete. 262 tests
pass in 3.59s.

## Acceptance Criteria â€” All Met

- [x] Standard failure action pattern: OCR fail â†’ crop â†’ deskew â†’ denoise â†’ threshold â†’ VLM
- [x] Skill failure_actions can reference this pattern via named constant (`VLM_FALLBACK_ACTIONS`)
- [x] Geometry tools (deskew, denoise, threshold) available in tool registry (already present)
- [x] VLM handles handwriting recognition (bypass OCR for HANDWRITING regions via `should_bypass_ocr()`)
- [x] Test: degraded scan with OCR confidence < 0.5 triggers VLM fallback
- [x] Test: handwritten region routes directly to VLM (skips OCR)
- [x] Test: thermal receipt with faded ink â€” geometry-first probe order succeeds

## Implementation

### `src/skills/vlm_fallback.py` â€” New module

**`VLM_FALLBACK_ACTIONS`**: Dict mapping all GapTypes to standard
escalation action strings. Skills can merge these with their own
specific actions. Every action (except UNGROUNDED) mentions VLM as
the final escalation step.

**`GEOMETRY_FIRST_PROBE_ORDER`**: Ordered probe list for degraded
documents â€” starts with header (auto-orient/deskew first), includes
handwriting bypass entry, and routes figures to read_chart.

**`should_bypass_ocr(region_type)`**: Returns True for handwriting,
stamp, and logo regions â€” these route directly to VLM, skipping OCR.

**`get_escalation_steps(failed_tool, confidence, threshold)`**: Returns
ordered list of tools to try: `["crop", "deskew", "denoise", "threshold", "ocr", "vlm"]`
for low-confidence OCR, `["vlm"]` for other failures, `[]` if confidence
is above threshold.

### `src/tests/test_vlm_fallback.py` â€” 28 tests
- **TestVLMFallbackActions** (8): all gap types covered, VLM mentioned in all relevant actions
- **TestGeometryFirstProbeOrder** (5): header first, handwriting bypass, figure routes to read_chart
- **TestShouldBypassOCR** (10): handwriting/stamp/logo bypass, text/table don't, case insensitive, constants
- **TestGetEscalationSteps** (6): low confidence escalation, high confidence no escalation, at threshold, non-OCR failure, correct order, custom threshold

## Test Results

```
262 passed, 1272 warnings in 3.59s
```

## Next Up

Starting BLK-042 (Industry skill library).


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
