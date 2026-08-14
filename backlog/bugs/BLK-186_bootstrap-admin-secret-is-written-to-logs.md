---
id: BLK-186
type: bug
title: "Bootstrap admin secret is written to plaintext logs"
priority: high
status: backlog
phase: 1
owner: devin
created: 2026-08-09T10:20:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [security, auth, logging, secrets, admin, bootstrap]
---

## Description

When auth boots with an empty key store, the generated bootstrap admin secret is emitted via `logger.warning()` in plaintext. This creates a direct credential disclosure path into terminal history, container logs, hosted logging sinks, and any downstream log aggregation system.

## Problem Statement

`src/api/auth.py` currently logs:

- key ID
- full bootstrap secret

The code explicitly states this is the only time the secret is shown, but logs are not an acceptable secret-delivery channel. In practice they are long-lived, copied, searchable, and often exposed to operators who should not automatically receive admin credentials.

This also conflicts with the project’s own secret-handling goals and prior backlog work around structured logging and not leaking credentials.

## Acceptance Criteria

- [ ] Bootstrap flow never writes raw secrets to application logs
- [ ] Secret delivery uses a safer one-time channel or explicit local-only stdout path with guardrails
- [ ] Structured logs and warning paths are redaction-safe for bootstrap auth events
- [ ] Tests assert that bootstrap logging does not contain the secret value
- [ ] Documentation explains how operators retrieve or rotate the initial admin credential safely

## Constraints

- Do not remove the ability to bootstrap auth for first-run local setups
- Any replacement UX must still make recovery possible when no keys exist
- Avoid leaking secrets through exception messages, traces, or telemetry attributes

## Dependencies

- Likely touches `src/api/auth.py` and related auth/bootstrap tests
- Related to implemented logging and auth hardening work, but not covered by current backlog items

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
