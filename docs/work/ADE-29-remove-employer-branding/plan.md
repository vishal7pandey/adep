# ADE-29 — Remove employer branding

Status: draft · Risk: low · Jira: ADE-29
Created: 2026-10-05 · Slug: remove-employer-branding · Spec: spec.md

## Summary

Mechanical rename inside `frontend/` (plus the stray `app/templates/page.tsx`): rename two component files with
`git mv` and replace identifiers by exact-string substitution, rename the palette tokens in `globals.css`, and
change the theme storage key. No logic changes.

**Size:** S

## Current state

- The two prefixed components in `frontend/components/ui/` (a button and a badge, each with a `...Props`
  interface) are imported by about 22 files; 161 and 100 occurrences of the two names.
- `frontend/app/globals.css` `@theme` block defines 14 `--color-*` palette tokens, named after the employer
  brand. `git grep` finds no use of those tokens as utilities (only `COLORS.purple` in analytics, a JS constant,
  unrelated).
- The employer-derived theme key is used in `frontend/app/layout.tsx`, `frontend/context/ThemeContext.tsx`,
  `frontend/tests/theme-context.test.tsx`.
- `frontend/tests/graph-visualization.test.tsx` mocks the badge module and uses a brand-named `data-testid`.
- No existing `Button` / `Badge` identifiers (checked with `git grep -w`).
- Commands: `cd frontend && pnpm install && pnpm test && pnpm run build`, `pnpm lint` (22 errors baseline).

## Approach

Rename with `git mv` (file history is preserved) and word-bounded text substitution of the exact identifiers,
then verify with grep, build, tests and lint. Smallest change that satisfies the spec.

**Alternatives rejected**
- Keep a re-export alias for the old names — leaves the old name in the tree, contradicts AC1.
- Read the old localStorage key once (ticket suggestion) — keeps the string in the code, contradicts AC1.
- Choose a new palette — the ticket says the look must not change.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Capture baselines: grep count, test count, lint error count, backend failures | none | AC1, AC2, AC3, AC6 | numbers recorded in notes.md |
| T2 | `git mv` the two component files; rename exported names and props interfaces; update all imports and usages, the test mock and test id | `frontend/components/ui/Button.tsx`, `Badge.tsx`, importing files, `frontend/tests/graph-visualization.test.tsx`, `app/templates/page.tsx` | AC1, AC2 | `pnpm build`, `pnpm test` |
| T3 | Rename the palette tokens and reword the comment in `globals.css` | `frontend/app/globals.css` | AC1, AC5 | `git diff` shows only renamed names; `pnpm build` |
| T4 | Rename the theme key to `adep_theme` | `frontend/app/layout.tsx`, `frontend/context/ThemeContext.tsx`, `frontend/tests/theme-context.test.tsx` | AC1, AC4 | `pnpm test` (theme-context) |
| T5 | Full verification: grep, build, tests, lint, backend suite | all | AC1-AC6 | commands in test-plan.md |

## Data, API and migration impact

None for data and API. The theme key changes (one-time reset of the saved theme for existing browsers).

## Security and failure modes

No auth, input or secret changes. Failure shows as a build/type error (missing import) or a failing test.

## Rollout and rollback

Merge to `master`; no deploy step (local tool). Rollback: `git revert` the merge commit.

## Risks and open points

- A name clash for `Button` / `Badge`: the build would fail and show it.
- Binary sample files keep coincidental byte matches; documented in the spec.
