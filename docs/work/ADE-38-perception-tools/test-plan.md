# ADE-38 — Test plan: perception tools

Status: implementing · Risk: medium · Jira: ADE-38

Test framework and conventions found: pytest, `monkeypatch` to replace provider functions
(`src.providers.vlm_azure.vlm`, `src.providers.image_cv.crop`, `src.providers.ocr_tesseract.ocr`) at the
module boundary `src.engine.tools` imports them through, a small real PNG fixture written to a temp
`DocumentStore`-shaped directory via `monkeypatch` on `get_document_store`; command
`uv run pytest src/tests/ -v -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_engine_tools.py::test_survey_layout_converts_normalized_to_original_pixel_space | zone bbox matches hand-computed pixel values against the real (non-downscaled) image size | n/a | n/a | planned |
| AC2 | unit | ::test_survey_region_translates_crop_relative_to_full_page_pixels | element bbox matches hand-computed full-page pixel values | n/a | n/a | planned |
| AC3 | unit | ::test_crop_and_read_calls_the_real_providers, ::test_ocr_page_calls_the_real_ocr_provider | mocked `crop`/`vlm`/`ocr` called with expected args | n/a | n/a | planned |
| AC4 | unit | ::test_ocr_page_falls_back_to_vlm_when_tesseract_unavailable | n/a | n/a | `ocr()` returns ok=False -> `vlm()` used, warning present | planned |
| AC5 | unit | ::test_missing_document_or_page_returns_structured_error_not_an_exception | n/a | n/a | nonexistent document_id/page_num -> `{"error": ...}` for every tool, no exception | planned |
| AC6 | unit | ::test_malformed_vlm_json_returns_empty_list_not_a_crash | n/a | n/a | non-JSON VLM response -> empty zones/elements, no crash | planned |
| AC7 | unit | (all above) | real small PNG fixture, providers mocked, no network/Azure/Tesseract | n/a | n/a | planned |

## Regression risk

None — new module, nothing else imports it yet.

## Untestable AC

None.

## Manual checks

None.

## Audit (after implementation)

<!-- Filled after implementation. -->
