"""API integration tests — full platform flow [BLK-025, TS].

Uses FastAPI TestClient with mocked providers. Tests cover:
- Health check
- CRUD for definitions, skills, templates
- Run lifecycle (start, get, list)
- SSE streaming
- Error handling
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.definitions.store import DefinitionStore


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Create a FastAPI TestClient with a temporary .adep/ store."""
    # Patch the singleton store to use tmp_path
    import src.definitions.store as store_module
    import src.config as config_module
    old_store = store_module._store
    old_auth = config_module.settings.auth_enabled
    store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
    # Disable auth for API integration tests (auth is tested separately in test_auth.py)
    config_module.settings.auth_enabled = False

    from src.api.main import create_app
    app = create_app()
    client = TestClient(app)

    yield client

    # Restore
    config_module.settings.auth_enabled = old_auth
    store_module._store = old_store


@pytest.fixture
def seeded_client(client: TestClient) -> TestClient:
    """Client with a pre-seeded skill, template, and definition."""
    # Create skill
    client.post("/api/v1/skills", json={
        "id": "sk-invoice-basic",
        "name": "Invoice Processing Skill",
        "description": "ReAct reasoning skill for extracting invoice metadata",
        "semantic_checks_enabled": False,
        "tools": ["ocr", "vlm", "crop"],
    })

    # Create template
    client.post("/api/v1/templates", json={
        "id": "tmpl-invoice-standard",
        "name": "Standard Invoice Schema",
        "description": "Extracts vendor, total, tax, line items",
        "fields": [
            {"name": "invoice_number", "type": "string", "description": "Invoice reference number", "required": True},
            {"name": "total", "type": "number", "description": "Grand total amount", "required": True},
        ],
    })

    # Create definition
    client.post("/api/v1/definitions", json={
        "id": "def-invoice-v1",
        "name": "Standard Invoice Extractor",
        "skill_ref": "invoice",
        "template_ref": "invoice",
        "tool_names": ["ocr", "vlm", "crop"],
    })

    return client


class TestHealthCheck:
    """Verify health check endpoints."""

    def test_health_root(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_health_v1(self, client: TestClient):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestDefinitionsCRUD:
    """Verify definition CRUD endpoints."""

    def test_create_and_get(self, client: TestClient):
        resp = client.post("/api/v1/definitions", json={
            "id": "def-test",
            "name": "Test Definition",
            "skill_id": "invoice",
            "template_id": "invoice",
            "tool_names": ["ocr"],
        })
        assert resp.status_code == 201

        resp = client.get("/api/v1/definitions/def-test")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Definition"

    def test_list(self, client: TestClient):
        client.post("/api/v1/definitions", json={
            "id": "def-1", "name": "Def 1", "skill_id": "x", "template_id": "y",
        })
        client.post("/api/v1/definitions", json={
            "id": "def-2", "name": "Def 2", "skill_id": "x", "template_id": "y",
        })
        resp = client.get("/api/v1/definitions")
        assert resp.status_code == 200
        data = resp.json()
        ids = {d["id"] for d in data}
        assert "def-1" in ids
        assert "def-2" in ids
        assert len(data) >= 20  # 2 user-created + 18 prebuilt [BLK-159]

    def test_update(self, client: TestClient):
        client.post("/api/v1/definitions", json={
            "id": "def-upd", "name": "Original", "skill_id": "x", "template_id": "y",
        })
        resp = client.put("/api/v1/definitions/def-upd", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_delete(self, client: TestClient):
        client.post("/api/v1/definitions", json={
            "id": "def-del", "name": "Delete", "skill_id": "x", "template_id": "y",
        })
        resp = client.delete("/api/v1/definitions/def-del")
        assert resp.status_code == 204

    def test_get_missing_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/definitions/nonexistent")
        assert resp.status_code == 404

    def test_create_duplicate_returns_409(self, client: TestClient):
        client.post("/api/v1/definitions", json={
            "id": "def-dup", "name": "Dup", "skill_id": "x", "template_id": "y",
        })
        resp = client.post("/api/v1/definitions", json={
            "id": "def-dup", "name": "Dup", "skill_id": "x", "template_id": "y",
        })
        assert resp.status_code == 409


class TestSkillsCRUD:
    """Verify skill CRUD endpoints."""

    def test_create_and_get(self, client: TestClient):
        resp = client.post("/api/v1/skills", json={
            "id": "sk-test",
            "name": "Test Skill",
            "description": "A test skill",
            "tools": ["ocr"],
        })
        assert resp.status_code == 201

        resp = client.get("/api/v1/skills/sk-test")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Skill"

    def test_list(self, client: TestClient):
        client.post("/api/v1/skills", json={"id": "sk-1", "name": "Skill 1"})
        client.post("/api/v1/skills", json={"id": "sk-2", "name": "Skill 2"})
        resp = client.get("/api/v1/skills")
        assert resp.status_code == 200
        data = resp.json()
        ids = {s["id"] for s in data}
        assert "sk-1" in ids
        assert "sk-2" in ids
        assert len(data) >= 21  # 2 user-created + 19 prebuilt [BLK-159]

    def test_delete(self, client: TestClient):
        client.post("/api/v1/skills", json={"id": "sk-del", "name": "Delete"})
        resp = client.delete("/api/v1/skills/sk-del")
        assert resp.status_code == 204

    def test_full_skill_round_trip(self, client: TestClient):
        """POST with all fields, GET returns exactly what was sent [BLK-121]."""
        skill_data = {
            "id": "sk-full",
            "name": "Full Skill",
            "description": "A skill with all fields populated",
            "system_prompt": "You are an expert extractor.",
            "tool_preferences": {"ocr": "paddle", "vlm": "azure"},
            "probe_order": [
                {"region_type": "header", "rationale": "Look for invoice number"},
                {"region_type": "table", "rationale": "Extract line items"},
            ],
            "invariants": [
                {"name": "sum_check", "fields": ["subtotal", "tax", "total"], "description": "subtotal + tax == total"},
            ],
            "failure_actions": {"missing": "retry_ocr", "low_confidence": "escalate_vlm"},
            "known_failures": "PaddleOCR fails on rotated text",
            "confidence_overrides": {"total": 0.9, "vendor": 0.85},
            "semantic_checks_enabled": True,
            "semantic_prompt": "Check vendor name looks like a real company",
            "tools": ["ocr", "vlm", "crop"],
        }
        resp = client.post("/api/v1/skills", json=skill_data)
        assert resp.status_code == 201

        resp = client.get("/api/v1/skills/sk-full")
        assert resp.status_code == 200
        data = resp.json()
        assert data["system_prompt"] == "You are an expert extractor."
        assert data["tool_preferences"] == {"ocr": "paddle", "vlm": "azure"}
        assert len(data["probe_order"]) == 2
        assert data["probe_order"][0]["region_type"] == "header"
        assert len(data["invariants"]) == 1
        assert data["invariants"][0]["name"] == "sum_check"
        assert data["failure_actions"] == {"missing": "retry_ocr", "low_confidence": "escalate_vlm"}
        assert data["known_failures"] == "PaddleOCR fails on rotated text"
        assert data["confidence_overrides"] == {"total": 0.9, "vendor": 0.85}
        assert data["semantic_checks_enabled"] is True
        assert data["semantic_prompt"] == "Check vendor name looks like a real company"
        assert data["tools"] == ["ocr", "vlm", "crop"]

    def test_partial_update_preserves_other_fields(self, client: TestClient):
        """PUT with partial data doesn't clobber unspecified fields [BLK-121]."""
        client.post("/api/v1/skills", json={
            "id": "sk-partial",
            "name": "Original",
            "description": "Original description",
            "system_prompt": "Original prompt",
            "tools": ["ocr"],
            "confidence_overrides": {"total": 0.9},
        })

        resp = client.put("/api/v1/skills/sk-partial", json={
            "name": "Updated Name",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Original description"
        assert data["system_prompt"] == "Original prompt"
        assert data["tools"] == ["ocr"]
        assert data["confidence_overrides"] == {"total": 0.9}

    def test_update_system_prompt_only(self, client: TestClient):
        """PUT can update just system_prompt without losing other data [BLK-121]."""
        client.post("/api/v1/skills", json={
            "id": "sk-update-prompt",
            "name": "Test",
            "system_prompt": "Old prompt",
            "probe_order": [{"region_type": "header", "rationale": "Check header"}],
        })

        resp = client.put("/api/v1/skills/sk-update-prompt", json={
            "system_prompt": "New prompt",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["system_prompt"] == "New prompt"
        assert len(data["probe_order"]) == 1
        assert data["probe_order"][0]["region_type"] == "header"


class TestTemplatesCRUD:
    """Verify template CRUD endpoints."""

    def test_create_and_get(self, client: TestClient):
        resp = client.post("/api/v1/templates", json={
            "id": "tmpl-test",
            "name": "Test Template",
            "fields": [{"name": "total", "type": "number", "required": True}],
        })
        assert resp.status_code == 201

        resp = client.get("/api/v1/templates/tmpl-test")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Template"

    def test_list(self, client: TestClient):
        client.post("/api/v1/templates", json={"id": "t1", "name": "T1"})
        client.post("/api/v1/templates", json={"id": "t2", "name": "T2"})
        resp = client.get("/api/v1/templates")
        assert resp.status_code == 200
        data = resp.json()
        ids = {t["id"] for t in data}
        assert "t1" in ids
        assert "t2" in ids
        assert len(data) >= 21  # 2 user-created + 19 prebuilt [BLK-159]


class TestRuns:
    """Verify run endpoints."""

    def test_start_run_missing_definition(self, client: TestClient):
        resp = client.post("/api/v1/runs", json={
            "definition_id": "nonexistent",
            "document_path": "test.png",
        })
        assert resp.status_code == 404

    def test_get_missing_run(self, client: TestClient):
        resp = client.get("/api/v1/runs/nonexistent")
        assert resp.status_code == 404

    def test_list_runs_empty(self, client: TestClient):
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0


class TestSSEStreaming:
    """Verify SSE streaming endpoint."""

    def test_stream_missing_run(self, client: TestClient):
        resp = client.get("/api/v1/runs/nonexistent/stream")
        assert resp.status_code == 404

    def test_stream_returns_event_stream(self, seeded_client: TestClient):
        """Verify SSE endpoint returns text/event-stream content type."""
        # First create a run (will fail on document but we test the endpoint)
        # Save a mock run directly to the store
        import src.definitions.store as store_module
        store_module._store.save_run("run-test", {
            "id": "run-test",
            "definition_id": "def-invoice-v1",
            "document_url": "test.png",
            "status": "completed",
            "current_cycle": 5,
            "total_fields": 7,
            "extracted_fields_count": 7,
            "fields": [
                {"id": "run-test_invoice_number", "name": "invoice_number",
                 "value": "INV-001", "confidence": 0.95,
                 "bbox": {"x": 10, "y": 10, "width": 100, "height": 30},
                 "page": 0, "status": "verified"},
            ],
        })

        resp = seeded_client.get("/api/v1/runs/run-test/stream")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        # Parse SSE events from the response
        body = resp.text
        events = []
        for line in body.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        # Should have field_update, progress, and complete events
        event_types = [e["type"] for e in events]
        assert "field_update" in event_types
        assert "progress" in event_types
        assert "complete" in event_types
