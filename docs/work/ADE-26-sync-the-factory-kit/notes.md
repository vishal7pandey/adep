# ADE-26 notes

- 2026-10-06: `factory sync --dry-run .` showed 5 created and 14 updated, no conflict; `factory sync .` (no `--force`) wrote exactly
  those; `factory sync --check .` then said "in sync with the factory source" (exit 0).
- 2026-10-06: `ci.yml` is user-owned and was edited by hand, only the `uses:` lines: `actions/checkout` v4 to v7 (3 places),
  `astral-sh/setup-uv` v3 to v10.2.0, `actions/setup-node` v4 to v7 (the versions the factory kit templates use, FACT-15),
  and `dorny/paths-filter` v3 to v4 (a third-party action the kit does not use; v3 declares `node20`, v4.0.3 declares `node24`).
  Disabled-step comments (ADE-1, ADE-20, ADE-21, ADE-27, ADE-28) and the `--deselect` list are untouched.
- 2026-10-06: the new `sonar.yml` and `sonar-project.properties` are create-mode (ours to edit). One adaptation: the `push` trigger
  said `branches: [main]`; this repo's default branch is `master`, so it is now `[master]`. Nothing else was changed and no value
  was invented: `sonar.organization` stays `REPLACE_ME_SONAR_ORGANIZATION`, `sonar.projectKey=vishal7pandey_adep` was filled in by
  the factory from the origin remote, and no secret was touched. The scan is skipped with a notice until the owner sets both.
- 2026-10-06: left for the owner when the scan is enabled: the sonar "Tests with coverage" step runs a plain
  `pytest -q --cov` (all tests, 2 known failures plus 7 clean-checkout failures, no deselects), so it must be adapted to the
  `ci.yml` backend command (`-m "not integration"` and the `--deselect` lines) before the first real scan; also
  `sonar.python.version=3.12` while CI uses 3.11.
- 2026-10-06: work-item statuses. 17 items were `in-review` with every PR merged (state read with `gh pr view <n> --json state`);
  moved with `factory advance <ID> merged --pr <n>` (the CLI writes `pr` as a string, FACT-20): ADE-1 #4, ADE-4 #5, ADE-5 #6,
  ADE-15 #15, ADE-19 #3, ADE-29 #18, ADE-31 #17, ADE-34 #8, ADE-35 #9, ADE-36 #10, ADE-37 #11, ADE-38 #12, ADE-39 #13, ADE-40 #14,
  ADE-41 #16, ADE-45 #20, ADE-51 #21. The CLI re-serialises the YAML, so unquoted dates (`created: 2026-10-05`) became quoted
  strings; harmless. ADE-30 is `spec-approved` (docs-only PR #7, merged) and was left as is: its status is not `in-review`,
  and moving it needs a decision from the owner.
- 2026-10-06: `factory doctor .`: managed files 31 tracked, all present, unmodified; skills 9 and 9; factory_version 0.1.0;
  harden lines all OK (secret scanning + push protection, dependabot alerts, dependabot security updates, codeql default
  setup); sonar lines OK but dormant (`sonar.organization` still has REPLACE_ME; `SONAR_TOKEN` not set).
