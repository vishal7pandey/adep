# Communication Protocol

> The authoritative contract governing how the four parties — **mgmt**,
> **backend**, **frontend**, and **reviewer** — communicate, coordinate, and respect
> boundaries within the ADEP project.
>
> **See also:** [RACI.md](RACI.md) for the responsibility assignment matrix.

---

## 1. Parties & Roles

| Party       | Agent Instance  | Responsibilities                                                      |
|-------------|-----------------|-----------------------------------------------------------------------|
| **mgmt**    | Cascade (you)   | Engineering management, product ownership, architecture, research,    |
|             |                 | review, task assignment, cross-team coordination, final approval.     |
| **backend** | Devin           | Backend development: Python package `ade/`, APIs, tools, providers,   |
|             |                 | agent logic, skills, templates, tests, infrastructure.               |
| **frontend**| Antigravity     | Frontend development: UI, client-side code, user-facing interfaces,   |
|             |                 | visual assets, frontend build tooling.                               |
| **reviewer**| External agent  | Independent adversarial review: security, reliability, process,      |
|             |                 | architecture audit. Read-only mandate. Sends findings to mgmt inbox. |
|             |                 | No write access to implementation code or team inboxes.              |

---

## 2. Code Boundaries

Each party owns a specific region of the codebase. **No party may modify
files outside its owned region without explicit written approval from mgmt
delivered via the comms system.**

### 2.1 Owned Regions

| Party       | Owned Paths (may freely modify)                                      |
|-------------|----------------------------------------------------------------------|
| **mgmt**    | `comms/`, `projectmgmt/`, `backlog/`, `implemented/`, `vision.md`,   |
|             | `README.md`, `pyproject.toml` (project metadata), `.env.example`,   |
|             | `.gitignore`, project-level config, architecture docs.               |
| **backend** | `src/` (the Python package), `notebooks/`, `pyproject.toml`          |
|             | (dependency additions only — removals need mgmt approval),           |
|             | `uv.lock`. Also owns `src/tests/` for the pytest suite.              |
| **frontend**| `frontend/` (to be created), any UI/client directories, static      |
|             | assets, frontend build config.                                       |

### 2.2 Shared Read-Only

All parties may **read** everything. Writing is what is restricted.

### 2.3 Boundary Violations

If a party needs a change outside its owned region, it must:

1. Write an email to `mgmt/inbox/` requesting the change with justification.
2. Wait for mgmt to either perform the change or grant written exception.
3. Never bypass the protocol by editing files directly.

---

## 3. Directory Structure

```
comms/
  PROTOCOL.md              ← this file
  README.md                ← quick-start overview
  mgmt/
    inbox/                 ← messages addressed TO mgmt
    active/                ← messages mgmt is currently working on
    archived/              ← completed/closed messages
  backend/
    inbox/                 ← messages addressed TO backend
    active/                ← messages backend is currently working on
    archived/              ← completed/closed messages
  frontend/
    inbox/                 ← messages addressed TO frontend
    active/                ← messages frontend is currently working on
    archived/              ← completed/closed messages
```

---

## 4. Message Lifecycle

Every message (an "email" `.md` file) moves through three states:

```
inbox/  →  active/  →  archived/
 (new)     (in-progress)  (done)
```

### 4.1 Sending a Message

1. The sender creates a `.md` file in the **recipient's `inbox/`** directory.
2. File naming convention: `YYYY-MM-DD_HHMM_from-to_slug.md`
   - Example: `2026-08-07_1430_mgmt-to-backend_add-ocr-provider.md`
3. The recipient picks up the message from their inbox, moves it to their
   `active/` folder when work begins, and to `archived/` when the work is
   complete or the message is closed.

### 4.2 Replying

Replies are **new messages** sent back to the original sender's `inbox/`.
The reply's `in-reply-to` frontmatter field references the original message
filename.

### 4.3 Closing a Message

The party that owns the message (the recipient) moves it to `archived/`
once the requested work is done or the conversation is concluded. The
archiver should append a `## Resolution` section to the message before
archiving.

---

## 5. Email Format

Every message is a Markdown file with YAML frontmatter followed by a
body. The format is intentionally email-like.

### 5.1 Frontmatter Schema

```yaml
---
from: mgmt              # sender party: mgmt | backend | frontend | reviewer
to: backend             # recipient party: mgmt | backend | frontend
subject: "Add new OCR provider"
date: 2026-08-07T14:30:00+05:30   # ISO 8601 with timezone
priority: high          # high | medium | low
status: new             # new | in-progress | blocked | done | closed
in-reply-to: null       # filename of the message this replies to (or null)
message-id: 2026-08-07_1430_mgmt-to-backend_add-ocr-provider
---
```

### 5.2 Body Structure

```markdown
## Context

<Why this message exists. Background the recipient needs.>

## Request

<What specifically needs to be done. Be concrete and actionable.>

## Acceptance Criteria

- [ ] <Criterion 1>
- [ ] <Criterion 2>

## Constraints

<Any deadlines, technical constraints, or things to avoid.>

## Notes

<Optional: references, links, additional context.>
```

### 5.3 Resolution Section (added before archiving)

```markdown
## Resolution

<What was done. Outcome. Any follow-up messages spawned.>
```

---

## 6. Communication Rules

1. **One message per topic.** Don't bundle unrelated requests.
2. **Be concrete.** Vague messages like "improve the code" are invalid.
   State exactly what, where, and why.
3. **Respect boundaries.** A message to backend asking for frontend changes
   will be rejected. Route to the correct party.
4. **Acknowledge receipt.** When a party picks up a message from inbox to
   active, they should update the `status` field to `in-progress`.
5. **Report blockers early.** If work is blocked, set `status: blocked` and
   send a reply to the sender explaining the blocker.
6. **No direct edits across boundaries.** All cross-boundary work requests
   go through comms messages.
7. **mgmt arbitrates.** If backend and frontend disagree on an interface,
   both send messages to mgmt. Mgmt decides and issues directives.
8. **mgmt does not implement code in backend or frontend regions.** mgmt
   is Accountable (A) for review and approval, but the Responsible (R)
   party does the implementation. mgmt may edit files in its own owned
   region (`comms/`, `projectmgmt/`, `backlog/`, `implemented/`,
   `vision.md`, project-level config) but must not directly edit
   `src/` or `frontend/` files. All code changes in those regions are
   requested via comms messages and implemented by the owning party.

---

## 7. Interface Contracts

When backend and frontend need to agree on an API or data contract:

1. Mgmt (or the requesting party) writes a contract proposal email.
2. The proposal goes to both `backend/inbox/` and `frontend/inbox/`.
3. Each party reviews and replies with approval or requested changes.
4. Once both approve, mgmt writes the final contract to
   `comms/contracts/` (created on demand) and both parties implement
   against it.
5. Any subsequent changes to the contract require a new proposal cycle.

---

## 8. Escalation

| Situation                              | Action                                     |
|----------------------------------------|--------------------------------------------|
| Boundary violation detected            | Email `mgmt/inbox/` with `priority: high`  |
| Blocked on another party's deliverable | Email that party's `inbox/`, cc mgmt by    |
|                                        | also emailing `mgmt/inbox/`                |
| Architecture decision needed           | Email `mgmt/inbox/` with full context      |
| Contract dispute                       | Both parties email `mgmt/inbox/`           |

---

## 9. File Naming Convention

```
YYYY-MM-DD_HHMM_from-to_slug.md
```

- **Date/time**: sender's local time at composition.
- **from-to**: lowercase party names, hyphen-separated.
- **slug**: short kebab-case description (max 5 words).

Examples:
- `2026-08-07_1430_mgmt-to-backend_add-ocr-provider.md`
- `2026-08-07_1520_backend-to-mgmt_ocr-provider-blocked.md`
- `2026-08-07_1600_frontend-to-backend_api-schema-question.md`

---

## 10. Tooling Standards

### 10.1 Python Package Management

**uv is the only allowed Python package manager.** No pip, no poetry,
no conda, no pipenv.

- Use `uv add <package>` to add dependencies
- Use `uv remove <package>` to remove dependencies (requires mgmt
  approval per §2.1)
- Use `uv sync` to install from `pyproject.toml` / `uv.lock`
- Use `uv run pytest` to run tests
- Use `uv run python -m src.api.main` to start the server

The project must use `pyproject.toml` (not `setup.py` or
`requirements.txt` alone) as the dependency source of truth.
`uv.lock` must be committed to the repository.

If `requirements.txt` exists for backwards compatibility, it must be
generated from `pyproject.toml` via `uv export --format requirements-txt`.

### 10.2 Frontend Package Management

Frontend uses npm (or pnpm if the frontend team prefers). This is
the frontend team's decision within their owned region.

