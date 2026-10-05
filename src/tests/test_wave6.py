"""Tests for Wave 6 — search/filter, document import, trace export [BLK-059, BLK-060, BLK-061]."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.documents.store import DocumentStore, DocumentMeta


@pytest.fixture
def client(tmp_path):
    """Create a test client with isolated stores."""
    import src.definitions.store as store_module
    import src.documents.store as doc_store_module
    import src.config as config_module

    old_def_store = store_module._store
    old_doc_store = doc_store_module._store
    old_auth = config_module.settings.auth_enabled

    store_module._store = store_module.DefinitionStore(base_dir=tmp_path / ".adep")
    doc_store_module._store = DocumentStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    from src.api.main import create_app

    app = create_app()
    yield TestClient(app)

    config_module.settings.auth_enabled = old_auth
    store_module._store = old_def_store
    doc_store_module._store = old_doc_store


# ---------------------------------------------------------------------------
# BLK-061: Search & filter
# ---------------------------------------------------------------------------


class TestDefinitionSearch:
    """Verify definition search and filter [BLK-061]."""

    def test_search_by_name(self, client):
        client.post(
            "/api/v1/definitions",
            json={
                "id": "inv-1",
                "name": "Invoice Extractor",
                "skill_id": "skill-1",
                "template_id": "tmpl-1",
            },
        )
        client.post(
            "/api/v1/definitions",
            json={
                "id": "rcpt-1",
                "name": "Receipt Extractor",
                "skill_id": "skill-2",
                "template_id": "tmpl-2",
            },
        )

        resp = client.get("/api/v1/definitions?q=invoice")
        assert resp.status_code == 200
        items = resp.json()
        ids = {item["id"] for item in items}
        assert "inv-1" in ids

    def test_filter_by_skill(self, client):
        client.post(
            "/api/v1/definitions",
            json={
                "id": "d1",
                "name": "Def 1",
                "skill_id": "skill-a",
                "template_id": "tmpl-1",
            },
        )
        client.post(
            "/api/v1/definitions",
            json={
                "id": "d2",
                "name": "Def 2",
                "skill_id": "skill-b",
                "template_id": "tmpl-2",
            },
        )

        resp = client.get("/api/v1/definitions?skill=skill-a")
        items = resp.json()
        assert len(items) == 1
        assert items[0]["id"] == "d1"

    def test_filter_by_template(self, client):
        client.post(
            "/api/v1/definitions",
            json={
                "id": "d1",
                "name": "Def 1",
                "skill_id": "s1",
                "template_id": "tmpl-x",
            },
        )
        client.post(
            "/api/v1/definitions",
            json={
                "id": "d2",
                "name": "Def 2",
                "skill_id": "s2",
                "template_id": "tmpl-y",
            },
        )

        resp = client.get("/api/v1/definitions?template=tmpl-x")
        items = resp.json()
        assert len(items) == 1
        assert items[0]["id"] == "d1"

    def test_combined_search_and_filter(self, client):
        client.post(
            "/api/v1/definitions",
            json={
                "id": "d1",
                "name": "Invoice Pro",
                "skill_id": "s1",
                "template_id": "t1",
            },
        )
        client.post(
            "/api/v1/definitions",
            json={
                "id": "d2",
                "name": "Invoice Basic",
                "skill_id": "s2",
                "template_id": "t2",
            },
        )

        resp = client.get("/api/v1/definitions?q=invoice&skill=s1")
        items = resp.json()
        assert len(items) == 1
        assert items[0]["id"] == "d1"


class TestSkillSearch:
    """Verify skill search and filter [BLK-061]."""

    def test_search_by_name(self, client):
        client.post(
            "/api/v1/skills",
            json={
                "id": "s1",
                "name": "Invoice Processing",
                "tools": ["ocr", "vlm"],
            },
        )
        client.post(
            "/api/v1/skills",
            json={
                "id": "s2",
                "name": "Receipt Processing",
                "tools": ["ocr"],
            },
        )

        resp = client.get("/api/v1/skills?q=invoice")
        items = resp.json()
        ids = {item["id"] for item in items}
        assert "s1" in ids  # user-created matches [BLK-159]

    def test_filter_by_tool(self, client):
        client.post(
            "/api/v1/skills",
            json={
                "id": "s1-unique-tool-test",
                "name": "Skill 1",
                "tools": ["ocr", "vlm"],
            },
        )
        client.post(
            "/api/v1/skills",
            json={
                "id": "s2-unique-tool-test",
                "name": "Skill 2",
                "tools": ["ocr"],
            },
        )

        resp = client.get("/api/v1/skills?tool=vlm")
        items = resp.json()
        ids = {item["id"] for item in items}
        assert "s1-unique-tool-test" in ids  # user-created matches [BLK-159]

    def test_filter_by_semantic(self, client):
        client.post(
            "/api/v1/skills",
            json={
                "id": "s1",
                "name": "Skill 1",
                "semantic_checks_enabled": True,
                "tools": [],
            },
        )
        client.post(
            "/api/v1/skills",
            json={
                "id": "s2",
                "name": "Skill 2",
                "semantic_checks_enabled": False,
                "tools": [],
            },
        )

        resp = client.get("/api/v1/skills?semantic=true")
        items = resp.json()
        assert len(items) == 1
        assert items[0]["id"] == "s1"


class TestTemplateSearch:
    """Verify template search and filter [BLK-061]."""

    def test_search_by_name(self, client):
        client.post(
            "/api/v1/templates",
            json={
                "id": "t1-unique-search-test",
                "name": "Invoice Schema",
                "fields": [{"name": "total", "type": "float"}],
            },
        )
        client.post(
            "/api/v1/templates",
            json={
                "id": "t2-unique-search-test",
                "name": "Receipt Schema",
                "fields": [{"name": "amount", "type": "float"}],
            },
        )

        resp = client.get("/api/v1/templates?q=invoice")
        items = resp.json()
        ids = {item["id"] for item in items}
        assert "t1-unique-search-test" in ids  # user-created matches [BLK-159]

    def test_filter_by_field_type(self, client):
        client.post(
            "/api/v1/templates",
            json={
                "id": "t1-unique-field-test",
                "name": "Template 1",
                "fields": [{"name": "total", "type": "float"}],
            },
        )
        client.post(
            "/api/v1/templates",
            json={
                "id": "t2-unique-field-test",
                "name": "Template 2",
                "fields": [{"name": "vendor", "type": "str"}],
            },
        )

        resp = client.get("/api/v1/templates?field_type=float")
        items = resp.json()
        ids = {item["id"] for item in items}
        assert "t1-unique-field-test" in ids  # user-created matches [BLK-159]


# ---------------------------------------------------------------------------
# BLK-059: Document import
# ---------------------------------------------------------------------------


class TestDocumentStore:
    """Verify DocumentStore [BLK-059]."""

    def test_import_png(self, tmp_path: Path):
        from PIL import Image

        store = DocumentStore(base_dir=tmp_path / ".adep")

        # Create a test PNG
        img_path = tmp_path / "test.png"
        Image.new("RGB", (800, 600), "white").save(img_path)

        meta = store.import_document(img_path, "test.png")
        assert meta.format == "png"
        assert meta.total_pages == 1
        assert len(meta.page_paths) == 1
        assert Path(meta.page_paths[0]).exists()
        assert Path(meta.thumbnail_path).exists()

    def test_import_bmp(self, tmp_path: Path):
        from PIL import Image

        store = DocumentStore(base_dir=tmp_path / ".adep")

        img_path = tmp_path / "test.bmp"
        Image.new("RGB", (400, 300), "white").save(img_path)

        meta = store.import_document(img_path, "test.bmp")
        assert meta.format == "bmp"
        assert meta.total_pages == 1

    def test_unsupported_format(self, tmp_path: Path):
        store = DocumentStore(base_dir=tmp_path / ".adep")
        img_path = tmp_path / "test.gif"
        img_path.write_bytes(b"GIF89a")

        with pytest.raises(ValueError, match="Unsupported format"):
            store.import_document(img_path, "test.gif")

    def test_file_too_large(self, tmp_path: Path):
        store = DocumentStore(base_dir=tmp_path / ".adep")

        # Create a file larger than 20MB
        img_path = tmp_path / "large.png"
        img_path.write_bytes(b"\x00" * (21 * 1024 * 1024))

        with pytest.raises(ValueError, match="exceeds 20MB"):
            store.import_document(img_path, "large.png")

    def test_get_document(self, tmp_path: Path):
        from PIL import Image

        store = DocumentStore(base_dir=tmp_path / ".adep")

        img_path = tmp_path / "test.png"
        Image.new("RGB", (800, 600), "white").save(img_path)

        meta = store.import_document(img_path, "test.png")
        retrieved = store.get_document(meta.doc_id)
        assert retrieved["document_id"] == meta.doc_id
        assert retrieved["total_pages"] == 1

    def test_get_page_path(self, tmp_path: Path):
        from PIL import Image

        store = DocumentStore(base_dir=tmp_path / ".adep")

        img_path = tmp_path / "test.png"
        Image.new("RGB", (800, 600), "white").save(img_path)

        meta = store.import_document(img_path, "test.png")
        page_path = store.get_page_path(meta.doc_id, 1)
        assert page_path.exists()

    def test_list_documents(self, tmp_path: Path):
        from PIL import Image

        store = DocumentStore(base_dir=tmp_path / ".adep")

        img_path = tmp_path / "test.png"
        Image.new("RGB", (800, 600), "white").save(img_path)

        store.import_document(img_path, "test1.png")
        store.import_document(img_path, "test2.png")

        docs = store.list_documents()
        assert len(docs) == 2

    def test_document_meta_to_dict(self):
        meta = DocumentMeta(
            doc_id="abc123",
            original_filename="test.pdf",
            format="pdf",
            total_pages=3,
            page_dimensions=[(100, 200), (100, 200), (100, 200)],
            page_paths=["p1.png", "p2.png", "p3.png"],
            thumbnail_path="thumb.jpg",
        )
        d = meta.to_dict()
        assert d["document_id"] == "abc123"
        assert d["total_pages"] == 3
        assert len(d["page_dimensions"]) == 3
        assert d["page_dimensions"][0] == {"width": 100, "height": 200}


class TestDocumentAPI:
    """Verify document API endpoints [BLK-059]."""

    def test_upload_document(self, client, tmp_path):
        from PIL import Image
        import io

        img = Image.new("RGB", (800, 600), "white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        resp = client.post(
            "/api/v1/documents",
            files={"file": ("test.png", buf, "image/png")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["format"] == "png"
        assert data["total_pages"] == 1

    def test_get_document(self, client, tmp_path):
        from PIL import Image
        import io

        img = Image.new("RGB", (800, 600), "white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        upload_resp = client.post(
            "/api/v1/documents",
            files={"file": ("test.png", buf, "image/png")},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = client.get(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["document_id"] == doc_id

    def test_get_document_not_found(self, client):
        resp = client.get("/api/v1/documents/nonexistent")
        assert resp.status_code == 404

    def test_list_documents(self, client, tmp_path):
        from PIL import Image
        import io

        for i in range(3):
            img = Image.new("RGB", (800, 600), "white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            client.post(
                "/api/v1/documents",
                files={"file": (f"test{i}.png", buf, "image/png")},
            )

        resp = client.get("/api/v1/documents")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_upload_unsupported_format(self, client):
        import io

        buf = io.BytesIO(b"GIF89a")
        resp = client.post(
            "/api/v1/documents",
            files={"file": ("test.gif", buf, "image/gif")},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# BLK-060: Trace export
# ---------------------------------------------------------------------------


class TestRunExport:
    """Verify run export endpoints [BLK-060]."""

    def test_export_json(self, client):
        # Create a run via store
        from src.definitions.store import get_store

        store = get_store()
        store.create(
            "runs",
            "test-run-1",
            {
                "id": "test-run-1",
                "definition_id": "def-1",
                "document_path": "/tmp/doc.pdf",
                "status": "completed",
                "fields": [
                    {
                        "name": "vendor",
                        "value": "ACME",
                        "confidence": 0.95,
                        "status": "extracted",
                        "page": 1,
                    },
                ],
                "extracted_fields_count": 1,
                "total_fields": 5,
                "token_usage_summary": {"total_tokens": 1000, "total_cost_usd": 0.005},
            },
        )

        resp = client.get("/api/v1/runs/test-run-1/export/json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == "test-run-1"
        assert data["status"] == "completed"
        assert len(data["fields"]) == 1
        assert data["token_usage"]["total_tokens"] == 1000

    def test_export_csv(self, client):
        from src.definitions.store import get_store

        store = get_store()
        store.create(
            "runs",
            "test-run-2",
            {
                "id": "test-run-2",
                "definition_id": "def-1",
                "document_path": "/tmp/doc.pdf",
                "status": "completed",
                "fields": [
                    {
                        "name": "vendor",
                        "value": "ACME",
                        "confidence": 0.95,
                        "status": "extracted",
                        "page": 1,
                        "bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.1},
                    },
                    {
                        "name": "total",
                        "value": 1500.00,
                        "confidence": 0.88,
                        "status": "extracted",
                        "page": 1,
                    },
                ],
                "extracted_fields_count": 2,
                "total_fields": 5,
            },
        )

        resp = client.get("/api/v1/runs/test-run-2/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        content = resp.text
        assert "field_name" in content
        assert "vendor" in content
        assert "ACME" in content
        assert "total" in content

    def test_export_json_not_found(self, client):
        resp = client.get("/api/v1/runs/nonexistent/export/json")
        assert resp.status_code == 404

    def test_export_csv_not_found(self, client):
        resp = client.get("/api/v1/runs/nonexistent/export/csv")
        assert resp.status_code == 404
