---
id: BLK-188
type: bug
title: "Bootstrap admin key is logged in plaintext to stderr/stdout"
priority: high
status: backlog
phase: 5
owner: devin
created: 2026-08-09T10:55:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [security, auth, secrets, observability]
---

## Description

`src/api/auth.py` `bootstrap_admin_key()` logs the raw bootstrap admin secret to the console:

```python
logger.warning(
    "Bootstrap admin key created — this is the ONLY time the secret "
    "will be shown. Key ID: %s, Secret: %s",
    key_id,
    secret,
)
```

In a production deployment where logs are shipped to a central aggregator (Datadog, CloudWatch, Loki, etc.), this secrets-in-logs is a security violation. Any logging pipeline that captures stderr/stdout will store the raw admin key in plaintext in logs, defeating the purpose of hashing the key at rest.

The key should be shown once, but not written to the shared logger channel. Common patterns: print to a dedicated one-time startup banner only when running in interactive TTY, or write to a one-time file with 0600 permissions and instruct the operator to read it once.

## Acceptance Criteria

- [ ] Raw secret is no longer passed to the logger
- [ ] The secret is written to a one-time bootstrap file (e.g. `.adep/bootstrap_key.txt` with mode 0600) OR printed only when TTY is detected
- [ ] A warning is logged telling the operator where to find the one-time secret
- [ ] Verify no log aggregator receives the raw secret

## Constraints

- Must still allow operators to recover/obtain the initial admin key once
- Must not break the test suite (tests bootstrap keys)
- Must follow the "never log secrets" policy from `src/observability/redaction.py`

## Dependencies

- None

## Notes

- Found during security audit of `src/api/auth.py`
- This is a secrets-in-logs vulnerability, similar in spirit to BLK-083 (PII redaction) and BLK-153

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
