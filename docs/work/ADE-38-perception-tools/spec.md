# ADE-38 — Engine: perception tools (survey_layout/survey_region, wired to ade's providers)

Status: spec-approved · Risk: medium · Jira: ADE-38
Created: 2026-10-05 · Slug: perception-tools

Part of the ADE-30 vertical slice (`docs/work/ADE-30-engine-vertical-slice/spec.md`). Independent of the
other engine stories. This is the one story that touches real image/VLM code rather than pure logic.

## Problem

The new engine needs to let the agent survey a page for semantic zones, re-survey a sub-region at native
resolution for dense symbols, crop-and-ask the VLM about a region, and OCR a page. ade2 has all four as
self-contained functions that open their own Azure client and shell out to Tesseract directly. ade
already has working `vlm()`, `ocr()`, `crop()` providers (`src/providers/`) with retries, error handling,
and a stricter grounding model — re-implementing the Azure/Tesseract calls would duplicate working code
and lose that grounding.

## Users and context

The new engine's agent loop (ADE-39), which wires these as `@agent.tool` functions. Grounded in reading
ade2's `src/ade2/tools.py` in full (the reference design for `survey_layout`/`survey_region`) and ade's
own `src/providers/vlm_azure.py::vlm()`, `src/providers/image_cv.py::crop()`,
`src/providers/ocr_tesseract.py::ocr()`, `src/tools/base.py::ToolResult`/`Grounding`/`BBox`, and
`src/documents/store.py::DocumentStore.get_page_path()` (1-indexed, raises `FileNotFoundError` rather
than returning `None`).

## Goals and non-goals

**Goals**
- `survey_layout`/`survey_region`: genuinely new to ade (VLM-based zone/symbol detection over a
  downscaled-then-native-resolution image), ported from ade2's design.
- `crop_and_read`/`ocr_page`: thin wrappers that call ade's existing `crop()`/`vlm()`/`ocr()` providers —
  not a reimplementation of the Azure or Tesseract calls.
- Every tool returns pixel-space bboxes tied to page and source tool (ade's `Grounding`), never ade2's
  bare normalized-coordinate dicts — the VLM is asked for normalized coordinates internally (resolution
  independence), but the function's own return value is always converted to pixel space before it
  leaves the module.
- `ocr_page` falls back to a VLM transcription (via `vlm()`) when Tesseract is unavailable, with an
  explicit warning saying so — ade's own `ocr()` provider returns `ok=False` and stops there; this
  module adds the fallback ade2 had.

**Non-goals**
- Reimplementing the Azure OpenAI client or the Tesseract call — those stay in `src/providers/`.
- Changing `src/providers/` or `src/tools/base.py` in any way.
- Wiring these as actual `@agent.tool` functions — that's ADE-39's job; this story exposes plain
  functions the agent loop will wrap.

## Requirements

- R1. `survey_layout(document_id, page_num=1)`: loads the page image via `DocumentStore.get_page_path`,
  downscales to a max dimension (1024px) for the VLM call, asks the VLM (via `vlm()`) for a JSON array of
  semantic zones with normalized `[ymin, xmin, ymax, xmax]` bboxes, converts each to pixel space against
  the *original* (non-downscaled) image dimensions before returning.
- R2. `survey_region(document_id, bbox_pixel, page_num=1)`: crops the given pixel bbox from the native
  image via `crop()`, surveys only that crop (downscaled to 1024px if the crop itself is larger) with a
  symbol-focused prompt, translates each returned element's bbox from crop-relative to full-page pixel
  space before returning.
- R3. `crop_and_read(document_id, bbox_pixel, question, page_num=1)`: crops via `crop()`, then calls
  `vlm()` on the cropped image with `question`; returns the answer plus a `Grounding` for the bbox given.
- R4. `ocr_page(document_id, page_num=1)`: calls `ocr()` on the full page; if it fails (e.g. Tesseract
  not installed), falls back to `vlm()` with a transcription prompt on the full page and includes a
  `warning` key explaining the fallback and its lower fidelity.
- R5. Every tool's return value includes a `Grounding`-shaped location for anything it reports (page is
  0-indexed internally per `src/tools/base.py::Grounding.page`, converted from the public 1-indexed
  `page_num`).
- R6. Malformed or non-JSON VLM output for `survey_layout`/`survey_region` does not crash the tool: it
  returns a structured error result (`{"error": ..., "zones"/"elements": []}`), same contract as a
  missing page or an empty crop.
- R7. `DocumentStore.get_page_path`'s `FileNotFoundError` (unlike ade2's `None`-returning
  `get_page_path`) is caught at this module's boundary and turned into the same structured
  `{"error": "..."}` result shape every other failure uses — never left to propagate as an exception.

## Acceptance criteria

- AC1. `survey_layout` with the VLM mocked to return a normalized-bbox JSON array: the returned zones'
  bboxes are pixel values consistent with the *original* image's width/height, not the downscaled
  working image's.
- AC2. `survey_region` with a given pixel bbox and the VLM mocked to return crop-relative normalized
  elements: the returned elements' bboxes are in full-page pixel space (verified against a known
  translation by hand for at least one element).
- AC3. `crop_and_read` and `ocr_page` call `src.providers.image_cv.crop`, `src.providers.vlm_azure.vlm`,
  `src.providers.ocr_tesseract.ocr` directly — proven by monkeypatching those exact functions and
  asserting they were invoked with the expected arguments, not a parallel reimplementation.
- AC4. `ocr_page` with `ocr()` mocked to return `ok=False`: the result's `text` comes from a mocked
  `vlm()` call instead, and a `warning` key explains the fallback.
- AC5. A document id / page number that doesn't exist (the `DocumentStore` raises `FileNotFoundError`):
  every tool in this module returns `{"error": "..."}` rather than letting the exception propagate.
- AC6. A VLM response that isn't valid JSON for `survey_layout`/`survey_region`: the tool returns an
  empty `zones`/`elements` list plus an `error` or equivalent note, not a crash.
- AC7. Hermetic tests: `vlm()`/`ocr()`/`crop()` mocked at the provider boundary, a small real fixture
  image written to a temp `DocumentStore`-shaped directory, no network, no live Azure/Tesseract.

## Edge cases and failure modes

- `survey_region`'s given bbox is degenerate (zero width/height after int rounding): return a structured
  error before calling `crop()` at all (matches `crop()`'s own "empty region" check, but catching it
  earlier avoids a wasted provider call).
- The VLM returns a JSON array but some elements are missing a `bbox` key: skip that element rather than
  crashing the whole response (log and continue).

## Non-functional requirements

- Observability: `logger = logging.getLogger(__name__)`; a VLM/OCR failure that triggers a fallback or
  returns an error logs at WARNING; a successful survey logs at INFO/DEBUG with counts (not raw VLM
  responses — may contain extracted document content).

## Assumptions

- Image dimensions are read directly via `PIL.Image.open(path).size` in this module — ade's providers
  don't expose a dedicated "get image size" helper, and this is a one-line, side-effect-free read.
- The downscale-for-overview logic (max 1024px) is this module's own code (small, ~10 lines), not routed
  through `src/providers/image_cv.py::resize` — that provider writes a new file and returns a
  `ToolResult` path, more machinery than a one-off in-memory resize before a temp save needs; revisit if
  a second caller needs the same downscale logic.

## Risks and dependencies

- Risk: medium — the first story that calls real provider code (even though every test mocks it) and
  defines how pixel/normalized coordinate conversion works for every future skill.
- Depends on: nothing hard (works with ade's already-merged providers). Used by: ADE-39 (wraps these as
  `@agent.tool` functions), ADE-40 (the P&ID skill's extraction loop calls these tools in practice).
