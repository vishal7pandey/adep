"""Tests for provider-config validation [BLK-173].

Verifies that partial or empty Azure OpenAI credentials are detected
and fail fast with a clear error message, preventing silent zero-output runs.
"""

import pytest

from src.config import Settings


class TestProviderConfigValidation:
    """Tests for Settings.validate_provider_config() [BLK-173]."""

    def test_partial_config_api_key_only_raises(self):
        """API key set but endpoint missing should raise ValueError."""
        settings = Settings(azure_api_key="test-key", azure_chat_endpoint="")
        with pytest.raises(ValueError, match="Partial Azure OpenAI configuration"):
            settings.validate_provider_config()

    def test_partial_config_endpoint_only_raises(self):
        """Endpoint set but API key missing should raise ValueError."""
        settings = Settings(azure_api_key="", azure_chat_endpoint="https://example.openai.azure.com")
        with pytest.raises(ValueError, match="Partial Azure OpenAI configuration"):
            settings.validate_provider_config()

    def test_partial_config_whitespace_only_treated_as_empty(self):
        """Whitespace-only values should be treated as empty (partial config)."""
        settings = Settings(azure_api_key="   ", azure_chat_endpoint="https://example.openai.azure.com")
        with pytest.raises(ValueError, match="Partial Azure OpenAI configuration"):
            settings.validate_provider_config()

    def test_empty_config_does_not_raise(self):
        """Both fields empty should not raise — PDF fallback is valid."""
        settings = Settings(azure_api_key="", azure_chat_endpoint="")
        # Should not raise
        settings.validate_provider_config()

    def test_full_config_does_not_raise(self):
        """Both fields set should not raise."""
        settings = Settings(
            azure_api_key="test-key",
            azure_chat_endpoint="https://example.openai.azure.com",
        )
        # Should not raise
        settings.validate_provider_config()

    def test_is_llm_configured_returns_true_when_both_set(self):
        settings = Settings(
            azure_api_key="test-key",
            azure_chat_endpoint="https://example.openai.azure.com",
        )
        assert settings.is_llm_configured() is True

    def test_is_llm_configured_returns_false_when_both_empty(self):
        settings = Settings(azure_api_key="", azure_chat_endpoint="")
        assert settings.is_llm_configured() is False

    def test_is_llm_configured_returns_false_when_partial(self):
        settings = Settings(azure_api_key="key", azure_chat_endpoint="")
        assert settings.is_llm_configured() is False

    def test_error_message_lists_set_and_unset_fields(self):
        """Error message should clearly indicate which fields are set and missing."""
        settings = Settings(azure_api_key="my-key", azure_chat_endpoint="")
        with pytest.raises(ValueError) as exc_info:
            settings.validate_provider_config()
        msg = str(exc_info.value)
        assert "AZURE_API_KEY" in msg
        assert "AZURE_CHAT_ENDPOINT" in msg
        assert "Missing" in msg
