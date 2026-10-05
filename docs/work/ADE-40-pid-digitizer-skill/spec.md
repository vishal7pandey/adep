# ADE-40 — Engine: P&ID digitizer skill content + end-to-end vertical-slice proof

Status: spec-approved · Risk: medium · Jira: ADE-40
Created: 2026-10-05 · Slug: pid-digitizer-skill

Part of the ADE-30 vertical slice (`docs/work/ADE-30-engine-vertical-slice/spec.md`). The proof-of-life
story: the first real skill content, and the test proving ADE-39's engine actually runs end to end.
Depends on ADE-39 (merged). Soft-depends on ADE-14/ADE-15 (both still To Do — stubbed per ADE-30's
Assumptions, same as ADE-39 already did for serialization).

## Problem

`src/engine/` has a working skill loader (ADE-34) and a working agent loop (ADE-39), but `skills/` does
not exist in the repo yet — there is no domain knowledge for the agent to load, and nothing has ever
exercised the full `build_agent()` → tool-call loop against a real document. This story adds both: one
skill directory and one integration test that drives the real engine against a real sample image.

## Users and context

Grounded in reading ade2's `skills/pid-dexpi-digitizer/SKILL.md` + `schema.json` in full (the reference
content and shape) and ade's own `src/engine/skills.py` (ADE-34's frontmatter format), `src/engine/
validation.py` (ADE-36's five structured invariant operators), `src/engine/agent.py` (ADE-39's
`validate_extraction`/`to_dexpi_xml` stub), and `sample-data/pid-diagrams/` (6 real P&ID
images/PDFs, none with an `.expected.json` ground truth file — ADE-15, which would add one, is still To
Do).

ADE-12's rule applies here as much as anywhere: port the *knowledge* (visual cues, document aliases,
what fields to extract, what must be true of the output), not ade2's files verbatim, and re-author the
invariants into ADE-36's structured shape rather than ade2's free-text-plus-keyword-matching one.

## Goals and non-goals

**Goals**
- `skills/pid-dexpi-digitizer/SKILL.md`: frontmatter in ADE-34's format (name, description, modality
  `graph_digitization`, visual_cues, document_aliases, probe_order, invariants) plus a markdown body
  describing the output shape.
- `skills/pid-dexpi-digitizer/schema.json`: the P&ID graph shape (`header`, `nodes`, `valves`,
  `instruments`, `off_page_connectors`, `edges`, `dexpi_xml`) — the same field names ade2's reference
  schema and ADE-39's `validate_extraction` completeness check already assume, since ADE-14/ADE-15
  haven't landed to check against instead (spec Assumptions, matches ADE-30's own rule for this exact
  situation).
- Invariants re-authored into ADE-36's five-operator shape: `non_empty` (nodes, edges must not be
  empty) and `all_rows_have` (every node needs `tag`+`type`; every edge needs `from_id`+`to_id` — the
  same fields `schema.json` already marks `required`, so a malformed node/edge fails both checks, not
  just one).
- One integration test that imports a real file from `sample-data/pid-diagrams/` through
  `DocumentStore`, builds the real engine (`build_agent()`) with a scripted `FunctionModel` standing in
  for the LLM (no real Azure/VLM calls — there is no ground truth to score against yet, so this proves
  the *pipeline* runs end to end, not extraction accuracy), and asserts the tool-call sequence reaches
  `validate_extraction` with a clean result for the fixed extraction, and that `to_dexpi_xml` behaves
  exactly as its documented stub (a clearly-labeled "not available yet" result, never a silently wrong
  answer) since ADE-14 hasn't landed.
- The PR documents the exact command to run this slice standalone, so ADE-31's future head-to-head
  evaluation knows where to point.

**Non-goals**
- Real extraction accuracy against a real document — there is no ground truth file for any
  `sample-data/pid-diagrams/` image yet (ADE-15's job). This story proves the pipeline runs, not that
  it extracts correctly.
- ADE-14 (real DEXPI export) or ADE-15 (evaluation ground truth) — both stay stubbed/absent.
- Wiring this skill or the engine to any FastAPI endpoint (ADE-32's job, after ADE-31).
- A second skill, or a general skill-authoring guide — one skill, proving the loader+agent+validation
  chain works for real content.

## Requirements

- R1. `skills/pid-dexpi-digitizer/SKILL.md` frontmatter: `name: pid-dexpi-digitizer`, a `description`
  stating what it's for and explicitly what it's NOT for (ade2's own convention, kept — it disambiguates
  skill selection), `modality: graph_digitization`, `visual_cues` (P&ID symbols, process lines, off-page
  connectors), `document_aliases` ("P&ID to DEXPI", "P&ID Digitization", etc.), `probe_order` (5 steps:
  title block, equipment/nozzles, valves, instruments, off-page connectors/piping — kept as ADE-34-format
  metadata; never rendered into the agent's prompt, per ADE-34's own guarantee), `invariants` in ADE-36's
  shape (R3).
- R2. `skills/pid-dexpi-digitizer/schema.json`: JSON Schema (draft-07, matching ADE-36's
  `validate_output`'s supported feature set — `type`, `properties`, `required`, `items`) for `header`
  (object), `nodes`/`valves`/`instruments`/`off_page_connectors`/`edges` (arrays of objects), `dexpi_xml`
  (string). `nodes` items require `id`/`tag`/`type`; `edges` items require `id`/`from_id`/`to_id`
  (matches ade2's reference and ADE-39's own completeness-check field names).
- R3. Invariants (SKILL.md frontmatter, ADE-36 shape — `{name, check, fields, ...}`):
  - `nodes_non_empty`: `check: non_empty`, `fields: [nodes]`.
  - `edges_non_empty`: `check: non_empty`, `fields: [edges]`.
  - `all_nodes_have_tag_and_type`: `check: all_rows_have`, `fields: [nodes]`, `require: [tag, type]`.
  - `all_edges_have_endpoints`: `check: all_rows_have`, `fields: [edges]`, `require: [from_id, to_id]`.
  (ade2's own two free-text invariants — "equipment types map to valid DEXPI classes" and "nozzles
  connect to pipe routes" — don't fit any of ADE-36's five operators and would need keyword-matching to
  express, the exact pattern ADE-36 was built to avoid; they're dropped rather than faked. The general
  valve/edge-density thinness heuristic ade2 also had is already covered generically, for any skill, by
  ADE-39's `validate_extraction` — not re-declared here.)
- R4. One integration test (`src/tests/test_pid_skill_e2e.py`): imports a real file from
  `sample-data/pid-diagrams/` via `DocumentStore.import_document`, calls `engine_skills.load_skill
  ("pid-dexpi-digitizer")` to confirm the real skill parses, builds the real `build_agent()` with a
  scripted `FunctionModel` (one `survey_layout_tool` call, then a `validate_extraction` call with a
  small fixed valid extraction matching `schema.json`, then a final text answer), and asserts: the skill
  loads without error, the tool-call sequence reaches `validate_extraction`, that result is `valid:
  True` for the fixed extraction, and a `to_dexpi_xml` call (scripted as a third tool call) returns the
  documented stub shape (`{"error": "...ADE-14...", "dexpi_xml": None}`), not a crash or a fabricated
  XML string.
- R5. PR description states the exact command to run this test standalone (for ADE-31's benefit).

## Acceptance criteria

(Numbered to match the Jira ticket's own AC1–AC4.)

- AC1. `SKILL.md` describes modality, visual cues, document aliases, domain hints, and structured
  invariants in ADE-34/ADE-36's formats. (R1, R3)
- AC2. `schema.json` matches the P&ID graph shape ADE-14/ADE-15 already assume (`header`, `nodes`,
  `valves`, `instruments`, `off_page_connectors`, `edges`) — confirmed neither has landed, so ade2's
  reference shape is used as-is rather than invented fresh. (R2)
- AC3. An integration test runs the full engine against one real sample image, with the LLM mocked to
  return a small fixed valid extraction, and asserts the tool-call sequence reaches
  `validate_extraction` with a clean result, and that the `to_dexpi_xml` stub behaves as ADE-30/ADE-39's
  spec says (clearly marked placeholder, not a silent wrong answer) since ADE-14 hasn't landed. (R4)
- AC4. The PR states exactly how to invoke this slice standalone. (R5)

## Edge cases and failure modes

- `load_skill("pid-dexpi-digitizer")` must return a real `Skill` with a non-`None` `schema` and
  non-empty `invariants` — if `schema.json` is missing or malformed, ADE-34's loader already degrades to
  `schema=None` with a logged warning rather than crashing; the test confirms schema is actually
  present, not just that loading didn't raise.
- The fixed extraction used in the test must itself satisfy `schema.json`'s `required` fields and all
  four invariants — the test is a proof the pipeline runs clean end to end, not a test of
  `validate_extraction`'s error paths (ADE-39's own test suite already covers those).

## Non-functional requirements

- No new logging conventions — this story adds data (a skill directory) and one test, no new code paths
  in `src/engine/` itself.

## Assumptions

- `schema.json`'s field names mirror ade2's reference and ADE-39's existing `validate_extraction`
  completeness-check keys (`nodes`, `valves`, `instruments`, `edges`, `off_page_connectors`) because
  ADE-14/ADE-15 haven't landed to check against instead; if either lands with different field names
  before this story merges, this skill's schema is updated to match them, not the other way around.
- No `sample-data/pid-diagrams/*.expected.json` ground-truth file exists for any image yet (confirmed:
  `ls sample-data/pid-diagrams/*.expected.json` finds none) — AC3's test therefore uses a scripted,
  hand-written fixed extraction rather than a real VLM read scored against ground truth; that scoring is
  explicitly ADE-31's job, once ADE-15 exists.
- `sample-pid-01.jpg` (the smallest file in `sample-data/pid-diagrams/`, 254 KB / 2201×1614) is the
  document AC3's test imports — picked for test speed, not for any content property; any of the six
  would equally prove the pipeline runs.

## Risks and dependencies

- Risk: medium — the first real skill content (wrong frontmatter shape would silently degrade, per
  ADE-34's own graceful-degradation design, rather than fail loudly) and the first test that touches
  `DocumentStore.import_document` on a real multi-megapixel image from this story's own suite (import
  cost, not correctness risk).
- Depends on: ADE-39 (merged). Soft depends on: ADE-14, ADE-15 (both stubbed/absent, as ADE-30's spec
  anticipated). Enables: ADE-31 (head-to-head evaluation — this story's PR names the standalone command
  ADE-31 needs).
