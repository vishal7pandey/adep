# ADE-15 — P&ID scoring: count recall and label precision against DEXPI ground truth

Status: approved · Risk: medium · Jira: ADE-15
Created: 2026-10-05 · Slug: pid-scoring

## Problem

ade has no way to say how good a P&ID extraction is. Its generic benchmark suite compares field values, which does not fit a graph of equipment, valves, instruments and piping, and the existing expected files are not trustworthy (ADE-10). The only prior evidence, from the ade2 prototype, was six noisy single runs. Without a trustworthy yardstick, ADE-31 (old engine against new engine) and every later change to the P&ID skill are decided by feel.

## Users and context

The maintainer and agents deciding whether the new engine (`src/engine/`, ADE-30) matches the old one (ADE-31, which gates ADE-32 and ADE-33). Ground truth is the DEXPI reference P&IDs: a Proteus XML file (the model) plus an SVG rendering (the text on the drawing). Those files are third-party material (DEXPI e.V.) and must not be committed here; they are fetched on demand.

## Goals and non-goals

**Goals:** two metrics with clear meaning, no model and no network needed to compute them, usable by any engine's output.
**Non-goals:** running an engine (ADE-31), DEXPI export (ADE-14), changing either engine, fixing ADE-10's expected files.

## Requirements

- R1. **Count recall** per category (equipment/nodes, valves, instruments, off-page connectors, piping segments/edges) against the Proteus XML: `min(found, truth) / truth`; categories with zero truth are reported as "not applicable", not as 1.0. **Over-extraction** `max(0, found - truth) / truth` is reported separately so a flood of guesses cannot look like recall.
- R2. **Label precision** against the SVG text: of the tags the extraction reports (nodes, valves, instruments), the fraction that are actually printed on the drawing. This catches hallucinated tags.
- R3. **Tag normalisation** makes the same physical label compare equal across sources: case, whitespace, separators and unicode superscripts are ignored ("SV 104.01" equals "sv104.01"). An instrument tag also matches when its letter run and number run appear as separate labels on the drawing (bubbles print "PI" and "4712.01" separately).
- R4. Ground truth is loaded from a reference directory given by the environment variable `ADE_DEXPI_REF_DIR` (or an argument). Missing directory or missing files give a clear message and an empty list, never a crash, and nothing from that directory is ever copied into the repo.
- R5. A helper renders a reference SVG to a PNG (for feeding an engine), using PyMuPDF which is already a dependency.
- R6. Output is a plain data object (per-category recall and over-extraction, label precision, counts found and expected) that serialises to JSON.

## Acceptance criteria

- AC1. Count recall is correct for fewer, equal and more found than truth, and "not applicable" when truth is zero; over-extraction is reported separately.
- AC2. Label precision is 1.0 for tags all on the drawing, drops for invented tags, and treats a tag whose parts appear as separate labels as present.
- AC3. Normalisation treats case, spaces, `-`, `/`, `.` and unicode superscripts as equivalent, and does not treat different tags as equal.
- AC4. Ground truth parsing of a hand-authored Proteus-style XML and SVG yields the expected counts and label set; a real reference file, when `ADE_DEXPI_REF_DIR` points at one, parses without error (manual check recorded in the PR, not a test that needs the files).
- AC5. With no reference directory configured, discovery returns an empty list with an explanatory message.
- AC6. SVG-to-PNG produces a non-empty PNG for a small SVG.
- AC7. All new tests are hermetic: no model, no network, no DEXPI file in the repo; the existing suite is not made worse.

## Edge cases and failure modes

An extraction with missing categories or non-dict items is scored as zero found, not an error. Malformed XML or SVG raises a clear error naming the file. Duplicate tags in an extraction count once for label precision but each item counts for recall.

## Non-functional requirements

No new dependency. No file under `sample-data/` or the reference directory is modified.

## Assumptions

- A1. Category mapping from DEXPI: equipment = `Equipment` elements; valves = components whose class ends in `Valve`; instruments = `ProcessInstrumentationFunction`; off-page connectors = `PipeOffPageConnector`; edges = `PipingNetworkSegment`. Checked against the three reference files by a one-off manual count.
- A2. The new skill's output shape (lists `nodes`, `valves`, `instruments`, `off_page_connectors`, `edges`, items with a `tag`) is the scorer's input shape; the old engine is mapped onto it by the ADE-31 adapter.

## Risks and dependencies

The licence of the reference material is unconfirmed: that is why nothing is committed. Depends on nothing; used by ADE-31.

## Open questions

None.
