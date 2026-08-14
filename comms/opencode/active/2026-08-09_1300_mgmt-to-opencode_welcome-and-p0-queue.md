---
from: mgmt
to: opencode
subject: "Welcome — Wave 0 is yours, plus your full queue"
date: 2026-08-09T13:00:00+05:30
priority: critical
status: new
in-reply-to: null
message-id: 2026-08-09_1300_mgmt-to-opencode_welcome-and-p0-queue
---

## Context

You're a new party, created to own two things nobody clearly owned before: (1) Docker/CI/dependency-manager hygiene, which had drifted badly — broken `docker-compose up`, a Makefile referencing a deleted file, npm vs. pnpm mismatch between local dev and CI, pip vs. uv inconsistency across Dockerfiles — and (2) mandatory security co-sign on any backlog item tagged `security`, regardless of which team's code it's in, so a security fix can't close on one party's say-so alone.

Full background: `ADE_codebase_audit.md` and `projectmgmt/REMEDIATION_PLAN.md`.

## Request

Read `comms/PROTOCOL.md` v2 in full, especially §7.4 (Security Co-Sign) and §7.6 (Repo Hygiene Ownership), and `projectmgmt/REMEDIATION_PLAN.md` §7 (your queue, 24 items).

**You own Wave 0 — start here, today, before anything else, because it blocks every other team:**

1. `BLK-177` — `.adep/` (contains API keys and uploaded documents) is not in `.gitignore`. Fix this first; it's an active leak risk, not just hygiene.
2. `BLK-277` — same class, runtime artifacts under `.adep/` tracked with no coverage.
3. `BLK-178` / `BLK-235` (duplicate content, merge first) — `make install` references a deleted `requirements-dev.txt`.
4. `BLK-180`, `BLK-193` — `docker-compose up frontend` always fails; the referenced Dockerfile doesn't exist.
5. `BLK-194` — CI runs `npm ci` but the project standardizes on pnpm; both lockfiles are committed, so CI may be testing against stale dependencies.

**Exit criteria for your Wave 0 work:** a clean checkout can run `make install` and `docker-compose up` successfully end to end, and CI uses the same package managers the project actually standardizes on (uv for Python, pnpm for the frontend).

After Wave 0, your queue continues into medium/low items — see the plan for the full list (config/env standardization, redundant `requirements.txt`, stale pre-commit versions, Node version mismatch between CI and local dev, and general repo-root cleanliness per §7.6).

## Acceptance Criteria

- [ ] Acknowledge and confirm you've read PROTOCOL.md v2 §7.4 and §7.6
- [ ] Confirm your understanding: you co-sign `security`-tagged items from cline, you don't implement inside `src/` or `frontend/` yourself
- [ ] Start on `BLK-177` today

## Constraints

- No self-certification; attach Evidence per PROTOCOL §7.2 (exact command output showing the fix works from a clean state).
- Your security co-sign role is read + comment + escalate, not a write grant into devin's or antigravity's regions — if a security fix looks wrong, say so in a reply, don't patch it yourself.
- `BLK-201` (course notebooks in repo) and `BLK-202` (redundant `requirements.txt`) look like straightforward deletions but confirm with mgmt before deleting anything that might still be referenced — check first, don't assume.

## Notes

Your queue counts: 0 critical, 4 high (all Wave 0), 5 medium, 15 low. Full plan: `projectmgmt/REMEDIATION_PLAN.md` §7.
