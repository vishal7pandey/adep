# ADE-41 — The configured Azure endpoint does not resolve: support the owner's OpenAI key for both engines

Status: approved · Risk: medium · Jira: ADE-41
Created: 2026-10-05 · Slug: openai-provider

## Problem

No real model call can run. The Azure OpenAI endpoint in the local configuration no longer resolves in DNS, so every real call fails with a connection error. As a result the new engine has only ever run against a scripted fake model, and ADE-31 (old engine against new engine) cannot produce any measurement. The owner decided on 2026-10-05 to use their personal OpenAI API key instead of Azure.

## Users and context

The maintainer and agents running either engine. Two code paths build model clients: `src/providers/vlm_azure.py` (the shared client used by the old engine's LLM calls and by the new engine's perception tools) and `src/engine/agent.py` (the new engine's chat model). Settings live in `src/config.py`. The key lives in a gitignored `.env`, which must never be read, printed or committed by an agent.

## Goals and non-goals

**Goals:** one provider switch that makes both engines work with an OpenAI key; Azure keeps working for anyone who has it; a repeatable, secret-free check that a real call works.
**Non-goals:** changing prompts or extraction logic, other providers (Gemini, Groq), embeddings, cost tracking changes.

## Requirements

- R1. A setting `llm_provider` (`ADE_LLM_PROVIDER`): `auto` (default), `openai`, `azure`. `auto` picks OpenAI when `OPENAI_API_KEY` is set and otherwise Azure, so existing Azure-only setups behave exactly as before. An unknown value is a clear error.
- R2. Settings `OPENAI_API_KEY` and `OPENAI_CHAT_MODEL` (default `gpt-5.4`, the model the project was designed around). A `chat_model` property returns the model or deployment for the active provider.
- R3. `src/providers/vlm_azure._get_client()` builds `openai.OpenAI(api_key=...)` for OpenAI and `AzureOpenAI` as before for Azure. The output-token limit is sent as `max_completion_tokens` for OpenAI (current models reject `max_tokens`) and as `max_tokens` for Azure.
- R4. The old engine's text LLM (`src/providers/llm.py`) and planner-client check follow the same switch.
- R5. The new engine's model builder returns an OpenAI model or an Azure model per the provider, built lazily, with no network at construction.
- R6. Provider validation: with OpenAI active, leftover partial Azure settings are ignored; with Azure active, the existing partial-config check is unchanged.
- R7. `python -m src.providers.smoke` makes one tiny chat call and one tiny vision call and prints a JSON report of booleans, counts, model names and error types only, never a key, endpoint, prompt or exception message.
- R8. `.env.example` lists the new variable names; AGENTS.md documents the switch, the smoke command and the rule that `.env` is never opened or printed.

## Acceptance criteria

- AC1. Provider resolution: `auto` with an OpenAI key gives OpenAI, `auto` without one gives Azure, an explicit value wins, names are case and space insensitive, an unknown value raises an error mentioning `llm_provider`.
- AC2. `is_llm_configured` and `validate_provider_config` behave as specified in R6 and keep the Azure semantics unchanged.
- AC3. The shared client factory builds the right client class for each provider, and the old VLM and LLM call paths send the right token-limit parameter and model name.
- AC4. The new engine builds an OpenAI-backed or Azure-backed model without network access.
- AC5. The smoke report never contains the key, records only error types, lists only chat model names, and says `NotConfigured` without calling anything when the provider has no credentials.
- AC6. A real smoke run against the owner's key succeeds for chat and vision (manual check recorded in the PR; the key is injected into the process environment and never displayed).
- AC7. The existing suite is not made worse; the old validation tests are pinned to the Azure path so a developer's real key cannot change them.

## Edge cases and failure modes

A key set but an explicit `azure` provider: Azure is used. `openai` forced without a key: not configured, a clear message, no crash at import. A model that rejects a parameter surfaces the provider's own error type in the smoke report.

## Non-functional requirements

No new dependency (the `openai` and `pydantic-ai` packages already provide both clients). No secret in any file, log line, test output or report.

## Assumptions

- A1. `gpt-5.4` accepts image input and `max_completion_tokens`; verified by the manual smoke run on 2026-10-05, also for `gpt-5.4-mini`.
- A2. The shared Azure-named module and function names stay (`vlm_azure`, `_get_client`) to keep the change small; renaming is not worth the churn.

## Risks and dependencies

Every real call spends the owner's money; the smoke check is a few hundred tokens. The shared module name is now slightly misleading and noted in its docstring. Blocks ADE-31.

## Open questions

None.
