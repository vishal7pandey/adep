"""Tests for Wave 7 — webhooks, i18n, analytics [BLK-064, BLK-065, BLK-066]."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.agent.webhooks import (
    WebhookConfig,
    WebhookEvent,
    WebhookStore,
    dispatch_webhook,
    emit_webhook_event,
    _sign_payload,
)
from src.agent.i18n import (
    SUPPORTED_LOCALES,
    DEFAULT_LOCALE,
    parse_accept_language,
    get_error_message,
    get_locales,
    detect_document_language,
)
from src.agent.analytics import (
    get_skill_analytics,
    get_template_analytics,
    get_document_analytics,
    get_failure_analytics,
)


@pytest.fixture
def client(tmp_path):
    """Create a test client with isolated stores."""
    import src.definitions.store as store_module
    import src.documents.store as doc_store_module
    import src.agent.webhooks as webhooks_module
    import src.config as config_module

    old_def_store = store_module._store
    old_doc_store = doc_store_module._store
    old_webhook_store = webhooks_module._store
    old_auth = config_module.settings.auth_enabled

    store_module._store = store_module.DefinitionStore(base_dir=tmp_path / ".adep")
    doc_store_module._store = doc_store_module.DocumentStore(base_dir=tmp_path / ".adep")
    webhooks_module._store = WebhookStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    from src.api.main import create_app

    app = create_app()
    with patch("src.agent.webhooks._validate_webhook_url"):
        yield TestClient(app)

    config_module.settings.auth_enabled = old_auth
    store_module._store = old_def_store
    doc_store_module._store = old_doc_store
    webhooks_module._store = old_webhook_store


# ---------------------------------------------------------------------------
# BLK-064: Webhooks
# ---------------------------------------------------------------------------


class TestWebhookConfig:
    """Verify WebhookConfig model [BLK-064]."""

    def test_construction(self):
        config = WebhookConfig(id="hook1", url="https://example.com/webhook")
        assert config.id == "hook1"
        assert config.url == "https://example.com/webhook"
        assert config.active is True
        assert WebhookEvent.RUN_COMPLETED in config.events

    def test_to_dict_masks_secret(self):
        config = WebhookConfig(id="hook1", url="https://example.com", secret="mysecret")
        d = config.to_dict()
        assert d["secret"] == "***"

    def test_to_dict_no_secret(self):
        config = WebhookConfig(id="hook1", url="https://example.com")
        d = config.to_dict()
        assert d["secret"] == ""

    def test_matches_event(self):
        config = WebhookConfig(
            id="hook1",
            url="https://example.com",
            events=[WebhookEvent.RUN_COMPLETED],
        )
        assert config.matches_event(WebhookEvent.RUN_COMPLETED)
        assert not config.matches_event(WebhookEvent.RUN_FAILED)

    def test_inactive_does_not_match(self):
        config = WebhookConfig(
            id="hook1",
            url="https://example.com",
            events=[WebhookEvent.RUN_COMPLETED],
            active=False,
        )
        assert not config.matches_event(WebhookEvent.RUN_COMPLETED)


class TestWebhookStore:
    """Verify WebhookStore CRUD [BLK-064]."""

    @pytest.fixture(autouse=True)
    def _mock_url_validation(self):
        """Mock SSRF validation for store tests (uses non-resolvable hostnames)."""
        with patch("src.agent.webhooks._validate_webhook_url"):
            yield

    def test_create_and_get(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        config = WebhookConfig(id="hook1", url="https://example.com", secret="s3cr3t")
        store.create("hook1", config)

        data = store.get("hook1")
        assert data["id"] == "hook1"
        assert data["url"] == "https://example.com"
        assert data["secret"] == "***"  # masked in get()

    def test_list(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        store.create("h1", WebhookConfig(id="h1", url="https://a.com"))
        store.create("h2", WebhookConfig(id="h2", url="https://b.com"))
        hooks = store.list()
        assert len(hooks) == 2

    def test_update(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        store.create("h1", WebhookConfig(id="h1", url="https://a.com"))
        updated = store.update("h1", {"url": "https://c.com", "active": False})
        assert updated["url"] == "https://c.com"
        assert updated["active"] is False

    def test_delete(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        store.create("h1", WebhookConfig(id="h1", url="https://a.com"))
        store.delete("h1")
        with pytest.raises(FileNotFoundError):
            store.get("h1")

    def test_get_all_for_event(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        store.create(
            "h1",
            WebhookConfig(
                id="h1",
                url="https://a.com",
                events=[WebhookEvent.RUN_COMPLETED],
            ),
        )
        store.create(
            "h2",
            WebhookConfig(
                id="h2",
                url="https://b.com",
                events=[WebhookEvent.BUDGET_WARNING],
            ),
        )
        configs = store.get_all_for_event(WebhookEvent.RUN_COMPLETED)
        assert len(configs) == 1
        assert configs[0].id == "h1"


class TestWebhookSignature:
    """Verify HMAC signature [BLK-064]."""

    def test_sign_payload(self):
        payload = b'{"event": "run.completed"}'
        sig = _sign_payload(payload, "mysecret")
        assert len(sig) == 64  # SHA256 hex

    def test_different_secrets_different_sigs(self):
        payload = b'{"event": "run.completed"}'
        sig1 = _sign_payload(payload, "secret1")
        sig2 = _sign_payload(payload, "secret2")
        assert sig1 != sig2


class TestWebhookAPI:
    """Verify webhook API endpoints [BLK-064]."""

    def test_create_webhook(self, client):
        resp = client.post(
            "/api/v1/webhooks",
            json={
                "id": "hook1",
                "url": "https://example.com/webhook",
                "events": ["run.completed"],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == "hook1"

    def test_list_webhooks(self, client):
        client.post(
            "/api/v1/webhooks",
            json={
                "id": "h1",
                "url": "https://a.com",
            },
        )
        resp = client.get("/api/v1/webhooks")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_webhook(self, client):
        client.post(
            "/api/v1/webhooks",
            json={
                "id": "h1",
                "url": "https://a.com",
            },
        )
        resp = client.get("/api/v1/webhooks/h1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "h1"

    def test_delete_webhook(self, client):
        client.post(
            "/api/v1/webhooks",
            json={
                "id": "h1",
                "url": "https://a.com",
            },
        )
        resp = client.delete("/api/v1/webhooks/h1")
        assert resp.status_code == 204

    def test_invalid_event(self, client):
        resp = client.post(
            "/api/v1/webhooks",
            json={
                "id": "h1",
                "url": "https://a.com",
                "events": ["invalid.event"],
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# BLK-065: i18n
# ---------------------------------------------------------------------------


class TestAcceptLanguage:
    """Verify Accept-Language parsing [BLK-065]."""

    def test_exact_match(self):
        assert parse_accept_language("es") == "es"

    def test_prefix_match(self):
        assert parse_accept_language("es-ES") == "es"

    def test_with_quality(self):
        assert parse_accept_language("es-ES,es;q=0.9,en;q=0.8") == "es"

    def test_default_fallback(self):
        assert parse_accept_language("ja") == DEFAULT_LOCALE

    def test_none_header(self):
        assert parse_accept_language(None) == DEFAULT_LOCALE

    def test_empty_header(self):
        assert parse_accept_language("") == DEFAULT_LOCALE


class TestErrorMessages:
    """Verify localized error messages [BLK-065]."""

    def test_english(self):
        msg = get_error_message("not_found", "en")
        assert "not found" in msg.lower()

    def test_spanish(self):
        msg = get_error_message("not_found", "es")
        assert "no encontrado" in msg.lower()

    def test_french(self):
        msg = get_error_message("not_found", "fr")
        assert "introuvable" in msg.lower()

    def test_fallback_to_english(self):
        msg = get_error_message("not_found", "xx")
        assert "not found" in msg.lower()

    def test_unknown_key(self):
        msg = get_error_message("nonexistent_key", "en")
        assert msg == "nonexistent_key"


class TestLocales:
    """Verify locales endpoint [BLK-065]."""

    def test_get_locales(self):
        locales = get_locales()
        assert len(locales) == len(SUPPORTED_LOCALES)
        codes = [l["code"] for l in locales]
        assert "en" in codes
        assert "es" in codes
        assert "zh" in codes

    def test_locales_api(self, client):
        resp = client.get("/api/v1/locales")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 6
        assert any(l["code"] == "en" for l in data)


class TestDocumentLanguageDetection:
    """Verify document language detection [BLK-065]."""

    def test_english(self):
        assert detect_document_language("Hello World this is English text") == "en"

    def test_chinese(self):
        assert detect_document_language("这是一段中文文本用于测试语言检测功能") == "zh"

    def test_empty(self):
        assert detect_document_language("") == "en"


# ---------------------------------------------------------------------------
# BLK-066: Analytics
# ---------------------------------------------------------------------------


class TestAnalytics:
    """Verify analytics aggregation [BLK-066]."""

    def test_skill_analytics_empty(self, tmp_path: Path):
        result = get_skill_analytics(base_dir=tmp_path / ".adep")
        assert result == []

    def test_skill_analytics_with_runs(self, tmp_path: Path):
        runs_dir = tmp_path / ".adep" / "runs"
        runs_dir.mkdir(parents=True)

        for i in range(3):
            run_data = {
                "id": f"run-{i}",
                "definition_id": "def-1",
                "status": "completed" if i < 2 else "failed",
                "fields": [
                    {"name": "vendor", "value": "ACME", "confidence": 0.9, "status": "extracted"},
                    {
                        "name": "total",
                        "value": 100,
                        "confidence": 0.8,
                        "status": "extracted" if i < 2 else "missing",
                    },
                ],
                "extracted_fields_count": 2 if i < 2 else 1,
                "total_fields": 2,
                "token_usage_summary": {"total_tokens": 5000, "total_cost_usd": 0.025},
            }
            (runs_dir / f"run-{i}.json").write_text(json.dumps(run_data))

        result = get_skill_analytics(base_dir=tmp_path / ".adep")
        assert len(result) == 1
        assert result[0]["skill_id"] == "def-1"
        assert result[0]["total_runs"] == 3
        assert result[0]["success_rate"] == 66.7

    def test_document_analytics(self, tmp_path: Path):
        runs_dir = tmp_path / ".adep" / "runs"
        runs_dir.mkdir(parents=True)

        for i in range(2):
            run_data = {
                "id": f"run-{i}",
                "definition_id": "def-1",
                "status": "completed",
                "fields": [],
                "token_usage_summary": {"total_tokens": 1000, "total_cost_usd": 0.005},
            }
            (runs_dir / f"run-{i}.json").write_text(json.dumps(run_data))

        result = get_document_analytics(base_dir=tmp_path / ".adep")
        assert result["total_runs"] == 2
        assert result["completed"] == 2
        assert result["total_tokens"] == 2000

    def test_failure_analytics(self, tmp_path: Path):
        runs_dir = tmp_path / ".adep" / "runs"
        runs_dir.mkdir(parents=True)

        run_data = {
            "id": "run-1",
            "definition_id": "def-1",
            "status": "failed",
            "fields": [
                {"name": "vendor", "status": "missing"},
                {"name": "total", "status": "missing"},
            ],
        }
        (runs_dir / "run-1.json").write_text(json.dumps(run_data))

        result = get_failure_analytics(base_dir=tmp_path / ".adep")
        assert result["total_failed_or_partial"] == 1
        assert len(result["top_failing_fields"]) == 2

    def test_analytics_api_endpoints(self, client):
        resp = client.get("/api/v1/admin/analytics/skills")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        resp = client.get("/api/v1/admin/analytics/documents")
        assert resp.status_code == 200
        assert "total_runs" in resp.json()

        resp = client.get("/api/v1/admin/analytics/failures")
        assert resp.status_code == 200
        assert "top_failing_fields" in resp.json()
