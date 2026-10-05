# ADE-38 — Plan: perception tools

Status: plan-approved · Risk: medium · Jira: ADE-38
Created: 2026-10-05 · Slug: perception-tools · Spec: spec.md

## Summary

One new module, `src/engine/tools.py`. `survey_layout`/`survey_region` are new code (ported design from
ade2's `tools.py`, read in full); `crop_and_read`/`ocr_page` are thin wrappers around ade's existing
`src/providers/vlm_azure.vlm`, `src/providers/image_cv.crop`, `src/providers/ocr_tesseract.ocr`.
**Size:** M.

## Current state

- `src/engine/` has `skills.py`, `budget.py`, `validation.py`, `history.py` (ADE-34/35/36/37); this
  story adds a sibling module, no changes to any of them.
- `src/documents/store.py::get_document_store().get_page_path(doc_id, page_number)` is 1-indexed and
  raises `FileNotFoundError` (not `None`) for a missing page/document.
- `src/tools/base.py`: `BBox = tuple[int,int,int,int]` (pixel, `x1,y1,x2,y2`), `Grounding(bbox, page=0,
  region_id=None, source_tool="", confidence=0.0)` (page is 0-indexed), `ToolResult(ok, data,
  grounding, error, tool, cost)`.
- Commands: `uv run pytest src/tests/ -v -m "not integration"`, `uv run ruff check src/`,
  `uv run ruff format src/`.

## Approach

1. `_get_page_image_path(document_id, page_num)`: wraps `get_document_store().get_page_path`, catching
   `FileNotFoundError` and returning `None` so callers can produce the module's uniform
   `{"error": ...}` shape instead of letting the exception propagate (R7).
2. `survey_layout(document_id, page_num=1)`: load image (PIL), downscale to max 1024px (new, local
   helper `_downscale_for_survey`), save to a temp PNG, call `src.providers.vlm_azure.vlm(temp_path,
   SURVEY_PROMPT)`, parse the JSON array from `result.data` (reusing a small `_parse_json_array` helper
   ported from ade2, tolerant of markdown fences), convert each zone's normalized bbox to pixel space
   against the *original* image's width/height, wrap each as containing a `Grounding`.
3. `survey_region(document_id, bbox_pixel, page_num=1)`: load image, crop in-memory (PIL, not via the
   `crop()` provider — this crop is for the survey resolution step, an internal detail, not something
   the agent asked for directly; `crop()` is reserved for `crop_and_read`, matching ade2's own structure
   where `survey_region` does its own PIL crop/downscale rather than calling the generic `crop_and_read`
   path), downscale that crop if needed, call `vlm()` on it, translate crop-relative normalized bboxes
   into full-page pixel space using the crop's own pixel offset and size.
4. `crop_and_read(document_id, bbox_pixel, question, page_num=1)`: resolve the page path, call
   `src.providers.image_cv.crop(page_path, bbox_pixel)` → get a cropped-image path from its
   `ToolResult.data`, then call `src.providers.vlm_azure.vlm(cropped_path, question)` → return the
   answer plus a `Grounding(bbox=bbox_pixel, page=page_num-1, source_tool="crop_and_read")`.
5. `ocr_page(document_id, page_num=1)`: resolve the page path, call `src.providers.ocr_tesseract.ocr`;
   if `result.ok` is False, fall back to `src.providers.vlm_azure.vlm(page_path, TRANSCRIBE_PROMPT)` and
   set a `warning` key.

**Alternatives rejected**
- Routing `survey_layout`/`survey_region`'s downscale through `src/providers/image_cv.py::resize`: that
  provider writes a file and returns a `ToolResult`, more ceremony than an in-memory PIL resize before
  one temp save needs (spec Assumptions).
- Having `survey_region` call `crop_and_read`/`crop()` for its own internal crop: would route a
  provider-level call through another provider call for no benefit; a direct PIL crop is simpler and
  matches ade2's own structure.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Failing tests first (red), with a small real fixture PNG | `src/tests/test_engine_tools.py` | AC1-AC7 | tests fail (no module yet) |
| T2 | `src/engine/tools.py`: page resolution + survey_layout + survey_region | `src/engine/tools.py` | AC1, AC2, AC5, AC6, AC7 | tests pass |
| T3 | `crop_and_read` + `ocr_page` (provider wrappers) | `src/engine/tools.py` | AC3, AC4 | tests pass |

## Data, API and migration impact

None — new, inert module; nothing calls it yet.

## Security and failure modes

No new attack surface: `document_id`/`page_num` only ever resolve through `DocumentStore`'s own path
logic (already hardened), never a raw filesystem path from the caller.

## Rollout and rollback

Merge; revert to undo. No migration, no runtime behavior change.

## Risks and open points

- Coordinate-conversion correctness (normalized ↔ pixel, crop-relative ↔ full-page) is the main risk;
  AC1/AC2 test it against hand-computed expected values, not just "a value came back."
