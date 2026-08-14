---
id: BLK-276
type: tech-debt
title: "requirements.txt pins three overlapping OpenCV builds and has grown to ~3,000 lines"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T10:30:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [dependencies, requirements, opencv, bloat, ops]
---

## Description

`requirements.txt` is ~2,990 lines and pins all three OpenCV distributions simultaneously:

```
opencv-contrib-python==5.0.0.93
opencv-python==5.0.0.93
opencv-python-headless==5.0.0.93
```

All three provide the same `cv2` import namespace and are mutually redundant/conflicting when installed together — only one is actually importable at a time in practice (`import cv2` is used in `src/providers/image_cv.py`, `src/tools/signature_detection.py`, `src/tools/table_detection.py`, and their tests; nothing distinguishes which variant it expects). Installing all three wastes install time/disk and risks silently picking whichever one's files land last on `sys.path`, which is a real source of "works on my machine" bugs.

The file also pulls in PaddleOCR, Tesseract bindings, an Azure VLM client, scikit-image, the full `transformers`/`tokenizers`/`safetensors` stack, SQLAlchemy, and the complete LangChain/LangGraph ecosystem — a large surface for a project whose original scope (per `notebooks/L2.ipynb`-`L9.ipynb`) was a single-course ReAct extraction agent. That broader scope question is a product decision (tracked narratively in the audit, not itself a ticket), but the concrete, unambiguous bug here is the triple OpenCV pin.

## Acceptance Criteria

- [ ] Pick exactly one OpenCV variant based on actual need (`opencv-python-headless` is almost always correct for a server-side/no-GUI backend like this one) and remove the other two
- [ ] Confirm `cv2`-importing modules (`image_cv.py`, `signature_detection.py`, `table_detection.py`) still work after narrowing to one variant
- [ ] Re-run `pip install -r requirements.txt` in a clean venv and confirm no `cv2`-related import errors
- [ ] Document in the PR how much install size/time this saves

## Constraints

- Verify no code path actually needs the GUI-enabled variant (`opencv-python`) or the `contrib` extras (`opencv-contrib-python`) before removing them — grep for any `cv2.xfeatures2d`, `cv2.imshow`, or other contrib/GUI-only APIs first
- This is a narrow, low-risk cleanup; don't scope-creep into a full dependency audit unless the user asks for that separately

## Dependencies

- `requirements.txt`
- `src/providers/image_cv.py`, `src/tools/signature_detection.py`, `src/tools/table_detection.py`

## Notes

- Found via full-repo audit (`ADE_codebase_audit.md`, §7); confirmed still present as of 2026-08-09 (`grep -c` shows all three still pinned at the same version)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T10:30 (mgmt)**: Logged after confirming all three OpenCV variants are still pinned and `cv2` is imported without variant-specific APIs in the three call sites checked.
