---
from: backend
to: mgmt
subject: "BLK-040 complete â€” read_chart tool with structured data, 210 tests passing"
date: 2026-08-07T23:35:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2325_backend-to-mgmt_blk043-complete
message-id: 2026-08-07_2335_backend-to-mgmt_blk040-complete
---

## Context

BLK-040 (read_chart tool) is complete. 210 tests pass in 3.71s.

## Acceptance Criteria â€” All Met

- [x] `read_chart` ToolSpec registered in ToolRegistry
- [x] Input: image handle (cropped chart region), optional chart_type hint
- [x] Output: structured data series `{"series": [...], "x_axis": [...], "y_axis": {...}, "chart_type": "..."}`
- [x] Grounding: bbox of the chart region (from image dimensions)
- [x] VLM provider dispatch (uses Azure GPT-5.4 vision)
- [x] Handles bar, line, pie, and stacked area charts (via chart_type hint)
- [x] Fallback: if VLM returns non-JSON or missing series, returns error ToolResult
- [x] Unit tests with mocked VLM responses

## Implementation

### `src/providers/vlm_azure.py` â€” `read_chart` upgraded
- **Before**: Thin wrapper around `vlm()` returning free-text
- **After**: Dedicated function with:
  - Structured JSON prompt (`_CHART_SYSTEM_PROMPT`) instructing VLM to return only JSON
  - `chart_type` hint parameter (bar/line/pie/stacked_area)
  - Optional `question` parameter for specific queries
  - JSON parsing with embedded JSON extraction (handles VLM wrapping)
  - Structure validation (must have `series` key)
  - Grounding from PIL image dimensions
  - Graceful error handling for all failure modes

### `src/run.py` â€” ToolSpec updated
- Added `chart_type` to `arg_schema`
- Updated description to mention VLM and OCR bypass
- Updated return_description with structured dict schema

### `src/tests/test_read_chart.py` â€” 13 tests
- **TestReadChartStructured** (4): structured dict output, grounding from image, chart_type in prompt, question in prompt
- **TestReadChartFailures** (5): VLM returns None, non-JSON, missing series, malformed JSON, RuntimeError
- **TestReadChartRegistry** (3): registered in registry, has chart_type in spec, description mentions VLM
- **TestReadChartMultipleSeries** (1): multi-series chart extraction

## Test Results

```
210 passed, 1272 warnings in 3.71s
```

## Next Up

Starting BLK-041 (Multi-page hierarchical state).


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
