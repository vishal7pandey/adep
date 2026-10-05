# ADE-41 — Plan: OpenAI provider for both engines

Status: approved · Risk: medium · Jira: ADE-41
Created: 2026-10-05 · Slug: openai-provider · Spec: spec.md

## Summary

Add a provider switch to `Settings`, apply it at the two places clients and models are built, add a secret-free smoke check, and document it. Size: S.

## Current state

- `src/config.py`: Azure-only fields (`azure_api_key`, `azure_chat_endpoint`, `azure_chat_deployment`), `validate_provider_config()` (partial Azure check, run at import) and `is_llm_configured()`.
- `src/providers/vlm_azure.py`: `_get_client()` builds `AzureOpenAI`; `_call_vlm()` sends `max_tokens=1000`; `llm.py` reuses that client for text calls.
- `src/engine/agent.py`: `_build_azure_model()` builds a pydantic-ai `OpenAIChatModel` with `AzureProvider`.
- `src/api/run_engine.py`: `_build_planner_client()` checks the two Azure fields directly.
- Tests: `src/tests/test_provider_config_validation.py` builds `Settings()` straight from the environment.
- Commands: `.venv/Scripts/python.exe -m pytest src/tests -q -m "not integration"`; formatting with the pinned ruff 0.16.2.

## Approach

`active_llm_provider` and `chat_model` on `Settings` are the single source of truth; everything else asks them. `vlm_azure.token_limit_kwargs()` picks the token-limit parameter name. The engine builds `OpenAIProvider` or `AzureProvider` lazily. The smoke module takes a client and settings, so it is testable with fakes. **Alternatives rejected:** a full provider abstraction layer (more than two providers are not needed); renaming `vlm_azure` (churn for no behaviour); reading the key from another project's file inside the code (a secret must come from the environment only).

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Settings fields, `active_llm_provider`, `chat_model`, `is_llm_configured`, `validate_provider_config` | `src/config.py` | AC1, AC2 | `src/tests/test_openai_provider.py` |
| T2 | Client factory and token-limit parameter; old LLM follows | `src/providers/vlm_azure.py`, `src/providers/llm.py` | AC3 | same |
| T3 | Engine model builder, planner client check | `src/engine/agent.py`, `src/api/run_engine.py` | AC4 | same |
| T4 | Smoke module | `src/providers/smoke.py` | AC5 | same |
| T5 | Pin old validation tests to Azure; docs | `src/tests/test_provider_config_validation.py`, `.env.example`, `AGENTS.md` | AC7 | full suite |
| T6 | Real smoke run with the owner's key injected into the process environment | none | AC6 | recorded in the PR |

## Data, API and migration impact

New optional environment variables; defaults keep Azure-only setups unchanged. No schema change.

## Security and failure modes

The key is read only from the environment, never logged; the engine logs the model name only (no endpoint, no key). The smoke report carries error types, not messages. A secret-scan of the diff is part of the PR.

## Rollout and rollback

Merge. Rollback: revert the commit; Azure behaviour was never removed.

## Risks and open points

Spend: only the smoke run (a few hundred tokens). The shared module's Azure name is cosmetic.
