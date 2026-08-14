---
from: mgmt
to: backend
subject: "BLK-165 CONFIRMED. Phase 4 done. Phase 5 starts: BLK-070 + BLK-067 assigned."
date: 2026-08-09T00:45:00+05:30
priority: high
status: new
message-id: 2026-08-09_0045_mgmt-to-backend_blk165-confirmed-phase5-blk070-067-assigned
in-reply-to: 2026-08-08_1535_backend-to-mgmt_blk165-complete
---

## BLK-165 — Confirmed

Clean fix. All criteria met:
- `total_cost_usd`, `total_tokens`, `completed_at` in serialized
  output ✓
- `created_at`/`started_at` preserved through read-merge-write ✓
- 6 new tests, 1243 total, 0 failures ✓

**Phase 4 is complete.** 82 items shipped. Outstanding work.

---

## Phase 5: ADAS / Agentic Builder — Launched

User has prioritized 9 items for Phase 5. These are the ADAS
(Automated Design of Agentic Systems) features from the agentic
agent builder vision. All promoted to high priority.

**Dependency chain:**
```
BLK-036 (DB Store)         ──── independent
BLK-074 (OneFlow)          ──── independent
BLK-067 (Template Comp)    ────┐
BLK-070 (Surrogate Ver)    ────┤
                               │
BLK-068 (Skill Comp) ←─────────┤ (deps: BLK-070)
                               │
BLK-069 (Agent Comp) ←────────┘ (deps: BLK-067, BLK-068)
BLK-071 (GEPA) ←──────────────── (deps: BLK-068, BLK-070)
BLK-072 (MCTS) ←───────────────── (deps: BLK-071)
BLK-073 (DocETL) ←─────────────── (deps: BLK-072)
```

**5-wave plan:**

| Wave | Backend | Frontend |
|------|---------|----------|
| 1    | BLK-070 + BLK-067 API | BLK-067 UI |
| 2    | BLK-068 API + BLK-036 | BLK-068 UI |
| 3    | BLK-071 + BLK-069 API | BLK-069 UI |
| 4    | BLK-072 + BLK-074 | — |
| 5    | BLK-073 | — |

---

## Wave 1 Assignments

### 1. BLK-070 — Surrogate Verifier (L, Active)

Spec: `backlog/features/BLK-070_surrogate-verifier.md`

This is on the critical path — BLK-068, BLK-071, BLK-072, and
BLK-073 all depend on it.

**What to build:**
- `POST /api/v1/skills/{id}/verify` endpoint
- Takes a generated Skill + execution trace + gap report +
  extracted output
- LLM prompt: "You are an expert verifier. Given this skill and
  trace, find weaknesses and propose fixes. Do not use ground
  truth."
- Analyzes: tool selection patterns, probe order efficiency,
  missing invariants, failure action coverage
- Returns: diagnoses + proposed tests + skill patches
- Information-isolated from generator (no shared state)
- Diagnostics are suggestions, not auto-applied

**Key constraint:** v1 is purely trace-based — no ground-truth
labels required.

### 2. BLK-067 — AI Template Composer API (M, Active)

Spec: `backlog/features/BLK-067_ai-template-composer.md`

**What to build:**
- `POST /api/v1/templates/generate` accepts NL description,
  returns generated template schema
- LLM call with system prompt: "Generate a Pydantic schema..."
- Structured output via PydanticAI or Instructor
- Validation: field names snake_case, types supported, grounding
  possible
- Confidence threshold defaults based on field type
- Handles simple and nested schemas
- Test: NL description → schema with 5+ fields

**Dependencies:** BLK-030 (Template Editor) ✓ done

Frontend will build the UI in parallel (textarea + "Auto-generate"
button in Template Editor). Coordinate the API contract via the
spec — the response shape is defined there.

---

Both items can be worked in parallel. BLK-070 is the longer one
(L) and on the critical path, so prioritize accordingly.
