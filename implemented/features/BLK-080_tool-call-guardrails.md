---
id: BLK-080
type: feature
title: "Tool call guardrails — argument validation, allowlist, sandboxing"
priority: high
status: backlog
phase: 4
owner: backend
created: 2026-08-08T01:45:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-009, BLK-043]
tags: [backend, security, guardrails, tools, validation, sandboxing]
---

## Description

The LLM proposes tool calls, but the execution layer must validate every
tool call before execution. Tools are on a strict allowlist, arguments
are validated against ToolSpec schemas, and dangerous operations are
sandboxed.

## Motivation

If the LLM is compromised via prompt injection or hallucination, it
could propose tool calls with malicious arguments — reading files
outside the document directory, calling external APIs, or executing
arbitrary code. Tool call guardrails prevent this.

## Guardrails

1. **Tool allowlist:** Only tools registered in the Tool Registry can be
   called. The LLM cannot invoke arbitrary functions or system commands.

2. **Argument schema validation:** Every tool call's arguments are
   validated against the tool's `ToolSpec.args_schema` (Pydantic). Invalid
   arguments → tool call rejected, logged, agent retries.

3. **Path sandboxing:** File-path arguments (e.g., `crop_image` bbox,
   `read_page` page number) are validated against the document's actual
   dimensions. No path traversal. No out-of-bounds page numbers.

4. **Rate limiting per tool:** Each tool has a max-calls-per-cycle and
   max-calls-per-run limit. Prevents the LLM from spamming a tool.

5. **Argument sanitization:** String arguments are stripped of control
   characters, null bytes, and shell metacharacters.

6. **Tool call audit log:** Every tool call (accepted or rejected) is
   logged with: tool name, arguments, result, timestamp, cycle number.

7. **No dynamic tool creation:** The LLM cannot create or register new
   tools at runtime. The tool registry is immutable during a run.

## Acceptance Criteria

- [ ] Unregistered tool calls are rejected + logged
- [ ] Invalid arguments are rejected + logged
- [ ] Path arguments are sandboxed to document directory
- [ ] Page numbers are validated against document page count
- [ ] Per-tool rate limits enforced
- [ ] String arguments sanitized (no control chars, null bytes)
- [ ] All tool calls (accepted/rejected) logged to trace
- [ ] Unit tests: injection via tool args, path traversal, out-of-bounds

## Dependencies

- BLK-009 (tool interface contracts)
- BLK-043 (prompt injection defense)
