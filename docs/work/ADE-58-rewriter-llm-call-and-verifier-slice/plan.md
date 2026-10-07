# ADE-58 — Rewriter LLM call and verifier slice (Sonar S930 ADE-58, S6466 ADE-59)

Status: draft · Risk: low · Jira: ADE-58
Created: 2026-10-07 · Slug: rewriter-llm-call-and-verifier-slice · Spec: spec.md

## Summary

Drop the `temperature` keyword and read `LLMResponse.content` in `decompose_skill`; make `_heuristic_verify` coalesce `None`
`gaps` / `satisfied` to empty lists. Update the old rewriter test mocks to the real return type.

**Size:** S

## Current state

- `src/ai/query_rewriter.py` `decompose_skill` (line 247): `response = invoke_llm(system_prompt=..., user_prompt=..., temperature=0.3, max_tokens=4000)`
  inside a `try/except Exception`, then `json.loads(response)` and `re.search(..., response)`.
- `src/providers/llm.py:53` `invoke_llm(system_prompt, user_prompt, *, max_tokens=2000) -> LLMResponse` (`.content`, token counts).
- `src/ai/surrogate_verifier.py` `_heuristic_verify` lines 77-78: ternaries on `gap_report is not None`, line 91 `for gap in gaps[:8]`.
- `src/tests/test_query_rewriter.py` mocks `invoke_llm` with a plain `str` (lines 246, 287, 304 and the rewrite tests).
- Tests via `uv run python -m pytest ...`; failing tests already in `src/tests/test_sonar_bug_fixes.py` (6 of 11 fail).

## Approach

1. `decompose_skill`: remove `temperature=0.3`; `text = response.content`; use `text` for `json.loads` and the regex fallback.
2. `_heuristic_verify`: `gaps = _value_from(gap_report, "gaps", None) or []` and the same for `satisfied` (the helper already copes with a
   `None` report), then iterate `gaps[:8]`.
3. `test_query_rewriter.py`: wrap the mocked replies in `LLMResponse(content=...)`.

**Alternatives rejected**
- Add `temperature` to `invoke_llm`: current OpenAI reasoning models reject it, and no other caller needs it.
- Keep `json.loads(response)` and make `invoke_llm` return a string: breaks every other caller.
- `# NOSONAR` or a dismissal for ADE-59: the `None` case is a real defect; fix it, then read what Sonar says.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Fix the call and the reply parsing | `src/ai/query_rewriter.py` | AC1, AC2 | `uv run python -m pytest src/tests/test_sonar_bug_fixes.py -q` |
| T2 | Update the old mocks to `LLMResponse` | `src/tests/test_query_rewriter.py` | AC2 | `uv run python -m pytest src/tests/test_query_rewriter.py -q` |
| T3 | Coalesce `None` collections | `src/ai/surrogate_verifier.py` | AC1, AC2 | `src/tests/test_sonar_bug_fixes.py`, `test_surrogate_verifier*.py` |
| T4 | Full suite, ruff, mutation audit, PR scan | none | AC1, AC2 | baseline 2 failures; no new Sonar/CodeQL issue on the PR |
| T5 | After merge and push scan read both Sonar issues | none | AC3 | API shows CLOSED |

## Data, API and migration impact

None. The `/skills/rewrite` route now gets real LLM decompositions when `use_llm` is true (it silently used the heuristic before).

## Security and failure modes

No new inputs. A failing model call still degrades to the heuristic decomposer.

## Rollout and rollback

Merge via PR; revert the merge commit to undo.

## Risks and open points

Sonar may keep reporting ADE-59 on the slice even after the `None` fix (the engine's complaint is about a literal `[]`); then try
`itertools.islice`, and only then a dismissal proposal with evidence.
