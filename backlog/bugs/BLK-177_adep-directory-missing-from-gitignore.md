---
id: BLK-177
type: bug
title: "<.adep> directory missing from .gitignore — potential API key and document data leak"
priority: high
status: verifying
phase: 5
owner: opencode
created: 2026-08-09T10:00:00+05:30
started: 2026-08-09T15:00:00+05:30
completed: 2026-08-09T15:45:00+05:30
estimate: S
depends-on: []
tags: [security, git, secrets, docs, infrastructure]
---

## Description

The root `.gitignore` does not exclude the `.adep/` directory. This directory contains:

- `.adep/api_keys/*.json` — hashed API keys, but also metadata (key_id, name, scopes, expiration)
- `.adep/documents/{doc_id}/` — uploaded document pages and thumbnails (potentially sensitive)
- `.adep/runs/*.json` — run traces, extracted field values, grounding metadata (PII)
- `.adep/cache/` — tool result cache with extracted data

If a developer runs `git add -A` or `git commit -A`, these files would be committed and pushed to the remote repository, leaking sensitive PII data and API key metadata.

The `.dockerignore` correctly excludes `.adep/`, but the git ignore does not.

## Acceptance Criteria

- [ ] Add `.adep/` to root `.gitignore`
- [ ] Verify `git status` no longer shows `.adep/` after committing
- [ ] Add a note in `CONTRIBUTING.md` or a SECURITY.md pointing out to never commit `.adep/`
- [ ] Consider adding `.adep/` to the frontend `.gitignore` as well if relevant

## Constraints

- Do not remove the `.adep/` directory itself; it is the runtime data store
- Should not break Docker build (already excluded there)

## Dependencies

- None

## Notes

- Found during cross-cutting infrastructure audit
- Related to BLK-122 (API auth) and BLK-059 (document store)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

## Resolution

Added `.adep/` to root `.gitignore` (new block after the `# Models / data caches` section) with a comment explaining it holds API keys, documents, run traces (PII), cache, and reports, and must never be committed. `.adep/` was left on disk (runtime store intact). Also added `frontend/package-lock.json` ignore as part of the adjacent BLK-194 work.

Verified: `git check-ignore` now reports `.adep/stats/aggregate.json`, `.adep/api_keys/foo.json`, `.adep/runs/x`, `.adep/cache/x`, `.adep/reports/x` as ignored, and `git rm -r --cached .adep/` removes the 446 tracked `.adep/` files from the index without touching the working tree.

## Evidence

- `.gitignore` diff: `+`.adep/` block appended (see file).
- `git check-ignore .adep/stats/aggregate.json .adep/runs/x .adep/api_keys/foo.json .adep/cache/x .adep/reports/x` → all 5 paths listed as ignored.
- `git ls-files | Select-String '^\.adep/'` → 0 matches after `git rm -r --cached .adep/`.
- CONTRIBUTING.md note routed to mgmt (mgmt owns that file) — opencode-to-mgmt REQUEST sent 2026-08-09.
