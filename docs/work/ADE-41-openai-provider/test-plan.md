# ADE-41 — Test plan: OpenAI provider

Status: approved · Risk: medium · Jira: ADE-41

Test framework and conventions found: pytest in `src/tests/`; new tests build `Settings(_env_file=None, ...)` and clear provider env vars, so a real `.env` cannot affect them. Run with `.venv/Scripts/python.exe -m pytest src/tests/test_openai_provider.py -q`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_openai_provider.py::TestProviderResolution | auto with a key gives openai; explicit wins | case and spaces ignored; auto without a key gives azure | unknown name raises a clear error | verified |
| AC2 | unit | src/tests/test_openai_provider.py::TestConfiguredAndValidation | key means configured | explicit openai without key is not configured | partial Azure still fails fast; leftover partial Azure ignored under openai | verified |
| AC3 | unit | src/tests/test_openai_provider.py::TestClientFactory | OpenAI client for openai, Azure for azure; right model and token parameter in VLM and old LLM | azure keeps `max_tokens` | n/a: provider is one of two values | verified |
| AC4 | unit | src/tests/test_openai_provider.py::TestEngineModel | engine builds an OpenAI model and an Azure model with no network | planner client present when configured | planner client absent when nothing is configured | verified |
| AC5 | unit | src/tests/test_openai_provider.py::TestSmoke | success report marks chat and vision ok and lists only chat model names | NotConfigured without any call | secret in exception messages never appears; only error types recorded | verified |
| AC6 | manual | n/a (manual check below) | real chat and vision calls succeed | gpt-5.4 and gpt-5.4-mini both work | n/a: a failing call is itself the observation | verified |
| AC7 | integration | whole suite and CI | new tests pass; old validation tests pinned | n/a: the suite either passes or not | existing suites unchanged | verified |

## Regression risk

`validate_provider_config()` runs at import for the module singleton: the new early return for OpenAI must not break import when only Azure settings exist (covered by the unchanged Azure tests). The old VLM and LLM paths changed their token parameter only under the OpenAI provider.

## Untestable AC

None. AC6 needs the real key and is a recorded manual check.

## Manual checks

2026-10-05, `python -m src.providers.smoke` with the owner's OpenAI key loaded into the process environment only: chat ok (15 tokens), vision ok and the red test image was identified (274 tokens on gpt-4o); `gpt-5.4` and `gpt-5.4-mini` also pass chat and vision. 139 models visible to the key. Nothing printed a key.

## Audit (after implementation)

Six mutations were applied one at a time, each caught by the named test; files were restored and the suite re-run green (31 passed):

| Mutation | Caught by |
|---|---|
| auto ignores the OpenAI key | `TestProviderResolution::test_auto_prefers_openai_when_a_key_is_set` |
| token limit always `max_tokens` | `TestClientFactory::test_vlm_uses_max_completion_tokens_and_the_openai_model` |
| `chat_model` always the Azure deployment | `TestProviderResolution::test_chat_model_follows_the_provider` |
| OpenAI still validates leftover Azure settings | `TestConfiguredAndValidation::test_openai_provider_ignores_leftover_partial_azure_settings` |
| smoke leaks the exception message | `TestSmoke::test_report_never_contains_the_key_and_records_error_types_only` |
| engine always builds Azure | `TestEngineModel::test_new_engine_builds_an_openai_model_without_network` |
