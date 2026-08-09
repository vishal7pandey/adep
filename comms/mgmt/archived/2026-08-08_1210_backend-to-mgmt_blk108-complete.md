---
from: backend
to: mgmt
subject: "BLK-108 complete â€” prebuilt templates and skills now serialize actual data"
date: 2026-08-08T12:10:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-08_0350_mgmt-to-backend_template-empty-fields.md
message-id: 2026-08-08_1210_backend-to-mgmt_blk108-complete
---

## Context

Fixed BLK-108: prebuilt templates and skills were seeded with empty
fields/data. The actual Pydantic Template classes and Skill dataclass
instances had the real schemas but they were never serialized into the
store JSON files.

## What Was Done

### Templates (Option A â€” auto-extract)

- Added `_extract_template_fields()` function that iterates
  `template_cls.model_fields` and extracts name, type, description,
  and required flag for each field.
- Added `_pydantic_type_to_str()` helper to convert type annotations
  (including `list[LineItem]`, `dict[str, Any]`) to readable strings.
- Replaced static `PREBUILT_TEMPLATES` with `_build_prebuilt_templates()`
  which imports all 12 Template classes and auto-extracts fields.
- All 12 templates now have non-empty `fields` arrays matching their
  Pydantic schemas (8-12 fields each).

### Skills (auto-serialize)

- Added `_serialize_skill()` function that converts a Skill dataclass
  instance to a JSON-compatible dict including: system_prompt,
  tool_preferences, probe_order, invariants (name + fields),
  failure_actions (serialized by GapType enum value), known_failures,
  and confidence_overrides.
- Replaced static `PREBUILT_SKILLS` with `_build_prebuilt_skills()`
  which imports all 12 Skill objects and serializes them.
- All 12 skills now have full metadata in the store.

### BLK-105 Cleanup

Also added a third invariant to `MedicalClaimSkill` (billed_amount
non-negative) and `AdBuySkill` (campaign_start before campaign_end)
to meet the 3+ invariants requirement.

## Acceptance Criteria

- [x] All 12 seeded templates have non-empty `fields` arrays
- [x] Fields match the Pydantic schema defined in the Template class
- [x] `GET /api/v1/templates` returns templates with fields populated
- [x] No regression in existing tests (754 passed, 0 failed)
- [x] Re-seeding works (doesn't overwrite existing templates)

## Notes

- The auto-extraction approach (Option A) ensures templates stay in
  sync with Pydantic classes automatically â€” no manual field lists
  to maintain.
- Skill serialization includes invariant names and fields but not the
  function bodies (those are not JSON-serializable). The frontend
  can display invariant names and the fields they cover.
- `seed_store()` still does NOT overwrite existing content, so users
  who already have seeded stores will need to delete `.adep/` to get
  the updated data. This is by design per BLK-092.


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
