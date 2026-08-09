---
id: BLK-086
type: feature
title: "Data exfiltration prevention & input sanitization"
priority: high
status: backlog
phase: 4
owner: backend
created: 2026-08-08T01:45:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-043, BLK-080, BLK-083]
tags: [backend, security, guardrails, exfiltration, input-sanitization, data-leak, defense]
---

## Description

Prevent the LLM from exfiltrating document data through tool calls,
external requests, or encoded output. Sanitize all inputs before they
reach the LLM and all outputs before they reach the system.

## Motivation

A prompt-injected LLM could attempt to:
- Encode document content into tool call arguments to send externally
- Embed document data in error messages or trace output
- Use steganographic techniques (unicode, whitespace encoding) to leak
  data past output filters
- Construct URLs or file paths that leak data via side channels

## Guardrails

1. **Input sanitization:** All text fed to the LLM (OCR output, document
   content, user instructions) is sanitized:
   - Remove control characters and zero-width unicode
   - Normalize unicode to NFC form
   - Strip HTML/XML tags from OCR text
   - Limit line length to 10,000 characters

2. **Tool output sanitization:** Tool results fed back to the LLM are
   sanitized the same way. No raw binary, no file paths, no environment
   variables in tool results.

3. **No outbound network from tools:** Tools cannot make HTTP requests
   to external URLs. The only network calls are to the configured LLM
   provider and OCR/VLM providers. No arbitrary URL fetching.

4. **Output encoding detection:** Scan LLM output for encoded data:
   - Base64 strings > 100 chars
   - Hex-encoded strings > 100 chars
   - URL-encoded payloads
   - Unicode escape sequences
   If detected, log a warning and strip from output.

5. **Tool argument size limits:** Tool call arguments are size-limited
   (default 10KB per argument). Prevents the LLM from embedding large
   document chunks in tool calls.

6. **No environment access:** Tools cannot access environment variables,
   system files, or process information. The tool execution context is
   sandboxed.

7. **Prompt isolation:** System prompt and user prompt are clearly
   separated. Document content is always in a marked "document data"
   section, never mixed with instructions.

## Acceptance Criteria

- [ ] Input text sanitized (control chars, unicode, HTML stripped)
- [ ] Tool results sanitized before feeding to LLM
- [ ] No outbound network calls from tools
- [ ] Encoded data in LLM output detected and stripped
- [ ] Tool argument size limited to 10KB
- [ ] Tools cannot access environment or system files
- [ ] System prompt and document content clearly separated
- [ ] Unit tests: base64 exfiltration, path traversal, unicode steganography

## Dependencies

- BLK-043 (prompt injection defense)
- BLK-080 (tool call guardrails)
- BLK-083 (PII redaction)
