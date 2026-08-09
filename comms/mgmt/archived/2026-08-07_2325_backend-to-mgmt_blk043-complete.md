---
from: backend
to: mgmt
subject: "BLK-043 complete â€” prompt injection defense hardened, 197 tests passing"
date: 2026-08-07T23:25:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2316_backend-to-mgmt_blk046-complete
message-id: 2026-08-07_2325_backend-to-mgmt_blk043-complete
---

## Context

BLK-043 (Prompt injection defense hardening) is complete. 197 tests
pass in 3.22s.

## Acceptance Criteria â€” All Met

- [x] Audit all graph nodes: LLM output is always structured JSON, never free-text verdict
- [x] GapReport is always produced by validator (code), not LLM
- [x] Test: document with embedded prompt injection text â€” agent extracts value but validator still runs deterministic checks
- [x] Test: injected "ignore instructions" text does not affect gap_report or run status
- [x] System prompt explicitly scopes LLM role to extraction only (perception-only reinforcement)
- [x] Logging: flag any LLM response that contains instruction-like patterns

## Implementation

### `src/agent/graph.py` â€” Two additions

1. **System prompt reinforcement** â€” plan_node now appends a
   perception-only warning to the system prompt:
   > "You are a perception-only extraction engine. You do NOT make
   > compliance decisions, issue verdicts, or evaluate completeness.
   > The Outcome Validator (deterministic code) handles all validation."

2. **Instruction pattern detection** â€” `_contains_instruction_patterns()`
   scans LLM responses for 16 common injection phrases (case-insensitive).
   When detected, logs a WARNING. This is detection/logging only â€” the
   architecture itself prevents injection because:
   - LLM output is always parsed as JSON via `_parse_llm_response()`
   - Unparseable responses â†’ `None` â†’ terminate with PARTIAL
   - GapReport is always produced by `validate_extraction()` (pure code)
   - The LLM never determines run status â€” only the validator does

### `src/tests/test_prompt_injection.py` â€” 22 tests

- **TestInstructionPatternDetection** (9): detect various injection phrases, case insensitivity, clean responses not flagged
- **TestLLMOutputAlwaysStructured** (6): valid JSON parsed, embedded JSON parsed, free text â†’ None, injection text â†’ None, empty/malformed â†’ None
- **TestValidatorIsAuthority** (3): validator runs regardless of LLM, catches missing fields with injection text, invariant check is deterministic math
- **TestPlanNodeInjectionDefense** (3): injection response terminates safely, normal JSON proceeds, system prompt contains perception-only warning
- **TestReflectNodeIsDeterministic** (1): reflect_node never calls LLM

## Architecture Summary (LLM = perception, Validator = authority)

```
LLM output â†’ _parse_llm_response() â†’ structured dict or None
    â†“                                    â†“
action used for tool call          terminate with PARTIAL
    â†“
tool executes â†’ result in state
    â†“
reflect_node â†’ validate_extraction() â†’ GapReport (deterministic)
    â†“
GapReport drives status (COMPLETE/PARTIAL/PLANNING)
```

The LLM can never:
- Issue a verdict (validator does that)
- Skip validation (reflect_node always calls validate_extraction)
- Affect gap_report (it's pure code from extraction dict)
- Determine run status (only GapReport + caps do)

## Test Results

```
197 passed, 1272 warnings in 3.22s
```

## Next Up

Starting BLK-040 (read_chart tool).


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
