# ADE-31 notes

## 2026-10-05: spec amended after approval (R8, assumptions, risks)

The approved spec assumed both engines could be compared with VLM-only perception. The first capped
smoke run (one run per engine, drawing C02V03, gpt-5.4-mini) disproved it for the old engine: with no
OCR provider its P&ID skill keeps calling `detect_layout`, which is not registered; five rejected
calls later it auto-pauses with nothing extracted (recall 0.0, 6k tokens). That would have measured
a missing tool, not the engine, so R8 now asks for each engine's native perception (old engine:
PaddleOCR via `--old-ocr paddle`). The new engine's behaviour is unchanged (its OCR tool falls back
to the VLM without Tesseract). Amended under the standing delegation; the change narrows nothing the
owner decided and is stated at the top of the Jira report.

## Eval environment (not the repo's own)

PaddleOCR needs `paddlepaddle`, which has no wheels for the repo's Python 3.14. The real comparison
runs in a throwaway Python 3.12 environment (`.venv312`, excluded locally via `.git/info/exclude`):
`UV_PROJECT_ENVIRONMENT=.venv312 uv sync --frozen --all-extras --python 3.12`, then
`uv pip install paddlepaddle==2.6.2 "numpy<2" "opencv-python<4.10" "opencv-python-headless<4.10" "opencv-contrib-python<4.10"`.
PaddleOCR 2.10 also needs two numpy aliases that numpy 1.26 lacks (`np.long`, `np.ulong`), applied by the
launcher before import. paddlepaddle 3.x fails on oneDNN (`fused_conv2d`), hence 2.6.2.
