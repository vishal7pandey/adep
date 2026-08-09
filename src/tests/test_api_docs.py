"""Tests for API documentation, landing page, and observability endpoints [Wave 5].

Tests cover:
- OpenAPI JSON endpoint at /api/v1/openapi.json
- Landing page at GET /
- /health and /api/v1/health endpoints
- /ready readiness check endpoint
- GET /api/v1/budget endpoint
- X-Request-ID header in responses
- HTTPError model in error responses
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app, HTTPError


@pytest.fixture
def client(tmp_path):
    """Create a test client with isolated store."""
    import src.definitions.store as store_module
    import src.config as config_module
    old_store = store_module._store
    old_auth = config_module.settings.auth_enabled
    store_module._store = store_module.DefinitionStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    app = create_app()
    yield TestClient(app)

    config_module.settings.auth_enabled = old_auth
    store_module._store = old_store


class TestOpenAPISpec:
    """Verify OpenAPI JSON is generated correctly [Wave 5.2]."""

    def test_openapi_json_endpoint(self, client):
        resp = client.get("/api/v1/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert spec["info"]["title"] == "ADEP — Agentic Document Extraction Platform"
        assert "paths" in spec

    def test_openapi_has_definitions_paths(self, client):
        resp = client.get("/api/v1/openapi.json")
        spec = resp.json()
        assert "/api/v1/definitions" in spec["paths"]
        assert "/api/v1/definitions/{definition_id}" in spec["paths"]

    def test_openapi_has_runs_paths(self, client):
        resp = client.get("/api/v1/openapi.json")
        spec = resp.json()
        assert "/api/v1/runs" in spec["paths"]
        assert "/api/v1/runs/{run_id}" in spec["paths"]
        assert "/api/v1/runs/{run_id}/verify" in spec["paths"]

    def test_openapi_has_budget_path(self, client):
        resp = client.get("/api/v1/openapi.json")
        spec = resp.json()
        assert "/api/v1/budget" in spec["paths"]

    def test_openapi_has_error_schemas(self, client):
        resp = client.get("/api/v1/openapi.json")
        spec = resp.json()
        assert "HTTPError" in spec.get("components", {}).get("schemas", {})

    def test_openapi_has_tags(self, client):
        resp = client.get("/api/v1/openapi.json")
        spec = resp.json()
        # Tags are on individual path operations
        def_path = spec["paths"].get("/api/v1/definitions", {})
        get_def = def_path.get("get", {})
        assert "definitions" in get_def.get("tags", [])
        runs_path = spec["paths"].get("/api/v1/runs", {})
        get_runs = runs_path.get("get", {})
        assert "runs" in get_runs.get("tags", [])


class TestLandingPage:
    """Verify landing page [Wave 5.2]."""

    def test_landing_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "ADEP" in resp.text
        assert "/docs" in resp.text
        assert "/api/v1/openapi.json" in resp.text


class TestHealthEndpoints:
    """Verify health and readiness checks [Wave 5.4]."""

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_v1(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_ready(self, client):
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


class TestRequestID:
    """Verify X-Request-ID header support [Wave 5.4]."""

    def test_request_id_generated(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers

    def test_request_id_passthrough(self, client):
        resp = client.get("/health", headers={"X-Request-ID": "test-123"})
        assert resp.headers["x-request-id"] == "test-123"


class TestBudgetEndpoint:
    """Verify GET /budget endpoint [Wave 5.2]."""

    def test_budget_returns_all_levels(self, client):
        resp = client.get("/api/v1/budget")
        assert resp.status_code == 200
        data = resp.json()
        assert "run" in data
        assert "definition_daily" in data
        assert "global_daily" in data
        assert "warnings" in data


class TestHTTPErrorModel:
    """Verify HTTPError model [Wave 5.2]."""

    def test_http_error_model(self):
        err = HTTPError(detail="Not found")
        assert err.detail == "Not found"

    def test_http_error_dict_detail(self):
        err = HTTPError(detail={"message": "Budget exceeded", "level": "run"})
        assert isinstance(err.detail, dict)
        assert err.detail["level"] == "run"

    def test_404_returns_error_format(self, client):
        resp = client.get("/api/v1/definitions/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
