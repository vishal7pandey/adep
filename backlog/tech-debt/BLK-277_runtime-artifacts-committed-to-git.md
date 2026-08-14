---
id: BLK-277
type: tech-debt
title: "Runtime/generated artifacts under .adep/ are tracked in git with no .gitignore coverage"
priority: medium
status: verifying
phase: 2
owner: opencode
created: 2026-08-09T10:45:00+05:30
started: 2026-08-09T15:00:00+05:30
completed: 2026-08-09T15:45:00+05:30
estimate: S
depends-on: []
tags: [git, hygiene, ops, runtime-state, repo-bloat]
---

## Description

`.adep/` is the runtime data directory for the platform (run history, uploaded document derivatives, OCR/VLM cache, generated reports, issued API-key records). `.gitignore` has no entries for it, so subdirectories that are clearly generated-at-runtime state are committed to git:

- `.adep/runs/` — 287 per-run directories as of 2026-08-09 (and growing continuously; 4 new ones appeared in the few minutes spent auditing this repo) — token usage, run traces, serialized results
- `.adep/documents/` — uploaded-document derivatives: `meta.json`, rendered `page_NNN.png`, `thumbnail.jpg` per document
- `.adep/cache/` — OCR/VLM response cache, sharded by hash prefix
- `.adep/reports/` — generated benchmark/eval report JSON snapshots
- `.adep/stats/aggregate.json` — a running aggregate that gets rewritten on every run (already showing as locally modified relative to the last commit)
- `.adep/api_keys/*.json` — issued API-key records (see Notes on `adep_96aee76986804255.json`)

None of this is source — it's all reproducible/regenerable output of using the running system. Committing it means the repo grows unboundedly with every run anyone executes locally, diffs on unrelated PRs get polluted with `aggregate.json`/run-directory noise, and reviewers can't tell generated state from an intentional data fixture.

## Problem Statement

- Repo bloat grows without bound as the system is used — 287 run directories already, all in git history permanently even if deleted later
- `git status` / `git diff` becomes noisy with runtime-generated changes (`.adep/stats/aggregate.json` shows as modified in the current working tree from ordinary use)
- `.adep/documents/` contains rendered page images and thumbnails from whatever was uploaded during testing — if real (non-sample) documents are ever tested locally, their content ends up permanently in git history
- `.adep/api_keys/adep_96aee76986804255.json` (a "Bootstrap Admin Key" record with `admin` scope) is tracked. The file stores a SHA-256 hash, not the raw key, so this specific file isn't a raw-secret leak — but tracking a live system's issued-key metadata in version control at all is the wrong pattern, and the same directory would leak a raw key if the hashing discipline ever slipped. Note: if the *raw* bootstrap key itself is written anywhere (logs, console output, etc.), that's the separate, more severe issue tracked in BLK-186 — this ticket is about the directory being committed at all, not about whether this particular file exposes a secret.

## Acceptance Criteria

- [ ] Add `.adep/runs/`, `.adep/documents/`, `.adep/cache/`, `.adep/reports/`, `.adep/api_keys/` to `.gitignore`
- [ ] Decide whether `.adep/stats/aggregate.json` should be gitignored (runtime-accumulated) or reset/seeded as a checked-in template (starting state) — pick one, don't leave it as a file that's both committed and routinely modified by normal use
- [ ] `git rm -r --cached` the now-ignored paths (keep working-tree files; only remove from tracking) in a dedicated commit with a clear message
- [ ] Confirm no currently-tracked file under these paths contains a raw (non-hashed) secret before/while removing from tracking — spot-check `.adep/api_keys/*.json` specifically
- [ ] Document in README/CONTRIBUTING (if present) that `.adep/` is local runtime state, not part of the source tree

## Constraints

- This changes git tracking, not application behavior — no runtime code changes needed
- Do not delete the files from disk, only from git tracking, unless the user confirms the local copies are also disposable
- Coordinate with BLK-186 if that ticket's fix also touches how/where the bootstrap key is written, to avoid two people editing the same area at once

## Dependencies

- `.gitignore`
- BLK-186 (bootstrap admin secret written to logs) — related but distinct; resolve independently, cross-reference in commit messages

## Notes

- Found while auditing the repo for backlog-worthy issues; not previously called out in `ADE_codebase_audit.md`
- `.adep/api_keys/adep_96aee76986804255.json` was inspected directly and confirmed to contain only `key_hash` (SHA-256, 64 hex chars) plus metadata — no raw key material in that file

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T10:45 (mgmt)**: Logged after observing `.adep/runs/` grow from 287 to 291+ directories mid-session and confirming none of `.adep/`'s generated subdirectories are gitignored.

## Resolution

The whole `.adep/` directory is now gitignored (supersedes per-subdir entries — `.adep/runs/`, `.adep/documents/`, `.adep/cache/`, `.adep/reports/`, `.adep/api_keys/`, `.adep/stats/aggregate.json` all covered by the parent). Decision on `stats/aggregate.json`: **gitignored**, not seeded — it is runtime-accumulated, gets rewritten every run, and there is no meaningfully "clean" seed state worth committing; `make seed` regenerates seeded state.

Ran `git rm -r --cached .adep/` — 446 tracked files removed from the index, all working-tree files kept on disk. Spot-checked `.adep/api_keys/adep_96aee76986804255.json` before untracking: contains only `key_hash` (SHA-256) + metadata, no raw secret — consistent with the ticket's Notes.

## Evidence

- `git check-ignore` on `.adep/stats/aggregate.json`, `.adep/runs/x`, `.adep/api_keys/foo.json`, `.adep/cache/x`, `.adep/reports/x` → all listed as ignored.
- `git ls-files | Select-String '^\.adep/'` → count 0 after untracking (was 446).
- `git status --short` no longer shows ` M .adep/stats/aggregate.json` or untracked `?? .adep/runs/` noise.
- No runtime code changes (tracking-only per Constraints). README/CONTRIBUTING note routed to mgmt (mgmt owns those files).
