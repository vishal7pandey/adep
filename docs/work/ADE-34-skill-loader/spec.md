# ADE-34 — Engine: skill loader (SKILL.md + schema.json as data)

Status: spec-approved · Risk: low · Jira: ADE-34
Created: 2026-10-05 · Slug: skill-loader

First story of the ADE-30 vertical slice (`docs/work/ADE-30-engine-vertical-slice/spec.md` has the full
migration context). No dependency on the other six stories.

## Problem

ade's current skills (`src/skills/`, 24 Python classes) require a new class, registration, and tests to
add a document type — the migration's whole point is to make that a two-file add instead. There is no
loader today for the data-driven format (`SKILL.md` + `schema.json`) the migration is adopting.

## Users and context

The new engine's agent loop (ADE-39) and its `list_skills`/`load_skill` tools. Grounded in reading ade2's
`src/ade2/skills.py` in full (the reference implementation) and ade's own layout: package root is `src`
(`pyproject.toml`: `packages = ["src"]`), tests live under `src/tests/`, and there is currently no
top-level `skills/` directory (confirmed — no collision with `src/skills/`, which stays untouched).

## Goals and non-goals

**Goals**
- A loader that reads a `skills/<id>/SKILL.md` (YAML frontmatter + markdown body) and an optional sibling
  `schema.json`, with zero Python needed to add a skill.
- Progressive disclosure: a cheap `list_skills()` (metadata only) and a full `load_skill(id)` (hints,
  schema, invariants).
- Deliberately omit `probe_order` from the agent-facing prompt rendering, so skills stay knowledge, not a
  script — carried over from ade2's design and ADE-12's explicit rule.

**Non-goals**
- Writing any actual skill content (ADE-40 adds the first real skill, the P&ID digitizer).
- Changing or touching `src/skills/` (the existing 24 Python classes) in any way.
- Validating the schema/invariants themselves (ADE-36's job) — this story only loads and hands them back.

## Requirements

- R1. `list_skills()` returns `id`, `name`, `description`, `modality`, `category`, `visual_cues`,
  `document_aliases` for every skill directory containing a `SKILL.md`, without reading the schema or the
  full markdown body.
- R2. `load_skill(skill_id)` returns a `Skill` object with `id`, `name`, `description`, `hints` (markdown
  body), `schema` (parsed `schema.json` or `None`), `modality`, `probe_order`, `invariants`, `ruleset`.
  Returns `None` for a nonexistent id.
- R3. A `schema.json` that fails to parse does not crash the loader: the skill still loads, `schema=None`,
  a warning is logged naming the skill id and the parse error.
- R4. `Skill.to_prompt_block()` renders description, domain knowledge (hints), invariants, and ruleset as
  a prompt-ready text block; `probe_order` is never included in this rendering.
- R5. Frontmatter parsing handles a UTF-8 BOM at the start of the file (some editors add one) and a file
  with no frontmatter at all (returns empty metadata, the whole file as body) without raising.

## Acceptance criteria

- AC1. (R1) Given three fixture skill directories (two with valid `SKILL.md`, one missing `SKILL.md`
  entirely), `list_skills()` returns exactly the two valid ones, each with the five metadata fields from
  their frontmatter.
- AC2. (R2) `load_skill("valid-skill")` on a fixture with both files returns a `Skill` with non-empty
  `hints` (the markdown body, not the frontmatter) and a `schema` dict matching the fixture's
  `schema.json`; `load_skill("missing-skill")` returns `None`.
- AC3. (R2) `load_skill` on a fixture directory with `SKILL.md` but no `schema.json` returns a `Skill`
  with `schema=None` (not an error).
- AC4. (R3) `load_skill` on a fixture with a `SKILL.md` but a malformed `schema.json` (invalid JSON)
  returns a `Skill` with `schema=None`; a warning-level log record is emitted naming the skill id.
- AC5. (R4) `to_prompt_block()` on a `Skill` with invariants and a non-empty `probe_order` produces text
  containing the invariant descriptions but not any `probe_order` step text.
- AC6. (R5) A fixture `SKILL.md` starting with a UTF-8 BOM parses identically to the same content without
  one; a fixture with no `---` frontmatter block at all loads with empty metadata and the full file as
  `hints`, without raising.
- AC7. All tests are hermetic: fixture directories under the test tree (not the real `skills/`, which
  does not exist yet), no network, no LLM.

## Edge cases and failure modes

- Empty `skills/` directory (or the directory doesn't exist yet): `list_skills()` returns `[]`, does not
  raise.
- A skill directory that is actually a file, not a directory (e.g. a stray `.DS_Store`): skipped, not
  treated as a skill.
- `schema.json` that parses but isn't a JSON object (e.g. a bare array or string): accepted as-is and
  handed back verbatim — schema shape validation is ADE-36's job, not this loader's.

## Non-functional requirements

- Observability: `logger = logging.getLogger(__name__)` in the new module, matching the standard this
  repo is adopting (see CPID-15 in the `chatpid` repo for the pattern this session already established).

## Assumptions

- The new skills live at repo-root `skills/`, sibling to `src/`, `sample-data/`, matching ade2's own
  layout (`SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"` in ade2, i.e. three
  levels up from the module) rather than nested under `src/`.
- No skills exist in the real `skills/` directory yet as of this story (ADE-40 adds the first one); this
  story's own tests use fixtures and do not require `skills/` to exist in the repo at all.

## Risks and dependencies

- Risk: low — pure data loading, no I/O beyond local file reads, no model calls, no changes to existing
  code paths.
- Depends on: nothing. Used by: ADE-39 (engine loop), ADE-40 (the P&ID skill content itself).
