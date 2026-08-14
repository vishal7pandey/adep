---
from: mgmt
to: backend
subject: "BLK-108: Prebuilt templates seeded with empty fields — root cause of template editor issue"
date: 2026-08-08T03:50:00+05:30
priority: high
status: done
message-id: 2026-08-08_0350_mgmt-to-backend-template-empty-fields
---

## Bug

The user reports: clicking Edit on an existing template shows no
fields. This is a **backend issue**, not a frontend mapping issue.

## Root Cause

`PREBUILT_TEMPLATES` in `src/definitions/prebuilt.py` (line 233)
seeds all 12 templates with `"fields": []`:

```python
PREBUILT_TEMPLATES: list[dict] = [
    {"id": "invoice", "name": "Invoice", "description": "Standard invoice template", "fields": []},
    {"id": "trade_finance_mt700", "name": "Trade Finance MT700", "description": "...", "fields": []},
    # ... all 12 have empty fields
]
```

The actual field schemas exist in the Python Template classes
(`src/templates/invoice.py`, etc.) but are never serialized into
the store JSON files. So `GET /api/v1/templates` returns templates
with zero fields.

The frontend only shows 6 fields because it's falling back to
`MOCK_TEMPLATES` (backend not running). When the backend IS running,
every template shows "0 fields".

## Fix

Serialize field schemas from the Template Pydantic classes into
`PREBUILT_TEMPLATES`. Either:

1. **Auto-extract**: Import each Template class, iterate
   `model_fields`, and build the field list dynamically
2. **Manual**: Explicitly define all fields in the dict

Option 1 is preferred — it stays in sync with the Template classes
automatically.

Full spec: `backlog/features/BLK-108_prebuilt-templates-empty-fields.md`

## Priority

**HIGH** — this blocks the user from viewing/editing any template.
Fix before BLK-103 (e2e tests) since the e2e tests need real
template data.

## Also Check: Skills

`PREBUILT_SKILLS` (line 218) similarly only has `id`, `name`,
`description`, and `tools`. The actual skill data (system_prompt,
probe_order, invariants, failure_actions) is not serialized. The
Skill Editor will have the same problem — editing a skill won't
show its existing configuration.

Fix both skills and templates in the same pass.

## Resolution

Fixed using Option A (auto-extract). Both templates and skills now
serialize actual data from Pydantic classes and Skill dataclass
instances. All 12 templates have 8-12 fields each. All 12 skills
have system_prompt, tool_preferences, probe_order, invariants,
failure_actions, known_failures, and confidence_overrides serialized.
754 tests pass with no regressions. Reply sent to mgmt/inbox/.
