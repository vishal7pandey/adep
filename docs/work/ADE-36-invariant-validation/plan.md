# ADE-36 — Plan: schema and invariant validation

Status: plan-approved · Risk: medium · Jira: ADE-36
Created: 2026-10-05 · Slug: invariant-validation · Spec: spec.md

## Summary

One new module, `src/engine/validation.py`. The JSON-Schema half is a direct port of ade2's
`_validate_node`/`_check_type`/`validate_output` (read in full). The invariant half is new: a fixed
5-operator vocabulary dispatch table replacing ade2's keyword-matching `_check_invariant`. **Size:** M.

## Current state

- `src/engine/` has `skills.py` (ADE-34) and `budget.py` (ADE-35); this story adds a sibling module, no
  changes to either.
- `src/agent/validator.py::Invariant` (ade's existing Python-callable model) is untouched — this story
  does not replace it, it's a separate, parallel model for the new data-driven skills.
- Commands: `uv run pytest src/tests/ -v -m "not integration"`, `uv run ruff check src/`,
  `uv run ruff format src/`.

## Approach

1. `validate_output(answer_json, schema)` / `_validate_node` / `_check_type` / `_strip_code_fence` —
   ported close to verbatim from ade2's `schema.py` (this half already had no defect).
2. `validate_invariants(data, invariants)` — new. For each invariant dict, dispatch on `check` to one of:
   `_check_non_empty`, `_check_balance_equals`, `_check_sum_equals`, `_check_all_rows_have`,
   `_check_tolerance_range`. Each takes `(data, invariant)` and returns one of three outcomes
   (`CHECKED`, `VIOLATED` with a message, `COULD_NOT_CHECK` with a reason) — a tri-state result object,
   not a bare bool, so the caller can tell "verified and fine" apart from "couldn't verify" without
   re-deriving it.
3. Field resolution is a plain `data.get(field_name)` — no recursive search, no dotted paths (per spec
   Non-goals; ade's skills and the P&ide shape are flat). An operator whose named field is missing or the
   wrong type returns `COULD_NOT_CHECK`, never raises.
4. Unknown `check` name -> `COULD_NOT_CHECK` naming the operator, via a dispatch-table `.get()` with a
   fallback, not a raised `KeyError`.

**Alternatives rejected**
- A general expression evaluator (parse `"a + b == c"` style strings): more general than any real skill
  needs right now, and re-introduces a parsing surface that could silently fail the same way ade2's regex
  did. The fixed vocabulary is explicit and each operator's success/failure is directly testable.
- Dotted-path field resolution now: no current skill needs it; adding it later is a small, additive
  change to the one `_get_field` helper, not a redesign.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Failing tests first (red) | `src/tests/test_engine_validation.py` | AC1-AC9 | tests fail (no module yet) |
| T2 | JSON-Schema validation (ported) | `src/engine/validation.py` | AC1 | tests pass |
| T3 | Invariant operator vocabulary + dispatch | `src/engine/validation.py` | AC2-AC8 | tests pass |

## Data, API and migration impact

None — new, inert module. This is also the first place the invariant *declaration shape* for the new
skill format is fixed; ADE-40's P&ID skill will declare its invariants in exactly this shape.

## Security and failure modes

None beyond what's in the spec (missing fields / wrong types / unknown operators degrade to
`COULD_NOT_CHECK`, never raise, never silently pass).

## Rollout and rollback

Merge; revert to undo. No migration, no runtime behavior change (nothing calls this module yet).

## Risks and open points

- The 5-operator vocabulary is a judgment call on "enough for now" (spec Assumptions); if ADE-40's P&ID
  invariants need a 6th operator, add it there in a small diff rather than redesigning this module.
