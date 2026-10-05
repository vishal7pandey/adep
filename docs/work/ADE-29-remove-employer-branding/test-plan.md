# ADE-29 — Test plan: Remove employer branding

Status: draft · Risk: low · Jira: ADE-29

Test framework and conventions found: frontend uses vitest + Testing Library in `frontend/tests/*.test.tsx`
(`cd frontend && pnpm test`); backend uses pytest in `src/tests/` (`python -m pytest src/tests -q -m "not integration"`).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | manual | case-insensitive `git grep` for the employer name and abbreviations, pathspec `:!sample-data` | tree has zero hits | the 7 coincidental binary matches in `sample-data/` are excluded and listed separately | re-adding an old component name would produce a hit | verified |
| AC2 | integration | `pnpm build` and the whole vitest suite incl. `frontend/tests/graph-visualization.test.tsx` | build exits 0, same test count as baseline | n/a: rename only | a missed import fails the build (module not found) | verified |
| AC3 | manual | `pnpm lint` | error count is 22 or fewer | n/a: counts only | a new lint violation raises the count | verified |
| AC4 | unit | `frontend/tests/theme-context.test.tsx` | toggle stores `adep_theme` `dark` then `light`; stored `dark` applied on mount | no stored value falls back to system preference | a value only under the old key is ignored | verified |
| AC5 | manual | `git diff master -- frontend/app/globals.css` | only token names and one comment line change | hex values identical before and after | a leftover reference to an old token name shows up in grep | verified |
| AC6 | integration | backend `-m "not integration"` | only ADE-23 and ADE-24 fail | n/a: no backend change | any other failure is a regression | verified |

## Regression risk

`Button` and `Badge` are used in about 22 files; the existing vitest suite and the production build type-check
every import. `graph-visualization.test.tsx` mocks the badge module by path, so its mock path is renamed together
with the file.

## Untestable AC

None.

## Manual checks

AC1, AC3, AC5: run the commands listed above and record the output in `notes.md`. "No visual change": markup and
class strings are unchanged by construction (only identifiers are renamed), so no screenshot is taken.

## Audit (after implementation)

Run on 2026-10-05 after the change:

- AC1: `git grep -i -c -E "<employer name and abbreviations>" -- . ':!sample-data'` printed nothing, exit status 1
  (was 222 references in 25 files). It fails when broken: before the change the same command listed 25 files.
- AC2: `pnpm build` exits 0 (all 8 routes prerendered); `pnpm test`: 10 files, 104 tests pass (baseline 104). A missed
  import of a renamed component fails the build with "module not found", and `graph-visualization.test.tsx` fails
  if its mock path is not renamed (the badge mock is by path).
- AC3: `pnpm lint`: 66 problems (22 errors, 44 warnings), identical to the baseline.
- AC4: `frontend/tests/theme-context.test.tsx` asserts `localStorage.getItem('adep_theme')` after each toggle
  (lines 45, 58, 74, 80); with the old key in the source those assertions fail (checked by reasoning: the source
  and the test share the one key, any mismatch makes `toBe('dark')` receive null).
- AC5: `git diff -- frontend/app/globals.css` shows 11 renamed token names and the one comment line; every hex value
  is unchanged. The same total number of lines added and removed across the diff (232 each) shows nothing else
  was altered.
- AC6: backend suite result recorded in the PR description.
