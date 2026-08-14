---
id: BLK-183
type: tech-debt
title: "Prompt-injection keyword detector only logs a warning — trivially bypassed, overlaps dead guardrails code"
priority: low
status: backlog
phase: 2
owner: devin
created: 2026-08-09T10:25:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [security, prompt-injection, agent, false-sense-of-security]
---

## Description

`_contains_instruction_patterns()` in `src/agent/graph.py` (~line 1175) is a fixed list of ~16 literal phrases (`"ignore previous instructions"`, `"reveal your instructions"`, `"skip validation"`, `"approve without checking"`, etc.) checked against each LLM response in `plan_node`. On a match it only logs a warning — it does not block, sanitize, redact, or otherwise act on the response:

```python
if response_text and _contains_instruction_patterns(response_text):
    logger.warning(
        "LLM response contains instruction-like patterns — "
        "possible prompt injection attempt [BLK-043]"
    )
```

The function's own docstring is honest about this: "This is a detection/logging function, not a blocking function — the architecture itself prevents injection because the LLM output is always parsed as structured JSON and the validator (deterministic code) always produces the final GapReport." That architectural claim (structured-JSON parsing + deterministic validator as the real defense) may well be true and sufficient — but the keyword list itself adds close to nothing on top of it: it's trivially bypassed by paraphrase, translation, synonyms, or Unicode tricks, and a match today does not feed into anything actionable (no run gets flagged for review, no alert is raised beyond a log line).

It also duplicates ground that `src/agent/guardrails/exfiltration_prevention.py` and `src/agent/guardrails/output_validation.py` appear to have been designed to cover more robustly — except those modules are dead code (BLK-179).

## Problem Statement

Low severity on its own, but it's an easy thing to mistake for real protection. If prompt-injection resistance is meant to be a real product guarantee (it's referenced as such in places), a 16-phrase keyword list logging to a file no one is watching is not that guarantee.

## Acceptance Criteria

- [ ] Decide explicitly: is `_contains_instruction_patterns` meant to be a real safety layer, or a cheap diagnostic signal?
- [ ] If diagnostic-only (matches current docstring intent): keep it, but make the warning surface somewhere actionable (structured log field / metric / run-level flag visible in the UI or `.adep` reports), not just a logger.warning that nobody consumes
- [ ] If meant to be a real defense: fold in the actually-designed detection from `guardrails/exfiltration_prevention.py` / `guardrails/output_validation.py` as part of resolving BLK-179, rather than maintaining two separate, weaker, unconnected detectors
- [ ] Document which of the two this is in the function's docstring/README so it isn't overstated

## Constraints

- Don't block or sanitize LLM output as a side effect of this ticket without a deliberate design decision — that's a behavior change with its own risk (false positives blocking legitimate runs)
- Resolve in the same pass as BLK-179 if the decision is to consolidate with the guardrails package

## Dependencies

- `src/agent/graph.py` (`_contains_instruction_patterns`, `plan_node`)
- BLK-179 (guardrails wire-or-delete decision)

## Notes

- Found via full-repo audit (`ADE_codebase_audit.md`, §9); confirmed still present and still log-only as of 2026-08-09

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T10:25 (mgmt)**: Logged after confirming the function still only logs a warning with no downstream consumer.
