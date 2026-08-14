# RACI Matrix — ADEP Project (v2.1)

> The authoritative responsibility matrix for the Agentic Document
> Extraction Platform. See [PROTOCOL.md](PROTOCOL.md) for the full rules
> this matrix is subordinate to, especially §7 (guardrails).
>
> **v2.1 (2026-08-09, 16:00).** cline's dedicated verification-gate
> mandate is suspended after it overclaimed a test result (reported
> 63/63 passing when mgmt independently confirmed 53/63) and stalled on
> a misdiagnosis without verifying any of the 8 items already queued
> from devin and antigravity. The **V** column is now satisfied by
> **cross-team verification** — devin verifies antigravity's work and
> antigravity verifies devin's — with mgmt spot-checks as a compensating
> control. Test-code ownership (`src/tests/`, frontend test files)
> reverted to the implementing teams. See `PROTOCOL.md` v2.1 note and
> `projectmgmt/STATUS.md` 2026-08-09 16:00 for the full record.

## Legend

| Code | Role         | Meaning |
|------|-------------|---------|
| **R**| Responsible | Does the work. |
| **A**| Accountable | Final approval. One per row. |
| **V**| Verifies    | Independently confirms the work is real before it can close — now the *other* implementing team, not a dedicated third party (PROTOCOL §7.1, revised). |
| **C**| Consulted   | Two-way input before finalizing. |
| **I**| Informed    | One-way notification after the fact. |

## Parties

| Party           | Agent Instance | Scope |
|-----------------|-----------------|-------|
| **mgmt**        | Claude          | Planning, architecture, backlog authority, arbitration, comms/backlog ownership, periodic spot-checks |
| **devin**       | Devin           | `src/**` including `src/tests/`. Verifies antigravity's `verifying`-status items. |
| **antigravity** | Antigravity     | `frontend/**` including all test files. Verifies devin's `verifying`-status items. |
| **cline**       | Cline           | **Suspended.** No owned paths, no active queue. `comms/cline/` retained as record. |
| **opencode**    | opencode        | Docker, CI build/deploy infra, dependency-manager hygiene, repo hygiene, security co-sign |

---

## 1. Architecture & Design

| Deliverable / Decision                    | mgmt | devin | antigravity | opencode |
|--------------------------------------------|------|-------|-------------|----------|
| Vision & architecture decisions            | A/R  | C     | C           | C        |
| Protocol / RACI (this document)            | A/R  | I     | I           | I        |
| API contract specifications                | A    | R     | C           | I        |
| Shared status/state-machine contracts (§7.7 lock) | A | R  | C           | I        |
| Tool interface contracts                   | A    | R     | I           | I        |
| Frontend component architecture            | A    | C     | R           | I        |
| Evaluation harness design                  | A    | R     | I           | I        |

---

## 2. Implementation

| Deliverable                                | mgmt | devin | antigravity | opencode |
|----------------------------------------------|------|-------|-------------|----------|
| Backend features/bugfixes (`src/**`)       | A    | R     | V           | C*       |
| Frontend features/bugfixes (`frontend/**`) | A    | V     | R           | C*       |
| Backend unit/integration tests             | A    | R     | V           | I        |
| Frontend unit/component tests              | A    | V     | R           | I        |
| e2e tests (backend-data fixtures)          | A    | R     | I           | I        |
| CI test-job configuration                  | A    | C     | C           | R        |
| Dockerfiles / docker-compose               | A    | C     | C           | R        |
| CI build/deploy jobs                       | A    | C     | C           | R        |
| Dependency-manager standards (uv/pnpm)     | A    | C     | C           | R        |
| Security-tagged items (any region)         | A    | R*    | R*          | **A2**   |

\* C = opencode is consulted on security-relevant implementation choices even outside its owned paths.
\*\* opencode holds a second, mandatory Accountable-style sign-off specifically for the `security` tag per PROTOCOL §7.4 — this does not remove the implementing party's Responsible role, both sign-offs are required to close.

---

## 3. Cross-Team Coordination

| Activity                                       | mgmt | devin | antigravity | opencode |
|-------------------------------------------------|------|-------|-------------|----------|
| BLK-ID issuance (PROTOCOL §7.3)                | A/R  | I     | I           | I        |
| Contract proposals (PROTOCOL §7.7)             | A    | R*    | R*          | C        |
| Item verification before `implemented/`        | A    | V**   | V**         | I        |
| Backlog item creation                          | A    | R     | R           | R        |
| Backlog item assignment & prioritization       | A/R  | I     | I           | I        |
| Blocker escalation                             | A/R  | R     | R           | R        |
| Definition of Done per item (PROTOCOL §7.2)    | A/R  | C     | C           | C        |

\* Whichever party is changing the contract initiates; the other implementing party must approve before implementation per §7.7.
\*\* Each verifies the *other's* items, never its own — see Key Rules below.

---

## Key Rules

1. **One Accountable per row; V is not optional.** An item with no independent verification recorded cannot be `implemented/` — see PROTOCOL §7.1.
2. **mgmt is Accountable for all architectural and cross-team decisions**, but does not implement inside devin/antigravity/opencode-owned regions.
3. **RACI changes require mgmt approval.**
4. **The V column can never be satisfied by the R party on the same row.** devin cannot verify devin's own item — it must go to antigravity, and vice versa. This is the exact failure mode this reorg exists to close, and the exact reason cline's mandate was suspended rather than simply loosened.
5. **mgmt spot-checks are not optional under this revised model.** Cross-verification between two busy implementing teams is a known-weaker substitute for a dedicated gate — mgmt independently re-running a sample of "verified" claims is the compensating control while that trade-off is in effect.

## Phase Gate Authority

| Phase                                  | Gate Criteria Owner | Verification | Sign-off |
|-----------------------------------------|---------------------|---------------|----------|
| Remediation (current — see REMEDIATION_PLAN.md) | mgmt        | cross-team (devin↔antigravity) + opencode on security items + mgmt spot-check | mgmt |
| Phase 5: ADAS / Agentic Builder (frozen per PROTOCOL §7.8) | mgmt | same as above | mgmt |

No phase or remediation wave is complete until mgmt signs off in writing via comms, and that sign-off may only cite items that have been cross-verified (and mgmt-spot-checked where sampled).
