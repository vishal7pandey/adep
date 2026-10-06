"""Regression tests for path containment (ADE-51 to ADE-54, CodeQL py/path-injection).

Each vulnerable route or function must refuse a path that escapes its intended directory, with the
project's normal error, and keep serving legitimate paths:

- ``ApiKeyStore.delete`` (``src/api/auth.py``): a key id must not reach files outside ``api_keys/``.
- ``POST /admin/benchmarks`` (``src/api/routes/benchmarks.py``): ``fixture_dir`` must stay inside
  the working directory.
- ``GET /documents/{id}/page/{n}`` (``src/api/routes/documents.py``): the page file served must lie
  inside the document store.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.auth import ApiKey, ApiKeyStore, _generate_key_id, _generate_secret, _hash_secret
from src.documents.store import DocumentStore

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_client(tmp_path: Path):
    """TestClient with auth off and every store pointed at ``tmp_path/.adep``."""
    import src.api.auth as auth_module
    import src.config as config_module
    import src.definitions.store as definitions_module
    import src.documents.store as documents_module

    old_definitions = definitions_module._store
    old_documents = documents_module._store
    old_keys = auth_module._key_store
    old_auth = config_module.settings.auth_enabled

    definitions_module._store = definitions_module.DefinitionStore(base_dir=tmp_path / ".adep")
    documents_module._store = DocumentStore(base_dir=tmp_path / ".adep")
    auth_module._key_store = ApiKeyStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    from src.api.main import create_app

    yield TestClient(create_app())

    config_module.settings.auth_enabled = old_auth
    definitions_module._store = old_definitions
    documents_module._store = old_documents
    auth_module._key_store = old_keys


def _make_key(store: ApiKeyStore) -> ApiKey:
    key = ApiKey(
        key_id=_generate_key_id(),
        key_hash=_hash_secret(_generate_secret()),
        name="containment test",
        scopes=["runs:read"],
        created_at="2026-10-06T00:00:00Z",
        active=True,
    )
    store.create(key)
    return key


# ---------------------------------------------------------------------------
# ADE-51 / ADE-52: ApiKeyStore.delete (auth.py:299 and :301)
# ---------------------------------------------------------------------------


class TestApiKeyDeleteContainment:
    def test_delete_rejects_relative_traversal_and_keeps_outside_file(self, tmp_path: Path):
        store = ApiKeyStore(base_dir=tmp_path / ".adep")
        outside = store.base_dir.parent / "victim.json"  # sibling of api_keys/
        outside.write_text("{}", encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            store.delete("../victim")

        assert outside.exists()

    def test_delete_rejects_absolute_key_id_and_keeps_outside_file(self, tmp_path: Path):
        store = ApiKeyStore(base_dir=tmp_path / ".adep")
        outside = tmp_path / "victim2.json"
        outside.write_text("{}", encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            store.delete(str(tmp_path / "victim2"))

        assert outside.exists()

    def test_delete_rejects_sibling_dir_sharing_the_key_dir_name_prefix(self, tmp_path: Path):
        store = ApiKeyStore(base_dir=tmp_path / ".adep")
        sibling = store.base_dir.parent / f"{store.base_dir.name}_evil"  # "api_keys_evil"
        sibling.mkdir()
        outside = sibling / "victim.json"
        outside.write_text("{}", encoding="utf-8")

        with pytest.raises(FileNotFoundError):
            store.delete(f"../{sibling.name}/victim")

        assert outside.exists()

    def test_delete_still_removes_a_legitimate_key(self, tmp_path: Path):
        store = ApiKeyStore(base_dir=tmp_path / ".adep")
        key = _make_key(store)

        store.delete(key.key_id)

        assert store.get(key.key_id) is None
        assert not (store.base_dir / f"{key.key_id}.json").exists()

    def test_delete_unknown_key_still_raises_file_not_found(self, tmp_path: Path):
        store = ApiKeyStore(base_dir=tmp_path / ".adep")

        with pytest.raises(FileNotFoundError):
            store.delete("key_does_not_exist")

    def test_delete_route_returns_404_for_traversal_id(
        self, app_client: TestClient, tmp_path: Path
    ):
        outside = tmp_path / ".adep" / "victim3.json"
        outside.write_text("{}", encoding="utf-8")

        resp = app_client.delete("/api/v1/admin/keys/..%5Cvictim3")
        assert resp.status_code == 404
        resp = app_client.delete("/api/v1/admin/keys/..%2Fvictim3")
        assert resp.status_code == 404

        assert outside.exists()


# ---------------------------------------------------------------------------
# ADE-53: POST /admin/benchmarks fixture_dir (benchmarks.py:60)
# ---------------------------------------------------------------------------


class _FakeReport:
    def to_dict(self) -> dict[str, Any]:
        return {"providers": []}


@pytest.fixture
def benchmark_env(app_client: TestClient, tmp_path: Path, monkeypatch):
    """Run from ``tmp_path/work`` with a spy for the benchmark runner."""
    import src.api.routes.benchmarks as benchmarks_module

    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)

    calls: list[str] = []

    def fake_run(fixture_dir: str, providers: list[str], baseline_provider: str | None = None):
        calls.append(fixture_dir)
        return _FakeReport()

    monkeypatch.setattr(benchmarks_module, "run_benchmark_suite", fake_run)
    monkeypatch.setattr(
        benchmarks_module, "save_benchmark_suite_report", lambda report: work / "saved.json"
    )
    return app_client, work, calls


class TestBenchmarkFixtureDirContainment:
    def test_relative_traversal_outside_cwd_is_rejected(self, benchmark_env, tmp_path: Path):
        client, _work, calls = benchmark_env
        outside = tmp_path / "outside"
        outside.mkdir()

        resp = client.post("/api/v1/admin/benchmarks", json={"fixture_dir": "../outside"})

        assert resp.status_code == 404
        assert calls == []

    def test_sibling_dir_sharing_the_cwd_name_prefix_is_rejected(
        self, benchmark_env, tmp_path: Path
    ):
        client, work, calls = benchmark_env
        sibling = tmp_path / f"{work.name}_evil"  # "work_evil" starts with "work"
        sibling.mkdir()

        resp = client.post("/api/v1/admin/benchmarks", json={"fixture_dir": f"../{sibling.name}"})

        assert resp.status_code == 404
        assert calls == []

    def test_the_cwd_itself_is_rejected(self, benchmark_env):
        client, _work, calls = benchmark_env

        resp = client.post("/api/v1/admin/benchmarks", json={"fixture_dir": "."})

        assert resp.status_code == 404
        assert calls == []

    def test_absolute_path_outside_cwd_is_rejected(self, benchmark_env, tmp_path: Path):
        client, _work, calls = benchmark_env
        outside = tmp_path / "outside_abs"
        outside.mkdir()

        resp = client.post("/api/v1/admin/benchmarks", json={"fixture_dir": str(outside)})

        assert resp.status_code == 404
        assert calls == []

    def test_relative_dir_inside_cwd_is_accepted(self, benchmark_env):
        client, work, calls = benchmark_env
        (work / "fixtures").mkdir()

        resp = client.post("/api/v1/admin/benchmarks", json={"fixture_dir": "fixtures"})

        assert resp.status_code == 200
        assert [Path(c).resolve() for c in calls] == [(work / "fixtures").resolve()]

    def test_absolute_dir_inside_cwd_is_accepted(self, benchmark_env):
        client, work, calls = benchmark_env
        inside = work / "abs_fixtures"
        inside.mkdir()

        resp = client.post("/api/v1/admin/benchmarks", json={"fixture_dir": str(inside)})

        assert resp.status_code == 200
        assert [Path(c).resolve() for c in calls] == [inside.resolve()]

    def test_missing_dir_inside_cwd_still_404(self, benchmark_env):
        client, _work, calls = benchmark_env

        resp = client.post("/api/v1/admin/benchmarks", json={"fixture_dir": "nope"})

        assert resp.status_code == 404
        assert calls == []


# ---------------------------------------------------------------------------
# ADE-54: GET /documents/{id}/page/{n} (documents.py:115)
# ---------------------------------------------------------------------------


_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16


class TestDocumentPageContainment:
    def test_legitimate_page_is_served(self, app_client: TestClient, tmp_path: Path):
        doc_dir = tmp_path / ".adep" / "documents" / "doc1"
        doc_dir.mkdir(parents=True)
        (doc_dir / "page_001.png").write_bytes(_PNG)

        resp = app_client.get("/api/v1/documents/doc1/page/1")

        assert resp.status_code == 200
        assert resp.content == _PNG

    def test_invalid_document_id_is_404_not_a_server_error(self, app_client: TestClient):
        resp = app_client.get("/api/v1/documents/..%5Cescape/page/1")

        assert resp.status_code == 404

    def test_page_file_outside_the_document_store_is_not_served(
        self, app_client: TestClient, tmp_path: Path, monkeypatch
    ):
        secret = tmp_path / "secret.png"
        secret.write_bytes(b"outside-the-store")
        import src.documents.store as documents_module

        store = documents_module.get_document_store()
        monkeypatch.setattr(store, "get_page_path", lambda doc_id, page: secret)

        resp = app_client.get("/api/v1/documents/doc1/page/1")

        assert resp.status_code == 404
        assert b"outside-the-store" not in resp.content
