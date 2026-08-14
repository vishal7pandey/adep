---
id: BLK-236
type: tech-debt
title: ".env.example missing 12 settings from config.py — incomplete template for new developers"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T14:40:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [config, env, docs, onboarding]
---

## Description

`src/config.py` defines 30+ settings, but `.env.example` only documents 18 of them. Missing settings include:

- `ADE_OTEL_ENDPOINT` (OpenTelemetry tracing endpoint)
- `ADE_LOG_FORMAT` (json vs console)
- `ADE_AUTH_ENABLED` is present but...
- `ADE_AUTO_ROUTE_THRESHOLD` (document classification threshold)
- `ADE_CACHE_ENABLED`, `ADE_CACHE_TTL_SECONDS`, `ADE_CACHE_MAX_SIZE_BYTES`, `ADE_CACHE_MEMORY_ENTRIES`, `ADE_CACHE_VERSION` (caching configuration)
- `ADE_MAX_CONCURRENT_RUNS` (async run execution)
- `ADE_RATE_LIMIT_ENABLED` and all rate limit settings (6 settings)
- `AZURE_EMBEDDING_ENDPOINT`, `AZURE_EMBEDDING_DEPLOYMENT` (embedding configuration)

## Problem Statement

- A new developer copying `.env.example` to `.env` won't know about caching, rate limiting, tracing, or embedding settings
- The defaults in `config.py` work for local development, but the `.env.example` is supposed to document all configurable settings
- Missing `AZURE_EMBEDDING_ENDPOINT` is notable — if embeddings are used, the developer won't know to configure them
- Rate limiting is disabled by default but the `.env.example` doesn't even mention it, so a production deployer wouldn't know to enable it

## Acceptance Criteria

- [ ] Add all missing settings from `config.py` to `.env.example` with sensible defaults and comments
- [ ] Group settings by category (Azure, Validation, Compaction, Logging, Budget, Auth, Cache, Rate Limiting, Async, Classification)
- [ ] Verify every setting in `config.py` has a corresponding entry in `.env.example`

## Constraints

- Don't add secrets to `.env.example` — use placeholder values
- Keep the file readable — group related settings with section comments

## Dependencies

- `.env.example`
- `src/config.py`

## Notes

- Found during full-repo audit; the `.env.example` was likely written early and not updated as new settings were added

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
