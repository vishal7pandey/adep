# Audit Ledger — 2026-08-08

*Auditor: mgmt (Principal Repository Auditor)*
*Scope: Full repository — backend (src/), frontend (frontend/), tests, config*

---

## Pass Plan

| Pass | Focus | Status |
|------|-------|--------|
| 1 | Repository map, architecture, existing issues | Done |
| 2 | Stubs, mocks, placeholders, unfinished work | Done |
| 3 | Core business logic, edge cases, shallow impls | Done |
| 4 | API, integration, persistence, config, errors | Done |
| 5 | Frontend code review, shallow impls, AI slop | Done |
| 6 | Tests, test gaps, doc/impl mismatches | Done |
| 7 | Security, reliability, performance, ops | Done |
| 8 | Final verification, retrospective, summary | Done |

---

## Findings Ledger

| ID | Category | Severity | Confidence | Status | File | Rationale |
|----|----------|----------|------------|--------|------|-----------|
| AUDIT-001 | Mock data | High | High | resolved | Pane1AgentConsole.tsx | startDemoRun is entirely fabricated mock data |
| AUDIT-002 | Bug | Medium | High | resolved | auth.py | _seconds_since uses localtime for UTC timestamp |
| AUDIT-003 | Contract mismatch | High | High | resolved | api.ts / runs.py | fetchRecentRuns expects array, backend returns paginated dict |
| AUDIT-004 | Shallow impl | High | High | resolved | SkillEditor.tsx | handleSave drops system_prompt, probe_order, invariants, failure_actions |
| AUDIT-005 | Shallow impl | Medium | High | resolved | Pane1AgentConsole.tsx | File upload only sets filename, never uploads to backend |
| AUDIT-006 | Shallow impl | Medium | High | resolved | tag_reading.py | read_tag hardcodes tesseract OCR, ignores configured provider |
| AUDIT-007 | Performance | Low | High | resolved | serialization.py | _serialize_graphml uses edges.index(edge) — O(n²) |
| AUDIT-008 | Contract mismatch | Medium | High | resolved | api.ts | Skill interface missing fields backend accepts |
| AUDIT-009 | Shallow impl | Medium | High | resolved | SkillEditor.tsx | addInvariant/addFailureAction use Date.now() for IDs — collision-prone |
| AUDIT-010 | Shallow impl | Low | High | resolved | serialization.py | _serialize_dexpi uses edges.index(edge) — O(n²) |
| AUDIT-011 | Mock data | High | High | resolved | Pane2ExtractedData.tsx | DEMO_FIELDS hardcoded mock extraction results |
| AUDIT-012 | Hardcoded | Medium | High | resolved | Pane3DocumentViewer.tsx | totalPages=2 hardcoded, hex colors not themed |
| AUDIT-013 | Bug | Medium | High | resolved | webhooks.py route | test_webhook sends without HMAC signature, dead variable |
| AUDIT-014 | Security | High | High | resolved | store.py | Path traversal — entity IDs not sanitized |
| AUDIT-015 | Test gap | Low | High | resolved | test_wave7.py | No test for POST /webhooks/{id}/test endpoint |

---

## Rejected / Duplicate

| ID | Reason |
|----|--------|
| AUDIT-D01 | SSE replay not live — already tracked as BLK-090/BLK-129 |
| AUDIT-D02 | Agent control endpoints are no-ops on synchronous runs — already tracked as BLK-129 |
| AUDIT-D03 | Skills API drops data — already tracked as BLK-121 (backend fixed, frontend tracked as AUDIT-004) |

---

## Blocked / Unverified

| Area | Reason |
|------|--------|
| Test execution | Cannot run pytest on Windows without verifying env setup |
| Frontend build | Cannot run next build without verifying env setup |

---

## Issue File Cross-Reference

| AUDIT ID | BLK ID | File |
|----------|--------|------|
| AUDIT-001 | BLK-139 | backlog/features/BLK-139_startDemoRun-mock-data.md |
| AUDIT-002 | BLK-140 | backlog/features/BLK-140_seconds-since-timezone-bug.md |
| AUDIT-003 | BLK-141 | backlog/features/BLK-141_fetchRecentRuns-contract-mismatch.md |
| AUDIT-004 | BLK-142 | backlog/features/BLK-142_skilleditor-drops-form-data.md |
| AUDIT-005 | BLK-143 | backlog/features/BLK-143_file-upload-not-uploaded.md |
| AUDIT-006 | BLK-144 | backlog/features/BLK-144_read-tag-hardcodes-tesseract.md |
| AUDIT-007+010 | BLK-145 | backlog/features/BLK-145_graphml-dexpi-on2-edge-ids.md |
| AUDIT-008 | BLK-146 | backlog/features/BLK-146_frontend-skill-interface-incomplete.md |
| AUDIT-009 | BLK-147 | backlog/features/BLK-147_skilleditor-date-now-id-collision.md |
| AUDIT-011 | BLK-148 | backlog/features/BLK-148_pane2-demo-fields-mock-data.md |
| AUDIT-012 | BLK-149 | backlog/features/BLK-149_pane3-hardcoded-pages-colors.md |
| AUDIT-013 | BLK-150 | backlog/features/BLK-150_test-webhook-no-signature.md |
| AUDIT-014 | BLK-151 | backlog/features/BLK-151_path-traversal-entity-ids.md |
