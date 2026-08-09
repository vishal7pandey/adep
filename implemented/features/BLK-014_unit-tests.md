---
id: BLK-014
type: feature
title: "Unit tests — full pytest suite with mocked providers"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-013]
tags: [tests, quality, v1-slice]
---

## Description

Complete the pytest suite covering all Phase 1 components. All tests use
mocked providers — no external API calls. Deterministic tests only [NFT].

## Acceptance Criteria

- [ ] Tool registry tests (existing — verify still pass)
- [ ] State + trace compaction tests (existing — verify still pass)
- [ ] Validator tests (existing — verify still pass)
- [ ] Provider tests with mocks (PaddleOCR, Tesseract, Azure VLM, OpenCV)
- [ ] ReAct graph integration test with mocked LLM + tools
- [ ] End-to-end invoice extraction test with mocked providers
- [ ] Give-up cap termination test
- [ ] All tests pass in CI

## Constraints

- Mocked providers only — no real API calls in tests [TS]
- Deterministic tests — no flaky tests [NFT]

## Dependencies

- BLK-013 (run() entry point — needed for e2e test)

## Notes

- vision.md §8 (guiding constraints: pytest with mocked providers)
