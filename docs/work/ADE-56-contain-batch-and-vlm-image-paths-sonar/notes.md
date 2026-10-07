# ADE-56 notes

- 2026-10-06: PR #24 CodeQL alert 50 (`py/path-injection`) remains open at `src/providers/vlm_azure.py:82` on commit
  `218d91e`. The attempted VLM guards using `any(...)`/generator expressions and `commonpath` did not clear the alert;
  CodeQL moved the alert between `realpath` and `open`.
- 2026-10-06: The repository already uses an inline, separator-aware `realpath` + `startswith(root + os.sep)` guard in
  `src/api/routes/documents.py`. Revised ADE-56's plan to name the working and temp roots and use a direct boolean condition
  instead of a collection/generator/helper. This retains the current tool API and allowed-root behavior.
- 2026-10-06: Alert 50 is separately tracked as ADE-67 (`finding-codeql-50`) per the findings policy; the existing Sonar
  issues remain ADE-56 and ADE-57. The direct-guard plan amendment invalidates the prior plan approval; wait for human
  re-approval before further implementation.
- 2026-10-06: Human approved the amended design in conversation. Replaced the VLM root collection/generator checks with two
  named roots and a direct `or`-combined separator-aware prefix condition. Ruff and factory verification pass; focused
  containment/VLM caller tests: 89 passed, 1 skipped. PR CodeQL must still pass before merge.
- 2026-10-06: Full non-integration suite: 1997 passed, 2 skipped, 19 deselected, 2 known baseline failures (ADE-23
  `test_seeded_definitions_exist` and ADE-24 `test_compact_run_not_in_executor_returns_false`). No additional failures.
- 2026-10-07: After current `master` was merged to restore CodeQL configuration, alert 50 still appeared on the direct
  two-root condition. Changed it to nested single-root early-return guards to match CodeQL's documented pattern; focused
  caller tests remain green (89 passed, 1 skipped). The previous CodeQL run on the base-synced head was `neutral` because
  configurations were missing; this variant requires a fresh scan before assessing closure.
