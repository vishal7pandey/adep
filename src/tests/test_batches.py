"""Tests for batch processing queue endpoints [BLK-118]."""

from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with auth disabled and temp .adep/ store."""
    import src.config as config_module
    import src.definitions.store as store_module
    from src.definitions.store import DefinitionStore

    monkeypatch.chdir(tmp_path)
    store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    from src.api.main import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_executor():
    """Mock the run executor to avoid actual run execution."""
    mock = MagicMock()
    mock.active_count = 0
    mock.queue_depth = 0
    mock.max_workers = 3

    def mock_enqueue(definition_id, document_path, run_id=None):
        ctx = MagicMock()
        ctx.run_id = run_id or f"run-test-{hash(definition_id + document_path) & 0xFFFFFFFF:08x}"
        ctx.definition_id = definition_id
        ctx.document_path = document_path
        ctx.status = "queued"
        ctx.created_at = "2025-01-01T00:00:00+00:00"
        return ctx

    mock.enqueue = mock_enqueue
    mock.get_run.return_value = None
    mock.cancel_run.return_value = True

    with patch("src.api.routes.batches.get_executor", return_value=mock):
        yield mock


@pytest.fixture
def mock_document_store(tmp_path, monkeypatch):
    """Mock the document store to avoid actual file processing."""
    mock = MagicMock()

    def mock_import(file_path, original_filename=None):
        meta = MagicMock()
        meta.doc_id = f"doc-{hash(original_filename or 'test') & 0xFFFFFFFF:08x}"
        return meta

    mock.import_document = mock_import
    mock.get_document.return_value = {"page_paths": [str(tmp_path / "page_001.png")]}

    with patch("src.api.routes.batches.get_document_store", return_value=mock):
        yield mock


@pytest.fixture
def mock_definition_store(tmp_path, monkeypatch):
    """Mock the definition store."""
    mock = MagicMock()
    mock.get_definition.return_value = {"id": "def-test", "name": "Test Definition"}
    mock.get_run.return_value = {"status": "completed", "fields": []}

    with patch("src.api.routes.batches.get_store", return_value=mock):
        yield mock


class TestBatchCreation:
    """Tests for POST /batches endpoint."""

    def test_create_batch_success(
        self, client, mock_executor, mock_document_store, mock_definition_store
    ):
        """Successfully create a batch with multiple files."""
        # Create a minimal valid PNG file
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        files = [
            ("files", ("test1.png", io.BytesIO(png_bytes), "image/png")),
            ("files", ("test2.png", io.BytesIO(png_bytes), "image/png")),
        ]
        data = {"definition_id": "def-test", "name": "Test Batch"}

        response = client.post(
            "/api/v1/batches",
            files=files,
            data=data,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Test Batch"
        assert body["definition_id"] == "def-test"
        assert body["total_runs"] == 2
        assert body["queued_runs"] == 2
        assert len(body["runs"]) == 2
        assert body["status"] == "queued"

    def test_create_batch_auto_definition(
        self, client, mock_executor, mock_document_store, mock_definition_store
    ):
        """Create a batch with auto-routing definition."""
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        files = [("files", ("test.png", io.BytesIO(png_bytes), "image/png"))]
        data = {"definition_id": "auto"}

        response = client.post(
            "/api/v1/batches",
            files=files,
            data=data,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["definition_id"] == "auto"

    def test_create_batch_no_files(self, client, mock_executor):
        """Creating a batch with no files should fail."""
        data = {"definition_id": "def-test"}
        response = client.post("/api/v1/batches", data=data)

        assert response.status_code == 422  # FastAPI validation error for missing files

    def test_create_batch_invalid_definition(
        self, client, mock_executor, mock_document_store, mock_definition_store
    ):
        """Creating a batch with a non-existent definition should fail."""
        mock_definition_store.get_definition.side_effect = FileNotFoundError()

        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        files = [("files", ("test.png", io.BytesIO(png_bytes), "image/png"))]
        data = {"definition_id": "def-nonexistent"}

        response = client.post(
            "/api/v1/batches",
            files=files,
            data=data,
        )

        assert response.status_code == 404

    def test_create_batch_unsupported_format(
        self, client, mock_executor, mock_document_store, mock_definition_store
    ):
        """Files with unsupported formats should be rejected."""
        files = [("files", ("test.txt", io.BytesIO(b"hello"), "text/plain"))]
        data = {"definition_id": "def-test"}

        response = client.post(
            "/api/v1/batches",
            files=files,
            data=data,
        )

        assert response.status_code == 400
        assert "No files were successfully processed" in response.json()["detail"]


class TestBatchListing:
    """Tests for GET /batches and GET /batches/{id}."""

    def test_list_empty_batches(self, client, mock_executor):
        """Listing batches when none exist returns empty list."""
        response = client.get("/api/v1/batches")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_batches_after_creation(
        self, client, mock_executor, mock_document_store, mock_definition_store
    ):
        """Listing batches after creating one returns the batch."""
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        files = [("files", ("test.png", io.BytesIO(png_bytes), "image/png"))]
        data = {"definition_id": "def-test", "name": "My Batch"}

        create_response = client.post("/api/v1/batches", files=files, data=data)
        assert create_response.status_code == 201
        batch_id = create_response.json()["id"]

        list_response = client.get("/api/v1/batches")
        assert list_response.status_code == 200
        batches = list_response.json()
        assert len(batches) == 1
        assert batches[0]["id"] == batch_id

    def test_get_batch_by_id(
        self, client, mock_executor, mock_document_store, mock_definition_store
    ):
        """Getting a batch by ID returns the batch."""
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        files = [("files", ("test.png", io.BytesIO(png_bytes), "image/png"))]
        data = {"definition_id": "def-test"}

        create_response = client.post("/api/v1/batches", files=files, data=data)
        batch_id = create_response.json()["id"]

        get_response = client.get(f"/api/v1/batches/{batch_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == batch_id

    def test_get_batch_not_found(self, client):
        """Getting a non-existent batch returns 404."""
        response = client.get("/api/v1/batches/batch-nonexistent")
        assert response.status_code == 404


class TestBatchCancel:
    """Tests for POST /batches/{id}/cancel."""

    def test_cancel_batch(self, client, mock_executor, mock_document_store, mock_definition_store):
        """Cancelling a batch cancels all its runs."""
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        files = [
            ("files", ("test1.png", io.BytesIO(png_bytes), "image/png")),
            ("files", ("test2.png", io.BytesIO(png_bytes), "image/png")),
        ]
        data = {"definition_id": "def-test"}

        create_response = client.post("/api/v1/batches", files=files, data=data)
        batch_id = create_response.json()["id"]

        cancel_response = client.post(f"/api/v1/batches/{batch_id}/cancel")
        assert cancel_response.status_code == 202
        body = cancel_response.json()
        assert body["cancelled_runs"] == 2

    def test_cancel_batch_not_found(self, client):
        """Cancelling a non-existent batch returns 404."""
        response = client.post("/api/v1/batches/batch-nonexistent/cancel")
        assert response.status_code == 404


class TestBatchDelete:
    """Tests for DELETE /batches/{id}."""

    def test_delete_batch(self, client, mock_executor, mock_document_store, mock_definition_store):
        """Deleting a batch removes its metadata file."""
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        files = [("files", ("test.png", io.BytesIO(png_bytes), "image/png"))]
        data = {"definition_id": "def-test"}

        create_response = client.post("/api/v1/batches", files=files, data=data)
        batch_id = create_response.json()["id"]

        delete_response = client.delete(f"/api/v1/batches/{batch_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] is True

        # Verify it's gone
        get_response = client.get(f"/api/v1/batches/{batch_id}")
        assert get_response.status_code == 404

    def test_delete_batch_not_found(self, client):
        """Deleting a non-existent batch returns 404."""
        response = client.delete("/api/v1/batches/batch-nonexistent")
        assert response.status_code == 404


class TestBatchExport:
    """Tests for export endpoints."""

    def test_export_json(self, client, mock_executor, mock_document_store, mock_definition_store):
        """Export batch as JSON returns all run results."""
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        files = [("files", ("test.png", io.BytesIO(png_bytes), "image/png"))]
        data = {"definition_id": "def-test"}

        create_response = client.post("/api/v1/batches", files=files, data=data)
        batch_id = create_response.json()["id"]

        export_response = client.get(f"/api/v1/batches/{batch_id}/export/json")
        assert export_response.status_code == 200
        results = export_response.json()
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["filename"] == "test.png"

    def test_export_csv(self, client, mock_executor, mock_document_store, mock_definition_store):
        """Export batch as CSV returns CSV content."""
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        files = [("files", ("test.png", io.BytesIO(png_bytes), "image/png"))]
        data = {"definition_id": "def-test"}

        create_response = client.post("/api/v1/batches", files=files, data=data)
        batch_id = create_response.json()["id"]

        export_response = client.get(f"/api/v1/batches/{batch_id}/export/csv")
        assert export_response.status_code == 200
        assert "text/csv" in export_response.headers.get("content-type", "")
        lines = export_response.text.strip().split("\n")
        assert lines[0] == "run_id,filename,field_name,value,confidence,status"

    def test_export_not_found(self, client):
        """Exporting a non-existent batch returns 404."""
        response = client.get("/api/v1/batches/batch-nonexistent/export/json")
        assert response.status_code == 404


class TestBatchStore:
    """Tests for the file-based batch store helpers."""

    def test_save_and_load_batch(self, tmp_path, monkeypatch):
        """Save and load a batch from disk."""
        monkeypatch.chdir(tmp_path)
        from src.api.routes.batches import save_batch, load_batch

        batch_data = {
            "id": "batch-test",
            "name": "Test",
            "definition_id": "def-test",
            "total_runs": 5,
        }
        save_batch("batch-test", batch_data)

        loaded = load_batch("batch-test")
        assert loaded["id"] == "batch-test"
        assert loaded["name"] == "Test"
        assert loaded["total_runs"] == 5

    def test_load_batch_not_found(self, tmp_path, monkeypatch):
        """Loading a non-existent batch raises FileNotFoundError."""
        monkeypatch.chdir(tmp_path)
        from src.api.routes.batches import load_batch

        with pytest.raises(FileNotFoundError):
            load_batch("batch-nonexistent")

    def test_list_batches(self, tmp_path, monkeypatch):
        """List batches returns all batches sorted by modification time."""
        monkeypatch.chdir(tmp_path)
        from src.api.routes.batches import save_batch, list_batches

        save_batch("batch-1", {"id": "batch-1", "name": "Batch 1"})
        save_batch("batch-2", {"id": "batch-2", "name": "Batch 2"})

        batches = list_batches()
        assert len(batches) == 2
        ids = [b["id"] for b in batches]
        assert "batch-1" in ids
        assert "batch-2" in ids


class TestBatchDocumentIdResolution:
    """Tests for SCRUM-479: document_id resolved to file path before build_initial_state."""

    def test_run_engine_resolves_document_id_to_file_path(self, tmp_path, monkeypatch):
        """When document_path is a document_id (not a raw path), run_engine
        resolves it to page_paths[0] before calling build_initial_state."""
        monkeypatch.chdir(tmp_path)

        # Create a real document store with a document
        from src.documents.store import DocumentStore

        doc_store = DocumentStore(base_dir=tmp_path / ".adep")
        doc_dir = doc_store.get_doc_dir("testdoc123456")
        doc_dir.mkdir(parents=True, exist_ok=True)
        page_path = doc_dir / "page_001.png"
        page_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        import json as _json

        (doc_dir / "meta.json").write_text(
            _json.dumps(
                {
                    "document_id": "testdoc123456",
                    "original_filename": "test.png",
                    "format": "png",
                    "total_pages": 1,
                    "page_dimensions": [{"width": 100, "height": 100}],
                    "page_paths": [str(page_path)],
                    "thumbnail": "",
                    "created_at": "2025-01-01T00:00:00+00:00",
                }
            )
        )

        # Mock definition store
        mock_store = MagicMock()
        mock_store.get_definition.return_value = {
            "id": "def-test",
            "skill_id": "invoice",
            "template_id": "invoice",
            "task_type": "extraction",
            "agent_config": {},
        }

        # Mock skill and template resolution
        mock_skill = MagicMock()
        mock_template = MagicMock()

        # Capture the document_path passed to build_initial_state
        captured_path = {}

        def mock_build_state(document_path, *args, **kwargs):
            captured_path["value"] = document_path
            return {"document": MagicMock(), "trace": [], "cycles": 0}

        with (
            patch("src.api.run_engine.get_store", return_value=mock_store),
            patch("src.api.run_engine.resolve_skill", return_value=mock_skill),
            patch("src.api.run_engine.resolve_template", return_value=mock_template),
            patch("src.api.run_engine.build_initial_state", side_effect=mock_build_state),
            patch("src.api.run_engine.build_tool_registry", return_value=MagicMock()),
            patch("src.api.run_engine.build_validator_config", return_value=MagicMock()),
            patch("src.api.run_engine.settings") as mock_settings,
            patch("src.api.run_engine.run_pdf_fallback", return_value=None),
            patch("src.documents.store.get_document_store", return_value=doc_store),
        ):
            mock_settings.is_llm_configured.return_value = True
            mock_settings.validate_provider_config = MagicMock()

            from src.api.run_engine import _execute_run_inner

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    _execute_run_inner(
                        definition_id="def-test",
                        document_path="testdoc123456",
                        store=mock_store,
                    )
                )
            except Exception:
                pass  # We only care about the document_path resolution
            finally:
                loop.close()

        # The document_path should have been resolved to the actual file path
        assert "value" in captured_path, "build_initial_state was never called"
        assert captured_path["value"] != "testdoc123456", (
            "document_id was not resolved — still passed as-is"
        )
        assert str(page_path) in captured_path["value"], (
            f"document_path was not resolved to page_paths[0]: {captured_path['value']}"
        )
