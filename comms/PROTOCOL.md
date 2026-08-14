# Communication Protocol

> The authoritative contract governing how the five parties — **mgmt**,
> **devin**, **antigravity**, **cline**, and **opencode** — communicate,
> coordinate, and respect boundaries within the ADEP project.
>
> **v2 (2026-08-09).** Supersedes the 3-party (mgmt/backend/frontend)
> version of this document. Rewritten as part of the mgmt takeover
> triggered by `ADE_codebase_audit.md` and the accumulated bug backlog —
> see `projectmgmt/REMEDIATION_PLAN.md` for why this reorg happened and
> what it is meant to fix. **The previous version of this protocol had no
> independent verification step, and the result is on record**: a
> `STATUS.md` claiming "145 items complete" and a "9.5/10" self-audit
> score, while the actual code shipped fake HITL approval gates, a
> guardrails subsystem that is 100% dead code, an agent loop silently
> bypassed for 7 of 9 "high-value" accuracy fixtures, an arbitrary
> file-read vulnerability, plaintext-logged admin credentials, and 30
> separate BLK-ID collisions from uncoordinated parallel audits. Every
> guardrail added in §7 below exists to close one of those specific
> failure modes. Read §7 first.
>
> **See also:** [RACI.md](RACI.md) for the responsibility matrix,
> [projectmgmt/REMEDIATION_PLAN.md](../projectmgmt/REMEDIATION_PLAN.md)
> for the actual work plan.
>
> **v2.1 (2026-08-09, 16:00) — cline's mandate suspended.** In its first
> working cycle, cline reported `BLK-246` as "63 tests passing" when the
> real number (mgmt-verified by running the suite directly) was 53/63,
> then stalled entirely on a misdiagnosis of a bug that no longer existed
> in the code it was debugging, and verified zero of the 8 items already
> queued up from devin and antigravity. §7.1 is rewritten below to use
> **cross-team verification** (devin verifies antigravity's work and vice
> versa) instead of a dedicated third-party gate. Test-code ownership
> reverts to §2.1's original devin/antigravity split. This is a pause,
> not a deletion — `comms/cline/` stays intact as a record, and the role
> can resume if reinstated. opencode's mandate and §7.4 are unaffected.

---

## 1. Parties & Roles

| Party           | Agent Instance | Responsibilities |
|-----------------|-----------------|-------------------|
| **mgmt**        | Claude (you)    | Engineering management, product ownership, architecture, backlog authority, BLK-ID issuance, cross-team arbitration, final approval. Does not implement in owned regions of other parties. |
| **devin**       | Devin           | Backend: the Python package `src/` — API routes, agent loop, providers, tools, skills, templates, run engine, auth/security logic that lives in backend code, **and `src/tests/`** (test ownership reverted from cline, see v2.1 note above). Also cross-verifies antigravity's `verifying`-status items (§7.1). |
| **antigravity** | Antigravity     | Frontend: `frontend/` — UI, client-side code, user-facing interfaces, visual assets, frontend build tooling, **and all frontend test files** (`*.test.*`, `*.spec.*`, `__tests__/`, reverted from cline, see v2.1 note above). Also cross-verifies devin's `verifying`-status items (§7.1). |
| **cline**       | Cline           | **Mandate suspended 2026-08-09 (v2.1 note above).** Was quality/verification/test engineering with a dedicated independent-verification gate. `comms/cline/` retained as historical record; no owned paths while suspended. |
| **opencode**    | opencode        | Platform, infra, security posture, and repo hygiene: Dockerfiles, `docker-compose*.yml`, CI/CD pipeline infra (build/lint/deploy jobs — test-content steps coordinate with whichever of devin/antigravity owns that suite), `Makefile`, dependency-manager standards enforcement (uv-only / pnpm-only), `.gitignore`, `.env.example`, deployment config, and top-level repo cleanliness. Mandatory co-signer on any backlog item tagged `security` (§7.4), regardless of which team's files it touches. |

No party may modify files outside its owned region without explicit written approval from mgmt delivered via the comms system. See §2 for exact boundaries and §7 for the guardrails that make this enforceable rather than aspirational.

---

## 2. Code Boundaries

### 2.1 Owned Regions (write access)

| Party           | Owned Paths (may freely modify) |
|-----------------|-----------------------------------|
| **mgmt**        | `comms/`, `projectmgmt/`, `backlog/` (incl. `implemented/`), `vision.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, top-level project metadata, `.env.example` *policy* (opencode owns the file's mechanical upkeep, mgmt owns what belongs in it), architecture docs, `ADE_codebase_audit.md` and any future audit reports. |
| **devin**       | `src/**` **including `src/tests/`** (reverted from cline, v2.1). `pyproject.toml` (dependency *additions* only — removals need mgmt approval). `notebooks/` if actively used (see BLK-201 — otherwise slated for removal by opencode). |
| **antigravity** | `frontend/**` **including all test files** (`*.test.*`, `*.spec.*`, `__tests__/**`, reverted from cline, v2.1). `package.json` dependency additions within `frontend/`. |
| **cline**       | *(none while suspended — v2.1)* |
| **opencode**    | `Dockerfile*`, `docker-compose*.yml`, `Makefile`, `.github/workflows/*` (build/lint/deploy jobs; test-execution steps now coordinate with whichever of devin/antigravity owns that test suite — see §2.3), `.gitignore`, `.env.example` (mechanical upkeep), `uv.lock` / `pnpm-lock.yaml` hygiene, `requirements*.txt` (if retained), top-level repo structure (no stray files at repo root — see §7.6). |

`e2e/**` and cross-stack test fixtures: owned by whichever team's domain the fixture primarily exercises (devin for definition/backend-data fixtures, antigravity for UI-flow fixtures) — see `REMEDIATION_PLAN.md` for the current split.

### 2.2 Shared Read-Only

All parties may **read** everything, including each other's owned regions, comms inboxes, and the full backlog. Reading is never restricted. Writing is what is restricted.

### 2.3 Files With Split Ownership

Some files legitimately need edits from two parties (e.g. a single `.github/workflows/ci.yml` with both a build job and a test job). For these:

1. The file's *dominant* owner (per §2.1) makes the edit.
2. If a party needs to touch a line inside a section owned by another party within the same file, it proposes the exact diff via a comms message instead of editing directly.
3. mgmt may split such a file into owner-clean pieces (e.g. `ci-build.yml` + `ci-test.yml`) if the shared-ownership friction becomes recurring.

### 2.4 Boundary Violations

If a party needs a change outside its owned region:

1. Write a message to `mgmt/inbox/` requesting the change with justification.
2. Wait for mgmt to either perform the change or grant a written, scoped exception.
3. Never bypass the protocol by editing files directly.

A boundary violation discovered after the fact (e.g. via `git diff` showing a party's commit touching another party's paths) is treated as a **priority: high** finding, filed by whoever finds it (any party, including the offending one) directly to `mgmt/inbox/`, no exceptions.

---

## 3. Directory Structure

```
comms/
  PROTOCOL.md              ← this file
  RACI.md                  ← responsibility matrix
  README.md                ← quick-start overview
  mgmt/        {inbox, active, archived}
  devin/       {inbox, active, archived}
  antigravity/ {inbox, active, archived}
  cline/       {inbox, active, archived}
  opencode/    {inbox, active, archived}
```

---

## 4. Message Lifecycle

Unchanged from v1: `inbox/ → active/ → archived/`.

1. The sender creates a `.md` file in the **recipient's `inbox/`**.
2. Naming: `YYYY-MM-DD_HHMM_from-to_slug.md` (e.g. `2026-08-09_1400_mgmt-to-devin_p0-security-queue.md`).
3. The recipient moves it to `active/` when work begins (`status: in-progress`), and to `archived/` when closed, with a `## Resolution` section appended (§7.1 defines what "closed" now requires).

Replies are new messages sent back to the original sender's `inbox/`, referencing the original via `in-reply-to`.

---

## 5. Email Format

### 5.1 Frontmatter Schema

```yaml
---
from: mgmt              # mgmt | devin | antigravity | cline | opencode
to: devin                # mgmt | devin | antigravity | cline | opencode
subject: "Add new OCR provider"
date: 2026-08-09T14:30:00+05:30
priority: high           # critical | high | medium | low
status: new              # new | in-progress | blocked | done | closed
in-reply-to: null
message-id: 2026-08-09_1400_mgmt-to-devin_add-ocr-provider
---
```

### 5.2 Body Structure

```markdown
## Context
## Request
## Acceptance Criteria
- [ ] <Criterion 1>
## Constraints
## Notes
```

### 5.3 Resolution Section (added before archiving)

```markdown
## Resolution

<What was done. Outcome.>

## Evidence

<Required per §7.2 — command output, test names + pass/fail, a diff
excerpt, or a screenshot reference. "It works" / "done" / "verified"
with no attached evidence is not a valid resolution and will bounce.>
```

---

## 6. Communication Rules

1. **One message per topic.** Don't bundle unrelated requests.
2. **Be concrete.** State exactly what, where, and why.
3. **Respect boundaries.** A message asking a party to touch files outside its §2.1 region is invalid — route to the owning party or to mgmt.
4. **Acknowledge receipt.** Moving inbox → active sets `status: in-progress`.
5. **Report blockers early.** `status: blocked` + explain in a reply.
6. **No direct edits across boundaries.**
7. **mgmt arbitrates** interface/contract disagreements between any two parties.
8. **mgmt does not implement in devin/antigravity/cline/opencode-owned regions.** mgmt is Accountable for review/approval; the Responsible party implements.
9. **No party grades its own homework.** A party may not mark its own backlog item `done`/`implemented` — see §7.1.

---

## 7. Guardrails (v2 — new)

These exist because the v1 protocol was pure honor system and the honor system failed in specific, documented ways. Each guardrail below names the failure it closes.

### 7.1 Independent Verification Gate — cross-team model (closes: false-success/overclaim pattern — BLK-219→BLK-287 hallucinated-success-through-fallback-bypass, BLK-221 false-success-through-status-mapping, BLK-281 treating-max-iterations-as-success, the retracted 9.5/10 self-audit)

**Revised 2026-08-09 16:00 (v2.1).** The original design routed every
verification through a dedicated third party (cline). That role is
suspended (see the note at the top of this document) after it
overclaimed a test result and stalled on a misdiagnosis without
verifying anything in its queue. The *principle* — no party grades its
own homework — is unchanged. The *mechanism* is now cross-team peer
verification between the two implementing teams:

- No backlog item may move from `backlog/in-progress/` to `implemented/` on the strength of the implementing party's own claim.
- The implementing party finishes the work, appends `## Resolution` + `## Evidence` (§7.2), and sends the item via comms with `status: verifying` to the **other** implementing team: **devin's backend items are verified by antigravity; antigravity's frontend items are verified by devin.** opencode's items are verified by whichever of devin/antigravity is less loaded, assigned by mgmt case by case. The item physically stays in `backlog/in-progress/` until verified.
- **The verifier re-runs the acceptance criteria independently**: runs the test, hits the endpoint, reads the diff against the claim. It does not trust the Resolution text; it trusts what it can reproduce. This means devin must be able to run `pnpm test`/hit the UI, and antigravity must be able to run `pytest`/`curl` the API — both are full engineering agents, this is not a specialization gap.
- The verifier either (a) appends a `## Verified by <verifier>` section with what it independently confirmed and moves the item to `implemented/`, or (b) reopens it with a comms message back to the implementer listing exactly what didn't hold up.
- **A party may never verify its own item.** If devin implemented it, devin cannot also be the one who signs it off, even informally.
- Security-tagged items still need opencode's co-sign in addition to cross-verification (§7.4) — that requirement is unaffected by this revision.
- mgmt is the appeals path if a party disputes a verification verdict, not a bypass around it, and **mgmt performs its own periodic spot-checks on top of cross-verification** (demonstrated 2026-08-09: running `pnpm test` directly caught cline's overclaim before it reached this stage) — cross-verification between two busy implementing teams is a known-weaker substitute for a dedicated gate, and mgmt spot-checking is the compensating control while that trade-off is in effect.
- Exception: mgmt's own work in mgmt-owned regions (comms/, backlog/, docs) does not require cross-verification — but factual claims mgmt makes about *other* teams' code must still be sourced from a verified item or mgmt's own direct check, not restated from memory.

### 7.2 Evidence Requirement (closes: "backlog is not reliable evidence of what's broken/fixed" — audit §5)

A `## Resolution` section is incomplete, and the verifying team (§7.1) must bounce it, unless it includes at least one of:
- Exact test command + pass/fail output (`pytest src/tests/test_x.py -v` output, not "tests pass").
- A `curl`/HTTP transcript for API behavior claims.
- A diff or file:line reference for code-shape claims ("the guard is now at `run_engine.py:142`").
- A screenshot reference for UI claims.

Vague resolutions ("fixed", "verified", "works now") with no attached evidence are treated as **not done**.

### 7.3 Single BLK-ID Authority (closes: 30 BLK-ID collisions from uncoordinated parallel audits — BLK-292)

- **Only mgmt issues new BLK-IDs.** A party that identifies a new bug/idea/tech-debt item sends the description to `mgmt/inbox/`; mgmt assigns the next sequential ID and creates the file.
- If an external or parallel audit process generates its own numbered findings outside this flow, mgmt re-numbers them into the canonical sequence *before* they land in `backlog/` — never after.
- Any party that discovers a duplicate ID reports it to mgmt immediately (`priority: high`) rather than silently working around it.

### 7.4 Security Co-Sign (closes: SSRF, arbitrary file read (BLK-241), auth fail-open (BLK-215), plaintext-logged admin secret (BLK-186/188), rate-limit-off-by-default (BLK-279))

- Any backlog item tagged `security` requires **opencode's written sign-off** in addition to cross-team verification (§7.1) before it can close — even when the fix lives entirely inside `src/` or `frontend/`.
- opencode's sign-off is a comms reply confirming the fix was read and the specific exploit scenario in the ticket no longer reproduces. This is a review/comment authority, not a write grant into devin's or antigravity's regions.
- mgmt maintains the list of `security`-tagged items as a standing P0 lens across all four teams' queues (see REMEDIATION_PLAN.md).

### 7.5 Dead-Code / Decorative-Code Ban (closes: guardrails subsystem 100% unwired — BLK-265; decorative prompt-injection detector — BLK-183/211; eval/benchmarks unwired — BLK-268)

- A module's docstring or a UI label may not claim a safety, validation, or protective behavior unless the cross-verifying team (§7.1) has confirmed (with a call-graph check or an integration test that would fail if the code were deleted) that production code paths actually invoke it.
- If code is written but not wired in, the correct backlog state is `tech-debt`, not `implemented`, and the docstring must say so ("not yet wired into the execution path") until it is.
- mgmt runs a periodic "wired vs. dead" cross-reference (grep every module's public symbols against every caller outside its own tests) as a standing recurring task while no dedicated QA role exists — this is the same check that found the guardrails subsystem (BLK-265) and should not depend on an external audit to repeat.

### 7.6 Repo Hygiene Ownership (closes: misplaced `app/` at root, duplicate `implemented/` dir, orphaned wrapper scripts, `vision.backup.*` files, `.tsbuildinfo` committed, course notebooks in repo, comms files committed to git history in bulk)

- opencode owns keeping the repo root clean: no stray scripts, no build artifacts, no backup files with timestamps in the name. Anything opencode finds outside an owned region gets filed as a BLK item routed to whichever team owns the correct destination (mgmt if it's ambiguous).
- Before any party commits, it should not need to `git add -A` — see CLAUDE.md guidance on staging specific files.

### 7.7 Contract-Change Lock (closes: run-metadata contract drift — BLK-185, status-contract drift across SSE/store/UI — BLK-280, unified state-machine contract — BLK-282, backend/frontend status mismatch — BLK-232)

- Shared contracts (run status enum, SSE event schema, run metadata fields, any type that crosses the `src/` ↔ `frontend/` boundary) cannot be changed by one party unilaterally.
- Changing party writes a contract proposal to **both** other code-owning parties' inboxes (per §9) — the recipient owns updating their own tests against the new contract per §2.1 — and opencode is CC'd if the change touches CI.
- All recipients must reply approve/object before the change ships. mgmt arbitrates disagreement.
- Cline blocks verification of any item that changed a shared contract without a contract-proposal message-id referenced in its Notes section.

### 7.8 Feature Freeze During Remediation (closes: scope creep — audit §7, "37,846 lines grown from a 5-notebook course exercise")

- No new Phase 5 (ADAS / agentic-builder) feature work — `BLK-067` through `BLK-076` and similar — starts until every `critical` and `high` priority item in `projectmgmt/REMEDIATION_PLAN.md` is `implemented/` and cross-team-verified (§7.1).
- mgmt may grant a scoped exception in writing; default is frozen.
- This is a priority-sequencing rule, not a permanent cancellation — see REMEDIATION_PLAN.md §Sequencing.

---

## 8. Interface Contracts

Unchanged mechanism, now subject to §7.7's lock: mgmt (or the requesting party) writes a contract proposal, sends to all affected inboxes, all approve, mgmt commits the final contract to `comms/contracts/` (created on demand).

---

## 9. Escalation

| Situation                              | Action |
|-----------------------------------------|--------|
| Boundary violation detected             | Message `mgmt/inbox/`, `priority: high` |
| Blocked on another party's deliverable  | Message that party's inbox, cc `mgmt/inbox/` |
| Architecture decision needed            | Message `mgmt/inbox/` with full context |
| Contract dispute                        | Both parties message `mgmt/inbox/` |
| Verifying team rejects a Resolution      | Reply to their bounce; if the implementer disagrees with the verdict, escalate to `mgmt/inbox/` — the verdict stands until mgmt overrules it in writing |
| Security-tagged item without opencode sign-off found in `implemented/` | Immediate `priority: critical` message to `mgmt/inbox/`; item is reopened |

---

## 10. File Naming Convention

`YYYY-MM-DD_HHMM_from-to_slug.md` — unchanged. `from`/`to` now draw from `{mgmt, devin, antigravity, cline, opencode}`.

---

## 11. Tooling Standards

### 11.1 Python Package Management

**uv is the only allowed Python package manager.** No pip, poetry, conda, pipenv. `uv add` / `uv remove` (removals need mgmt approval) / `uv sync` / `uv run pytest`. `pyproject.toml` + committed `uv.lock` are the source of truth. opencode audits for drift (stray `requirements.txt`, pip usage in Dockerfiles/Makefiles — see BLK-195/200/202/226) as a standing responsibility, not a one-time fix.

### 11.2 Frontend Package Management

**pnpm is the project standard** (see BLK-194 — CI must match). opencode owns enforcing this in CI; antigravity owns it in `frontend/`.

### 11.3 Docker / CI

opencode owns `Dockerfile*`, `docker-compose*.yml`, and the non-test portions of `.github/workflows/*`. Any of these referencing a file that doesn't exist (deleted `requirements-dev.txt`, missing `frontend/Dockerfile`, etc.) is a `priority: high` opencode item the moment it's found — a broken build pipeline blocks everyone.
