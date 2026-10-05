# ADE-15 — P&ID scoring: count recall and label precision against DEXPI ground truth

Status: plan-approved · Risk: medium · Jira: ADE-15
Created: 2026-10-05 · Slug: pid-scoring · Spec: spec.md

## Summary

Add two small pure modules under `src/eval/`: ground truth loading and rendering, and scoring. No change to either engine. Size: S to M.

## Current state

- `src/eval/` already holds a generic suite (`accuracy.py`, `benchmark_suite.py`, `benchmarks.py`, `fixtures.py`, `harness.py`); none of it scores graphs or labels.
- PyMuPDF is already a dependency (`pyproject.toml`); it opens SVG and renders it.
- The new engine's P&ID skill schema (`skills/pid-dexpi-digitizer/schema.json`) defines the output lists the scorer reads.
- Reference files are outside this repo (`ADE_DEXPI_REF_DIR`); on this machine they exist read-only in the chatpid checkout's `data/dexpi_real/`.
- Commands: `.venv/Scripts/python.exe -m pytest src/tests/test_pid_*.py -q`.

## Approach

`src/eval/pid_ground_truth.py`: `GroundTruth` dataclass (`counts`, `labels`), `load_ground_truth(xml, svg)`, `reference_dir()`, `discover_references(dir)` returning `(references, message)`, `svg_to_png(svg, png, zoom)`.
`src/eval/pid_scoring.py`: `normalize_tag`, `tag_parts`, `score_extraction(extraction, gt) -> PidScore` (dataclass with `to_dict`).
Pure functions, standard library plus PyMuPDF for rendering. **Alternatives rejected:** F1 on object ids (the XML ids are not visible on the drawing so they cannot be matched); depending on pydexpi for parsing (a heavy new dependency for counting tags).

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | `normalize_tag`, `tag_parts` with tests | `src/eval/pid_scoring.py`, `src/tests/test_pid_scoring.py` | AC3 | unit tests |
| T2 | Count recall, over-extraction, label precision, `score_extraction` | same | AC1, AC2 | unit tests |
| T3 | Ground truth parser from Proteus XML and SVG | `src/eval/pid_ground_truth.py`, `src/tests/test_pid_ground_truth.py` | AC4 | tests on hand-authored XML/SVG |
| T4 | Reference discovery and `svg_to_png` | same | AC5, AC6 | tests with tmp dirs |
| T5 | Manual check on the three real reference files, recorded in the PR; full suite, ruff format | repo | AC4, AC7 | run output |

## Data, API and migration impact

None: new modules only, nothing imports them yet.

## Security and failure modes

Reads only files it is pointed at, never writes next to them; errors name the file; no network.

## Rollout and rollback

Merge the PR. Rollback: revert the commit.

## Risks and open points

Category mapping is a judgement (assumption A1) and is checked against real files by hand. Licence of the reference files: nothing is committed.
