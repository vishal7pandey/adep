"""Tests for reviewer findings fixes — BLK-152, BLK-153, BLK-154, BLK-155.

Tests cover:
- BLK-152: SSRF protection — URL validation blocks private/loopback/metadata IPs
- BLK-153: Auth enabled by default, .env.example has ADE_AUTH_ENABLED
- BLK-154: CI pipeline uses uv (ci.yml content check)
- BLK-155: Atomic writes — temp file + os.replace, O_EXCL for create
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.agent.webhooks import (
    SSRFError,
    WebhookConfig,
    WebhookStore,
    _validate_webhook_url,
    _atomic_write,
)


# ---------------------------------------------------------------------------
# BLK-152: SSRF protection
# ---------------------------------------------------------------------------


class TestSSRFValidation:
    """Verify webhook URL validation blocks SSRF vectors [BLK-152]."""

    def test_blocks_loopback_ip(self):
        with pytest.raises(SSRFError, match="blocked range"):
            _validate_webhook_url("https://127.0.0.1/webhook")

    def test_blocks_localhost(self):
        with pytest.raises(SSRFError, match="blocked range"):
            _validate_webhook_url("https://localhost/webhook")

    def test_blocks_private_ip_10(self):
        with pytest.raises(SSRFError, match="blocked range"):
            _validate_webhook_url("https://10.0.0.1/webhook")

    def test_blocks_private_ip_172(self):
        with pytest.raises(SSRFError, match="blocked range"):
            _validate_webhook_url("https://172.16.0.1/webhook")

    def test_blocks_private_ip_192(self):
        with pytest.raises(SSRFError, match="blocked range"):
            _validate_webhook_url("https://192.168.1.1/webhook")

    def test_blocks_cloud_metadata(self):
        with pytest.raises(SSRFError, match="blocked range"):
            _validate_webhook_url("https://169.254.169.254/latest/meta-data/")

    def test_blocks_link_local(self):
        with pytest.raises(SSRFError, match="blocked range"):
            _validate_webhook_url("https://169.254.1.1/webhook")

    def test_blocks_http_scheme(self):
        with pytest.raises(SSRFError, match="scheme"):
            _validate_webhook_url("http://example.com/webhook")

    def test_blocks_ftp_scheme(self):
        with pytest.raises(SSRFError, match="scheme"):
            _validate_webhook_url("ftp://example.com/webhook")

    def test_blocks_no_hostname(self):
        with pytest.raises(SSRFError, match="no hostname"):
            _validate_webhook_url("https:///webhook")

    def test_valid_https_accepted(self):
        # Should not raise — example.com resolves to a public IP
        # Use resolve=False to avoid actual DNS lookup in tests
        _validate_webhook_url("https://example.com/webhook", resolve=False)

    def test_validation_at_create_time(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        config = WebhookConfig(id="bad", url="https://127.0.0.1/webhook")
        with pytest.raises(SSRFError):
            store.create("bad", config)

    def test_validation_at_update_time(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        with patch("src.agent.webhooks._validate_webhook_url"):
            store.create("h1", WebhookConfig(id="h1", url="https://example.com"))
        with pytest.raises(SSRFError):
            store.update("h1", {"url": "https://10.0.0.1/webhook"})

    def test_dispatch_blocked_returns_no_leak(self):
        """Verify dispatch doesn't leak status codes for blocked targets."""
        from src.agent.webhooks import dispatch_webhook

        config = WebhookConfig(id="bad", url="https://127.0.0.1/webhook")
        result = dispatch_webhook(config, "run.completed", {"run_id": "test"})
        assert not result["delivered"]
        assert result["error"] == "URL validation failed"
        assert result["status_code"] == 0


# ---------------------------------------------------------------------------
# BLK-153: Auth enabled by default
# ---------------------------------------------------------------------------


class TestAuthDefault:
    """Verify auth is enabled by default [BLK-153]."""

    def test_auth_enabled_default_is_true(self):
        from src.config import Settings

        s = Settings(_env_file=None)  # Check default, not .env override
        assert s.auth_enabled is True

    def test_env_example_has_auth_enabled(self):
        env_example = Path(".env.example")
        content = env_example.read_text()
        assert "ADE_AUTH_ENABLED=true" in content

    def test_env_example_documents_risk(self):
        env_example = Path(".env.example")
        content = env_example.read_text()
        assert "production" in content.lower() or "NOT recommended" in content


# ---------------------------------------------------------------------------
# BLK-154: CI pipeline uses uv
# ---------------------------------------------------------------------------


class TestCIPipeline:
    """Verify CI pipeline uses uv, not pip [BLK-154]."""

    def test_ci_uses_uv_sync(self):
        ci_path = Path(".github/workflows/ci.yml")
        content = ci_path.read_text()
        assert "uv sync" in content
        assert "pip install -r requirements" not in content

    def test_ci_uses_uv_run_for_tools(self):
        ci_path = Path(".github/workflows/ci.yml")
        content = ci_path.read_text()
        assert "uv run ruff" in content
        assert "uv run mypy" in content
        assert "uv run pytest" in content

    def test_ci_uses_uv_setup_action(self):
        ci_path = Path(".github/workflows/ci.yml")
        content = ci_path.read_text()
        assert "setup-uv" in content


# ---------------------------------------------------------------------------
# BLK-155: Atomic writes
# ---------------------------------------------------------------------------


class TestAtomicWrites:
    """Verify atomic write helpers [BLK-155]."""

    def test_atomic_write_creates_file(self, tmp_path: Path):
        path = tmp_path / "test.json"
        _atomic_write(path, '{"key": "value"}')
        assert path.exists()
        assert path.read_text() == '{"key": "value"}'

    def test_atomic_write_replaces_existing(self, tmp_path: Path):
        path = tmp_path / "test.json"
        path.write_text('{"old": true}')
        _atomic_write(path, '{"new": true}')
        assert path.read_text() == '{"new": true}'

    def test_atomic_write_no_tmp_files_left(self, tmp_path: Path):
        path = tmp_path / "test.json"
        _atomic_write(path, '{"key": "value"}')
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_definition_store_create_uses_atomic(self, tmp_path: Path):
        from src.definitions.store import DefinitionStore

        store = DefinitionStore(base_dir=tmp_path / ".adep")
        store.create("definitions", "test-def", {"id": "test-def", "name": "Test"})
        data = store.read("definitions", "test-def")
        assert data["name"] == "Test"
        # No tmp files left behind
        def_dir = tmp_path / ".adep" / "definitions"
        tmp_files = list(def_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_definition_store_update_uses_atomic(self, tmp_path: Path):
        from src.definitions.store import DefinitionStore

        store = DefinitionStore(base_dir=tmp_path / ".adep")
        store.create("definitions", "test-def", {"id": "test-def", "name": "Test"})
        store.update("definitions", "test-def", {"id": "test-def", "name": "Updated"})
        data = store.read("definitions", "test-def")
        assert data["name"] == "Updated"

    def test_definition_store_create_atomic_excl(self, tmp_path: Path):
        """Verify O_EXCL prevents TOCTOU race in create."""
        from src.definitions.store import DefinitionStore

        store = DefinitionStore(base_dir=tmp_path / ".adep")
        store.create("definitions", "dup", {"id": "dup"})
        with pytest.raises(FileExistsError):
            store.create("definitions", "dup", {"id": "dup"})

    def test_webhook_store_create_uses_atomic(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        with patch("src.agent.webhooks._validate_webhook_url"):
            config = WebhookConfig(id="wh1", url="https://example.com")
            store.create("wh1", config)
        # No tmp files left behind
        hooks_dir = tmp_path / ".adep" / "webhooks"
        tmp_files = list(hooks_dir.glob("*.tmp"))
        assert len(tmp_files) == 0
