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
