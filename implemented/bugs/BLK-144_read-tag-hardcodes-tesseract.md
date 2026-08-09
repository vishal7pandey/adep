---
id: BLK-144
type: bug
title: "read_tag hardcodes tesseract OCR — ignores configured OCR provider"
priority: medium
status: backlog
phase: 4
owner: backend
created: 2026-08-08T14:45:00+05:30
estimate: S
tags: [backend, bug, graph-tools, ocr, config]
---

## Problem

`read_tag` in `src/tools/graph/tag_reading.py` hardcodes an import of
`ocr_tesseract` instead of using the configured OCR provider from
`settings.ocr_provider`. If the system is configured to use PaddleOCR
(the default), `read_tag` will still use Tesseract, which may not be
installed.

## Evidence

`src/tools/graph/tag_reading.py:126`:
```python
from src.providers.ocr_tesseract import ocr as _ocr_impl
```

The rest of the codebase uses a provider selection pattern:
- `src/run.py` builds the tool registry based on `settings.ocr_provider`
- `src/providers/ocr_paddle.py` and `src/providers/ocr_tesseract.py`
  both expose an `ocr()` function with the same interface

The config default is `ocr_provider: str = "paddle"` (config.py:46).

## Impact

- If PaddleOCR is the configured provider but Tesseract is not
  installed, `read_tag` will fail with an `ImportError` at runtime.
- Even if both are installed, using Tesseract when PaddleOCR is
  configured produces inconsistent OCR results — the tag reading tool
  uses a different engine than the rest of the pipeline.
- The tool is registered in `run.py` without indicating it has a
  hard dependency on Tesseract.

## Reproduction or reasoning

1. Set `ADE_OCR_PROVIDER=paddle` (or leave default).
2. Ensure Tesseract is not installed.
3. Call `read_tag(image_path, bbox)` — fails with ImportError.
4. Trace: `tag_reading.py:126` → `from src.providers.ocr_tesseract
   import ocr` → ModuleNotFoundError.

## Proposed resolution

Use the same provider selection pattern as `src/run.py`:

```python
from src.config import settings

def read_tag(image_path, bbox, **kwargs):
    if settings.ocr_provider == "tesseract":
        from src.providers.ocr_tesseract import ocr as _ocr_impl
    else:
        from src.providers.ocr_paddle import ocr as _ocr_impl
    # ... rest of function
```

## Acceptance criteria

- [ ] `read_tag` uses the configured OCR provider
- [ ] Works with both `paddle` and `tesseract` providers
- [ ] No hardcoded provider import at module level

## Validation plan

- Test with `ADE_OCR_PROVIDER=paddle` — should use PaddleOCR
- Test with `ADE_OCR_PROVIDER=tesseract` — should use Tesseract
- Test with Tesseract not installed and provider=paddle — should work

## Related issues

BLK-110 (graph extraction tools — this is part of that feature)
