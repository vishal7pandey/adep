---
id: BLK-006
type: feature
title: "Azure GPT-5.4 VLM provider (vlm, read_chart, read_table)"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-003]
tags: [providers, vlm, azure, gpt-5.4, reading]
---

## Description

Implement the Azure OpenAI VLM provider using GPT-5.4 vision capabilities
for `vlm`, `read_chart`, and `read_table` tools. Uses Azure OpenAI Service
with config from env vars (AZURE_API_KEY, AZURE_CHAT_ENDPOINT,
AZURE_CHAT_DEPLOYMENT).

## Acceptance Criteria

- [ ] `src/providers/vlm_azure.py` with vlm, read_chart, read_table functions
- [ ] Each function accepts image + question, returns ToolResult with answer
- [ ] Uses Azure OpenAI client (not plain OpenAI client)
- [ ] Retry + exponential backoff on rate limits (429) [EH]
- [ ] Config-driven: selected when `ADE_VLM_PROVIDER=azure`
- [ ] Unit tests with mocked Azure client

## Constraints

- Azure config from env vars only [AKM]
- GPT-5.4 deployment name from AZURE_CHAT_DEPLOYMENT
- Retry with tenacity [EH]

## Dependencies

- BLK-003 (ToolRegistry)
- Azure OpenAI endpoint configured in .env

## Notes

- vision.md §9 (LLM decision: GPT-5.4 via Azure)
- .env.example has the Azure config template
- L8 notebook shows VLM usage patterns
