# ADE-55 — Notes

- `ci.yml` does not pass `-m "not integration"`; the sonar step adds it as a safeguard (the only deliberate difference).
- The first PR scan reported `Detected project binding: NONEXISTENT` and then `ANALYSIS SUCCESSFUL`: SonarCloud created the
  project from the PR analysis. The anonymous `search_projects` API returned 0 projects right after it (a pull-request-only
  analysis has no main-branch analysis yet); the check is repeated after the merge scan on `master`.
- The scan warned that `sonar.tests` is not set (test files found by path heuristic). Optional follow-up: `sonar.tests=src/tests`.
