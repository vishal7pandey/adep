"""LLM guardrails — defense-in-depth for untrusted LLM output [BLK-079..086].

No single guardrail is the last line of defense. The LLM is treated as
an untrusted perception engine. Every output is validated, sanitized,
and audited before it reaches tool execution or state mutation.

Modules:
- output_validation: Schema validation, field allowlist, sanitization [BLK-079]
- tool_guardrails: Tool allowlist, argument validation, sandboxing [BLK-080]
- loop_detection: Circular reasoning and loop detection [BLK-082]
- retry_circuit_breaker: Retry storm prevention and circuit breaker [BLK-085]
"""

from __future__ import annotations
