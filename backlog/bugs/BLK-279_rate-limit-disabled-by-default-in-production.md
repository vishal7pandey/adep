---
id: BLK-279
type: bug
title: "Rate limiting disabled by default — unsafe for production deploy"
priority: medium
status: backlog
phase: 5
owner: devin
created: 2026-08-09T11:20:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-183]
tags: [security, rate-limit, config, production]
---

## Description

`src/config.py` sets `rate_limit_enabled: bool = False`. The rationale is "disabled by default for tests," but there is no environment-aware enforcement. If someone deploys to production without explicitly setting `ADE_RATE_LIMIT_ENABLED=true`, the rate-limiting middleware is completely inert and the API has no protection against abuse, scraping, or runaway clients.

This is a footgun: the config value that is safe for tests is also the value that defaults in production. This is the same class of issue as BLK-153 (auth disabled by default) — a safety feature defaults to OFF.

## Acceptance Criteria

- [ ] Default `rate_limit_enabled` to `True` in `config.py`
- [ ] Tests explicitly set `ADE_RATE_LIMIT_ENABLED=false` in their test fixtures (or use the existing `settings` override mechanism)
- [ ] Add a startup warning when rate limiting is disabled, analog to the BLK-153 auth warning
- [ ] Update `.env.example` to document the default

## Constraints

- Must not break the existing test suite (tests likely rely on disabled rate limiting)
- Must follow the "safe by default" principle established by BLK-153 for auth

## Dependencies

- BLK-183 (frontend/CORS env configurability) — for consistency of the config story

## Notes

- Found during config/env audit
- Related to BLK-123 (rate limiting) and BLK-176 (config env standardization)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
