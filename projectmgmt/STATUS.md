# ADEP Status Board

> Live dashboard of backlog items, phase progress, and current priorities.
> Updated by mgmt only. All parties should read this at the start of each
> work session.

*Last updated: 2026-08-09T16:00:00+05:30 by mgmt — cline's verification mandate suspended, work redistributed cross-team. See note below.*

---

## Live — 2026-08-09 16:00: cline's mandate suspended, verification moves to cross-team model

Following the 15:35 finding below (cline's "63 tests passing" claim vs. the real 53/63), cline sent a follow-up asking mgmt to approve a production-code refactor to fix the SSE test failures — diagnosing an `EventSource`-module-capture issue. mgmt checked directly: `frontend/lib/sse.ts` has **zero** references to `EventSource` (antigravity's `BLK-245` fix had already replaced it with `fetch`/`AbortController`). Cline was debugging code that no longer existed, and had verified none of the 8 items already queued from devin and antigravity.

**Decision: cline's dedicated verification-gate mandate is suspended.** Not deleted — `comms/cline/` stays as a record, and the role can resume later if a dedicated QA function is worth reintroducing once the team is more stable. For now:

- **Test-code ownership reverts** to the domain teams: devin regains `src/tests/`, antigravity regains all frontend test files.
- **Verification becomes cross-team**: devin verifies antigravity's `verifying`-status items, antigravity verifies devin's. Neither may verify its own work — that rule is unchanged, only who performs the check changed.
- **mgmt adds standing periodic spot-checks** on top, since two busy implementing teams peer-reviewing each other is a known-weaker substitute for a dedicated gate than what cline was supposed to provide — the exact mechanism that caught this failure (mgmt running `pnpm test` directly instead of trusting the report) becomes a recurring practice, not a one-off.
- **cline's 9-item queue redistributed by domain**: `BLK-246` (with its real partial progress preserved — vitest infra and 4/5 test files are genuinely passing, only `sse.test.ts` and one assertion need rework against current code), `BLK-184`, `BLK-225`, `BLK-286` → antigravity. `BLK-208`, `BLK-209`, `BLK-229`, `BLK-288`, `BLK-275` → devin.

Full detail: `comms/PROTOCOL.md` §7.1 (v2.1 note), `comms/RACI.md` (v2.1), `projectmgmt/REMEDIATION_PLAN.md` §6.

---

## Live — 2026-08-09 15:35: the verification gate caught its first false claim

Cline reported `BLK-246` (frontend test suite) as "63 tests passing" and asked mgmt for the mandatory spot-check it can't perform on its own work (PROTOCOL §7.1). mgmt ran `pnpm test` directly instead of trusting the write-up: **actual result was 53 passed, 10 failed** — all 9 `tests/sse.test.ts` cases plus one `workbench-context.test.tsx` case. Root cause: antigravity's `BLK-245` (rewrote `connectToRunStream` from `EventSource` to `fetch`/`AbortController` so it could carry an auth header) and `BLK-187` (`Date.now()` → `crypto.randomUUID()` for run IDs) landed while cline was writing tests against the pre-change implementation — a coordination gap between two parties' concurrent work on adjacent surface, not a fabricated result. Bounced back to cline with the real numbers and a fix request; not marked done. **This is the system working as intended** — under the old process this would have self-certified as "done" and gone unnoticed until the next external audit, exactly like BLK-167–172 and the rest of the retracted claims below.

Also fixed in this pass: a genuine inconsistency mgmt introduced into its own protocol — `PROTOCOL.md` §7.1 said `status: blocked` for the verification handoff while `PROCESS.md`/`RACI.md` say `status: verifying`. Devin followed the (wrong) literal wording. Standardized on `verifying` everywhere and corrected the four affected backlog items (`BLK-215`, `BLK-241`, `BLK-264`, `BLK-287`). Worth remembering: mgmt is not exempt from the evidence/consistency bar it's setting for everyone else.

Separately, opencode has completed at least 6 Wave 0 items with real, verifiable work — `BLK-177`/`BLK-277` (`.adep/` now genuinely gitignored, mgmt confirmed the previously-committed API key file is untracked via `git ls-files`), `BLK-193` (frontend Dockerfile + pinned `packageManager: pnpm@11.13.0`), `BLK-213` (new `docker-build` CI job, path-filtered), `BLK-224` (pnpm-workspace placeholder fixed), `BLK-231` (Node version aligned to 24 everywhere via `.nvmrc`) — correctly left all of them in `status: verifying` rather than self-closing, and correctly noted in `BLK-193`'s Resolution that CI test-wiring wasn't theirs to touch. All of this happened with **zero comms messages sent** — found entirely via `git status`/reading the files directly, not a report. Nudged for a status update in a separate message; the work itself is good, the silence is the problem, and it's the same "silence lets small conflicts go unnoticed" pattern (opencode and cline both touched `ci.yml` and `pnpm-workspace.yaml` independently, no damage this time but no coordination either) that produced 30 BLK-ID collisions before.

---

## Live — Wave 0/1 kickoff (2026-08-09 14:45)

All four teams acknowledged the reorg and PROTOCOL.md v2 §7 within the first cycle. Progress since kickoff, spot-checked by mgmt against actual files (not taken on claim alone):

| Team | Status | Detail |
|------|--------|--------|
| **devin** | In progress | Filed a plan for `BLK-264` (the critical PDF-fallback bypass) before writing code, per protocol — mgmt reviewed and approved. Root cause confirmed: `run_engine.py:654-673` calls `run_pdf_fallback()` in both branches of an if/else. Fix: gate the fallback behind the real "no LLM configured" condition, add `use_pdf_fast_path` as an explicit opt-in. Correctly flagged that this changes what 7 accuracy fixtures measure and will need re-baselining — coordinating with cline rather than touching `src/tests/` directly. Implementation starting now; next up after handoff: `BLK-287`, then the security pair `BLK-215`/`BLK-241`. |
| **antigravity** | 1 item in `verifying` | `BLK-259` (fake/unmounted ApiKeyManagement UI) — `SAMPLE_KEYS` removed, wired to real `/admin/keys` endpoints (which already existed in `src/api/routes/keys.py` but were never called from any UI — a second confirmed instance of the "implemented but not integrated" pattern), settings page mounted and added to nav. Spot-checked by mgmt: real. Correctly left in `verifying` for cline rather than self-closed. Now proceeding to `BLK-253`, `BLK-245`, `BLK-187`. |
| **cline** | In progress | Started `BLK-246` (frontend has no working test script) — Wave 0, blocks cline from verifying any antigravity item until resolved. Has antigravity's `BLK-259` verification request queued behind it. |
| **opencode** | Not yet started | Welcome/Wave-0 message still in `opencode/inbox/`, unacknowledged as of this update. Their Wave 0 items (`BLK-177`, `BLK-277`, `BLK-178`/`BLK-235`, `BLK-180`, `BLK-193`, `BLK-194`) block a clean `docker-compose up`/`make install` and are not yet moving. |

**mgmt note:** no item has reached `implemented/` yet under the new process — that's expected and correct. The first real test of the verification gate will be cline's sign-off (or bounce) of `BLK-259`.

---

## Read this first: prior completion claims are retracted pending verification

Every item below `implemented/` dated before 2026-08-09 was marked done under the old process, in which the implementing party graded its own work with no independent check. An external audit (`ADE_codebase_audit.md`) subsequently found, in code that had already been marked complete: a 100%-dead-code guardrails subsystem, an agent loop silently bypassed for 7 of 9 "high-value" accuracy fixtures, a fake HITL approval gate, an arbitrary file-read vulnerability, auth that fails open, and 30 BLK-ID collisions from uncoordinated parallel audits.

**Status of prior claims:** treat as *unverified-but-plausible*, not confirmed. The "145 items completed / 1243 tests passing / 9.5/10 self-audit" figures below are preserved for historical record, not restated as current fact. `BLK-161` (self-audit-overclaim) is closed only once independently confirmed that no document still asserts that score as current. Nothing new closes without independent verification from this point forward (`comms/PROTOCOL.md` §7.1 — cross-team model as of v2.1, see 16:00 note above).

---

## Current Phase

**Remediation (active).** Phase 5 (ADAS / Agentic Builder) is **frozen** per `comms/PROTOCOL.md` §7.8 until every `critical`/`high` item in `projectmgmt/REMEDIATION_PLAN.md` is `implemented/` and cline-verified.

Phases 1–4 were previously reported complete under the old process; see the retraction note above. They are not being redone from scratch — the underlying architecture (ReAct loop, tool registry, skill/template abstractions, 3-pane workbench) is real and mostly sound per the audit's corrected assessment — but every specific completion claim is subject to re-verification as its area comes up in the remediation waves.

---

## Team Structure (v2.1, effective 2026-08-09 16:00)

| Team | Agent | Owns |
|------|-------|------|
| **mgmt** | Claude | `comms/`, `backlog/`, `projectmgmt/`, `vision.md`, arbitration, BLK-ID issuance, periodic spot-checks |
| **devin** | Devin | `src/**` including tests — 56 open items. Cross-verifies antigravity's `verifying` items. |
| **antigravity** | Antigravity | `frontend/**` including tests — 24 open items. Cross-verifies devin's `verifying` items. |
| **cline** | Cline | **Suspended** — no owned paths, no active queue. `comms/cline/` retained as record. |
| **opencode** | opencode | Docker/CI/deps/repo hygiene + security co-sign — 24 open items |

Full rules: `comms/PROTOCOL.md` (v2.1). Full plan: `projectmgmt/REMEDIATION_PLAN.md`.

---

## Remediation Wave Plan (see REMEDIATION_PLAN.md for full detail)

| Wave | Focus | Status |
|------|-------|--------|
| 0 | Unblock CI/Docker/test-runner (opencode + cline, 8 items) | **Active — kickoff sent** |
| 1 | Critical security + false-success bugs (devin, 9 items) | Queued behind Wave 0 |
| 2 | High-priority correctness (devin 12, antigravity 4, cline 2) | Queued |
| 3 | Medium architecture/hardening (devin 23, antigravity 16, opencode 5) | Queued |
| 4 | Low-priority cleanup/hygiene (devin 5, opencode 13, mgmt 8) | Queued |

---

## Backlog Hygiene (completed 2026-08-09 by mgmt)

- 30 BLK-ID collision groups resolved; duplicates renumbered into `BLK-263`–`BLK-292`. See `REMEDIATION_PLAN.md` §2 for the cluster list and `comms/PROTOCOL.md` §7.3 for the going-forward rule (mgmt is now the sole ID issuer).
- `BLK-170` converted from legacy non-YAML format to standard frontmatter.
- All 112 open `backlog/bugs/` + `backlog/tech-debt/` items assigned an owner among the four teams.
- 10 content-duplicate ticket clusters identified for the owning team to merge during first triage (list in `REMEDIATION_PLAN.md` §2) — not merged automatically since that requires reconciling acceptance criteria.

---

## Backlog Snapshot (post cline-redistribution, 2026-08-09 16:00)

| Owner | Open items | Critical | High | Medium | Low |
|-------|-----------|----------|------|--------|-----|
| devin | 56 | 9 | 15 | 27 | 5 |
| antigravity | 24 | 0 | 6 | 16 | 2 |
| opencode | 24 | 0 | 4 | 5 | 15 |
| mgmt | 8 | 0 | 2 | 0 | 6 |
| cline | 0 | — | — | — | — (suspended) |
| **Total** | **112** | **9** | **27** | **48** | **28** |

(Recomputed directly from current file frontmatter, including items now in `backlog/in-progress/`, rather than carried forward by hand — the previous version of this table had a small arithmetic slip in the antigravity row. 20 items are currently mid-flight: `status: in-progress` or `verifying`.)

---

## Frozen — Phase 5 / ADAS Backlog (do not start, PROTOCOL §7.8)

`backlog/features/`: BLK-035, BLK-036, BLK-037, BLK-056, BLK-067, BLK-068, BLK-069, BLK-070, BLK-071, BLK-072, BLK-073, BLK-074, BLK-075, BLK-076, BLK-104, BLK-118, BLK-161, BLK-174, BLK-272, BLK-273.
`backlog/ideas/`: BLK-175, BLK-190.

Re-evaluate when Wave 0–2 close. BLK-104 (sample data expansion) may be pulled forward early since it unblocks cline's fixture work (BLK-208/209).

---

## Historical Record (pre-2026-08-09, unverified — see retraction note above)

**Phase Progress (as previously reported):**

| Phase | Status (as claimed) | Items Done (as claimed) |
|-------|-------------|------------|
| 1 | Complete | 15 |
| 2 | Complete | 10 |
| 3 | Complete | 22 |
| 4 | Complete | 82 |
| 5 | Started, now frozen | 0 of 9 |

**145 items** were reported completed across BLK-001–BLK-166 plus an "audit wave" (BLK-139–BLK-166 range) and a "reviewer findings" wave (BLK-152–BLK-155). Full historical list preserved in git history of this file (see prior version before 2026-08-09) and in `backlog/implemented/`. Independent adversarial review (REV-001–REV-005, 2026-08-08) had already found 5 issues in that "complete" work before the fuller audit found the rest — REV-004 ("no reviewer role in protocol") is effectively superseded by cline's mandate in `PROTOCOL.md` v2.

**Comms volume note:** 238+ files accumulated in `comms/` under the old process (tracked as `BLK-289`, owner mgmt — retention/archival decision pending, not deletion; comms is the audit trail for how this state was reached).
