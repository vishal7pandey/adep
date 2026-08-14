---
id: BLK-209
type: tech-debt
title: "Test fixture sample PDF is not a real PDF — fake bytes bypass PyMuPDF in mocked tests, hiding real failures"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T12:20:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [testing, fixtures, pymupdf, test-quality, false-positive]
---

## Description

The `sample_pdf` fixture in `src/tests/test_e2e.py` creates a fake PDF:

```python
@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal fake PDF file for testing."""
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake pdf for testing\n%%EOF")
    return pdf_path
```

This is not a valid PDF — it's 32 bytes of fake header/footer text. PyMuPDF (`fitz`) cannot open it, which means any code path that tries to actually parse the PDF (like `run_pdf_fallback`) will fail. The mocked e2e tests work because they mock `build_tool_registry` and `build_react_graph`, bypassing any real PDF parsing.

## Problem Statement

- The fake PDF gives false confidence — tests pass because PDF parsing is mocked, but the fake PDF would cause `pymupdf.FileDataError` if any non-mocked code path tried to open it
- The integration tests (`TestE2ERealProviders`) use real sample PDFs from `sample-data/`, but those tests are skipped when providers aren't configured — so the fake PDF is the only one used in CI
- If someone accidentally removes a mock or changes the code path to call `run_pdf_fallback` without mocking, the test will fail with a confusing `pymupdf.FileDataError` instead of a clear assertion failure
- The previous session already noted `pymupdf.FileDataError` failures in `test_e2e.py` — this fake PDF is likely the root cause for any non-mocked test paths

## Acceptance Criteria

- [ ] Replace the fake PDF fixture with a minimal valid PDF (can be generated with PyMuPDF or checked in as a binary fixture)
- [ ] Alternatively, use a real sample PDF from `sample-data/` for all e2e tests (not just integration tests)
- [ ] Verify that non-mocked code paths (like `run_pdf_fallback`) can open the fixture without errors
- [ ] Add a comment explaining why a real (or valid minimal) PDF is necessary

## Constraints

- The fixture should be small (under 10KB) to avoid bloating the test suite
- If generating a PDF with PyMuPDF in the fixture, ensure PyMuPDF is available in the test environment

## Dependencies

- `src/tests/test_e2e.py` (`sample_pdf` fixture)
- Related to the `pymupdf.FileDataError` failures noted in the previous audit session

## Notes

- Found during full-repo audit; the fake PDF was likely created as a quick hack during initial test development and never replaced with a real fixture

## Implementation Log

- **2026-08-09T16:00 (mgmt)**: Reassigned from `cline` (mandate suspended, see projectmgmt/STATUS.md 2026-08-09 16:00 note) to `devin`. Test-code ownership for this file's domain reverts to the implementing team; independent verification now happens via cross-team review (devin<->antigravity) instead of a dedicated gate.

- **2026-08-09 (mgmt)**: Assigned to `cline` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
