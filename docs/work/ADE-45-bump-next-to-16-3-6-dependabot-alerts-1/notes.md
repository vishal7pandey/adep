# ADE-45 notes

- 2026-10-05: one work item covers Dependabot alerts 1, 2, 3, 6, 7, 27 (Jira ADE-45 to ADE-50); alerts 6, 7, 27 are
  the lockfile twins of 1, 2, 3. Target version 16.3.6 (highest first-patched across the three advisories).
- 2026-10-05: `eslint-config-next` left at 16.3.0 on purpose (no alert, keeps lint baseline stable).
- 2026-10-05: lockfile diff is larger than the version bump: pnpm 11 re-resolved `next`'s optional `sharp` packages
  (0.35.3 to 0.35.5, libvips 1.3.2 to 1.3.4) and rewrote peer-dependency suffixes (`supports-color`). No other direct dependency moved.
- 2026-10-05: running `pnpm <script>` after hand-editing `package.json` makes pnpm 11 re-sync the lockfile and
  node_modules to the edited value; do not hand-edit the pin to test a mutation without re-running `pnpm add`.
- Closure: Jira tickets close only when each alert reads `fixed` (`factory-findings`).
