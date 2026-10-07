# ADE-69 — Image read inside the path guard (Sonar S2083 re-raised)

Status: draft · Risk: high · Jira: ADE-69
<!-- Security finding: neutral wording on purpose; this repo is public. -->

One SonarCloud issue: `pythonsecurity:S2083` (BLOCKER vulnerability), Sonar issue `AaEUi-pJNs-rcCYFSaoq`, `src/providers/vlm_azure.py:81`
(`_encode_image`, the `open(real_path, "rb")`), raised by the analysis of PR #24 after the ADE-57 fix. ADE-57 itself closed
(Sonar `AaESHmAUjNIvKL1jZh9X` CLOSED/FIXED, CodeQL accepts the guard). Only this issue is in scope.

## Repro

Environment: `master` @ ce93e7c. Not reproducible as a behaviour: the code already refuses every path outside the working directory
tree and the system temp directory (`src/tests/test_sonar_path_containment.py`, all green). The defect is the scanner's view:
Sonar's taint engine follows `image_path` through `os.path.realpath` to `real_path` to `open` and does not treat the existing guard as
a sanitizer, because the guard first picks `root` with a conditional expression and then checks `startswith(root + os.sep)` once, with
the sink after the `raise`, not inside the guard's true branch.

Automated repro: none can fail on current code. A failing regression test is not possible here (the behaviour is already correct);
the evidence is the Sonar API: issue `AaEUi-pJNs-rcCYFSaoq` status OPEN on master today, expected CLOSED after the fix and a
push scan. Two extra tests are added that pin the sibling-prefix cases the restructure must not loosen.

Reproducibility: always (Sonar reports it on every analysis).

## Expected

`_encode_image` reads a file only inside a branch guarded by `real_path.startswith(<one literal root> + os.sep)`, one check
per root, and raises `ImagePathNotAllowed` otherwise; behaviour identical to today.

## Actual

The read sits after a single check on a conditionally chosen root; Sonar reports the read as unsanitized.

## Root cause (with evidence)

- Where: `src/providers/vlm_azure.py:73-81`.
- Why it fails: the sanitizer is expressed so that Sonar cannot see that the sink is dominated by a check on a fixed base.
  The same idea written as a single base, one check, and the write in the guarded flow (`save_batch`) was accepted by Sonar.
- Introduced by: the CodeQL-driven restructure in PR #24.
- Evidence: Sonar API issue `AaEUi-pJNs-rcCYFSaoq`, status OPEN, line 81.

## Blast radius

Only `_encode_image` (callers: `_call_vlm`, hence `vlm`, `read_chart`, `read_table`, `classify`, `engine/tools`). No behaviour
change, no API change, no other file touched.

## Regression criterion (AC1)

AC1: The existing tests in `src/tests/test_sonar_path_containment.py` stay green and the two new sibling-prefix tests
(`TestImagePathSiblingPrefix`) pass: a path in `<cwd>-evil/` or `<tmp>-evil/` is refused with `ValueError`, the client is never called.

AC2: After the merge and the push scan, the Sonar API
(`https://sonarcloud.io/api/issues/search?issues=AaEUi-pJNs-rcCYFSaoq&componentKeys=vishal7pandey_adep`) shows the issue CLOSED, and
CodeQL stays green on the PR (no new `py/path-injection` alert from this change).

## Fix constraints

- `os.path.realpath` on the root and the candidate, then a single inline `startswith(root + os.sep)` per root whose true branch holds
  the read and the return; the refusal is the code after the loop. No helper, no `Path.resolve()` / `parents` forms (CodeQL does
  not recognise them). Minimal diff: `_encode_image` only.
- Do not touch other findings, `dependabot.yml` or kit files.

## Risks

Risk high (security-relevant code), diff tiny. If Sonar still reports it, investigate; a false-positive claim becomes a dismissal
proposal with evidence for the owner, never applied by the agent. Rollback: revert the merge commit.
