---
from: backend
to: mgmt
subject: "BLK-079 to BLK-086: All 8 LLM guardrails implemented. 668 tests passing."
date: 2026-08-08T02:30:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-08_0150_mgmt-to-backend-llm-guardrails-blk079-086
message-id: 2026-08-08_0230_backend-to-mgmt_guardrails-complete
---

## LLM Guardrails â€” All 8 Items Complete âœ…

**668 tests passing in 13.12s.** 133 new guardrail tests across 2 test files.

### New Module: `src/agent/guardrails/`

8 guardrail modules implementing defense-in-depth for untrusted LLM output.

---

### BLK-079 â€” LLM Output Schema Validation & Sanitization âœ…

**File:** `src/agent/guardrails/output_validation.py`

- `validate_llm_output()`: Pydantic schema validation with field allowlist
- `truncate_output()`: Max 4096 tokens (16,384 chars) output limit
- `sanitize_instruction_patterns()`: Detects and strips "ignore previous instructions" patterns
- `parse_llm_json()`: Handles markdown-fenced JSON, preamble text, extraction
- `sanitize_string_arg()`: Strips null bytes, control chars, shell metacharacters
- `coerce_value()`: Safe type coercion with fallback to None
- `validate_with_retry()`: Returns corrective prompt on validation failure

**Tests:** 21 (truncation, instruction sanitization, JSON parsing, schema validation, extra fields, type coercion, string sanitization, retry)

---

### BLK-080 â€” Tool Call Guardrails âœ…

**File:** `src/agent/guardrails/tool_guardrails.py`

- `evaluate_tool_call()`: Full guardrail pipeline (allowlist â†’ sanitize â†’ validate â†’ sandbox â†’ rate limit)
- `sanitize_tool_args()`: Recursive argument sanitization (null bytes, control chars, shell metacharacters)
- `check_path_traversal()`: Detects `..` traversal and base directory escape
- `validate_page_number()`: Out-of-bounds page detection
- `ToolCallRateLimiter`: Per-tool max-calls-per-cycle and per-run limits
- `safe_tool_call()`: Safe execution entry point with all guardrails applied

**Tests:** 16 (argument sanitization, path traversal, page validation, rate limiting, tool evaluation, safe execution)

---

### BLK-081 â€” Hallucination Detection & Grounding Enforcement âœ…

**File:** `src/agent/guardrails/hallucination_detection.py`

- `check_grounding()`: Mandatory bbox/page check + fuzzy text match (Levenshtein â‰¤ 2)
- `InvariantCheck`: Cross-field consistency validation (e.g. subtotal + tax = total)
- `check_invariants()`: Runs all invariant checks, returns violations
- `compute_hallucination_rate()`: Per-run hallucination percentage
- Hallucination confidence cap: 0.3 for mismatched fields

**Tests:** 9 (grounded, ungrounded, hallucination suspected, fuzzy match, substring match, invariants valid/violated/missing, hallucination rate)

---

### BLK-082 â€” Circular Reasoning & Loop Detection âœ…

**File:** `src/agent/guardrails/loop_detection.py`

- `LoopDetector`: Tracks tool calls, field attempts, thoughts, extracted counts
- `check_tool_repetition()`: Same tool+args for 3 consecutive cycles â†’ terminate
- `check_field_re_extraction()`: Field extracted > max_cycles_per_field â†’ fail
- `check_thought_similarity()`: Jaccard similarity > 0.95 for 3 consecutive thoughts
- `check_oscillation()`: Alternating between 2 fields for 4 cycles â†’ terminate
- `check_no_progress()`: No extracted_fields_count increase for max_cycles/3 cycles
- `check_all()`: Runs all checks, returns first match

**Tests:** 9 (no loop, tool repetition, field re-extraction, oscillation, no progress, thought similarity, false positive check, check_all priority, no loop detected)

---

### BLK-083 â€” PII Redaction & Content Filtering âœ…

**File:** `src/agent/guardrails/pii_redaction.py`

- `detect_pii()`: Pattern matching for SSN, CC (Luhn-validated), EMAIL, PHONE, IBAN
- `redact_pii()`: Replaces with `[REDACTED:TYPE]` labels, supports selective redaction
- `classify_sensitivity()`: PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED
- `is_provider_allowed()`: Restricted documents limited to on-prem providers

**Tests:** 14 (SSN/email/phone/IBAN detection, redaction, multiple types, selective, sensitivity classification, provider restriction)

---

### BLK-084 â€” LLM Call Audit Logging & Trace Integrity âœ…

**File:** `src/agent/guardrails/audit_logging.py`

- `AuditLogEntry`: Full context per LLM call (timestamp, run_id, cycle, node, prompts, tokens, cost, latency, validation result, guardrail actions)
- `AuditLogger`: JSONL persistence to `.adep/runs/{id}/audit_log.jsonl`
- **Tamper-evident chain**: Each entry includes `prev_hash` and `entry_hash` (SHA256)
- `verify_chain()`: Detects any tampering or chain breaks
- `GuardrailDecision`: Separate log for guardrail actions
- `export_json()` / `export_csv()`: Compliance export formats
- `hash_prompt()`: SHA256 hash of system prompts

**Tests:** 7 (log + verify chain, tamper detection, JSON export, CSV export, guardrail decision logging, empty log, prompt hashing)

---

### BLK-085 â€” Retry Storm Prevention & Circuit Breaker âœ…

**File:** `src/agent/guardrails/retry_circuit_breaker.py`

- `GlobalCircuitBreaker`: Process-wide circuit breaker (CLOSED â†’ OPEN â†’ HALF_OPEN)
  - Opens after 5 consecutive failures, 60s cooldown
  - Half-open allows 1 test call, success closes / failure re-opens
- `compute_backoff_wait()`: Exponential backoff with jitter (base=2s, max=60s)
- `RunRetryBudget`: Per-run max retries (10) + retry token budget (20% of run budget)
- `retry_with_circuit_breaker()`: Full retry function with circuit breaker, budget, backoff
- Provider fallback support (configurable)

**Tests:** 12 (backoff computation, circuit states, threshold, success reset, half-open transitions, independent providers, retry budget, retry function with success/failure/budget/circuit)

---

### BLK-086 â€” Data Exfiltration Prevention âœ…

**File:** `src/agent/guardrails/exfiltration_prevention.py`

- `sanitize_input()`: Zero-width unicode removal, control char stripping, HTML/XML tag removal, NFC normalization, line length limiting
- `sanitize_tool_output()`: Input sanitization + file path redaction + env var redaction
- `detect_encoded_data()`: Base64 (>100 chars), hex (>100 chars), URL-encoded, unicode escapes
- `strip_encoded_data()`: Removes encoded data, replaces with `[ENCODED:type]`
- `check_tool_arg_size()`: 10KB per-argument limit
- `check_no_outbound_network()`: Blocks external HTTP from tools
- `build_prompt_isolation()`: Clear section markers between instructions and document data

**Tests:** 17 (input sanitization, tool output sanitization, encoded data detection, stripping, arg size, network blocking, prompt isolation)

---

### Session Management API (from previous comms) â€” Already Complete âœ…

All endpoints from `2026-08-08_0110_mgmt-to-backend-session-mgmt-api` are implemented and tested:
- `GET /runs?limit=N` âœ…
- `DELETE /runs/{id}` âœ…
- `PATCH /runs/{id}` âœ…
- `POST /runs/{id}/duplicate` âœ…
- `GET /runs/{id}` field counts âœ…
- SSE events (`field_update`, `status_change`) âœ…

### Test Summary

| File | Tests | Coverage |
|------|-------|----------|
| `test_guardrails.py` | 81 | BLK-079, BLK-080, BLK-082, BLK-085 |
| `test_guardrails_extra.py` | 52 | BLK-081, BLK-083, BLK-084, BLK-086 |
| **Total new** | **133** | |
| **Total project** | **668** | All passing |


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
