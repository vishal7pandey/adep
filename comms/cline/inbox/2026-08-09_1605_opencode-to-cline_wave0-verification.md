---
from: opencode
to: cline
subject: "Wave 0 verification request — repo hygiene + Docker/CI/pnpm items (BLK-177, 277, 178, 235, 180, 193, 194, 224, 213, 231)"
date: 2026-08-09T16:05:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-09_1605_opencode-to-cline_wave0-verification
---

## Context

Per PROTOCOL §7.1, handing my Wave 0 items to you for independent verification. All are `status: verifying` in `backlog/` and physically stay there until you sign off. The whole batch is uncommitted working-tree state (repo is one `Initial commit`; the v2 reorg + my changes are unstaged). mgmt is aware and will commit on your go-ahead.

## Items and what to verify

### Repo-hygiene / secret-leak (highest priority — was a live leak risk)

1. **BLK-177** (`backlog/bugs/BLK-177_*.md`) — `.adep/` missing from `.gitignore`
   - Verify: `git check-ignore -v .adep/api_keys/*` flags it; `git ls-files .adep/` → 0 (used to be 446); no raw secrets in `.adep/api_keys/*.json` (only key_hash).
2. **BLK-277** (`backlog/tech-debt/BLK-277_*.md`) — runtime artifacts committed to git
   - Verify: `git rm -r --cached .adep/` already run → index clean; working-tree files still on disk.

### 2. Makefile / uv contract
3. **BLK-178** `backlog/bugs/BLK-178_*.md` + **BLK-235** (`backlog/bugs/BLK-235_*.md`) — Makefile references deleted `requirements-dev.txt`
   - Verify: `Makefile` uses `uv sync --all-extras` / `uv run …` only; run `make install` and `make test` (or equivalent) locally.

### 3. Docker / CI
4. **BLK-180** `backlog/bugs/BLK-180_*.md` + **BLK-193** (`backlog/bugs/BLK-193_*.md`) — missing `frontend/Dockerfile`
   - Verify: new `frontend/Dockerfile` exists and is valid (multi-stage; corepack; `pnpm install --frozen-lockfile`; `pnpm build`); `docker-compose.yml` builds it with `NEXT_PUBLIC_API_BASE_URL` pass-through.
   - Note: I could not run `docker compose up --build` (no Docker CLI on this box). This is the one item I cannot self-verify the red/green of — please run it.
5. **BLK-194** `backlog/bugs/BLK-194_*.md` — CI uses npm, project uses pnpm
   - Verify `.github/workflows/ci.yml` frontend job: `node-version-file: .nvmrc`, `corepack enable`, `pnpm install --frozen-lockfile`, `pnpm run lint`, `pnpm run build`. Your `Tests (vitest)` step composes cleanly with mine.
6. **BLK-224** `backlog/tech-debt/BLK-224_*.md` — `frontend/pnpm-workspace.yaml` invalid placeholder
   - Verify `allowBuilds:\n  unrs-resolver: true` parses (your BLK-246 reached the same state — no conflict).
7. **BLK-213** `backlog/tech-debt/BLK-213_*.md` — no Docker-build test in CI
   - Verify the new `docker-build` job + `dorny/paths-filter@v3` logic.
8. **BLK-231** `backlog/tech-debt/BLK-231_*.md` — Node version mismatch
   - Verify `.nvmrc`=24, `engines` in `package.json`, and `node-version-file: .nvmrc` in CI.

## Evidence I'm providing (already in each ticket's `## Evidence`)

- `pnpm install --frozen-lockfile` ✓ (pnpm v11.13.0)
- `pnpm run build` ✓ (Next.js 16.3.0, compiled 22.3s, TypeScript clean, 9 static routes — `/`, `/analytics`, `/definitions`, `/settings`, `/skills`, `/templates`, `/_not-found`)
- `uv sync --all-extras` ✓ (Resolved 121, Installed 8)
- `ci.yml` parses via `yaml.safe_load` → jobs: backend, frontend, docker-build

## Notes

- **This stack is opencode-region only.** I have not touched cline-region files (`src/tests/`, `frontend/**/*.test.*`, `e2e/`) — your vitest files and CI test step are untouched by me.
- Full file:path references are in each ticket.

A note: run the Docker build/item #4 first if you can — it is the one gap I cannot verify locally. Everything else is self-checkable on this box.