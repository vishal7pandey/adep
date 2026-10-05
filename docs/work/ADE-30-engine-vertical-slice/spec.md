# ADE-30 — Land the ade2 engine beside the old one (first vertical slice)

Status: draft · Risk: high · Jira: ADE-30
Created: 2026-10-05 · Slug: engine-vertical-slice

## Problem

ade's extraction engine (`src/agent/`, a hand-built LangGraph state machine — `graph.py` 1,666 +
`oneflow.py` 607 lines, 6,942 lines across 20 files) and its 24 Python skill classes (2,755 lines,
scripted `probe_order`, 48 invariant functions) are expensive to extend: a new document type needs a new
Python class, registration, and tests. The owner confirmed (ADE-13, 2026-10-05) a strangler migration to
a design proven in the `ade2` prototype: a framework-run tool loop instead of a hand-built graph, skills
as markdown+schema data instead of Python classes, and a small perception toolbox exposed directly as
agent tools. Nothing of the old engine is deleted until a head-to-head evaluation (ADE-31) shows the new
one matches or beats it — this ticket only has to prove the new design works on one real skill, side by
side with the old engine, changing nothing the API already serves.

## Users and context

Internal: whoever runs extractions through ade's API, today served exclusively by `src/agent/`. This
ticket adds a second, inert path; no end user is affected until ADE-32 (a separate, gated ticket) switches
the default. Grounded in:
- `src/agent/` (the current engine) and `src/skills/` (the 24 Python skill classes) — read to confirm scope and line counts above.
- `src/tools/base.py` — ade's existing contracts: `BBox` (pixel-space `(x1,y1,x2,y2)`), `Grounding` (every
  extracted value traces to a bbox + page + source tool — a stricter invariant than ade2 has), `RegionType`.
- `src/providers/vlm_azure.py` (`vlm()`, `read_table()`, `read_chart()`), `src/providers/ocr_tesseract.py`
  (`ocr()`), `src/providers/image_cv.py` (`crop()`, `deskew()`, ...) — ade's existing perception primitives,
  all returning ade's `ToolResult` type. None of these exist in ade2; they are reused, not reimplemented.
- `src/documents/store.py` (`DocumentStore`, `DocumentMeta`) — ade's existing per-document page/manifest
  store, the counterpart to ade2's `ingest.py`.
- The full `ade2` source (owner-provided, 2026-10-05, concatenated single file covering all 14 backend
  modules, 94 skills, tests, eval scripts) — read in full. What follows about ade2 is from reading that
  source directly, not from the earlier Confluence summary (that source is a later, partially-hardened
  snapshot: CORS/auth/rate-limit/path-traversal are already fixed there, contradicting the stale audit
  text embedded in the same file — don't re-flag those).
- ADE-12 (migration epic), ADE-13 (decision, confirmed), the Confluence decision record.

## Goals and non-goals

**Goals**
- Prove the ade2 design — a framework-run tool loop, progressive disclosure, skills as data — works
  inside ade's actual codebase, reusing ade's existing perception providers and grounding model, not
  ade2's.
- Ship one skill (the P&ID DEXPI digitizer) running end-to-end on the new engine against a real sample
  document, so ADE-31 has something concrete to put next to the old engine.
- Leave the old engine and the live API completely unaffected.

**Non-goals**
- Porting all 94 ade2 skills (that's ADE-18, gated on this slice proving out) or even all 24 of ade's
  current skills.
- Switching any real traffic to the new engine (ADE-32, gated on ADE-31).
- Fixing ade2's known defects *in ade2* — they are simply not carried over (see Edge cases).
- A new VLM/OCR/crop implementation — `src/providers/` already has these; reuse them.
- DEXPI/SPICE serialization logic itself (ADE-14, ADE-16 own that; this ticket calls whatever exists,
  stubbing if ADE-14 hasn't landed yet — see Open questions).

## Requirements

- R1. A new `src/engine/` package runs a tool-calling loop driven by a framework (pydantic-ai, matching
  ade2's proof of the design) rather than a hand-authored state graph.
- R2. The loop exposes perception tools backed by ade's existing providers: `vlm()` (crop_and_read
  equivalent), `ocr()`, `crop()` — plus two tools that are genuinely new to ade, ported from ade2:
  `survey_layout` (VLM-based semantic zone detection over a downscaled page) and `survey_region`
  (re-survey a sub-region at native resolution for dense symbols).
- R3. A skill loader reads `skills/<id>/SKILL.md` (YAML frontmatter + markdown hints) and
  `skills/<id>/schema.json`, with zero Python required per skill, following ade2's format.
- R4. The loop reasons about a budget (turns/cost/time) the way ade2's `budget.py` does, ported with the
  same public shape (`Budget`, `BudgetTracker.status()`), since it's generic and not one of ade2's flagged
  defects.
- R5. Every extracted value keeps ade's existing grounding guarantee (`src/tools/base.py::Grounding`):
  the new engine's tools return pixel-space bboxes tied to page and source tool, not ade2's bare
  normalized-coordinate dicts.
- R6. The old `src/agent/` engine, its skills, and the live API routes are not modified by this ticket.
  The new engine is importable and testable but not reachable from any existing endpoint.
- R7. Validation against a skill's schema and invariants happens with a real expression evaluator or
  explicit per-field checks declared in the skill's frontmatter — not keyword matching on free-text
  descriptions (ade2's `schema.py::_check_invariant` does the latter; ADE-12 already flags it as a defect
  not to copy).
- R8. The SQLite-backed run history (ade2's `history.py` pattern: durable record of each run's steps) is
  ported without the global `threading.Lock` serializing every write — a per-call connection (SQLite's
  default) inside `asyncio.to_thread` is enough; WAL mode if concurrent writers become a real issue.

## Acceptance criteria

- AC1. (R1, R6) `import src.engine` succeeds and `pytest src/tests/` (the full existing suite) still
  passes unchanged — nothing in `src/agent/`, `src/skills/`, or `src/api/routes/` is touched by this
  ticket's diff.
- AC2. (R2, R5) Unit tests exercise `survey_layout` and `survey_region` against a fixture image with the
  VLM call mocked, asserting: zones/elements come back with pixel-space bboxes (not ade2's normalized
  0.0–1.0 floats), and `survey_region`'s elements are translated into the *page's* pixel space, not the
  crop's.
- AC3. (R2) `crop_and_read`, `ocr_page` tools in the new engine call `src/providers/vlm_azure.vlm()` and
  `src/providers/ocr_tesseract.ocr()` directly — proven by a test that monkeypatches those provider
  functions and asserts the engine tool called them, not a reimplementation.
- AC4. (R3) A skill loader test reads a real `skills/<id>/SKILL.md` + `schema.json` pair (the P&ID
  digitizer skill, added by this ticket under `skills/pid-dexpi-digitizer/`) and returns parsed
  frontmatter, hints body, and schema; a missing `schema.json` returns a skill with `schema=None` rather
  than raising.
- AC5. (R4) A budget test proves turns/cost accounting matches ported behaviour: N recorded perception
  calls reduce `remaining_turns`/`remaining_cost_usd` by the expected amount; `status()` returns at least
  one recommendation string once turns drop below the ported low-budget threshold.
- AC6. (R7) A validation test proves a genuinely broken invariant (e.g. an empty required array) is
  caught by a real field check, and that an invariant whose target field is absent from the data is
  reported as "could not be checked" rather than silently "passed" — the false-positive gap ADE-12 flags
  is closed, not reproduced.
- AC7. (R8) A concurrency test runs N≥10 simulated writes to the run-history store concurrently (via
  `asyncio.gather` over the async wrappers) and asserts all N rows are present afterward, with no test
  asserting on or requiring a single global lock.
- AC8. (Goal) An integration test runs the full new-engine loop against one real sample P&ID image from
  `sample-data/pid-diagrams/` with the LLM call mocked to return a small, fixed valid extraction, and
  asserts the mocked tool-call sequence reaches a `validate_extraction` call before any final answer.
- AC9. (Failure path) With the mocked model returning malformed JSON from `crop_and_read`, the loop does
  not crash: the tool returns a structured error the agent can see and continue from, matching ade's
  existing `_safe_tool`-style contract rather than propagating an unhandled exception.

## Edge cases and failure modes

- ade2's known defects are deliberately NOT reproduced: the keyword-matching invariant checker (R7), the
  global SQLite lock (R8), ade2's bare `except Exception` guess-and-retry around the VLM's
  `max_completion_tokens` vs `max_tokens` parameter name (worth a narrower except in the port, logged,
  not silent), and ade2's hand-rolled schema validation in parallel with an unused native-structured-output
  path (`agent.py` sets `output_type=str` while pydantic-ai supports typed output — pick one; recommend
  native structured output via `schema.json`, since ade2 itself drifted away from its own stated design
  here, per its own `AUDIT.md`'s "Other Findings").
- A skill directory with a `SKILL.md` but malformed `schema.json`: load as a skill with `schema=None` and
  log a warning, matching ade2's own handling — do not crash the loader for one bad skill.
- Azure VLM call timeout/5xx: must propagate as a real tool error (visible to the agent and to logs), not
  be silently retried and masked (ade2's `_vlm_call` already does this correctly for all but the
  param-name-guess case — keep that narrow exception, don't broaden it).
- Running with no sample documents or no Azure credentials: the hermetic test suite (AC2–AC7, AC9) must
  pass regardless; only AC8 needs a real sample image (already committed under `sample-data/`) and a
  mocked model.

## Non-functional requirements

- Security: no new attack surface in this ticket — the new engine has no HTTP route yet (R6). When ADE-32
  eventually wires one, the `/uploads`-style path-traversal guard ade2 already has (and ade's own
  equivalent) must be carried over; out of scope here.
- Observability: every new-engine tool call and validation result is logged (`logging.getLogger(__name__)`
  per module), matching the standard this repo just established for `chatpid` (CPID-15) and expected here.

## Assumptions

- Pydantic-ai is an acceptable new dependency for this one package (autonomy policy requires asking before
  adding a dependency — flagging it here explicitly rather than assuming silent approval; see Open
  questions).
- The P&ID digitizer is the right first skill (not invoice, bank-statement, or utility-bill): it's the one
  skill ADE-15 is already building ground truth and an evaluation harness for, so ADE-31 has a real
  evaluation to run against this slice immediately, not just a smoke test.
- ADE-14 (DEXPI export) may not have landed yet when this ticket is implemented; if so, `to_dexpi_xml` is
  stubbed to return a clearly-marked placeholder rather than blocking this ticket on ADE-14's timeline —
  AC8's integration test does not require real DEXPI output, only that the loop reaches validation.

## Risks and dependencies

- **Risk: high**, per the header, because: (a) it adds a new runtime dependency (pydantic-ai) and a new
  package that other tickets (ADE-31 through ADE-33) build directly on top of — mistakes here propagate;
  (b) it's the first concrete code of a multi-month architecture migration, so the patterns set here
  (how skills load, how grounding works, how budget is reasoned about) are hard to change later without
  re-touching everything downstream.
- Depends on: nothing blocking (the source blocker is resolved). Soft dependency on ADE-14/ADE-15 for a
  *complete* P&ID round-trip, handled via the stub in Assumptions.
- Blocks: ADE-31 (head-to-head evaluation needs this slice to exist), ADE-32, ADE-33.

## Open questions

1. Adding `pydantic-ai` as a dependency: the autonomy policy says ask first. Recommended answer: yes,
   scoped to `src/engine/`'s own extras/optional group if `pyproject.toml` supports that, so it's not a
   hard dependency of the parts of ade that don't use the new engine yet.
2. Should the new engine's tools be registered under `src/engine/tools.py` (mirroring ade2's module name)
   or under `src/tools/` next to the existing providers (mirroring ade's own layout)? Recommended answer:
   `src/engine/tools.py` containing only the two *new* tools (`survey_layout`, `survey_region`) plus thin
   wrappers calling `src/providers/`'s existing functions — keeps the new engine's tool surface in one
   file (matching ade2's own tools.py, which the agent system prompt documents closely), without moving
   or duplicating ade's existing provider code.
