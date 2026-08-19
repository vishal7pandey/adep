"""Tests for session management API endpoints [BLK-077].

Tests cover:
- GET /runs?limit=N (sorted by recency)
- GET /runs/{id} (returns extracted_fields_count, total_fields, status, fields)
- DELETE /runs/{id}
- PATCH /runs/{id} (rename)
- POST /runs/{id}/duplicate
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    """Create a test client with isolated store."""
    import src.definitions.store as store_module
    import src.config as config_module
    old_store = store_module._store
    old_auth = config_module.settings.auth_enabled
    store_module._store = store_module.DefinitionStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    from src.api.main import create_app
    app = create_app()
    yield TestClient(app)

    config_module.settings.auth_enabled = old_auth
    store_module._store = old_store


def _create_run(store, run_id: str, data: dict | None = None) -> dict:
    """Helper to create a run in the store."""
    run_data = {
        "id": run_id,
        "definition_id": "def-1",
        "document_path": "/tmp/doc.pdf",
        "status": "completed",
        "current_cycle": 6,
        "total_fields": 6,
        "extracted_fields_count": 5,
        "fields": [
            {"name": "vendor", "value": "ACME", "confidence": 0.95, "status": "extracted"},
            {"name": "total", "value": 1500, "confidence": 0.88, "status": "extracted"},
            {"name": "date", "value": "2026-01-01", "confidence": 0.90, "status": "extracted"},
        ],
        "name": "Test Run",
        "created_at": "2026-08-08T01:00:00+05:30",
    }
    if data:
        run_data.update(data)
    store.create("runs", run_id, run_data)
    return run_data


class TestListRuns:
    """Verify GET /runs?limit=N [BLK-077]."""

    def test_list_with_limit(self, client):
        from src.definitions.store import get_store
        store = get_store()
        for i in range(5):
            _create_run(store, f"run-{i:03d}", {"created_at": f"2026-08-08T0{i}:00:00+05:30"})

        resp = client.get("/api/v1/runs?limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3

    def test_list_default_limit(self, client):
        from src.definitions.store import get_store
        store = get_store()
        _create_run(store, "run-001")

        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_search_matches_document_url(self, client):
        """Regression [BLK-185, SCRUM-18]: search must match the canonical
        ``document_url`` field actually persisted by run_executor/run_engine,
        not the stale ``document_path`` key.
        """
        from src.definitions.store import get_store
        store = get_store()
        _create_run(store, "run-aaa", {"document_url": "/tmp/invoice_2026.pdf", "document_path": None})
        _create_run(store, "run-bbb", {"document_url": "/tmp/receipt_2026.pdf", "document_path": None})

        resp = client.get("/api/v1/runs?q=invoice")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == "run-aaa"

    def test_search_falls_back_to_legacy_document_path(self, client):
        """Legacy runs persisted with the old ``document_path`` key must still
        be searchable [BLK-185, SCRUM-18]."""
        from src.definitions.store import get_store
        store = get_store()
        _create_run(store, "run-legacy", {"document_path": "/tmp/legacy_report.pdf"})

        resp = client.get("/api/v1/runs?q=legacy_report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == "run-legacy"


class TestGetRun:
    """Verify GET /runs/{id} returns correct field counts [BLK-077]."""

    def test_get_run_returns_field_counts(self, client):
        from src.definitions.store import get_store
        store = get_store()
        _create_run(store, "run-001")

        resp = client.get("/api/v1/runs/run-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["extracted_fields_count"] == 5
        assert data["total_fields"] == 6
        assert data["status"] == "completed"
        assert len(data["fields"]) == 3

    def test_get_run_not_found(self, client):
        resp = client.get("/api/v1/runs/nonexistent")
        assert resp.status_code == 404


class TestDeleteRun:
    """Verify DELETE /runs/{id} [BLK-077]."""

    def test_delete_run(self, client):
        from src.definitions.store import get_store
        store = get_store()
        _create_run(store, "run-001")

        resp = client.delete("/api/v1/runs/run-001")
        assert resp.status_code == 200
        assert resp.json() == {"deleted": True}

        # Verify it's gone
        resp2 = client.get("/api/v1/runs/run-001")
        assert resp2.status_code == 404

    def test_delete_run_not_found(self, client):
        resp = client.delete("/api/v1/runs/nonexistent")
        assert resp.status_code == 404


class TestPatchRun:
    """Verify PATCH /runs/{id} (rename) [BLK-077]."""

    def test_patch_rename(self, client):
        from src.definitions.store import get_store
        store = get_store()
        _create_run(store, "run-001")

        resp = client.patch("/api/v1/runs/run-001", json={"name": "My Invoice Extraction"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "My Invoice Extraction"

        # Verify persistence
        resp2 = client.get("/api/v1/runs/run-001")
        assert resp2.json()["name"] == "My Invoice Extraction"

    def test_patch_not_found(self, client):
        resp = client.patch("/api/v1/runs/nonexistent", json={"name": "test"})
        assert resp.status_code == 404


class TestDuplicateRun:
    """Verify POST /runs/{id}/duplicate [BLK-077]."""

    def test_duplicate_run(self, client):
        from src.definitions.store import get_store
        store = get_store()
        _create_run(store, "run-001")

        resp = client.post("/api/v1/runs/run-001/duplicate")
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "queued"
        assert data["extracted_fields_count"] == 0
        assert data["fields"] == []
        assert data["definition_id"] == "def-1"
        assert data["document_url"] == "/tmp/doc.pdf"
        assert data["id"] != "run-001"
        assert "source_run_id" in data

    def test_duplicate_not_found(self, client):
        resp = client.post("/api/v1/runs/nonexistent/duplicate")
        assert resp.status_code == 404


class TestExportEndpoints:
    """Verify export endpoints work with _get_run_or_404 [BLK-060]."""

    def test_export_json(self, client):
        from src.definitions.store import get_store
        store = get_store()
        _create_run(store, "run-001")

        resp = client.get("/api/v1/runs/run-001/export/json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == "run-001"
        assert data["extracted_fields_count"] == 5

    def test_export_json_includes_document_url(self, client):
        """Regression [BLK-185, SCRUM-18]: export must surface the canonical
        ``document_url`` field, not an always-null ``document_path``."""
        from src.definitions.store import get_store
        store = get_store()
        _create_run(store, "run-001", {"document_url": "/tmp/doc.pdf", "document_path": None})

        resp = client.get("/api/v1/runs/run-001/export/json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_url"] == "/tmp/doc.pdf"

    def test_export_csv(self, client):
        from src.definitions.store import get_store
        store = get_store()
        _create_run(store, "run-001")

        resp = client.get("/api/v1/runs/run-001/export/csv")
        assert resp.status_code == 200
        assert "vendor" in resp.text
        assert "ACME" in resp.text
