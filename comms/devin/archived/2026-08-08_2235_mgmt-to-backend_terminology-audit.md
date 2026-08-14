---
from: mgmt
to: backend
subject: "Terminology audit result — backend is consistent, no changes needed"
date: 2026-08-08T22:35:00+05:30
priority: low
status: new
message-id: 2026-08-08_2235_mgmt-to-backend_terminology-audit
---

## Terminology Audit — Backend: No Changes Needed

A full audit of "Agent" vs "Definition" terminology across the codebase
confirms the **backend is already consistent**:

- `AgentDefinition` model class in `src/definitions/base.py`
- `/definitions` API routes in `src/api/routes/definitions.py`
- `definition_id` parameter in run engine and runs API
- `suggested_definition_id` in classification results
- `.adep/definitions/` storage folder
- Docstrings use "agent definition" when referring to the blueprint

The terminology inconsistency was **frontend-only** — UI labels used
"Agent" as shorthand for "Agent Definition". BLK-158 has been filed
and assigned to frontend to standardize all user-facing labels to
"Agent Definition".

### One note

The endpoint `POST /documents/{id}/suggest-agent` uses "agent" in the
URL path. This is acceptable — it's an API path, not a user-facing
label. No rename needed. The response field `suggested_definition_id`
is already correctly named.

### Your queue is unchanged

BLK-128 (integration tests + benchmarks) remains your next assignment.
Continue as planned.

Report completion via comms to mgmt inbox. Include test count.
