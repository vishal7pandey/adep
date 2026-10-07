"""Regression tests for document store path containment (ADE-73, CodeQL py/path-injection).

The document id and page number reach file operations in ``DocumentStore`` and its routes. Every
operation must refuse an id or path that escapes ``documents/``, a bad id must be a clean 4xx (never an
unhandled ``ValueError``), and legitimate ids and the run-creation document guard keep working.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.documents.store import DocumentStore

_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16
# URL-encoded ids that reach the route as an invalid document id.
_BAD_URL_IDS = ["..%5Cescape", "..%2Fescape", "%2Fetc", "has%20space", "a.b"]


@pytest.fixture
def env(tmp_path: Path):
    """TestClient (auth off) with the document and definition stores under ``tmp_path/.adep``."""
    import src.api.auth as auth_module
    import src.config as config_module
    import src.definitions.store as definitions_module
    import src.documents.store as documents_module

    old = (
        definitions_module._store,
        documents_module._store,
        auth_module._key_store,
        config_module.settings.auth_enabled,
    )
    definitions_module._store = definitions_module.DefinitionStore(base_dir=tmp_path / ".adep")
    documents_module._store = DocumentStore(base_dir=tmp_path / ".adep")
    auth_module._key_store = auth_module.ApiKeyStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    from src.api.main import create_app

    yield TestClient(create_app()), documents_module._store
    (
        definitions_module._store,
        documents_module._store,
        auth_module._key_store,
        config_module.settings.auth_enabled,
    ) = old


def _make_doc(store: DocumentStore, doc_id: str = "doc1") -> Path:
    doc_dir = store.docs_dir / doc_id
    doc_dir.mkdir(parents=True)
    (doc_dir / "meta.json").write_text(f'{{"document_id": "{doc_id}", "page_paths": []}}')
    (doc_dir / "page_001.png").write_bytes(_PNG)
    (doc_dir / "thumbnail.jpg").write_bytes(b"jpeg-bytes")
    return doc_dir


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not permitted here")


class TestStoreOperations:
    @pytest.mark.parametrize("bad", ["../x", "..\\x", "/abs", "a/b", "", ".hidden", "a b"])
    def test_every_operation_rejects_an_invalid_id(self, env, bad: str):
        _, store = env
        with pytest.raises(ValueError):
            store.get_document(bad)
        with pytest.raises(ValueError):
            store.get_page_path(bad, 1)
        with pytest.raises(ValueError):
            store.get_thumbnail_path(bad)

    def test_legitimate_id_still_works(self, env):
        _, store = env
        _make_doc(store)
        assert store.get_document("doc1")["document_id"] == "doc1"
        assert store.get_page_path("doc1", 1).read_bytes() == _PNG
        assert store.get_thumbnail_path("doc1").read_bytes() == b"jpeg-bytes"

    def test_unknown_document_is_file_not_found(self, env):
        _, store = env
        with pytest.raises(FileNotFoundError):
            store.get_document("nope")
        with pytest.raises(FileNotFoundError):
            store.get_page_path("nope", 1)
        with pytest.raises(FileNotFoundError):
            store.get_thumbnail_path("nope")

    def test_missing_page_is_file_not_found(self, env):
        _, store = env
        _make_doc(store)
        with pytest.raises(FileNotFoundError):
            store.get_page_path("doc1", 9)

    def test_document_dir_symlinked_outside_the_store_is_refused(self, env, tmp_path: Path):
        _, store = env
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "meta.json").write_text('{"document_id": "leak"}')
        (outside / "page_001.png").write_bytes(b"outside")
        (outside / "thumbnail.jpg").write_bytes(b"outside")
        _symlink_or_skip(store.docs_dir / "doc1", outside)
        with pytest.raises(ValueError):
            store.get_document("doc1")
        with pytest.raises(ValueError):
            store.get_page_path("doc1", 1)
        with pytest.raises(ValueError):
            store.get_thumbnail_path("doc1")

    def test_page_file_symlinked_outside_the_store_is_refused(self, env, tmp_path: Path):
        _, store = env
        doc_dir = _make_doc(store)
        outside = tmp_path / "secret.png"
        outside.write_bytes(b"outside")
        _symlink_or_skip(doc_dir / "page_002.png", outside)
        with pytest.raises(ValueError):
            store.get_page_path("doc1", 2)

    def test_list_documents_still_lists(self, env):
        _, store = env
        _make_doc(store)
        assert [d["document_id"] for d in store.list_documents()] == ["doc1"]


class TestDocumentRoutes:
    @pytest.mark.parametrize("bad", _BAD_URL_IDS)
    def test_get_document_invalid_id_is_404(self, env, bad: str):
        client, _ = env
        assert client.get(f"/api/v1/documents/{bad}").status_code == 404

    @pytest.mark.parametrize("bad", _BAD_URL_IDS)
    def test_thumbnail_invalid_id_is_404(self, env, bad: str):
        client, _ = env
        assert client.get(f"/api/v1/documents/{bad}/thumbnail").status_code == 404

    @pytest.mark.parametrize("bad", _BAD_URL_IDS)
    def test_page_invalid_id_is_404(self, env, bad: str):
        client, _ = env
        assert client.get(f"/api/v1/documents/{bad}/page/1").status_code == 404

    @pytest.mark.parametrize("bad", _BAD_URL_IDS)
    def test_suggest_agent_invalid_id_is_404(self, env, bad: str):
        client, _ = env
        assert client.post(f"/api/v1/documents/{bad}/suggest-agent").status_code == 404

    def test_legitimate_document_routes_still_serve(self, env):
        client, store = env
        _make_doc(store)
        assert client.get("/api/v1/documents/doc1").json()["document_id"] == "doc1"
        thumb = client.get("/api/v1/documents/doc1/thumbnail")
        assert thumb.status_code == 200 and thumb.content == b"jpeg-bytes"
        page = client.get("/api/v1/documents/doc1/page/1")
        assert page.status_code == 200 and page.content == _PNG

    def test_thumbnail_outside_the_store_is_not_served(self, env, tmp_path: Path, monkeypatch):
        client, store = env
        secret = tmp_path / "secret.jpg"
        secret.write_bytes(b"outside-the-store")
        monkeypatch.setattr(store, "get_thumbnail_path", lambda doc_id: secret)
        resp = client.get("/api/v1/documents/doc1/thumbnail")
        assert resp.status_code == 404
        assert b"outside-the-store" not in resp.content


class TestEngineCallers:
    def test_page_image_path_for_invalid_id_is_none(self, env):
        from src.engine.tools import _get_page_image_path

        assert _get_page_image_path("../x", 1) is None


class TestRunCreationDocumentRoots:
    """The BLK-241 guard on POST /runs ``document_url`` (runs.py) keeps its behaviour."""

    def _seed_definition(self) -> None:
        import src.definitions.store as definitions_module

        definitions_module._store.create(
            "definitions",
            "def-test",
            {"id": "def-test", "name": "Test", "skill_id": "invoice", "template_ref": "invoice"},
        )

    def test_sibling_dir_sharing_the_adep_prefix_is_403(self, env, tmp_path: Path, monkeypatch):
        client, _ = env
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        self._seed_definition()
        evil = tmp_path / ".adep-evil"
        evil.mkdir()
        (evil / "x.png").write_bytes(_PNG)
        resp = client.post(
            "/api/v1/runs",
            json={"definition_id": "def-test", "document_url": str(evil / "x.png")},
        )
        assert resp.status_code == 403

    def test_sibling_dir_sharing_the_sample_data_prefix_is_403(
        self, env, tmp_path: Path, monkeypatch
    ):
        client, _ = env
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        self._seed_definition()
        evil = tmp_path / "sample-data-evil"
        evil.mkdir()
        (evil / "x.png").write_bytes(_PNG)
        resp = client.post(
            "/api/v1/runs",
            json={"definition_id": "def-test", "document_url": str(evil / "x.png")},
        )
        assert resp.status_code == 403

    def test_traversal_out_of_adep_is_403(self, env, tmp_path: Path, monkeypatch):
        client, _ = env
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        self._seed_definition()
        (tmp_path / ".adep").mkdir(exist_ok=True)
        resp = client.post(
            "/api/v1/runs",
            json={
                "definition_id": "def-test",
                "document_url": str(tmp_path / ".adep" / ".." / "x.png"),
            },
        )
        assert resp.status_code == 403

    def test_auto_route_with_a_file_path_is_a_clean_4xx(self, env, tmp_path: Path, monkeypatch):
        client, _ = env
        monkeypatch.chdir(tmp_path)
        resp = client.post(
            "/api/v1/runs",
            json={"definition_id": "auto", "document_url": "sample-data/does-not-exist.png"},
        )
        assert resp.status_code == 400
