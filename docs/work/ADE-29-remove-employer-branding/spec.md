# ADE-29 — Remove employer branding

Status: draft · Risk: low · Jira: ADE-29
Created: 2026-10-05 · Slug: remove-employer-branding

## Problem

ADEP is the owner's personal project, but the current files still carry the name of a former employer (and its
brand) in about 260 identifiers: the two UI components `Button` and `Badge` whose names carry the employer's
abbreviation as a prefix (and their files), the Tailwind
palette tokens in `frontend/app/globals.css` (named after that employer's brand palette), a code comment, and the
employer-derived theme localStorage key. The owner wants every such mention gone from the current tree.

## Users and context

The owner, as the only developer and user of the ADEP workbench (`frontend/`, Next.js + Tailwind + vitest). Grounded
by reading the two component files in `frontend/components/ui/`, `frontend/app/globals.css`,
`frontend/context/ThemeContext.tsx`, `frontend/app/layout.tsx`, the 25 files found by a case-insensitive `git grep`
for the employer name, and ticket ADE-29. Git history is out of scope here (a separate, owner-approved step).

## Goals and non-goals

**Goals**
- No mention of the employer or its brand in any tracked text file of the working tree.
- Identical behaviour and look: same markup, same colours, same theme switching.

**Non-goals**
- Rewriting git history (the term also lives in 4 old commits; handled separately).
- Redesigning the UI or changing any colour value.
- Fixing the 22 existing frontend lint errors (ADE-28) or other tickets.

## Requirements

- R1. The two prefixed components (files, exported names, props interfaces, imports, usages, test mocks and test
  ids) must be renamed to plain `Button` and `Badge`.
- R2. The Tailwind `@theme` palette tokens named after the employer brand must be renamed to neutral colour names
  with unchanged hex values; the comment naming the palette must be reworded.
- R3. The theme localStorage key must be renamed to `adep_theme`, in the init script, `ThemeContext` and the tests.
- R4. No tracked text file may contain the employer name or its abbreviations (case-insensitive).
- R5. Behaviour, rendered markup and colours must be unchanged.

## Acceptance criteria

- AC1. A case-insensitive `git grep` for the employer name and its two abbreviations over the working tree,
  excluding the binary demo documents under `sample-data/` (see Edge cases), returns no lines. (R1, R2, R3, R4)
- AC2. `cd frontend && pnpm build` passes and `pnpm test` passes with the same number of tests as before. (R1, R5)
- AC3. `pnpm lint` reports no more errors than the baseline of 22 (ADE-28). (R5)
- AC4. The theme tests (`frontend/tests/theme-context.test.tsx`) pass against the new key: toggling stores
  `adep_theme` as `dark` / `light`, and a stored `dark` value is applied on mount. Failure path: with no stored
  value the theme falls back to the system preference exactly as before. (R3, R5)
- AC5. No hex value or utility class other than the renamed identifiers changes: the diff of `globals.css`
  contains only renamed token names and one comment line. (R2, R5)
- AC6. The backend test suite is unaffected (`-m "not integration"`: the 2 known failures ADE-23 / ADE-24, nothing
  else). (R5)

## Edge cases and failure modes

- Seven binary files in `sample-data/` (5 JPG/PDF reported as "Binary file ... matches", 2 PDFs printed as a
  garbage line) contain a three-character byte sequence (the abbreviation with an ampersand) by coincidence inside
  compressed streams, between random bytes. They are not mentions, cannot be edited without
  corrupting the demo set (AGENTS.md says not to touch `sample-data/`), and are why AC1 excludes `sample-data/`.
- A user with a theme saved under the old key loses it once and sees the system-preferred theme on next load, then
  the choice is stored under the new key. See Assumptions.
- A name clash for `Button` / `Badge` with another import in a touched file would fail the build; checked by
  `pnpm build`.

## Non-functional requirements

- Compatibility: no API, route, or data change. No dependency or CI change.
- Security: no secrets touched; `.env` is not opened.

## Assumptions

- The ticket suggests reading the old localStorage key once to keep a saved theme. That would keep the employer
  string in the code and contradict AC1 (zero hits), so it is not done. Cost: a one-time theme reset to the system
  preference for the owner's browser. The owner can overrule.
- Palette hex values stay as they are (the ticket says the look must not change); only the names change. The
  owner can ask for a different palette separately.
- The stray top-level `app/templates/page.tsx` (outside `frontend/`) is only updated for the renamed imports.

## Risks and dependencies

Low: mechanical rename, fully reversible by `git revert`, no runtime data, one user. Might conflict with other open
frontend branches (ADE-13 migration); merge early.
