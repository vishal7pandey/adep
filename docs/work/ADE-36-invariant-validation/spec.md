# ADE-36 — Engine: schema and invariant validation (real checks, not keyword matching)

Status: spec-approved · Risk: medium · Jira: ADE-36
Created: 2026-10-05 · Slug: invariant-validation

Part of the ADE-30 vertical slice (`docs/work/ADE-30-engine-vertical-slice/spec.md`). This story exists
specifically to NOT reproduce ade2's worst flagged defect.

## Problem

ade2's `src/ade2/schema.py::_check_invariant` matches an invariant's free-text `description` against
hardcoded keyword patterns (e.g. `"rpn" in desc_lower and "s * o * d" in desc_lower`) to pick a
sub-checker, then runs a regex against that same free text to pull out field names. When the keyword
matches but the regex doesn't fire, the invariant is reported as checked-and-passed even though nothing
was actually verified — a silent false positive, acknowledged in ade2's own test comments. ADE-12
explicitly flags this as not to port.

ade's *current* invariant model (`src/agent/validator.py::Invariant`) has the opposite problem for this
migration: it's a Python callable (`fn: InvariantFn`), which is exactly the "write Python per skill"
overhead the migration is trying to remove. Neither existing design is usable as-is for a YAML-frontmatter
skill.

## Users and context

The new engine's `validate_extraction` tool (ADE-39), and every skill's `SKILL.md` frontmatter (loaded by
ADE-34). Grounded in reading ade2's `schema.py` in full (both the part worth keeping — recursive
JSON-Schema validation — and the part that isn't) and ade's own `src/agent/validator.py::Invariant`
(confirms ade's current model requires a Python function per invariant, which SKILL.md frontmatter cannot
express).

## Goals and non-goals

**Goals**
- Keep ade2's recursive JSON-Schema validator (`validate_output`/`_validate_node`/`_check_type`) — it has
  no keyword-matching problem and is a safe, direct port.
- Replace ade2's free-text invariant checker with structured invariants: a skill declares `{"check":
  "<operator>", "fields": [...]}` in its frontmatter instead of a free-text description for a regex to
  guess at. A small, fixed vocabulary of check operators, each resolving its named fields by real lookup.
- Three-state result per invariant: checked-and-passed, checked-and-violated, or could-not-be-checked
  (a named field is absent from the data) — the last state is never silently counted as passed.

**Non-goals**
- A general expression language (arbitrary arithmetic/boolean expressions over field paths) — a small
  fixed operator vocabulary covering what ade's current skills and ADE-15's P&ID ground truth actually
  need (see Requirements) is enough for this slice; extend the vocabulary later if a real skill needs an
  operator that doesn't exist yet.
- Porting ade's existing `src/agent/validator.py::Invariant` (Python-callable) model itself — that stays
  as-is for the 24 existing Python skills, untouched by this story.
- Nested/dotted field paths beyond one level (e.g. `header.total`) — the skills this slice targets
  (P&ID, and ade's existing simple schemas) use flat top-level array/scalar fields; add dotted-path
  resolution later if a skill actually needs it.

## Requirements

- R1. `validate_output(answer_json, schema)` does recursive JSON-Schema validation (type checking,
  required fields, nested objects/arrays) exactly as ade2's does — ported with no behavior change, since
  this half has no keyword-matching problem.
- R2. Invariants are declared as structured dicts, not free prose: `{"name": str, "check": <operator>,
  "fields": [str, ...], **operator_specific_kwargs}`.
- R3. A fixed operator vocabulary, each resolving named top-level fields by direct dict lookup (not regex
  on a description):
  - `non_empty`: the one named field (a list) must have at least one element.
  - `balance_equals`: four named fields `[start, increase, decrease, end]`; `start + increase - decrease
    == end` (within a small float tolerance).
  - `sum_equals`: N named fields where the sum of all but the last equals the last (within tolerance).
  - `all_rows_have`: one named array field; every element (dict) must have a truthy value for every key
    in a `require` list.
  - `tolerance_range`: one named array field; for every row whose `result_field` (default `"result"`)
    equals `"PASS"` (case-insensitive), `min_field <= value_field <= max_field` must hold.
- R4. `validate_invariants(data, invariants)` returns, per invariant: `checked` (passed, no violation),
  `violated` (with a violation message), or `could_not_check` (a named field is missing from `data` or
  not the expected type) — three disjoint lists, never conflating "missing" with "passed".
- R5. An unknown `check` operator name is treated as `could_not_check` with a message naming the unknown
  operator, not a silent pass and not a crash.

## Acceptance criteria

- AC1. (R1) `validate_output` on a schema with nested objects and required fields: a conforming payload
  returns `valid=True`, `errors=[]`; a payload missing a nested required field returns the specific
  missing-field path in `errors`.
- AC2. (R3, R4) `non_empty` on an empty array -> violated, with a message naming the field; on a
  non-empty array -> checked (passed).
- AC3. (R3, R4) `balance_equals` on `{"opening": 100, "deposits": 50, "withdrawals": 30, "closing":
  120}` -> checked (100+50-30=120); on `closing=121` -> violated with the arithmetic shown in the message.
- AC4. (R3, R4) `sum_equals` on `{"subtotal": 80, "tax": 8, "total": 88}` -> checked; on `total=90` ->
  violated.
- AC5. (R3, R4) `all_rows_have` on a `nodes` array where every dict has a non-empty `tag` -> checked; on
  one row with `tag=""` or missing -> violated, naming the row index.
- AC6. (R3, R4) `tolerance_range` on a `characteristics` array where a `PASS` row has
  `measured_value` outside `[tolerance_min, tolerance_max]` -> violated; a `PASS` row within range ->
  checked; a non-`PASS` row outside range -> not counted as a violation (only `PASS` rows are checked,
  matching the real-world meaning: a FAIL row is expected to be out of tolerance).
- AC7. (R4, R5) An invariant naming a field absent from `data` -> `could_not_check`, never silently
  counted as passed — this is the exact false-positive gap ADE-12 flags against ade2, closed here.
- AC8. (R5) An invariant with `check: "no_such_operator"` -> `could_not_check` with a message naming the
  unknown operator; does not raise.
- AC9. Hermetic unit tests, no network, no LLM.

## Edge cases and failure modes

- A field value of the wrong type for its operator (e.g. `non_empty` on a field that's a string, not a
  list) -> `could_not_check`, not a crash and not a silent pass.
- `balance_equals`/`sum_equals` with a non-numeric value in any named field -> `could_not_check`.
- `all_rows_have` where the named array itself is empty -> `could_not_check` (nothing to check — distinct
  from `non_empty`'s own job of flagging an empty array; a skill wanting both declares both invariants).

## Non-functional requirements

- Observability: `logger = logging.getLogger(__name__)`; a violation logs at WARNING, a could-not-check
  logs at DEBUG (routine, not every skill names every field).

## Assumptions

- The five operators in R3 cover what ade's existing sample-data skills and ADE-15's P&ID ground truth
  need (confirmed by reading ade2's own invariant descriptions for bank-statement, FAIR/tolerance tables,
  and the P&ID node/edge checks — the same real-world checks this migration is porting the *capability*
  of, not the free-text-matching *mechanism*). A skill needing a sixth operator adds it to this module in
  its own small PR when that skill is actually written, rather than speculatively building more now.

## Risks and dependencies

- Risk: medium — this defines the invariant declaration shape every future skill's frontmatter depends
  on (including ADE-40's P&ID digitizer); a shape mistake here is more costly to fix later than in
  ADE-34/35's purer, more contained modules.
- Depends on: nothing hard (works against plain dicts in its own tests). Used by: ADE-39 (the engine
  loop's `validate_extraction` tool), ADE-40 (the P&ID skill's invariants are declared in this shape).
