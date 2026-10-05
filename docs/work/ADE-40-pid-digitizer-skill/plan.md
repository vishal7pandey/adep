# ADE-40 — Plan: P&ID digitizer skill content + end-to-end proof

Status: plan-approved · Risk: medium · Jira: ADE-40
Created: 2026-10-05 · Slug: pid-digitizer-skill · Spec: spec.md

## Summary

One new skill directory (`skills/pid-dexpi-digitizer/{SKILL.md,schema.json}` — the first skill ever
ported to the new engine, `skills/` doesn't exist yet) and one new integration test
(`src/tests/test_pid_skill_e2e.py`) proving `build_agent()` actually runs end to end against a real
document. **Size: M.**

## Current state

- `skills/` does not exist in the repo at all (confirmed: `ls skills/` → no such directory). ADE-34's
  `list_skills()`/`load_skill()` already handle a missing `SKILLS_DIR` gracefully (return `[]`/`None`),
  so creating the directory is purely additive.
- `sample-data/pid-diagrams/` has 6 real files, no `.expected.json` for any of them.
  `sample-pid-01.jpg` is smallest (254 KB, 2201×1614 JPEG).
- `src/documents/store.py::DocumentStore.import_document(file_path)` already handles JPEG import
  (via PIL, converts to PNG, generates a thumbnail) — reused as-is, no changes.
- `src/engine/agent.py::validate_extraction`'s completeness check already looks for exactly
  `nodes`/`valves`/`instruments`/`edges`/`off_page_connectors` keys (ADE-39) — this skill's
  `schema.json` must use the same names or the two would silently disagree.

## Approach

1. `skills/pid-dexpi-digitizer/SKILL.md`: frontmatter (`name`, `description`, `modality:
   graph_digitization`, `visual_cues`, `document_aliases`, `probe_order`, `invariants` per spec R1/R3)
   plus a short markdown body (what this skill reconstructs, what the output shape is) — written fresh
   from ade2's reference content, not copy-pasted (ADE-12's rule).
2. `skills/pid-dexpi-digitizer/schema.json`: JSON Schema per spec R2, field names matching ade2's
   reference and ADE-39's completeness check.
3. `src/tests/test_pid_skill_e2e.py`:
   - Import `sample-data/pid-diagrams/sample-pid-01.jpg` via a real `DocumentStore` pointed at a
     `tmp_path` base dir (never the real `.adep/`, matching every other engine test's isolation).
   - `engine_skills.load_skill("pid-dexpi-digitizer")` against the *real* `skills/` directory (not
     monkeypatched — this is the one test in the whole engine suite that intentionally exercises the
     real repo-root `skills/` path, since proving the real file parses is the point) — assert it
     returns a `Skill` with `schema is not None` and 4 invariants.
   - `build_agent(model=FunctionModel(script))` where `script` returns, in order: a
     `survey_layout_tool` call, a `validate_extraction` call with a small fixed dict satisfying
     `schema.json` (one node, one edge, both required fields present), a `to_dexpi_xml` call, then a
     final text answer. `survey_layout`'s own VLM call is monkeypatched (same ADE-38 boundary every
     other engine test already uses) so the test touches zero network/Azure.
   - Assert: the call sequence happened in order, `validate_extraction`'s result is `valid: True`
     (schema + all 4 invariants pass for the fixed extraction), `to_dexpi_xml`'s result matches ADE-39's
     documented stub shape exactly (`error` names ADE-14, `dexpi_xml` is `None`).
4. PR body: a "Run standalone" section naming the exact pytest node id (per spec R5/AC4).

**Alternatives rejected**
- Scoring the real image with a real VLM call: no ground truth exists yet (ADE-15), so there's nothing
  to score against; would also need live Azure credentials, breaking this test's hermeticity for no
  benefit this story can use.
- Porting ade2's two free-text invariants (DEXPI-class validity, nozzle connectivity) by inventing a
  sixth ADE-36 operator just for them: over-engineering for two checks with no second user yet; the
  spec explicitly drops them (R3) rather than force-fitting or faking verification.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Failing test first (red): assert the skill loads and the agent reaches validate_extraction | `src/tests/test_pid_skill_e2e.py` | AC1-AC4 | test fails (no `skills/` dir yet) |
| T2 | Skill content | `skills/pid-dexpi-digitizer/SKILL.md`, `schema.json` | AC1, AC2 | test's load_skill assertions pass |
| T3 | Confirm the full pipeline assertion passes | (no new files — T1's test, now green) | AC3 | test passes |

## Data, API and migration impact

None — `skills/` is new, read-only reference data; nothing in `src/` changes. The test writes only to
`tmp_path`, never `.adep/`.

## Security and failure modes

No new attack surface: the test imports a file already committed to the repo (`sample-data/`), through
`DocumentStore`'s existing, already-hardened import path. No new runtime code.

## Rollout and rollback

Merge; revert to undo (deletes the skill directory and the test). No migration.

## Risks and open points

- If `sample-pid-01.jpg`'s real pixel dimensions ever exceed `DocumentStore`'s decompression-bomb guard
  (100M pixels) this would fail loudly, not silently — not a risk in practice (2201×1614 ≈ 3.5M pixels).
