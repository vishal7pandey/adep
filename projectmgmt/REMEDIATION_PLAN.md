# ADEP Remediation Plan

> Owner: mgmt. Status: **active, supersedes Phase 5 as the current priority** (PROTOCOL §7.8).
> Created: 2026-08-09. This is the plan mgmt is executing against until further notice.

---

## 0. Why this document exists

The user's assessment, after reading the bug backlog and `ADE_codebase_audit.md`, was blunt: **this codebase is a shell, a house of cards.** That is not a rhetorical exaggeration — it is a precise description of a documented pattern:

- `projectmgmt/STATUS.md` claimed **145 items complete**, **1243 tests passing**, and a **9.5/10 self-audit score**, under the old mgmt/backend/frontend structure where each party graded its own homework.
- An independent audit then found, in the *same codebase*: a guardrails subsystem (8 files, ~2,140 lines) that is **100% dead code** wired into nothing; a ReAct agent **silently bypassed by a regex parser** for 7 of the 9 document types used as "high-value accuracy fixtures" — meaning the accuracy numbers built on those fixtures measure a script, not the agent; a **fake HITL approval gate**; an **arbitrary file-read vulnerability**; an **admin bootstrap secret logged in plaintext**; auth middleware that **fails open** for unmapped HTTP methods; `compact`/`rollback` API endpoints that are **no-op stubs returning HTTP 200**; and **30 separate BLK-ID collisions** created by uncoordinated parallel audits writing to the same backlog directory.
- The self-audit score of 9.5/10 was itself filed as a bug (BLK-161, "self-audit-overclaim") and never actually retracted in the status board.

None of this means the underlying engineering is worthless — the frontend, in particular, was independently found to be in reasonably good shape where checked, and the core ReAct loop, tool registry, and skill/template abstractions are real, working architecture. What's broken is **the process that was supposed to keep claims honest**, and a long tail of correctness/security bugs that a process with real verification would have caught before they were called "done."

This plan exists to fix both: the immediate defects (§3–§7) and the process that let them ship silently (§1, and `comms/PROTOCOL.md` §7).

---

## 1. Governing principles for this remediation (and afterward)

1. **Verification is not optional and not self-administered.** Nothing closes without independent sign-off from a party that didn't implement it (`comms/PROTOCOL.md` §7.1 — cross-team since v2.1, see §6). Anything currently sitting in `implemented/` from before 2026-08-09 is **unverified-but-plausible**, not confirmed — see §2.
2. **Evidence beats prose.** "Fixed" / "verified" / "works now" with no attached command output, diff, or reproduction is treated as not done (`PROTOCOL.md` §7.2).
3. **No new feature work until the foundation is real.** Phase 5 (ADAS / agentic builder — BLK-067 through BLK-076 and similar) is frozen (`PROTOCOL.md` §7.8) until every `critical` and `high` item below is `implemented/` and cross-team-verified. Building a self-improving-agent-builder on top of a silently-bypassed agent loop is how this problem compounds, not how it gets fixed.
4. **Security bugs need two signatures.** Implementer + opencode, always (`PROTOCOL.md` §7.4).
5. **One party issues IDs.** mgmt only, from now on (`PROTOCOL.md` §7.3) — this is why the 30-collision cleanup in §2 was a one-time mgmt action, not something to repeat.
6. **Fix the pipes before the product.** A team cannot be verified, and cannot ship, through a broken build. Wave 0 (§3) is CI/Docker/test-runner fixes specifically because they block everyone else's ability to prove anything.

---

## 2. Backlog hygiene already completed by mgmt (2026-08-09, this session)

Before assigning any work, the backlog itself had to stop lying about its own IDs and format:

- **30 BLK-ID collision groups resolved.** Every duplicate ID (e.g. two unrelated tickets both claiming `BLK-217`) had its second occurrence renumbered into the free range starting at `BLK-263`. Full old→new mapping is preserved in each renumbered file's `## Implementation Log` and in git history for this commit. Highest ID is now `BLK-292`.
- **BLK-170** converted from a legacy non-YAML format (the only file still using it) to the standard `ITEM-TEMPLATE.md` frontmatter.
- **Every open item in `backlog/bugs/` and `backlog/tech-debt/` (112 files)** has been assigned an `owner` among `devin | antigravity | cline | opencode | mgmt` — see §4–§8 for the queues. `backlog/features/` and `backlog/ideas/` were left with their existing owners/status; see §9 for why (feature freeze).
- Filed as `BLK-292` (owner: mgmt) — the ID-collision problem itself, now fixed, kept as a record so a future session doesn't wonder why the numbering has a gap-then-jump at 262→263.

**Known content-duplicate clusters** (same underlying bug, filed twice under different IDs by different audit passes — not ID collisions, *content* collisions). These are not merged automatically because merging requires reading both tickets' full acceptance criteria and reconciling them, which is triage work for the owning team, not a mechanical rename. Each owning team's **first task** is to merge these before starting implementation, so effort isn't spent twice:

| Cluster | Tickets | Owner |
|---|---|---|
| Bootstrap admin secret logged in plaintext | BLK-186, BLK-188 | devin |
| Prompt-injection detection is cosmetic/bypassable | BLK-183, BLK-211 | devin |
| LLM provider silently returns empty content on failure | BLK-191, BLK-234 | devin |
| Skill/Template registry manual duplication | BLK-251, BLK-267 | devin |
| Frontend test coverage is near-zero | BLK-225, BLK-246, BLK-286 | cline |
| Makefile references a `requirements-dev.txt` that doesn't exist | BLK-178, BLK-235 | opencode |
| "Implement but don't integrate" — dead/unwired subsystems (guardrails, hitl, eval, benchmarks) | BLK-214 (meta), BLK-265, BLK-268, BLK-204, BLK-205, BLK-199 | devin implements the wire-or-delete decision per module; mgmt tracks BLK-214 as the umbrella |
| Backend/frontend run-status contract mismatch | BLK-232, BLK-280, BLK-282, BLK-185 | devin drives the contract (PROTOCOL §7.7 lock — antigravity + cline must approve) |
| pip vs. uv inconsistency across Docker/Makefile | BLK-195, BLK-196(part), BLK-200, BLK-226 | opencode |

---

## 3. Wave 0 — Unblock the pipes (start immediately, in parallel, no dependencies)

Nothing else in this plan can be verified or deployed while these are broken. These are prioritized above some `critical`-labeled items because they're structurally blocking rather than because of raw severity.

| Team | BLK-ID | Why it's Wave 0 |
|---|---|---|
| opencode | BLK-177 | `.adep/` (API keys, documents) not gitignored — active secret-leak risk, fix before anyone commits again |
| opencode | BLK-178 / BLK-235 | `make install` references a deleted file — broken for every new contributor/agent |
| opencode | BLK-180 | `docker-compose up frontend` always fails — no one can run the full stack |
| opencode | BLK-193 | Frontend Dockerfile referenced but doesn't exist — same failure, different entry point |
| opencode | BLK-194 | CI uses npm, project uses pnpm — CI is running against the wrong lockfile |
| opencode | BLK-277 | `.adep/` runtime artifacts tracked in git with no `.gitignore` — same class as BLK-177, compounds repo bloat every run |
| cline | BLK-246 | Frontend test suite has no working test script — cline **cannot verify anything frontend** until this runs |
| cline | BLK-184 | Frontend tests hit real network — verification results are flaky/non-deterministic until mocked |
| mgmt | BLK-292 | ID collisions — **done**, see §2 |

**Exit criteria for Wave 0:** `docker-compose up` succeeds end-to-end from a clean checkout; `make install` succeeds; CI runs the correct package manager for each stack; `.adep/` is gitignored and no longer tracked; `pnpm test` (or equivalent) runs and produces real pass/fail output for the frontend suite.

---

## 4. devin queue — backend (`src/**`, including tests as of v2.1) — 56 items

devin owns the largest and highest-stakes share, because the audit's most severe findings (silent agent bypass, dead guardrails, false-success reporting, auth fail-open, arbitrary file read) all live in `src/`.

### Wave 1 — Critical (9 items, security-tagged ones need opencode co-sign per PROTOCOL §7.4)

| ID | Title |
|---|---|
| BLK-264 | PDF fallback silently bypasses the ReAct agent for 9/22 skills even when the LLM is fully configured — **this is the audit's #1 finding; the "accuracy" numbers this project has cited are built on it** |
| BLK-287 | Hallucinated success through the same fallback bypass — false agentic confidence |
| BLK-265 | Guardrails subsystem (2,140 lines) is 100% dead code — wire it into `act_node`/`observe_node`/`plan_node` for real, or delete the package and its docstring's claims (PROTOCOL §7.5 — no more decorative safety code) |
| BLK-215 | Auth middleware fails **open** for any HTTP method not explicitly listed — unauthenticated DELETE/PATCH/PUT on real endpoints [security] |
| BLK-241 | Run preview endpoint reads arbitrary server-side files — extension-only gate, fully attacker-controlled path [security] |
| BLK-240 | `graph.invoke()` blocks the entire event loop despite a docstring claiming `asyncio.to_thread` |
| BLK-218 | Graph extraction runtime skips graph-specific validation/control metrics in the live loop |
| BLK-270 | Pause/resume is not actually resumable — store state drifts from executor state |
| BLK-280 | Frontend/SSE/store each define a different run-status contract (PROTOCOL §7.7 lock applies — antigravity must approve the unified contract) |

### Wave 2 — High (12 items)

BLK-173, BLK-185, BLK-186+BLK-188 (merge first, §2), BLK-217, BLK-220, BLK-221, BLK-232, BLK-242, BLK-243, BLK-244, BLK-254, BLK-256, BLK-281, BLK-284 — correctness/security items: silent zero-output failures, contract drift breaking rename/search/duplicate/preview, dead webhook dispatch, disabled retry dedup, no-op compact/rollback endpoints presented as working, unindexed sync auth I/O on every request, upload accepting anything with an image extension with no size/content guard, max-iterations treated as success, definition-level overrides partially ignored.

### Wave 3 — Medium (23 items, architecture/hardening)

BLK-181, BLK-189, BLK-191+BLK-234 (merge first), BLK-204, BLK-205, BLK-211+BLK-183 (merge first), BLK-212, BLK-223, BLK-233, BLK-251+BLK-267 (merge first), BLK-255, BLK-257, BLK-263, BLK-266, BLK-274, BLK-278, BLK-279 [security — opencode co-sign], BLK-282, BLK-290.

Themes: collapse the skill/template registry to auto-discovery (fixes the exact drift pattern that caused BLK-172 duplicate definitions previously); make `RunStatus` a real enum; calibrate or remove fixed confidence values; bound run-context memory; enable rate limiting by default in production config; make circuit breakers provider-keyed as documented.

### Wave 4 — Low (5 items)

BLK-199 (backlog status drift — features marked done that are actually already wired, just filed wrong), BLK-216, BLK-268, BLK-291, and the leftover half of BLK-183/211 cleanup.

### Wave T — Test/CI items redistributed from cline (5 items, v2.1)

BLK-208 (e2e tests use the wrong definition for invoice tests), BLK-209 (fake PDF fixture bypasses PyMuPDF in mocked tests — this is exactly the kind of test-integrity gap that let BLK-264's fallback bypass go unnoticed), BLK-229 + BLK-288 (merge — no integration-marker filtering in CI, integration tests silently skipped), BLK-275 (deprecated FastAPI lifecycle hooks / stale test-runtime APIs). Verified by antigravity per the cross-team model (§1, PROTOCOL §7.1 v2.1).

---

## 5. antigravity queue — frontend (`frontend/**`, including tests as of v2.1) — 24 items

The corrected audit assessment of the frontend was **more favorable** than the backlog implied — `GraphVisualizationView`, `Pane2ExtractedData`, `WorkbenchLayout`, and `lib/api.ts` were all confirmed to use real props/real fetches, not mock data, when spot-checked. The remaining frontend bugs are real but narrower than devin's.

### Wave 2 — High (4 items)

| ID | Title |
|---|---|
| BLK-187 | Frontend run-state model collapses distinct backend outcomes into misleading UI states |
| BLK-245 | SSE `EventSource` leaks on unmount and cannot carry an `Authorization` header — auth/SSE mismatch |
| BLK-253 | Pane2 export/history swallow errors silently and fabricate `confidence=1.0` on manual edits |
| BLK-259 | ApiKeyManagement UI is fake/in-memory — never mounted, hardcoded `SAMPLE_KEYS`, makes zero API calls |

### Wave 3 — Medium (16 items)

BLK-170 (guardrail warning, coordinate with devin's `suggestAgent`), BLK-179 (hardcoded hex colors survive the BLK-134 tokenization that claimed 100%), BLK-182, BLK-247, BLK-248, BLK-249 (`GraphVisualizationView` fabricates mock JSON when smart-P&ID output is missing — a second, more subtle instance of the fallback-fabrication pattern devin is fixing), BLK-250, BLK-252, BLK-258, BLK-260, BLK-261, BLK-262 (a11y: no focus trap/Escape/restore on modals), BLK-269, BLK-271 (still uses `Date.now()` for run IDs despite BLK-147 claiming this was fixed — a direct instance of the overclaim pattern, worth a moment's pause), BLK-203, BLK-219 (cosmetic, wrong BLK-ID referenced in an error string).

### Wave T — Test items redistributed from cline (4 items, v2.1)

BLK-246 (frontend test suite — real progress already made: vitest infra + 4/5 test files passing; finish `tests/sse.test.ts` against the current `fetch`-based `connectToRunStream`, not the `EventSource` version it replaced, and fix one `workbench-context.test.tsx` assertion for `crypto.randomUUID()`), BLK-184 (frontend tests hit real network, merge into BLK-246), BLK-225 + BLK-286 (merge — near-zero frontend coverage, same cluster as BLK-246). Verified by devin per the cross-team model (§1, PROTOCOL §7.1 v2.1).

---

## 6. cline — mandate suspended 2026-08-09 16:00, queue redistributed

cline was created to be the independent verification gate (§1). In its first working cycle it reported `BLK-246` as "63 tests passing" when the actual, mgmt-verified result was 53/63 — a real overclaim, not a coordination artifact, since cline's own follow-up message continued diagnosing an `EventSource`-capture bug that no longer existed anywhere in the file it was debugging (`frontend/lib/sse.ts` had zero references to `EventSource` after antigravity's `BLK-245` rewrite). It verified zero of the 8 items already waiting from devin and antigravity. mgmt suspended the mandate rather than continue routing new work through it.

**Verification is now cross-team** (PROTOCOL §7.1 v2.1, RACI.md v2.1): devin verifies antigravity's `verifying`-status items, antigravity verifies devin's, opencode's security items still get opencode's own co-sign from whichever of the two runs their verification, and mgmt performs periodic spot-checks on top as the compensating control (a peer pair is a weaker gate than a dedicated third party, and mgmt caught this exact failure by spot-checking rather than trusting the report).

**Its 9-item queue was redistributed by domain**, folded into §4 and §5 below:

| ID | Was cline's, now | Note |
|---|---|---|
| BLK-246 | antigravity | Substantial real progress preserved (vitest infra, 4/5 test files passing) — see the file's Implementation Log for exactly what to keep vs. fix. Do not restart from scratch. |
| BLK-184 | antigravity | Frontend tests hit real network — merge into the BLK-246 effort |
| BLK-225, BLK-286 | antigravity | Merge into the BLK-246 effort — same near-zero-coverage cluster |
| BLK-208, BLK-209 | devin | E2E fixture correctness (wrong definition, fake PDF bytes) — backend-data concern |
| BLK-229, BLK-288 | devin | CI integration-marker filtering — backend pytest markers |
| BLK-275 | devin | Deprecated FastAPI lifecycle hooks / stale test-runtime APIs |

`comms/cline/` is retained as a historical record, not deleted. The mandate can be reinstated later if a dedicated QA role is worth reintroducing once the team is more stable — this is a pause, not a verdict on the concept.

---

## 7. opencode queue — Docker/CI/dependency/repo hygiene — 24 items

### Wave 0 (see §3): BLK-177, BLK-178/235, BLK-180, BLK-193, BLK-194, BLK-277

### Wave 2 — High (already counted in Wave 0 above — no additional highs remain after Wave 0)

### Wave 3 — Medium (5 items)

BLK-176 (config/env bootstrap standardization), BLK-195 (Dockerfile uses pip not uv), BLK-279 is devin's but opencode co-signs (production rate-limit default).

### Wave 4 — Low, repo cleanliness (13 items)

BLK-196, BLK-200, BLK-201 (course notebooks unrelated to the platform, candidate for deletion — confirm with mgmt first), BLK-202 (2,991-line `requirements.txt` redundant with `pyproject.toml`/`uv.lock`), BLK-207, BLK-210, BLK-213, BLK-224, BLK-226, BLK-227, BLK-230, BLK-231, BLK-236, BLK-276, BLK-285.

These are individually low-severity but collectively are exactly the "37,846 lines grown from a 5-notebook course exercise" scope creep the audit called out (§7 of `ADE_codebase_audit.md`). Clearing them is what makes the repo legible to the next person (or agent) who opens it.

---

## 8. mgmt queue — 8 items

BLK-292 (done, §2), BLK-214 (umbrella tracking for the "implement but don't integrate" pattern — mgmt tracks devin's per-module wire-or-delete decisions here rather than owning code), BLK-197 (duplicate `implemented/` dir at repo root), BLK-198 (136KB `vision.backup.*` files committed as garbage), BLK-206 (three standalone design docs at repo root with no integration), BLK-222 (`ADE_codebase_audit.md` itself belongs in `projectmgmt/` or `docs/`, not repo root — will be relocated once this plan is reviewed), BLK-228 (sample-data inventory mismatch — mgmt owns sample data per prior BLK-104 precedent), BLK-289 (238 comms/ files committed to git — runtime artifacts, needs a retention/archival decision, not a delete — comms is the audit trail).

---

## 9. Features and ideas — frozen, not abandoned

`backlog/features/` (19 items, mostly the Phase 5 ADAS/agentic-builder line: BLK-067 Template Composer through BLK-076 cost estimator, plus BLK-035/036/037/056/104/118/174/272/273) and `backlog/ideas/` (2 items) are **not reassigned or reprioritized in this pass**. Per `PROTOCOL.md` §7.8, all Phase 5 feature work is frozen until every `critical` and `high` item in §4–§7 is `implemented/` and cross-team-verified. Re-evaluate this list when the freeze lifts — some of it (e.g. BLK-104 sample data expansion) may be pulled forward earlier if it unblocks the e2e-fixture work now in devin's Wave T (BLK-208/209).

`BLK-161` (self-audit-overclaim, filed as a feature/process item) is the one exception worth calling out by name: it is the ticket that predicted this entire reorg. It should be the first thing verified as actually retracted — check that no document in the repo still asserts a 9.5/10 self-audit score or "145 items complete" without the "unverified-but-plausible" caveat from §1.

---

## 10. Exit criteria — what "actually valuable" means, concretely

This plan is done, not when the backlog is empty, but when all of the following are independently true (cross-team-verified, evidence attached):

1. **No execution path silently substitutes a different implementation than the one it claims to run.** (BLK-264/287 closed — the fallback bypass is gated or explicit, not automatic.)
2. **No module's docstring claims a safety/validation behavior that isn't wired into production code.** (BLK-265 and the rest of the "implement but don't integrate" cluster closed.)
3. **No unauthenticated request can read arbitrary files or bypass auth on any HTTP method.** (BLK-215, BLK-241 closed, opencode co-signed.)
4. **Every "success" status shown to a user reflects a run that actually produced the claimed output.** (BLK-221, BLK-281, BLK-274, BLK-244, BLK-283, BLK-259, BLK-249, BLK-253 closed.)
5. **Backend and frontend agree on one status contract**, not three. (BLK-280/232/282/185 closed under the PROTOCOL §7.7 lock.)
6. **A clean checkout builds, tests, and runs via `docker-compose up` and `make install` without manual fixes.** (Wave 0 closed.)
7. **The frontend test suite runs, is mocked (not hitting real network), and has meaningful coverage beyond error-path assertions.** (antigravity's Wave T closed.)
8. **The backlog's own IDs are unique and its format is consistent** (done, §2) **and stay that way** (PROTOCOL §7.3 enforced going forward).
9. **STATUS.md contains no unverified completion claims.**

Only after all nine hold does it make sense to lift the Phase 5 freeze and resume building the agentic-builder layer on top of this platform.
