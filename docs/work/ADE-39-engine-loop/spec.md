# ADE-39 — Engine: the loop itself (pydantic-ai agent wiring ADE-34 to ADE-38 together)

Status: spec-approved · Risk: high · Jira: ADE-39
Created: 2026-10-05 · Slug: engine-loop

Part of the ADE-30 vertical slice (`docs/work/ADE-30-engine-vertical-slice/spec.md`). Depends on ADE-34
(skill loader), ADE-35 (budget), ADE-36 (validation), ADE-37 (history), ADE-38 (perception tools) — all
merged. This is the story that turns five inert modules into one running agent.

## Problem

`src/engine/` has five modules that nothing calls each other yet: a skill loader, a budget tracker, a
validator, a history store, and perception tools. ade2 has exactly this wiring in `src/ade2/agent.py` —
a framework-run tool loop (pydantic-ai) rather than a hand-authored state machine, a thin system prompt
the agent plans its own approach from, and `@agent.tool` wrappers that record budget cost before
delegating to the real tool. That design is what ADE-30 approved porting; this story is the port.

## Users and context

Grounded in reading ade2's `src/ade2/agent.py` in full (the reference design) and ade's own
`src/engine/skills.py`, `budget.py`, `validation.py`, `history.py`, `tools.py` (ADE-34–38, this story's
direct inputs), `src/documents/store.py::DocumentStore.get_document()/get_page_path()`, and
`src/config.py::settings` (Azure credentials, already used by `src/providers/vlm_azure.py`).

Two differences from ade2's design, both forced by decisions already made in earlier stories:

1. **Pixel-space bboxes, not normalized.** ADE-38's `survey_layout`/`survey_region`/`crop_and_read` take
   and return pixel-space `BBox` tuples (ade's own convention), never ade2's bare normalized
   `[ymin,xmin,ymax,xmax]` floats. ade2's system prompt and tool docstrings describe normalized
   coordinates throughout — this story's system prompt and tool docstrings must say pixel space instead,
   or the agent will pass the wrong kind of number to ADE-38's tools.
2. **No real DEXPI/SPICE serializers yet.** ade2's `to_dexpi_xml`/`to_spice_netlist` call
   `ade2.dexpi.serialize_to_dexpi_xml`/`ade2.spice.serialize_to_spice_netlist` — real serializers with a
   matching `parse_dexpi_xml` for round-trip validation. ADE-14 (DEXPI 1.3/Proteus 4.1.1 export+import)
   and ADE-16 (SPICE netlist exporter) are the tickets that will build ade's equivalents, and neither has
   landed. ade's existing `src/tools/graph/serialization.py::_serialize_dexpi` is NOT that: it is a
   simplified, home-grown XML shape (its own `<DEXPI>` tag names, not the real DEXPI/Proteus schema) built
   for the old LangGraph graph's node/edge shape, not ade2's richer P&ID shape (separate valves/
   instruments/off_page_connectors arrays, nozzles, loop numbers). Bridging the two shapes well enough to
   round-trip correctly is exactly ADE-14/16's job, not this story's — reusing it here would produce
   output that *looks* like it round-trips but silently drops fields ADE-14 hasn't been asked to handle
   yet. Per ADE-30's spec Assumptions ("stub cleanly if they haven't landed"), `to_dexpi_xml`/
   `to_spice_netlist` are clean stubs here: a structured `{"error": "...", "dexpi_xml": None}` naming the
   blocking ticket, never an exception, never a half-correct XML string.

## Goals and non-goals

**Goals**
- One new module, `src/engine/agent.py`: `ExtractionState` (deps dataclass), a thin system prompt, and
  `build_agent()` returning a pydantic-ai `Agent` with every ADE-34–38 module wired as a tool.
- Every perception/validation/serialization tool records its budget cost (via
  `ctx.deps.budget.record_tool(name)`, using the exact tool-name keys `budget.py`'s `TOOL_TURNS`/
  `TOOL_COST_USD` already anticipate) before delegating to the real function.
- `validate_extraction` combines schema conformance (ADE-36), skill invariants (ADE-36), and ade2's
  P&ID-specific completeness/thinness heuristics (empty-collection and valve/edge-density checks) — all
  of which work today, independent of DEXPI. A `dexpi_xml` key, if present, gets only a well-formedness
  check (`xml.etree.ElementTree.fromstring`), not the full round-trip entity-count comparison ade2 does
  (that needs ADE-14's parser).
- `build_agent(model=None)`: accepts an optional pre-built pydantic-ai `Model` so tests (and, later,
  eval harnesses) can inject a scripted `FunctionModel`/`TestModel` instead of a real Azure client. When
  `model` is omitted, builds the real `AzureProvider`/`OpenAIChatModel` from `src.config.settings`,
  mirroring `vlm_azure.py`'s existing credential wiring — no new way of reading Azure credentials.
- `pydantic-ai` added as a new dependency, scoped to an optional-dependencies group (not pulled into
  every existing install path) per the owner's approval on ADE-30.

**Non-goals**
- Real DEXPI/SPICE serialization (ADE-14, ADE-16) — stubbed here, not implemented.
- Wiring this agent to any FastAPI endpoint, or touching `src/agent/`, `src/skills/`, or any existing
  API route — this module is importable and testable but unreachable from the running app until ADE-32
  (switch the API) after ADE-31's head-to-head evaluation.
- A real end-to-end run against a live document and a live Azure model — that proof is ADE-40's job
  (the P&ID digitizer skill content + end-to-end vertical-slice proof), once there is a skill to load.

## Requirements

- R1. `ExtractionState` dataclass: `document_id: str = ""`, `skill_id: str = ""`,
  `todo: list[dict[str, str]]`, `validations: list[dict[str, Any]]`,
  `budget: BudgetTracker` (default-factory, so each run gets its own tracker and clock).
- R2. `build_agent(model: Model | None = None) -> Agent[ExtractionState, str]`: builds (or accepts) the
  model, constructs a pydantic-ai `Agent` with `deps_type=ExtractionState`, `output_type=str`, the system
  prompt below, and registers every tool in R3–R9. Building the real Azure model must stay lazy — the
  module itself must be importable with no Azure credentials set (AC3), matching `vlm_azure.py`'s own
  lazy client.
- R3. Perception tools (`@agent.tool`, each records its budget cost under the tool name used as the key
  into `budget.py`'s `TOOL_TURNS`): `list_document_pages` (wraps `DocumentStore.get_document`),
  `survey_layout_tool`, `survey_region_tool`, `crop_and_read_tool`, `ocr_page_tool` (wrap ADE-38's
  `src.engine.tools` functions of the same name minus `_tool`). Docstrings describe bboxes as
  **pixel-space** `(x1, y1, x2, y2)`, not normalized.
- R4. `budget_status` (`@agent.tool`, free): returns `ctx.deps.budget.status()` without recording a cost
  (free per `budget.py`'s own `TOOL_TURNS["budget_status"] = 0` and ade2's "FREE — use liberally" design).
- R5. `update_plan` (`@agent.tool`, free): records tool cost (`"update_plan"`, 0 turns per `TOOL_TURNS`),
  sets `ctx.deps.todo = tasks`, returns the plan plus a `{completed, in_progress, pending}` summary.
- R6. `validate_extraction` (`@agent.tool`, free): records cost; builds a result combining:
  - schema conformance via `validate_output` (ADE-36) when the loaded skill has a schema;
  - invariants via `validate_invariants` (ADE-36) when the loaded skill has invariants — `checked`/
    `violated`/`could_not_check` all surfaced to the agent, `could_not_check` never silently dropped;
  - completeness: any of `nodes`/`valves`/`instruments`/`edges`/`off_page_connectors` present in `data`
    but empty is an error (ported from ade2, modality-independent — these keys only exist in P&ID-shaped
    data in the first place);
  - thinness: valve-count and edge-count ratios against equipment count, as warnings (ported from ade2);
  - a `dexpi_xml` key, if present: a well-formedness check only (not a round-trip comparison), and a
    missing-key warning when `skill.modality == "graph_digitization"` and no `dexpi_xml` is present yet.
  Appends the result to `ctx.deps.validations` and returns it.
- R7. `to_dexpi_xml` / `to_spice_netlist` (`@agent.tool`, each records its own tool-name cost): clean
  stubs. Each returns `{"error": "<serializer not available yet (ADE-14|ADE-16)>", "dexpi_xml": None}`
  (or `spice_netlist`) — never raises, never fabricates XML.
- R8. `list_skills` / `load_skill` (`@agent.tool_plain`, no state, no budget cost — matches ade2): wrap
  ADE-34's `list_skills()`/`load_skill()`; `load_skill` returns `{"error": "..."}` for an unknown id
  rather than `None` (tool-plain functions can't return `None` meaningfully to the model).
- R9. System prompt: documents every tool above and a suggested working sequence (survey, check budget,
  re-survey dense regions, read, validate, serialize, validate again, return) without injecting any
  skill's `probe_order` — skill knowledge is loaded via `load_skill` at runtime, not baked into the system
  prompt (ADE-12's rule, carried through ADE-34's `to_prompt_block`). Explicitly states bboxes are pixel
  space.
- R10. `pyproject.toml`: new `[project.optional-dependencies]` group (e.g. `engine`) adding `pydantic-ai`,
  resolved and lock-updated via `uv add --optional engine pydantic-ai`; not added to the unconditional
  `dependencies` list.

## Acceptance criteria

(Numbered to match the Jira ticket's own AC1–AC6; this spec's requirements map onto them as noted.)

- AC1. `build_agent()` returns a pydantic-ai `Agent` with every ADE-34/35/36/37/38 module reachable as a
  tool — a framework-run tool loop, not a hand-authored LangGraph state machine. (R2, R3–R8)
- AC2. The system prompt documents the tool catalogue and a suggested working sequence but does not
  inject any skill's `probe_order`. (R9)
- AC3. `import src.engine.agent` succeeds with no Azure credentials set, and the full existing suite
  (`pytest src/tests/`) is unchanged by this story's diff — `src/agent/`, `src/skills/`, and every
  existing API route are untouched; the new engine is importable and testable but not reachable from any
  existing endpoint. (R2)
- AC4. A tool-call failure (bad VLM JSON from ADE-38, a validation error, a serializer stub) returns a
  structured error the agent sees and can act on, never an exception that crashes the run. (R3, R6, R7)
- AC5. Hermetic integration test: the model call is mocked (a scripted sequence of tool calls via
  pydantic-ai's `FunctionModel`/`TestModel`), proving the loop actually drives tool calls — including a
  `validate_extraction` call — through to a final answer. No live Azure/LLM credentials needed. (R2)
- AC6. `pyproject.toml` gets `pydantic-ai` added narrowly (an optional-dependencies group), not as a hard
  dependency pulled into every existing install path. (R10)

## Edge cases and failure modes

- `load_skill_tool` called with an unknown skill id: `{"error": "Skill '<id>' not found"}`, never `None`
  (R8).
- `validate_extraction` called before any skill was loaded (`ctx.deps.skill_id` empty): schema/invariant
  checks are skipped (nothing to check against), but completeness/thinness checks still run against
  whatever keys `data` happens to contain.
- `to_dexpi_xml`/`to_spice_netlist` called with any input: always the same clean stub result regardless
  of `data`'s shape — there is nothing to validate yet because there is no serializer (R7).
- `update_plan` called with a malformed `tasks` list (missing `status` key on an item): `.get("status")`
  already guards this in the summary count (ported from ade2's own defensive `.get`), so a missing key
  just doesn't count toward any bucket rather than raising.

## Non-functional requirements

- Observability: `logger = logging.getLogger(__name__)`; `build_agent()` logs at INFO when building the
  real Azure-backed model (deployment + endpoint, never the API key); `validate_extraction` logs at INFO
  with error/warning counts (not raw data — may contain extracted document content).
- This story does not touch `src/engine/history.py` directly (no run-loop orchestration — "start a run,
  record events, complete a run" is a caller's job, not the agent's); `ExtractionState` and the agent are
  the pieces a future caller (ADE-40, then ADE-32) wires to `history.py`.

## Assumptions

- `DocumentStore.get_document(doc_id)` (already exists, `src/documents/store.py`) is ade's equivalent of
  ade2's `ingest.list_pages()` — page count and per-page dimensions. Reused directly, no new store method.
- The real Azure model construction (`AzureProvider`/`OpenAIChatModel`) mirrors
  `vlm_azure.py::_get_client()`'s existing settings usage (`settings.azure_api_key`,
  `settings.azure_chat_endpoint`, `settings.azure_chat_deployment`) rather than inventing a second way to
  read Azure credentials.
- `pydantic-ai`'s exact pinned version is resolved by `uv add` at implementation time; this spec does not
  pin a version number itself.

## Risks and dependencies

- Risk: **high** — the first story where all five prior engine modules are exercised together, the first
  new third-party dependency in `src/engine/`, and the first place an incorrect bbox-space assumption
  (pixel vs. normalized) would silently produce wrong crops if the system prompt or a tool docstring says
  the wrong thing.
- Depends on: ADE-34, ADE-35, ADE-36, ADE-37, ADE-38 (all merged). Blocks: ADE-40 (P&ID skill content +
  end-to-end proof — needs a real agent to run), and eventually ADE-31 (head-to-head evaluation).
