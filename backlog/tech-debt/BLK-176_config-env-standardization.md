---
id: BLK-176
type: tech-debt
title: "Standardize config and environment bootstrap for provider, auth, and runtime validation"
priority: medium
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T09:30:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [config, env, bootstrap, auth, ops, standards]
---

## Description

The project currently mixes configuration conventions across settings, environment variables, docs, and code paths. Examples include `ADE_` prefixed settings in `src/config.py`, Azure aliases such as `AZURE_API_KEY`, optional auth toggles, and partial runtime startup checks. This creates ambiguity for onboarding, local development, CI, and production deployment.

The result is increased drift risk: settings can be valid in one place, silently ignored in another, or fail only when a run is already underway. This should be treated as a platform-level technical debt item because it affects reliability and developer speed across backend and frontend.

## Problem Statement

The repo has already fixed several configuration and security issues, but the broader environment model is still inconsistent across layers:

- `_env_` conventions are not consistently documented
- provider readiness is not validated uniformly
- auth and provider configuration are allowed to drift silently
- startup behavior is not explicit about required and optional settings

This increases the chance of broken local setup, incorrect provider selection, and confusing runtime failures.

## Acceptance Criteria

- [ ] A single canonical config schema is documented for local dev, CI, and production
- [ ] Required/optional settings are explicitly classified and validated at startup
- [ ] `.env.example` matches the settings model and all aliases are documented
- [ ] Auth and provider toggles are validated with actionable warnings or startup errors
- [ ] Bad config states produce a deterministic, user-readable error before expensive work begins

## Constraints

- Must preserve compatibility for local developer workflows
- Must avoid breaking existing support for Azure-backed providers and optional tools
- Any validation should be explicit and explainable; no hidden magic in runtime paths

## Dependencies

- `src/config.py`
- env documentation and onboarding guides
- provider bootstrap logic for Azure/VLM/OCR integrations

## Notes

- Related to earlier fixes for auth defaults and provider selection
- This is a foundational reliability issue, not a feature-only concern
- Serves as the configuration backbone for benchmark, queueing, and production deployment work

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T09:30 (mgmt)**: Logged from cross-cutting review of settings, env usage, and startup reliability gaps across backend components.
