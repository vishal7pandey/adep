---
id: BLK-234
type: tech-debt
title: "LLM provider silently returns empty response on failure — no error propagation to caller"
priority: medium
status: backlog
phase: 2
owner: devin
created: 2026-08-09T14:30:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [providers, llm, error-handling, silent-failure]
---

## Description

`src/providers/llm.py` `invoke_llm()` catches all exceptions and returns `LLMResponse(content="", input_tokens=0, output_tokens=0)`:

```python
except Exception as e:
    logger.error("LLM call failed: %s", e)
    return LLMResponse(content="", input_tokens=0, output_tokens=0)
```

The `@retry` decorator on `_call_llm` also has `retry_error_callback=lambda retry_state: None`, meaning it returns `None` after exhausting retries instead of raising.

This means callers of `invoke_llm()` (the AI template composer, surrogate verifier) receive an empty string with zero tokens and no indication that the LLM call failed. They can't distinguish between "the LLM returned empty" and "the LLM call failed entirely."

## Problem Statement

- The template composer (`src/ai/template_composer.py`) calls `invoke_llm()` and parses the response as JSON — an empty string will cause a JSON parse error, which gets caught and returned as `{"error": "..."}` — but the error message will say "JSON parse failed" instead of "LLM call failed"
- The surrogate verifier (`src/ai/surrogate_verifier.py`) has the same pattern — the root cause (LLM failure) is masked as a parsing error
- The `retry_error_callback=lambda retry_state: None` silently swallows the retry exhaustion — no exception, no structured error, just `None`
- Token tracking records zero tokens for failed calls, making it impossible to distinguish "free call" from "failed call" in budget reports
- The API endpoint returns 503 with the masked error message, giving the user misleading information

## Acceptance Criteria

- [ ] Either raise an exception on failure (let callers decide how to handle it) or return a structured error response with a `failed: bool` flag
- [ ] Remove the `retry_error_callback=lambda retry_state: None` — let tenacity raise `RetryError` after exhaustion
- [ ] Add a `failed` or `error` field to `LLMResponse` so callers can check success
- [ ] Update callers to check for failure and propagate meaningful error messages

## Constraints

- Don't break the API contract — the API endpoints should still return 503 on LLM failure, but with a meaningful message
- The retry logic itself is fine — it's the silent swallowing that's the problem

## Dependencies

- `src/providers/llm.py`
- `src/agent/token_tracking.py` (`LLMResponse` dataclass)
- `src/ai/template_composer.py` (caller)
- `src/ai/surrogate_verifier.py` (caller)

## Notes

- Found during full-repo audit; this is a common anti-pattern in LLM wrapper code — catching everything to "be safe" but actually hiding failures from callers

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
