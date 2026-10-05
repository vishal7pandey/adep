# ADE-38 — Test plan: perception tools

Status: in-review · Risk: medium · Jira: ADE-38

Test framework and conventions found: pytest, `monkeypatch` to replace provider functions
(`src.providers.vlm_azure.vlm`, `src.providers.image_cv.crop`, `src.providers.ocr_tesseract.ocr`) at the
module boundary `src.engine.tools` imports them through, a small real PNG fixture written to a temp
`DocumentStore`-shaped directory via `monkeypatch` on `get_document_store`; command
`uv run pytest src/tests/ -v -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_engine_tools.py::test_survey_layout_converts_normalized_to_original_pixel_space | zone bbox matches hand-computed pixel values against the real (non-downscaled) image size | n/a | n/a | verified |
| AC2 | unit | ::test_survey_region_translates_crop_relative_to_full_page_pixels | element bbox matches hand-computed full-page pixel values | n/a | n/a | verified |
| AC3 | unit | ::test_crop_and_read_calls_the_real_providers, ::test_ocr_page_calls_the_real_ocr_provider | mocked `crop`/`vlm`/`ocr` called with expected args | n/a | n/a | verified |
| AC4 | unit | ::test_ocr_page_falls_back_to_vlm_when_tesseract_unavailable | n/a | n/a | `ocr()` returns ok=False -> `vlm()` used, warning present | verified |
| AC5 | unit | ::test_missing_document_or_page_returns_structured_error_not_an_exception | n/a | n/a | nonexistent document_id/page_num -> `{"error": ...}` for every tool, no exception | verified |
| AC6 | unit | ::test_malformed_vlm_json_returns_empty_list_not_a_crash | n/a | n/a | non-JSON VLM response -> empty zones/elements, no crash | verified |
| AC7 | unit | (all above) | real PNG fixture (2000x1000, above `_MAX_SURVEY_DIM`), providers mocked, no network/Azure/Tesseract | n/a | n/a | verified |

## Regression risk

None — new module, nothing else imports it yet. Full suite: 1828 passed (1820 pre-existing + 8 new),
same 9 pre-existing unrelated failures as the clean-checkout baseline (ADE-23/24 and others per
`AGENTS.md`), no regressions.

## Untestable AC

None.

## Manual checks

None.

## Audit (after implementation)

Fixture note: the page fixture is 2000x1000 (deliberately above `_MAX_SURVEY_DIM = 1024`) so that
`survey_layout`'s downscaled working image and the original image have genuinely different
dimensions — a fixture at or below 1024px can't distinguish "converted against the original" from
"converted against the downscaled copy" (see M1 below).

Mutation testing (5 mutations against `src/engine/tools.py`, each applied, tested, then reverted and
confirmed byte-identical via `diff -q` against a backup):

| # | Mutation | Result |
|---|----------|--------|
| M1 | `survey_layout` computes `w, h` from the downscaled working image instead of the original | Caught (after strengthening the fixture to 2000x1000; see note above) |
| M2 | `survey_region` drops the crop's pixel offset `(x1, y1)` when translating crop-relative bboxes to full-page space | Caught |
| M3 | `crop_and_read` calls `vlm()` on the original page image instead of the cropped image | Caught |
| M4 | `ocr_page` always reports `engine="tesseract"`, even on the VLM fallback path | Caught |
| M5 | `_get_page_image_path` no longer catches `FileNotFoundError` | Caught |

All 5 mutations are caught by the test suite. M1 initially passed unchanged under the 200x100
fixture (both the original and downscaled image share one dimension once downscaling is a no-op),
which was a real test-coverage gap, not a passing result — fixed by widening the fixture past the
downscale threshold rather than by weakening the mutation.
