---
from: mgmt
to: backend
subject: "Major backlog load — BLK-121 to BLK-130. Includes a data-loss bug and a zero-auth security gap."
date: 2026-08-08T13:55:00+05:30
priority: high
status: new
message-id: 2026-08-08_1355_mgmt-to-backend-major-load
---

## Context

I audited the codebase against what we claim to have built and found
significant gaps. Ten new items, BLK-121 through BLK-130.

Two are urgent: a **silent data-loss bug** and **the API has no
authentication at all**.

## Urgent

### BLK-121 — Skills API silently discards skill data (BUG)

`CreateSkillRequest` / `UpdateSkillRequest` in
`src/api/routes/skills.py` accept only 6 fields: `id`, `name`,
`description`, `semantic_checks_enabled`, `semantic_prompt`, `tools`.

BLK-108 made the store **serialize** the full skill: `system_prompt`,
`tool_preferences`, `probe_order`, `invariants`, `failure_actions`,
`known_failures`, `confidence_overrides`.

So `GET` returns full skill data, but `POST`/`PUT` drop everything
outside those 6 fields. **Read/write asymmetry.**

The frontend Skill Editor (BLK-101) has full UI for all of it. The
user edits a system prompt, adds invariants, sets a probe order,
clicks Save — and it is silently discarded. On reload their work is
gone.

Silent data loss is worse than an error. Fix first.

Note: templates are fine — `CreateTemplateRequest` accepts `fields`.
Please verify definitions have no equivalent gap.

### BLK-122 — API authentication (SECURITY)

There is no auth middleware, no API key validation, no identity.
Every endpoint is public:

- `POST /api/v1/runs` — anyone can spend our LLM budget
- `DELETE /api/v1/definitions/{id}` — anyone can delete agents
- `GET /api/v1/documents/{id}/page/{n}` — anyone can read any document
- `GET /api/v1/admin/analytics/*` — anyone can read all analytics

Budget enforcement is global, so a single actor can exhaust the daily
budget for everyone.

Requirements: API key model (hashed, never plaintext), auth
middleware, scopes, per-key budgets, 5 management endpoints,
`ADE_AUTH_ENABLED` flag defaulting to **false** so the existing suite
is unaffected.

## Architecture

### BLK-129 — Async run execution (XL, high leverage)

Runs execute synchronously inside the HTTP request. This single fact
is the root cause of things we have been treating as separate issues:

- **BLK-090** — SSE is a replay of a finished trace, not live progress
- **BLK-046** — pause/resume/stop cannot interrupt a synchronous run;
  agent control is currently theatre
- **BLK-118** — batch processing is impossible without concurrency
- HTTP timeouts on long documents lose results
- One long run blocks the worker

Move to a bounded async worker pool, return `202 Accepted`, publish
live SSE events, make cancellation cooperative at cycle boundaries.
In-process asyncio only for v1 — **no Celery or Redis yet.**

**This changes the run-start API contract.** Per PROTOCOL.md §7, send
a contract proposal to mgmt before implementing so frontend adapts in
the same cycle. Do not just change it.

### BLK-124 — Tool result caching (high value)

No caching exists anywhere. Every run re-pays full OCR and VLM cost.
The ReAct loop calls `ocr` on overlapping regions within one run and
pays each time. Iterative skill tuning is needlessly expensive.

Content-addressed cache keyed on **region pixel bytes** plus params
plus provider version — not file path or bbox coordinates, so two
different bboxes cropping identical pixels share an entry.

`ToolSpec.cacheable` defaults to `False`. Opt in per tool.
**Correctness over hit rate** — a wrong hit is far worse than a miss.

## Missing Tools

### BLK-125 — `detect_tables`

Does not exist, despite being the canonical example in
`comms/README.md` and being needed by `InvoiceSkill` (line items),
`BillOfQuantitiesSkill` (entire document), `AdBuySkill`, and
`MetallurgicalAssaySkill`.

Those skills currently prompt the VLM on the whole page and hope for
well-formed rows. That is why line-item sum invariants fail for
structural reasons rather than perception errors.

Ruled tables via OpenCV (deterministic), unruled via projection
profiles, VLM only for merged cells. Cell-level bboxes required so
Pane 3 can highlight individual cells.

### BLK-126 — `detect_signatures`

`TradeFinanceScrutinySkill` needs to verify documents are signed and
stamped. `CommercialLeaseSkill`, `ComplianceAuditSkill`, and
`MedicalClaimSkill` all have signature requirements. No tool exists.

**Scope boundary, non-negotiable:** this detects *presence* only. Not
authenticity, not identity, not forgery. Those require reference
specimens and carry legal liability. State the limit in the docstring
so downstream users don't over-trust it.

### BLK-127 — `classify_document` + auto-routing

Users must pick an agent before uploading, with no basis for the
decision. Picking wrong yields empty fields and no indication the
*agent choice* was the problem.

Add classification plus
`POST /api/v1/documents/{id}/suggest-agent`, and support
`definition_id: "auto"` on run start.

**If no prediction clears the threshold, fail fast with candidates.
Never silently guess** — guessing burns budget and produces confusing
results.

## Quality

### BLK-128 — Real-provider integration tests (most important quality item)

All 754 tests are mocked, including BLK-103's e2e tests. **Nothing has
ever verified the platform extracts correctly against real providers.**

We cannot answer "does this work?" or "did that change help?"

Mocks cannot catch prompts that confuse the real model, miscalibrated
confidence, wasteful probe orders, or cost estimates that are wrong by
an order of magnitude.

Specifically included: **confidence calibration measurement.** Bucket
predictions by reported confidence, compare to actual correctness. If
fields reported at 0.9 are only 60% correct, our scores are lying and
every threshold in the system is wrong. Flag buckets where
|reported − actual| > 0.15.

Integration tests must never run in CI by default — they cost real
money. Skip cleanly when credentials are absent.

I will supply labelled ground-truth fixtures under BLK-104.

### BLK-130 — Structured logging + OpenTelemetry

Logging is unstructured string formatting with no correlation between
request, run, cycle, and provider call. Add JSON logging with
contextvar propagation and OTLP spans. Reuse BLK-083 for redaction —
field names may be logged, field values may not. Prompts logged as
hash plus token count, never full text.

### BLK-123 — Rate limiting

No throttling exists. A caller can hammer `POST /runs` and exhaust
the budget in seconds. Token bucket per key/IP, tiered limits,
`X-RateLimit-*` headers, concurrent SSE cap. Disabled by default.

## Priority Order

Finish uv migration and BLK-109 first — both already approved and in
flight. Then:

| # | Item | Why this position |
|---|------|-------------------|
| 1 | **BLK-121** | Silent data loss, small fix |
| 2 | **BLK-122** | Zero auth is a deployment blocker |
| 3 | **BLK-110/111** | Already approved, finish the graph extraction arc |
| 4 | **BLK-129** | Unblocks BLK-118, properly closes BLK-090 (send contract proposal first) |
| 5 | **BLK-124** | Large cost reduction, needed for BLK-128 warm benchmarks |
| 6 | **BLK-128** | Ground truth on accuracy and calibration |
| 7 | **BLK-125** | Fixes structural line-item failures |
| 8 | **BLK-127** | Enables the upload-first UX |
| 9 | **BLK-130** | Observability |
| 10 | **BLK-123** | Rate limiting |
| 11 | **BLK-126** | Signature detection |
| 12 | **BLK-106** | New document types |

## Standing Constraints

- Every item must keep the existing suite green. New middleware and
  features default to **disabled** where they could affect tests.
- New dependencies via `uv add` only, per PROTOCOL.md §10.1.
- Anything changing an API contract goes through the §7 proposal
  process before implementation.
- If you disagree with a priority or see a better sequencing, say so.
  You have more context on the code than I do — push back rather than
  silently reordering.

Full specs are in `backlog/features/BLK-121` through `BLK-130`.
