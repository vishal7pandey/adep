"""OpenAI provider support (ADE-41): one switch covers both engines. No network, no real key.

Every Settings here is built with _env_file=None and explicit values, so a developer's real .env
(which may hold a real key) can never change what these tests assert.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.config import Settings


def make(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("OPENAI_API_KEY", "OPENAI_CHAT_MODEL", "ADE_LLM_PROVIDER", "AZURE_API_KEY"):
        monkeypatch.delenv(name, raising=False)


class TestProviderResolution:
    def test_auto_prefers_openai_when_a_key_is_set(self):
        assert make(OPENAI_API_KEY="sk-test").active_llm_provider == "openai"

    def test_auto_falls_back_to_azure_without_an_openai_key(self):
        assert (
            make(azure_api_key="k", azure_chat_endpoint="https://x").active_llm_provider == "azure"
        )
        assert make().active_llm_provider == "azure"  # legacy default, unchanged

    def test_explicit_choice_wins_over_auto(self):
        assert make(llm_provider="azure", OPENAI_API_KEY="sk-test").active_llm_provider == "azure"
        assert make(llm_provider="openai").active_llm_provider == "openai"

    def test_provider_name_is_case_and_space_insensitive(self):
        assert make(llm_provider="  OpenAI ").active_llm_provider == "openai"

    def test_unknown_provider_is_rejected_with_a_clear_message(self):
        with pytest.raises(ValueError, match="llm_provider"):
            make(llm_provider="bedrock").validate_provider_config()

    def test_chat_model_follows_the_provider(self):
        s = make(OPENAI_API_KEY="sk-test", OPENAI_CHAT_MODEL="gpt-x", azure_chat_deployment="dep-y")
        assert s.chat_model == "gpt-x"
        assert make(llm_provider="azure", azure_chat_deployment="dep-y").chat_model == "dep-y"


class TestConfiguredAndValidation:
    def test_openai_key_means_configured(self):
        assert make(OPENAI_API_KEY="sk-test").is_llm_configured() is True

    def test_explicit_openai_without_a_key_is_not_configured(self):
        assert make(llm_provider="openai").is_llm_configured() is False

    def test_azure_semantics_are_unchanged(self):
        assert make(azure_api_key="k", azure_chat_endpoint="https://x").is_llm_configured() is True
        assert make(azure_api_key="k").is_llm_configured() is False

    def test_openai_provider_ignores_leftover_partial_azure_settings(self):
        make(
            OPENAI_API_KEY="sk-test", azure_api_key="stale", azure_chat_endpoint=""
        ).validate_provider_config()

    def test_azure_partial_config_still_fails_fast(self):
        with pytest.raises(ValueError, match="Partial Azure OpenAI configuration"):
            make(llm_provider="azure", azure_api_key="k").validate_provider_config()


class _Recorder:
    """Stands in for openai.OpenAI / AzureOpenAI: records how it was built and what it was asked."""

    built: list[tuple[str, dict]] = []

    def __init__(self, kind: str):
        self.kind = kind

    def factory(self):
        def build(**kwargs):
            _Recorder.built.append((self.kind, kwargs))
            return FakeClient()

        return build


class FakeClient:
    def __init__(self):
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        msg = SimpleNamespace(content="ok")
        usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)


@pytest.fixture
def providers(monkeypatch):
    """Patch the provider modules to use a chosen Settings and fake openai classes."""
    import openai

    from src.providers import llm, vlm_azure

    _Recorder.built = []
    monkeypatch.setattr(openai, "OpenAI", _Recorder("openai").factory())
    monkeypatch.setattr(openai, "AzureOpenAI", _Recorder("azure").factory())

    def use(settings: Settings):
        monkeypatch.setattr(vlm_azure, "settings", settings)
        monkeypatch.setattr(llm, "settings", settings)
        monkeypatch.setattr(vlm_azure, "_client", None)
        return vlm_azure, llm

    return use


class TestClientFactory:
    def test_openai_provider_builds_a_plain_openai_client(self, providers):
        vlm_azure, _ = providers(make(OPENAI_API_KEY="sk-test"))
        vlm_azure._get_client()
        kind, kwargs = _Recorder.built[0]
        assert kind == "openai" and kwargs == {"api_key": "sk-test"}

    def test_azure_provider_still_builds_an_azure_client(self, providers):
        vlm_azure, _ = providers(
            make(llm_provider="azure", azure_api_key="k", azure_chat_endpoint="https://x")
        )
        vlm_azure._get_client()
        kind, kwargs = _Recorder.built[0]
        assert kind == "azure" and kwargs["azure_endpoint"] == "https://x"

    def test_vlm_uses_max_completion_tokens_and_the_openai_model(self, providers, tmp_path):
        vlm_azure, _ = providers(make(OPENAI_API_KEY="sk-test", OPENAI_CHAT_MODEL="gpt-x"))
        img = tmp_path / "a.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")
        vlm_azure._call_vlm(str(img), "what is this?")
        call = vlm_azure._client.calls[0]
        assert call["model"] == "gpt-x"
        assert "max_completion_tokens" in call and "max_tokens" not in call

    def test_vlm_keeps_max_tokens_on_azure(self, providers, tmp_path):
        vlm_azure, _ = providers(
            make(
                llm_provider="azure",
                azure_api_key="k",
                azure_chat_endpoint="https://x",
                azure_chat_deployment="dep",
            )
        )
        img = tmp_path / "a.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")
        vlm_azure._call_vlm(str(img), "q")
        call = vlm_azure._client.calls[0]
        assert (
            call["model"] == "dep" and "max_tokens" in call and "max_completion_tokens" not in call
        )

    def test_old_engine_text_llm_follows_the_same_switch(self, providers):
        vlm_azure, llm = providers(make(OPENAI_API_KEY="sk-test", OPENAI_CHAT_MODEL="gpt-x"))
        llm._call_llm("sys", "user", max_tokens=50)
        call = vlm_azure._client.calls[0]
        assert call["model"] == "gpt-x"
        assert call["max_completion_tokens"] == 50 and "max_tokens" not in call


class TestEngineModel:
    def test_new_engine_builds_an_openai_model_without_network(self, monkeypatch):
        from src.engine import agent as engine_agent

        monkeypatch.setattr(
            engine_agent, "settings", make(OPENAI_API_KEY="sk-test", OPENAI_CHAT_MODEL="gpt-x")
        )
        model = engine_agent._build_model()
        assert model.model_name == "gpt-x"
        assert type(model.client).__name__ == "AsyncOpenAI"

    def test_new_engine_still_builds_an_azure_model(self, monkeypatch):
        from src.engine import agent as engine_agent

        monkeypatch.setattr(
            engine_agent,
            "settings",
            make(
                llm_provider="azure",
                azure_api_key="k",
                azure_chat_endpoint="https://x.openai.azure.com",
                azure_chat_deployment="dep",
            ),
        )
        model = engine_agent._build_model()
        assert model.model_name == "dep"
        assert type(model.client).__name__ == "AsyncAzureOpenAI"

    def test_planner_client_exists_when_openai_is_configured(self, monkeypatch):
        from src.api import run_engine

        monkeypatch.setattr(run_engine, "settings", make(OPENAI_API_KEY="sk-test"))
        assert run_engine._build_planner_client() is not None
        monkeypatch.setattr(run_engine, "settings", make())
        assert run_engine._build_planner_client() is None


class TestSmoke:
    def test_report_never_contains_the_key_and_records_error_types_only(self):
        from src.providers import smoke

        secret = "sk-SECRET-VALUE-123"

        class Boom(Exception):
            pass

        class BadClient(FakeClient):
            def __init__(self):
                super().__init__()
                self.models = SimpleNamespace(list=self._list)

            def _list(self):
                raise Boom(f"leaked {secret}")

            def _create(self, **kwargs):
                raise Boom(f"also {secret}")

        report = smoke.check(make(OPENAI_API_KEY=secret), BadClient())
        text = json.dumps(report)
        assert secret not in text
        assert report["provider"] == "openai" and report["key_set"] is True
        assert report["chat"]["ok"] is False and report["chat"]["error_type"] == "Boom"
        assert report["models"]["ok"] is False

    def test_report_marks_success_and_lists_only_chat_model_names(self):
        from src.providers import smoke

        class GoodClient(FakeClient):
            def __init__(self):
                super().__init__()
                ids = ["gpt-x", "gpt-x-mini", "text-embedding-3-large", "whisper-1", "o9"]
                self.models = SimpleNamespace(
                    list=lambda: SimpleNamespace(data=[SimpleNamespace(id=i) for i in ids])
                )

        report = smoke.check(make(OPENAI_API_KEY="sk-test"), GoodClient())
        assert report["chat"]["ok"] is True and report["vision"]["ok"] is True
        assert set(report["models"]["chat_models"]) == {"gpt-x", "gpt-x-mini", "o9"}

    def test_unconfigured_provider_says_so_without_calling_anything(self):
        from src.providers import smoke

        report = smoke.check(make(llm_provider="openai"), None)
        assert report["key_set"] is False and report["chat"]["ok"] is False
        assert report["chat"]["error_type"] == "NotConfigured"
