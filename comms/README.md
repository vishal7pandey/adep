# Comms — Inter-Team Messaging System

> A file-based communication protocol for coordinating between mgmt,
> devin, antigravity, cline, and opencode on the ADEP project.
> **v2 (2026-08-09)** — 5-party structure, replaces the old
> mgmt/backend/frontend setup. See [PROTOCOL.md](PROTOCOL.md) for why.

## Quick Start

1. **To send a message**: create a `.md` file in the recipient's `inbox/` using the [email format](PROTOCOL.md#5-email-format).
2. **To work on a message**: move it to `active/`, set `status: in-progress`.
3. **To close a message**: append `## Resolution` + `## Evidence` (required — see [PROTOCOL §7.2](PROTOCOL.md#72-evidence-requirement-closes-backlog-is-not-reliable-evidence-of-what-is-brokenfixed--audit-5)), set `status: done`, move to `archived/`.

## Directory Layout

```
comms/
  README.md   PROTOCOL.md   RACI.md
  mgmt/        {inbox, active, archived}
  devin/       {inbox, active, archived}
  antigravity/ {inbox, active, archived}
  cline/       {inbox, active, archived}
  opencode/    {inbox, active, archived}
```

## Parties

- **mgmt** (Claude) — planning, architecture, backlog authority, arbitration.
- **devin** (Devin) — backend: `src/**` excluding tests.
- **antigravity** (Antigravity) — frontend: `frontend/**` excluding tests.
- **cline** (Cline) — all tests (`src/tests/`, `frontend/**.test.*`, `e2e/`) + the independent verification gate. **Nothing reaches `implemented/` without cline's sign-off.**
- **opencode** (opencode) — Docker, CI build/deploy, dependency-manager hygiene, repo hygiene, and mandatory co-sign on anything tagged `security`.

## What Changed From v1 (and why)

The previous mgmt/backend/frontend structure let each implementing party mark its own work "done" with no independent check. The result, found by an external audit (`ADE_codebase_audit.md`) after `STATUS.md` had already claimed 145 items complete and a 9.5/10 self-audit score: a dead guardrails subsystem, a fake HITL approval gate, an agent loop silently bypassed for most "high-value" accuracy fixtures, an arbitrary file-read vulnerability, and 30 BLK-ID collisions from uncoordinated parallel audits. **cline** and **opencode** exist specifically to close those gaps — cline as the verification gate no implementer can bypass, opencode as the security/infra co-sign and the owner of the "is this build/CI/dependency setup actually consistent" question. Full detail: [PROTOCOL.md §7](PROTOCOL.md#7-guardrails-v2--new).

## Key Rules

- Each party writes only to its owned region (PROTOCOL §2). Cross-boundary changes go through mgmt.
- **No party grades its own homework.** cline verifies before anything closes.
- **Security items need two sign-offs**: the implementer's and opencode's.
- **Only mgmt issues new BLK-IDs.**
- Python: uv only. Frontend: pnpm.
- One message per topic, concrete and actionable, evidence attached before closing.

Read [PROTOCOL.md](PROTOCOL.md) for the full specification and [RACI.md](RACI.md) for who does what.
