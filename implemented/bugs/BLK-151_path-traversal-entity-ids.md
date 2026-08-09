---
id: BLK-151
type: bug
title: "Path traversal vulnerability — entity IDs not sanitized in DefinitionStore"
priority: high
status: done
started: 2026-08-08T16:30:00+05:30
completed: 2026-08-08T16:45:00+05:30
phase: 4
owner: backend
created: 2026-08-08T15:00:00+05:30
estimate: S
tags: [backend, security, path-traversal, store]
---

## Problem

`DefinitionStore._path_for()` in `src/definitions/store.py` constructs
file paths by directly interpolating user-supplied entity IDs:

```python
def _path_for(self, entity_type: str, entity_id: str) -> Path:
    return self.base_dir / entity_type / f"{entity_id}.json"
```

No validation or sanitization is performed on `entity_id`. All API
routes pass user-supplied path parameters directly to the store
methods. An attacker can supply `entity_id = "../../etc/passwd"` to
read, write, or delete files outside the `.adep/` directory.

## Evidence

`src/definitions/store.py:52-54`:
```python
def _path_for(self, entity_type: str, entity_id: str) -> Path:
    return self.base_dir / entity_type / f"{entity_id}.json"
```

API routes pass user-supplied IDs directly:
- `src/api/routes/skills.py:97-103`: `get_skill(skill_id)` → `store.get_skill(skill_id)` → `store.read("skills", skill_id)`
- `src/api/routes/definitions.py:73-79`: `get_definition(definition_id)` → `store.get_definition(definition_id)`
- `src/api/routes/runs.py:98-104`: `get_run(run_id)` → `store.get_run(run_id)`
- `src/api/routes/webhooks.py:77-83`: `get_webhook(webhook_id)` → `store.get(webhook_id)`

No route validates that the ID contains only safe characters.

## Impact

- **Read:** `GET /api/v1/skills/..%2F..%2F..%2Fetc%2Fpasswd` could read
  arbitrary files as JSON (would fail JSON parse, but file existence
  could be probed).
- **Write:** `POST /api/v1/skills` with `id: "../../etc/cron.d/malicious"`
  could write arbitrary JSON files outside `.adep/`.
- **Delete:** `DELETE /api/v1/skills/..%2F..%2F..%2Fimportant` could
  delete arbitrary `.json` files.
- When `auth_enabled=false` (the default), any client can exploit this.

## Reproduction or reasoning

1. Start the backend with default config (`auth_enabled=false`).
2. `POST /api/v1/skills` with body `{"id": "../../test-payload", "name": "test"}`
3. Check the filesystem — a file `.adep/skills/../../test-payload.json`
   is created, which resolves to `test-payload.json` in the project
   root (or further up the tree depending on `..` count).
4. `DELETE /api/v1/skills/../../test-payload` deletes it.

## Proposed resolution

Add ID validation in `_path_for` or in each API route:

```python
import re
_SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

def _path_for(self, entity_type: str, entity_id: str) -> Path:
    if not _SAFE_ID.match(entity_id):
        raise ValueError(f"Invalid entity ID: {entity_id}")
    return self.base_dir / entity_type / f"{entity_id}.json"
```

Or use `Path.resolve()` and verify the resolved path is within
`self.base_dir`.

## Acceptance criteria

- [ ] Entity IDs are validated — only alphanumeric, dash, underscore
- [ ] Path traversal attempts return 400 Bad Request
- [ ] All entity types (definitions, skills, templates, runs, webhooks)
      are protected
- [ ] Document IDs in DocumentStore are also validated
- [ ] Tests verify path traversal is blocked

## Validation plan

- `POST /api/v1/skills` with `id: "../../test"` → 400
- `GET /api/v1/skills/..%2F..%2Ftest` → 400
- `DELETE /api/v1/skills/../../test` → 400
- Normal IDs still work

## Related issues

BLK-122 (auth middleware — when auth is enabled, only authenticated
users can exploit this, but auth is disabled by default)
