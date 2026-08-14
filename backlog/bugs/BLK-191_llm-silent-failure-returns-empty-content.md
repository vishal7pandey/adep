---
id: BLK-191
type: bug
title: "LLM and template composer silently return empty content on failure — no error surfaced to caller"
priority: medium
status: backlog
phase: 5
owner: devin
created: 2026-08-09T11:10:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [backend, error-handling, reliability, observability]
---

## Description

`src/providers/llm.py` `invoke_llm()` swallows all exceptions and returns `LLMResponse(content="")` with no indication of failure:

```python
except Exception as e:
    logger.error("LLM call failed: %s", e)
    return LLMResponse(content="", input_tokens=0, output_tokens=0)
```

Likewise, `_call_llm` uses tenacity with `retry_error_callback=lambda retry_state: None`, which converts a retry-exhausted failure into `None` rather than raising. The caller of `invoke_llm` (e.g. `src/ai/template_composer.py`, `src/ai/surrogate_verifier.py`, and the graph's plan node) receives empty content with no way to distinguish "the LLM had nothing to say" from "the LLM call failed".

This causes:
- Silent empty template generation (BLK-067) — user sees an empty shell with no error
- Silent empty verifier diagnoses (BLK-070)
- Difficult debugging — failures are only visible in logs, not in the API response

## Acceptance Criteria

- [ ] `invoke_llm` returns a result that clearly distinguishes success (content) from failure (error/status)
- [ ] Callers (template_composer, surrogate_verifier, plan node) surface the failure to the API layer with a user-readable error
- [ ] Tests added: LLM failure returns an error, not empty content masquerading as success

## Constraints

- Must preserve backward compatibility where empty-string content is a legitimate outcome
- Must not expose internal error details (stack traces) to the API consumer — log details server-side, return a clean message

## Dependencies

- None

## Notes

- Found during provider layer audit
- Related to BLK-157 (silent error swallowing) which was fixed for other paths but missed the LLM provider
- Related to BLK-067 / BLK-070 (AI composers)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
