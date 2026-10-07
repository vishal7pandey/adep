# ADE-58 — Rewriter LLM call and verifier slice (Sonar S930 ADE-58, S6466 ADE-59)

Status: draft · Risk: low · Jira: ADE-58
<!-- Bug fix from scanner findings. -->

Covers two SonarCloud bug findings:

| Jira | Sonar issue | Rule | Location |
|------|-------------|------|----------|
| ADE-58 | `AaESHmCCjNIvKL1jZh-E` | `python:S930` (BLOCKER bug): unexpected named argument `temperature` | `src/ai/query_rewriter.py:293` |
| ADE-59 | `AaESHmB5jNIvKL1jZh-D` | `pythonbugs:S6466` (CRITICAL bug): access on a collection that may raise `IndexError` | `src/ai/surrogate_verifier.py:91` |

ADE-58 is the key of this work item; ADE-59 closes separately on its own re-queried Sonar issue. Only these two issues are in scope.

## Repro

Environment: `master` @ d13c1e9, Python 3.14 venv, Windows; platform independent.

Automated repro: `src/tests/test_sonar_bug_fixes.py`, run `uv run python -m pytest src/tests/test_sonar_bug_fixes.py -q`.
On current code 6 of 11 tests fail (5 pass and pin behaviour):
- ADE-58, four tests drive `decompose_skill` through the real `invoke_llm` (stubbed chat client) or through an `autospec`
  stub of `invoke_llm`: the call raises `TypeError: invoke_llm() got an unexpected keyword argument 'temperature'`, which the
  broad `except` turns into a result with `rationale="LLM decomposition failed: ..."` and no sub-skills; `_call_llm` is called 0 times.
- ADE-59, two tests: `_heuristic_verify` with a gap report whose `gaps` is `None` (dict key or object attribute) raises
  `TypeError: 'NoneType' object is not subscriptable` at `surrogate_verifier.py:91`.

Reproducibility: always.

## Expected

- `decompose_skill` calls `invoke_llm(system_prompt, user_prompt, max_tokens=...)` with only the arguments it accepts (no
  `temperature`: `invoke_llm` has no such parameter, and current OpenAI reasoning models reject it, so it is removed rather than added),
  reads the reply text from `LLMResponse.content`, and returns the proposed sub-skills.
- `_heuristic_verify` treats a gap report with no, empty or `None` `gaps` / `satisfied` as empty and never raises.

## Actual

- The LLM decomposition path never worked: the `temperature` keyword raised `TypeError` on every call and the broad `except`
  silently fell back to the heuristic decomposer. Fixing only the keyword would expose a second defect on the same line of
  code: `invoke_llm` returns an `LLMResponse`, but the code passes it to `json.loads` as a string (existing tests mocked a plain `str`).
- `gaps[:8]` fails on `None`. (A slice of an empty list is safe; Sonar's finding comes from the path where `gap_report is None`
  yields a literal `[]`. The real defect it points at is the unguarded `None` case above.)

## Root cause (with evidence)

- Where: `src/ai/query_rewriter.py:290-295` and `:304`; `src/ai/surrogate_verifier.py:77-78,91`.
- Why it fails: a call written against a different callee signature and return type (`temperature=`, str reply) than
  `src/providers/llm.py:53` `invoke_llm(system_prompt, user_prompt, *, max_tokens) -> LLMResponse`; and a collection read without
  coalescing `None` to an empty list.
- Introduced by: always present (original implementations).
- Evidence: the 6 failing tests; `src/providers/llm.py:53`.

## Blast radius

- `decompose_skill` is called by `rewrite_failing_skill` (and `/skills/rewrite` route); with the LLM path broken it always
  returned the heuristic result. After the fix the LLM path is live for `use_llm=True`: real model calls (paid) now happen on
  that path, as designed. Failure of the call still degrades to the heuristic.
- Existing tests in `src/tests/test_query_rewriter.py` mock `invoke_llm` with a plain `str`; they encoded the wrong contract and are
  updated to return `LLMResponse`.
- Other `invoke_llm` callers (`oneflow`, `agent_composer`, `prompt_evolver`, `skill_composer`, `surrogate_verifier`,
  `template_composer`, `workflow_optimizer`, `run_engine`) already use `.content` and no `temperature` (grep checked).
- `_heuristic_verify` is reached from `verify_skill` when the model returns no usable JSON.

## Regression criterion (AC1)

AC1: The failing tests in `src/tests/test_sonar_bug_fixes.py` pass after the fix and fail on the current code: `decompose_skill`
calls the model without `temperature`, parses `LLMResponse.content`, and returns the sub-skills; `_heuristic_verify` handles `None`
collections.

AC2: Behaviour that works today is unchanged: heuristic fallback when the call raises, no-JSON and bad-JSON replies degrade to a result
with no sub-skills, at most 8 gaps are diagnosed; the updated `test_query_rewriter.py` and the backend suite stay at the known
baseline (`-m "not integration"`: only ADE-23 and ADE-24 fail).

AC3: After the merge and the push scan, the Sonar API shows `AaESHmCCjNIvKL1jZh-E` (ADE-58) and `AaESHmB5jNIvKL1jZh-D` (ADE-59)
CLOSED. If Sonar still reports ADE-59 on the corrected code, investigate; a false-positive claim becomes a dismissal proposal to the
owner with this evidence, never applied by the agent.

## Fix constraints

- Remove `temperature=0.3` at the call site; do not add a parameter to `invoke_llm`.
- Use `response.content`; keep the fallback behaviour. Minimal diff: `query_rewriter.py`, `surrogate_verifier.py`, the existing
  `test_query_rewriter.py` mocks, the new test file, this folder.
- Do not touch other findings or unrelated files.

## Risks

Low. The LLM decomposition path becomes live (it was dead); any failure still falls back to the heuristic, so the worst case is
today's behaviour. Rollback: revert the merge commit.
