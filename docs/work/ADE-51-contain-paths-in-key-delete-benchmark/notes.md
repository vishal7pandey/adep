# ADE-51 notes

- 2026-10-06: one work item covers CodeQL `py/path-injection` alerts 3 to 6 (Jira ADE-51 to ADE-54). Pattern per the chatpid
  CPID-34 fix, which closed alerts 1 and 2 there: `os.path.realpath` on base and candidate, then `startswith(base + os.sep)`,
  inline at each call site, before any filesystem probe.
- 2026-10-06: benchmarks route now validates provider names before the directory (so the existing invalid-provider test, which uses a
  directory outside the cwd, still answers 400) and answers 404 for an out-of-base directory (same as a missing one).
- 2026-10-06: sibling routes `get_thumbnail` and `get_document` in `documents.py` have the same unhandled `ValueError` for an invalid
  id; left for the later sweep (not in the four alerts).
- 2026-10-06: the mutation audit found a gap (prefix check without `os.sep` survived); closed with two sibling-prefix tests.
- Closure: Jira tickets close only when each alert reads `fixed` (`factory-findings`).
