# ADE-31 — Test plan: Head-to-head P&ID evaluation: old LangGraph engine vs new engine

Status: approved · Risk: medium · Jira: ADE-31

Test framework and conventions found: pytest, tests in `src/tests/test_*.py`, run with `.venv/Scripts/python.exe -m pytest src/tests/<file> -q`; classes grouped by behaviour; stubs not mocks of the code under test; no network or key in unit tests.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_pid_compare.py::TestRunComparison | 2 stub engines x 2 drawings x N=3: each called 3 times per drawing, call order alternates A,B within each repetition, records hold seconds from a fake clock, score, tokens | N=1: one run each; one engine only | n/a: invalid N is rejected by the CLI (covered under AC6 argument checks) | verified |
| AC2 | unit | src/tests/test_pid_compare.py::TestSummarize | recalls 0.5/0.7/0.9 -> mean 0.7, stdev 0.2, min 0.5, max 0.9 | single success -> stdev None; zero successes -> all None | failed runs excluded from the means, counted in failures | verified |
| AC3 | unit | src/tests/test_pid_compare.py::TestFailureIsolation | engine raising on run 2 -> failure record, other runs complete | engine returns `{}` / no lists -> `UnparseableOutput` failure | exception text `sk-secret-123` absent from records, file, table | verified |
| AC4 | unit | src/tests/test_pid_engines.py::TestGraphToExtraction | mixed graph maps to 2/2/2/1/4 and carries tags | empty graph -> five empty lists; unknown type -> nodes | `None`, missing keys, non-dict nodes/edges do not raise | verified |
| AC5 | unit | src/tests/test_usage_meter.py | sync and async fake create counted, totals match | call cap and token cap exactly at the limit: next call raises, underlying not called | exception inside the body still restores originals | verified |
| AC6 | unit | src/tests/test_pid_compare.py::TestResultsAndTable | results JSON has meta, records, summary; default dir is `.adep/eval` (and `git check-ignore` agrees); table has per-drawing and overall rows with n and failures | no prices -> no dollar column; with prices -> dollars | `OPENAI_API_KEY=sk-fake-key-123` set: value absent from file and table; missing refs dir -> clear error before any engine call | verified |
| AC7 | unit | src/tests/test_pid_compare.py::TestBudget | meter exhausted midway -> remaining runs `skipped_budget`, summary and table flag incomplete | cap hit on the very first run -> all skipped, no crash | n/a: nothing to reject, failure path is the cap itself | verified |
| AC8 | manual | (see Manual checks) | real run executes and numbers are posted | n/a | n/a: the old engine failing every run is reported as a finding | planned |

## Regression risk

New files only; the one touched shared thing is `settings.ocr_provider`, which the old adapter sets and restores (tested in test_pid_engines). Existing suite must stay at the known baseline (2 failures ADE-23/24, unchanged).

## Untestable AC

None.

## Manual checks

AC8: (1) capped smoke run, one run per engine on one drawing; (2) the full N=5 x 3 drawings x 2 engines run; (3) confirm the results file is git-ignored and contains no key (`grep` for the key prefix is done with the key loaded in the shell, output suppressed); (4) post the table, spread and verdict on ADE-31 and in Confluence.

## Audit (after implementation)

Method: for each behaviour, one mutation was applied to the implementation, the three test files were run with `-x`, and the file was restored; 15 of 15 mutations were caught (script kept in the scratchpad, not committed). The suite as a whole: 1968 passed, 2 failed (the known ADE-23 and ADE-24 failures, identical on a clean tree).

| AC | Test (file:line) | Mutation tried | Result |
|----|------------------|----------------|--------|
| AC1 | src/tests/test_pid_compare.py:98 | engine loop moved outside the repetition loop (no interleaving) | caught |
| AC2 | src/tests/test_pid_compare.py:124, :131 | population instead of sample standard deviation; failed runs let into the means | caught, caught |
| AC3 | src/tests/test_pid_compare.py:150, :163 | store `str(exc)` instead of the type; accept output with no category lists | caught, caught |
| AC4 | src/tests/test_pid_engines.py:20 | count `pipe` nodes as equipment; stop mapping valves | caught, caught |
| AC5 | src/tests/test_usage_meter.py:46, :73, :99 | skip the call-cap check; stop counting async; skip restore on exit | caught x3 |
| AC6 | src/tests/test_pid_compare.py:243 | remove the key redaction | caught |
| AC7 | src/tests/test_pid_compare.py:197, :215 | skip the budget check before a run; record the cap as a failure | caught, caught |
| R8 | src/tests/test_pid_engines.py:104 | adapter ignores its configured OCR provider; does not restore it | caught, caught |

AC6's table and argument checks (:251, :257, :276) and the git-ignore check (:235) were verified by reasoning and by running them, not mutated: the table test asserts row counts and column presence; the git-ignore test shells out to `git check-ignore` on the real path. AC8 is the manual real run (see the PR and the Jira report).
