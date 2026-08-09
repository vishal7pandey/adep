# ADEP Status Board

> Live dashboard of backlog items, phase progress, and current priorities.
> Updated by mgmt only. All parties should read this at the start of each
> work session.

*Last updated: 2026-08-09T00:45:00+05:30 by mgmt — BLK-165/166 complete (1243 tests), Phase 5 kickoff, 9 items prioritized, 145 items*

---

## Current Phase

**Phase 4: Polish, Scale & Evolve** - **complete**.
**Phase 5: ADAS / Agentic Builder** - in progress.

Phases 1 (Engine), 2 (Platform API), and 3 (Frontend) are **complete**.
**1243 tests passing.** Frontend build clean. 145 items completed. Phase 5 (ADAS) launched.

### Codebase Audit — Complete (2026-08-08)

Full multi-pass repository audit completed. 13 issue files created
(BLK-139 through BLK-151). All 13 verified and **completed by both teams**.
Audit ledger at `projectmgmt/audit-ledger.md`.

**Audit items completed by backend (5 items, +23 tests):**
- **BLK-151** - Path traversal fix. Entity ID regex validation in store.py + documents/store.py. **DONE**.
- **BLK-140** - `calendar.timegm` replaces `time.mktime`. **DONE**.
- **BLK-150** - `get_raw()` method, HMAC signature in test webhook. **DONE**.
- **BLK-144** - Config-driven OCR provider selection in read_tag. **DONE**.
- **BLK-145** - `enumerate()` replaces `edges.index()`. **DONE**.

**Audit items completed by frontend (8 items, build clean):**
- **BLK-141** - `fetchRecentRuns` unwraps paginated response. **DONE**.
- **BLK-146** - `Skill` interface extended with all backend fields. **DONE**.
- **BLK-147** - `crypto.randomUUID()` replaces `Date.now()`. **DONE**.
- **BLK-139** - `startDemoRun` removed, real `startExtractionRun` + SSE wired. **DONE** (minor residual: `sample_invoice.pdf` fallback at 2 locations).
- **BLK-143** - File upload sends `FormData` to `POST /documents`. **DONE**.
- **BLK-148** - `DEMO_FIELDS` removed, real `fetchRun` + SSE `onFieldUpdate`. **DONE**.
- **BLK-142** - `handleSave` sends full form data to `createSkill`. **DONE**.
- **BLK-149** - Dynamic `totalPages`, hex colors tokenized to CSS vars. **DONE**.

**Previously completed (prior audit wave):**
- **BLK-121** - Skills API data loss. **DONE**.
- **BLK-122** - API authentication. **DONE**.
- **BLK-110** - Graph extraction tools (8 tools). **DONE**.
- **BLK-106** - 6 new document types. **DONE**.
- **BLK-137** - Frontend API client mock data. **DONE**.
- **BLK-138** - Backend stub mode removed. **DONE**.
- **BLK-134** - Dark mode + theme system. **DONE** (Phase 2 tokenization ongoing).

### Independent Reviewer Findings (2026-08-08)

An independent adversarial review (REV-001 through REV-005) surfaced
5 findings. 4 issue files created (BLK-152 to BLK-155). 1 protocol gap
(REV-004) resolved by adding `reviewer` role to PROTOCOL.md.

- **BLK-152** - SSRF via unvalidated webhook URL (CRITICAL, security) — **DONE**
- **BLK-153** - Auth disabled by default, missing from .env.example (HIGH) — **DONE**
- **BLK-154** - CI pipeline broken — references deleted requirements-dev.txt (HIGH) — **DONE**
- **BLK-155** - Non-atomic store writes with TOCTOU race (MEDIUM) — **DONE**
- **REV-004** - Protocol gap: no reviewer role. **RESOLVED** — PROTOCOL.md updated.

**Audit items completed by frontend (4 items, build clean):**
- **BLK-134** - 100% tokenization, 0 hardcoded hex values remaining. **DONE**.
- **BLK-112** - P&ID graph visualization with DEXPI/GraphML/Smart P&ID toggles. **DONE**.
- **BLK-135** - API key management UI with sessionStorage auth. **DONE**.
- **BLK-116** - Side-by-side run comparison with color-coded diff table. **DONE**.

Also still identified from prior audit:
- **BLK-129** - Synchronous run execution is the root cause of fake SSE
  (BLK-090), non-functional agent control (BLK-046), and blocked batch
  processing (BLK-118). One fix, four symptoms.
- **BLK-128** - All tests are mocked. Accuracy and confidence
  calibration have never been measured against real providers.
- **BLK-124** - No caching anywhere. Every run re-pays full OCR/VLM cost.
- **BLK-125** - `detect_tables` does not exist despite 4 skills needing it.

---

## Phase Progress

| Phase | Status       | Items Done | Backlog |
|-------|-------------|------------|---------|
| 1     | Complete     | 15         | 0       |
| 2     | Complete     | 10         | 0       |
| 3     | Complete     | 22         | 0       |
| 4     | Complete     | 82         | 0       |
| 5     | In progress  | 0          | 9       |

---

## Backend Queue (priority order)

| #  | ID      | Title                                      | Est | Status   |
|----|---------|--------------------------------------------|-----|----------|
| 1  | BLK-070 | Surrogate Verifier                         | L   | Active   |
| 2  | BLK-067 | AI Template Composer (API)                 | M   | Active   |

---

## Frontend Queue (priority order)

| #  | ID      | Title                                      | Est | Status   |
|----|---------|--------------------------------------------|-----|----------|
| 1  | BLK-067 | AI Template Composer (UI)                  | M   | Active   |

---

## Cross-team / mgmt

| ID      | Title                                    | Owner    | Status  |
|---------|------------------------------------------|----------|---------|
| BLK-118 | Batch processing queue                   | both     | Backlog |
| BLK-104 | Expand sample data + ground-truth labels | mgmt     | Active  |

**BLK-104 is now a dependency of BLK-128** - integration tests need
labelled `.expected.json` fixtures. mgmt owns producing them.

---

## Pending Contract Proposals (PROTOCOL.md S7)

| Item    | Change                                          | Status  |
|---------|-------------------------------------------------|---------|
| BLK-129 | `POST /runs` returns 202 + queued, not 201 + result | Implemented |

Backend instructed to propose before implementing. Frontend notified
not to build around current synchronous behaviour.

---

## Superseded / Deleted

| Old ID  | Replaced by | Reason |
|---------|-------------|--------|
| BLK-057 | BLK-117     | Absorbed into comprehensive a11y item |
| BLK-062 | BLK-117     | Absorbed into comprehensive a11y item |
| BLK-066 | BLK-119     | Absorbed into analytics dashboard |
| BLK-042 | BLK-087     | Superseded by full GICS catalogue |
| BLK-090 | BLK-129     | Root cause is sync execution, not SSE |

---

## Deferred (v2/v3)

| ID      | Title                                    | Phase |
|---------|------------------------------------------|-------|
| BLK-035 | Multi-document orchestration             | v2    |
| BLK-036 | Database-backed Definition Store         | Phase 5 (promoted) |
| BLK-037 | Multi-tenant support                     | v3    |
| BLK-056 | Responsive & mobile layout               | v2    |
| BLK-058 | Error boundaries & crash reporting       | v2    |

---

## Phase 5 Backlog - ADAS / Agentic Builder (all promoted to high)

**Dependency chain (critical path: BLK-070 → 068 → 071 → 072 → 073):**

```
BLK-036 (DB Store, L)     ──────────── independent
BLK-074 (OneFlow, M)      ──────────── independent (deps: BLK-008 ✓)
BLK-067 (Template Comp, M) ──────┐
BLK-070 (Surrogate Ver, L) ──────┤
                                 │
BLK-068 (Skill Comp, L) ←────────┤ (deps: BLK-029 ✓, BLK-070)
                                 │
BLK-069 (Agent Comp, L) ←────────┘ (deps: BLK-031 ✓, BLK-067, BLK-068)
BLK-071 (GEPA, L) ←──────────────── (deps: BLK-068, BLK-070)
BLK-072 (MCTS, L) ←───────────────── (deps: BLK-071)
BLK-073 (DocETL, L) ←─────────────── (deps: BLK-072)
```

**Wave plan:**

| Wave | Backend                              | Frontend                     |
|------|--------------------------------------|------------------------------|
| 1    | BLK-070 (Surrogate Verifier, L)      | BLK-067 UI (Template Comp, M) |
|      | BLK-067 API (Template Composer, M)   |                              |
| 2    | BLK-068 API (Skill Composer, L)      | BLK-068 UI (Skill Composer, M) |
|      | BLK-036 (DB Store, L)                |                              |
| 3    | BLK-071 (GEPA, L)                    | BLK-069 UI (Agent Composer, L) |
|      | BLK-069 API (Agent Composer, L)      |                              |
| 4    | BLK-072 (MCTS, L)                    | —                            |
|      | BLK-074 (OneFlow, M)                 |                              |
| 5    | BLK-073 (DocETL, L)                  | —                            |

| ID      | Title                                    | Est | Status   | Wave |
|---------|------------------------------------------|-----|----------|------|
| BLK-070 | Surrogate Verifier                       | L   | Active   | 1    |
| BLK-067 | AI Template Composer                     | M   | Active   | 1    |
| BLK-068 | AI Skill Composer                        | L   | Backlog  | 2    |
| BLK-036 | Database-backed Definition Store         | L   | Backlog  | 2    |
| BLK-069 | Agent Composer from natural language     | L   | Backlog  | 3    |
| BLK-071 | Reflective Prompt Evolution (GEPA)       | L   | Backlog  | 3    |
| BLK-072 | MCTS workflow optimization               | L   | Backlog  | 4    |
| BLK-074 | OneFlow single-agent mode                | M   | Backlog  | 4    |
| BLK-073 | DocETL query rewriting                   | L   | Backlog  | 5    |
| BLK-075 | Provider comparison & selection          | low      | low      | —    |
| BLK-076 | Dynamic cost estimator                   | low      | low      | —    |

---

## Completed - 145 items

**Phase 1 (Engine):** BLK-001 to BLK-015
**Phase 2 (Platform API):** BLK-016 to BLK-025
**Phase 3 (Frontend):** BLK-026 to BLK-034, BLK-038, BLK-045, BLK-048,
BLK-053, BLK-054, BLK-055, BLK-077, BLK-078
**Phase 4:** BLK-039, BLK-040, BLK-041, BLK-042, BLK-043, BLK-044,
BLK-046, BLK-047, BLK-049, BLK-050, BLK-051, BLK-052, BLK-059,
BLK-060, BLK-061, BLK-063, BLK-064, BLK-065, BLK-066, BLK-079 to
BLK-086, BLK-087, BLK-088 to BLK-100, BLK-101, BLK-102, BLK-103,
BLK-105, BLK-107, BLK-108, BLK-109, BLK-113, BLK-114, BLK-115,
BLK-133, BLK-137, BLK-138, BLK-121, BLK-122, BLK-110, BLK-106,
BLK-139, BLK-140, BLK-141, BLK-142, BLK-143, BLK-144, BLK-145,
BLK-146, BLK-147, BLK-148, BLK-149, BLK-150, BLK-151, BLK-132,
BLK-117, BLK-136, BLK-111, BLK-120, BLK-134, BLK-112, BLK-135, BLK-116,
BLK-152, BLK-153, BLK-154, BLK-155, BLK-125, BLK-126, BLK-127, BLK-124,
BLK-131, BLK-128, BLK-156, BLK-157, BLK-158, BLK-159, BLK-160, BLK-058, BLK-162, BLK-129,
BLK-130, BLK-163, BLK-164, BLK-123, BLK-119, BLK-165, BLK-166

All archived under `implemented/`.

---

## Comms Hygiene

mgmt inbox archived — backend BLK-165 + frontend BLK-166
completions moved to `comms/mgmt/archived/`. Inbox empty.

**BLK-165 COMPLETE** — Persist cost/tokens/timestamps in run
records. 1243 tests (+6 new). Extended `serialize_extraction_result`
with `total_cost_usd`, `total_tokens`, `completed_at`. Fixed
overwrite bug: `save_run` → read-merge-`update_run`. Phase 4
done.

**BLK-166 COMPLETE** — All mock/demo data removed.
`generateMockRuns` deleted from analytics. `sample_invoice.pdf`
fallbacks removed from Pane1AgentConsole + RunComparisonView.
`ExtractionRun` interface extended. Cost + processing time charts
wired to real backend fields. Build clean, 0 TS errors.

**Phase 4 is complete.** 82 items, 1243 tests, frontend clean.

**Phase 5 (ADAS / Agentic Builder) launched.** 9 items promoted
to high priority. Dependency chain analyzed, 5-wave plan created.
Wave 1 assigned: BLK-070 (Surrogate Verifier) + BLK-067 (Template
Composer) to backend, BLK-067 UI to frontend.

**Active work:**
- Backend: BLK-070 (Surrogate Verifier, L) + BLK-067 API (M)
- Frontend: BLK-067 UI (Template Composer, M)
- mgmt: BLK-104 (sample data expansion — ongoing)

**Still open:**
- BLK-161 (mgmt process fix — retract 9.5/10 self-audit score)
- BLK-118 (batch processing queue — both teams, after Phase 5 Wave 2)
- BLK-128 (real provider integration tests — needs BLK-104 fixtures)