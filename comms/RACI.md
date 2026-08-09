# RACI Matrix — ADEP Project

> The authoritative responsibility matrix for the Agentic Document Extraction
> Platform. Defines who is **R**esponsible, **A**ccountable, **C**onsulted,
> and **I**nformed for every major deliverable and decision.

---

## Legend

| Code | Role         | Meaning                                                        |
|------|-------------|----------------------------------------------------------------|
| **R**| Responsible | Does the work. Owns execution.                                |
| **A**| Accountable | Final approval. One per row. Signs off on quality/completeness.|
| **C**| Consulted   | Provides input/expertise before work is finalized. Two-way comms.|
| **I**| Informed    | Kept in the loop after decisions/work. One-way notification.   |

---

## Parties

| Party     | Agent Instance  | Scope                                         |
|----------|-----------------|-----------------------------------------------|
| **mgmt** | Cascade         | Design, planning, architecture, review, comms |
| **backend** | Devin        | Python backend: `src/`, `notebooks/`, `tests/` |
| **frontend**| Antigravity  | Frontend: `frontend/`, UI, client-side code    |

---

## 1. Architecture & Design

| Deliverable / Decision                        | mgmt | backend | frontend |
|----------------------------------------------|------|---------|----------|
| Vision & architecture decisions (§9)          | A/R  | C       | C        |
| RACI matrix (this document)                   | A/R  | I       | I        |
| Communication protocol (PROTOCOL.md)          | A/R  | I       | I        |
| API contract specifications                   | A    | R       | C        |
| Agent Definition data model                   | A    | R       | C        |
| Tool interface contracts (ToolSpec, Grounding)| A    | R       | I        |
| Frontend component architecture               | A    | C       | R        |
| State model design (LangGraph State)          | A    | R       | I        |
| Definition Store schema (file-based v1)       | A    | R       | I        |
| Evaluation harness design                     | A    | R       | I        |

---

## 2. Backend Implementation (Phase 1: Engine)

| Deliverable                                    | mgmt | backend | frontend |
|-----------------------------------------------|------|---------|----------|
| Tool interface contracts (ToolSpec, Grounding) | A    | R       | I        |
| Package scaffolding (src/ layout)              | A    | R       | I        |
| LangGraph State + node skeletons              | A    | R       | I        |
| Tool Registry implementation                  | A    | R       | I        |
| PaddleOCR provider                             | A    | R       | I        |
| Tesseract provider                             | A    | R       | I        |
| Azure GPT-5.4 VLM provider                     | A    | R       | I        |
| PIL + OpenCV geometry provider                 | A    | R       | I        |
| ReAct graph (plan/act/observe/reflect/terminate)| A  | R       | I        |
| Outcome Validator (deterministic gap-report)   | A    | R       | I        |
| Give-up caps (per-field, per-document)         | A    | R       | I        |
| InvoiceSkill implementation                    | A    | R       | I        |
| InvoiceTemplate implementation                 | A    | R       | I        |
| `run()` entry point                            | A    | R       | I        |
| Unit tests (pytest, mocked providers)          | A    | R       | I        |
| Evaluation harness                             | A    | R       | I        |

---

## 3. Backend Implementation (Phase 2: Platform API)

| Deliverable                                    | mgmt | backend | frontend |
|-----------------------------------------------|------|---------|----------|
| AgentDefinition model (serializable composition)| A  | R       | C        |
| Definition Store (file-based CRUD)             | A    | R       | I        |
| FastAPI app scaffold                           | A    | R       | C        |
| REST: /definitions endpoints                   | A    | R       | C        |
| REST: /skills endpoints                        | A    | R       | C        |
| REST: /templates endpoints                     | A    | R       | C        |
| REST: /runs endpoints                          | A    | R       | C        |
| WebSocket: streaming run progress              | A    | R       | C        |
| run(definition, input) wiring through API      | A    | R       | I        |
| API integration tests                          | A    | R       | I        |

---

## 4. Frontend Implementation (Phase 3: UI)

| Deliverable                                    | mgmt | backend | frontend |
|-----------------------------------------------|------|---------|----------|
| Frontend project scaffold (React + Tailwind + shadcn) | A | C | R |
| API client (REST + WebSocket)                  | A    | C       | R        |
| Chat Interface                                 | A    | C       | R        |
| Skill Editor (structured form)                 | A    | C       | R        |
| Template Editor (schema builder UI)            | A    | C       | R        |
| Agent Definition Builder (wizard)              | A    | C       | R        |
| Real-time reasoning trace display              | A    | C       | R        |
| Structured result viewer                       | A    | C       | R        |
| Frontend tests (unit + e2e)                    | A    | I       | R        |

---

## 5. Cross-Team Coordination

| Activity                                       | mgmt | backend | frontend |
|-----------------------------------------------|------|---------|----------|
| API contract negotiation                       | A    | R       | R        |
| Interface contract approval                    | A    | C       | C        |
| Cross-boundary change requests                 | A    | R*      | R*       |
| Sprint / phase planning                        | A/R  | C       | C        |
| Phase gate review & sign-off                   | A/R  | C       | C        |
| Risk & blocker escalation                      | A/R  | R       | R        |
| Definition of Done per phase                   | A/R  | C       | C        |
| comms/ protocol maintenance                    | A/R  | I       | I        |

\* *The requesting party writes the comms message; mgmt approves the cross-boundary work.*

---

## 6. Operations & Infrastructure

| Deliverable                                    | mgmt | backend | frontend |
|-----------------------------------------------|------|---------|----------|
| pyproject.toml / uv.lock (dependency additions) | A  | R       | I        |
| pyproject.toml / uv.lock (dependency removals) | A/R  | C       | I        |
| Tooling standards (uv, npm, etc.)              | A/R  | C       | C        |
| .env.example maintenance                       | A/R  | C       | I        |
| .gitignore maintenance                         | A/R  | C       | C        |
| README.md maintenance                          | A/R  | C       | C        |
| vision.md maintenance                          | A/R  | C       | C        |
| Deployment configuration                       | A    | R       | C        |
| CI/CD pipeline                                 | A    | R       | C        |
| Backlog item creation                          | A    | R       | R        |
| Backlog item assignment & prioritization       | A/R  | I       | I        |
| STATUS.md updates                              | A/R  | I       | I        |
| Item lifecycle (move backlog → in-progress → implemented) | A | R | R |
| Phase gate review & sign-off                   | A/R  | C       | C        |

---

## Key Rules

1. **One Accountable per row.** If a row shows `A` for mgmt only, mgmt is
   the approver — the Responsible party does the work but mgmt signs off.
2. **mgmt is Accountable for all architectural decisions.** Backend and
   frontend are Responsible for implementation within their owned regions,
   but mgmt reviews and approves design choices.
3. **Cross-boundary work requires comms.** If backend needs a frontend change
   (or vice versa), the requesting party sends a comms message to mgmt. Mgmt
   either performs the change or grants written exception (per PROTOCOL.md §2.3).
4. **Consulted means two-way communication.** The Responsible party must seek
   input from Consulted parties before finalizing. Use comms messages, not
   ad-hoc edits.
5. **Informed means one-way notification.** The Responsible party sends a
   comms message to the Informed party after completion. No response required.
6. **RACI changes require mgmt approval.** Only mgmt may add, remove, or
   reassign roles in this matrix.

---

## Phase Gate Authority

| Phase  | Gate Criteria Owner | Implementation Reviewer | Sign-off |
|--------|--------------------|------------------------|----------|
| Phase 1: Engine       | mgmt | mgmt | mgmt |
| Phase 2: Platform API | mgmt | mgmt + frontend (C) | mgmt |
| Phase 3: Frontend     | mgmt | mgmt + backend (C) | mgmt |
| Phase 4: Polish       | mgmt | mgmt | mgmt |

No phase is considered complete until mgmt signs off in writing via a comms
message to both backend and frontend inboxes.
