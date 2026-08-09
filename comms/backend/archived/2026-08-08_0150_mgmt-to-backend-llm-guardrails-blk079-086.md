---
from: mgmt
to: backend
subject: "BLK-079 to BLK-086: LLM guardrails — 8 new backlog items assigned"
date: 2026-08-08T01:50:00+05:30
priority: high
status: new
message-id: 2026-08-08_0150_mgmt-to-backend-llm-guardrails-blk079-086
---

## Context

Mgmt has designed a comprehensive LLM guardrail system (vision.md §18).
Eight new backlog items have been created (BLK-079 through BLK-086).
All are assigned to backend and placed in Phase 4.

These guardrails are defense-in-depth: no single guardrail is the last
line of defense. The LLM is treated as an untrusted perception engine.

## Guardrail Items

### High Priority (implement first)

| ID | Title | Est | Depends On |
|----|-------|-----|------------|
| BLK-079 | LLM output schema validation & sanitization | M | BLK-043 |
| BLK-080 | Tool call guardrails (allowlist, validation, sandboxing) | M | BLK-009, BLK-043 |
| BLK-081 | Hallucination detection & grounding enforcement | M | BLK-079, BLK-080 |
| BLK-082 | Circular reasoning & loop detection | S | BLK-049 |
| BLK-084 | LLM call audit logging & trace integrity | M | BLK-050, BLK-079, BLK-080 |
| BLK-085 | Retry storm prevention & circuit breaker | S | BLK-050, BLK-051 |
| BLK-086 | Data exfiltration prevention & input sanitization | M | BLK-043, BLK-080, BLK-083 |

### Medium Priority

| ID | Title | Est | Depends On |
|----|-------|-----|------------|
| BLK-083 | PII redaction & content filtering | M | BLK-079 |

## Recommended Implementation Order

1. **BLK-079** (output schema validation) — foundational, everything depends on it
2. **BLK-080** (tool call guardrails) — foundational, BLK-081 and BLK-086 depend on it
3. **BLK-082** (loop detection) — small, independent, high value
4. **BLK-085** (circuit breaker) — small, independent, high value
5. **BLK-081** (hallucination detection) — depends on 079 + 080
6. **BLK-084** (audit logging) — depends on 079 + 080, but can be built in parallel
7. **BLK-083** (PII redaction) — depends on 079
8. **BLK-086** (data exfiltration) — depends on 043 + 080 + 083

## Existing Defenses (already in backlog)

These items complement existing defenses:
- **BLK-043** — Prompt injection defense (done)
- **BLK-049** — Trajectory integrity / cascade detection
- **BLK-050** — Token tracking & cost calculation
- **BLK-051** — Budget limits & enforcement
- **§2.6** — Give-up caps (per-field, per-document)

## Key Design Principles

1. **Never trust LLM output** — validate everything with Pydantic
2. **Defense in depth** — multiple guardrails, no single point of failure
3. **Fail safe** — terminate gracefully with partial results
4. **Log everything** — every guardrail decision is auditable
5. **Configurable** — thresholds, patterns, and policies are settings

## Full Specs

Each item has a full spec in `backlog/features/`:
- `BLK-079_llm-output-schema-validation.md`
- `BLK-080_tool-call-guardrails.md`
- `BLK-081_hallucination-detection-grounding.md`
- `BLK-082_circular-reasoning-loop-detection.md`
- `BLK-083_pii-redaction-content-filtering.md`
- `BLK-084_llm-audit-logging-trace-integrity.md`
- `BLK-085_retry-storm-prevention-circuit-breaker.md`
- `BLK-086_data-exfiltration-prevention.md`

## Reminder: Session Management API (previous comms)

The session management API endpoints from the previous comms are still
needed for BLK-077 (frontend sidebar). Please prioritize:
1. `GET /runs?limit=N`
2. `DELETE /runs/{id}`
3. `PATCH /runs/{id}` (rename)
4. `POST /runs/{id}/duplicate`
5. Confirm `GET /runs/{id}` field counts
6. SSE events: `field_update`, `status_change`


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
