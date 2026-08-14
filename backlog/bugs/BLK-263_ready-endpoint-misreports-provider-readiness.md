---
id: BLK-263
type: bug
title: "Readiness endpoint claims app is ready without validating provider connectivity"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T09:45:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [healthcheck, readiness, providers, observability, ops]
---

## Description

The `GET /ready` endpoint in `src/api/main.py` only verifies that the definition store can list definitions. It does not validate whether the configured OCR/VLM providers are reachable, credentials are present, or runtime dependencies are available. The endpoint therefore reports `{"status": "ready"}` even when the application cannot actually perform extraction tasks.

This is a reliability bug: the app signals readiness to load but not to work. It weakens operational confidence and makes deployment health checks misleading.

## Problem Statement

The readiness contract is stronger than the implementation. The API claims to check whether the app is ready, but the check does not cover the main mission-critical dependencies: OCR provider, VLM provider, and required document runtime dependencies. In practice this means a deployment can appear healthy while returning 500s or zero-output failures during real extraction runs.

## Acceptance Criteria

- [ ] `/ready` verifies at least provider configuration presence, not just file store health
- [ ] `/ready` reports degraded state when OCR/VLM config is missing or unreachable
- [ ] Response includes actionable detail on which provider or dependency is failing
- [ ] `GET /health` remains a simple liveness check while `/ready` becomes a stronger readiness signal
- [ ] Readiness checks are documented as operational contract, not just local dev convenience

## Constraints

- Must not turn a healthy app into a flaky readiness check during local development
- Provider checks should be non-blocking for optional capabilities unless required by the selected route
- Validation should prefer explicit status and detail payloads over vague boolean-only responses

## Dependencies

- BLK-173 (provider config validation)
- BLK-176 (config + env standardization)
- backend observability and health check contract

## Notes

- Directly relevant to `src/api/main.py` readiness check and `vision.md §2.7` provider failure propagation
- The project already has health checks in place, but they do not reflect actual extraction readiness

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T09:45 (mgmt)**: Identified during a health/ops audit of readiness semantics and provider failure handling.
