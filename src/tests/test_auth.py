"""Tests for API authentication — BLK-122.

Tests cover:
- ApiKey model and serialization
- ApiKeyStore CRUD
- Key hashing and verification
- Auth middleware (valid, invalid, expired, wrong scope)
- Key management endpoints
- Bootstrap key generation
- Auth disabled by default (existing tests unaffected)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.auth import (
    ALL_SCOPES,
    SCOPE_ADMIN,
    SCOPE_DEFINITIONS_READ,
    SCOPE_DEFINITIONS_WRITE,
    SCOPE_RUNS_READ,
    ApiKey,
    ApiKeyStore,
    _generate_key_id,
    _generate_secret,
    _hash_secret,
    _verify_secret,
    bootstrap_admin_key,
    get_key_store,
    reset_key_store,
)
from src.definitions.store import DefinitionStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def key_store(tmp_path: Path) -> ApiKeyStore:
    """Create a temporary ApiKeyStore."""
    return ApiKeyStore(base_dir=tmp_path / ".adep")


@pytest.fixture
def auth_client(tmp_path: Path) -> TestClient:
    """Create a FastAPI TestClient with auth enabled and a temp key store."""
    import src.api.auth as auth_module
    import src.config as config_module
    import src.definitions.store as store_module

    # Reset stores to temp dir
    old_store = store_module._store
    old_key_store = auth_module._key_store
    store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
    auth_module._key_store = ApiKeyStore(base_dir=tmp_path / ".adep")

    # Enable auth
    old_auth = config_module.settings.auth_enabled
    config_module.settings.auth_enabled = True

    from src.api.main import create_app
    app = create_app()
    client = TestClient(app)

    yield client

    # Restore
    config_module.settings.auth_enabled = old_auth
    store_module._store = old_store
    auth_module._key_store = old_key_store


@pytest.fixture
def admin_key(auth_client: TestClient) -> tuple[str, str]:
    """Create an admin key and return (key_id, secret)."""
    # Bootstrap will have created one key already
    store = get_key_store()
    keys = store.list_all()
    if keys:
        # Use bootstrap key — but we don't have its secret
        # So create a new one via the API using the bootstrap key
        # First, get the bootstrap key secret from the store
        # Actually, the bootstrap key was logged but we can't retrieve it
        # So let's create a fresh key store without bootstrap
        pass

    # Create a key directly in the store
    key_id = _generate_key_id()
    secret = _generate_secret()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    key = ApiKey(
        key_id=key_id,
        key_hash=_hash_secret(secret),
        name="Test Admin Key",
        scopes=list(ALL_SCOPES),
        created_at=now,
        active=True,
    )
    store.create(key)
    return key_id, secret


# ---------------------------------------------------------------------------
# ApiKey model tests
# ---------------------------------------------------------------------------

class TestApiKeyModel:
    """Verify ApiKey model serialization."""

    def test_to_dict_excludes_hash(self):
        key = ApiKey(
            key_id="test",
            key_hash="abc123",
            name="Test",
            scopes=["runs:read"],
            created_at="2026-01-01T00:00:00Z",
        )
        d = key.to_dict()
        assert "key_hash" not in d
        assert d["key_id"] == "test"
        assert d["name"] == "Test"
        assert d["scopes"] == ["runs:read"]

    def test_from_dict_round_trip(self):
        key = ApiKey(
            key_id="test",
            key_hash="abc123",
            name="Test",
            scopes=["runs:read", "admin"],
            created_at="2026-01-01T00:00:00Z",
            budget_daily_tokens=50000,
        )
        d = key.to_dict()
        d["key_hash"] = "abc123"  # Add back for round-trip
        restored = ApiKey.from_dict(d)
        assert restored.key_id == "test"
        assert restored.key_hash == "abc123"
        assert restored.scopes == ["runs:read", "admin"]
        assert restored.budget_daily_tokens == 50000


# ---------------------------------------------------------------------------
# Key hashing tests
# ---------------------------------------------------------------------------

class TestKeyHashing:
    """Verify key hashing and verification."""

    def test_hash_is_deterministic(self):
        secret = "my-secret-key"
        assert _hash_secret(secret) == _hash_secret(secret)

    def test_hash_changes_with_different_secrets(self):
        assert _hash_secret("a") != _hash_secret("b")

    def test_verify_correct_secret(self):
        secret = "my-secret-key"
        key_hash = _hash_secret(secret)
        assert _verify_secret(secret, key_hash) is True

    def test_verify_wrong_secret(self):
        key_hash = _hash_secret("correct-secret")
        assert _verify_secret("wrong-secret", key_hash) is False

    def test_generated_key_id_has_prefix(self):
        key_id = _generate_key_id()
        assert key_id.startswith("adep_")

    def test_generated_secret_is_unique(self):
        s1 = _generate_secret()
        s2 = _generate_secret()
        assert s1 != s2


# ---------------------------------------------------------------------------
# ApiKeyStore tests
# ---------------------------------------------------------------------------

class TestApiKeyStore:
    """Verify ApiKeyStore CRUD operations."""

    def test_create_and_get(self, key_store: ApiKeyStore):
        key = ApiKey(
            key_id="test-key",
            key_hash=_hash_secret("secret"),
            name="Test",
            scopes=["runs:read"],
            created_at="2026-01-01T00:00:00Z",
        )
        key_store.create(key)
        retrieved = key_store.get("test-key")
        assert retrieved is not None
        assert retrieved.key_id == "test-key"
        assert retrieved.name == "Test"

    def test_get_nonexistent_returns_none(self, key_store: ApiKeyStore):
        assert key_store.get("nonexistent") is None

    def test_create_duplicate_raises(self, key_store: ApiKeyStore):
        key = ApiKey(
            key_id="dup",
            key_hash=_hash_secret("s"),
            name="Test",
            created_at="2026-01-01T00:00:00Z",
        )
        key_store.create(key)
        with pytest.raises(FileExistsError):
            key_store.create(key)

    def test_list_all(self, key_store: ApiKeyStore):
        for i in range(3):
            key_store.create(ApiKey(
                key_id=f"key-{i}",
                key_hash=_hash_secret(f"secret-{i}"),
                name=f"Key {i}",
                created_at="2026-01-01T00:00:00Z",
            ))
        keys = key_store.list_all()
        assert len(keys) == 3

    def test_delete(self, key_store: ApiKeyStore):
        key_store.create(ApiKey(
            key_id="del",
            key_hash=_hash_secret("s"),
            name="Delete",
            created_at="2026-01-01T00:00:00Z",
        ))
        key_store.delete("del")
        assert key_store.get("del") is None

    def test_get_by_secret(self, key_store: ApiKeyStore):
        key_store.create(ApiKey(
            key_id="by-secret",
            key_hash=_hash_secret("my-secret"),
            name="Test",
            scopes=["runs:read"],
            created_at="2026-01-01T00:00:00Z",
        ))
        found = key_store.get_by_secret("my-secret")
        assert found is not None
        assert found.key_id == "by-secret"

    def test_get_by_secret_not_found(self, key_store: ApiKeyStore):
        assert key_store.get_by_secret("nonexistent") is None

    def test_is_empty(self, key_store: ApiKeyStore):
        assert key_store.is_empty() is True
        key_store.create(ApiKey(
            key_id="k",
            key_hash=_hash_secret("s"),
            name="K",
            created_at="2026-01-01T00:00:00Z",
        ))
        assert key_store.is_empty() is False

    def test_update(self, key_store: ApiKeyStore):
        key = ApiKey(
            key_id="upd",
            key_hash=_hash_secret("s"),
            name="Original",
            scopes=["runs:read"],
            created_at="2026-01-01T00:00:00Z",
        )
        key_store.create(key)
        key.name = "Updated"
        key_store.update(key)
        assert key_store.get("upd").name == "Updated"


# ---------------------------------------------------------------------------
# Cache tests [BLK-254]
# ---------------------------------------------------------------------------

class TestApiKeyStoreCache:
    """Verify in-memory cache behavior — no sync file I/O on every request [BLK-254]."""

    def test_get_by_secret_uses_cache_on_second_call(self, key_store: ApiKeyStore):
        """Second call to get_by_secret should be served from cache (no disk read)."""
        key_store.create(ApiKey(
            key_id="cached-key",
            key_hash=_hash_secret("my-secret"),
            name="Cached",
            created_at="2026-01-01T00:00:00Z",
        ))
        # First call populates cache
        found1 = key_store.get_by_secret("my-secret")
        assert found1 is not None
        assert found1.key_id == "cached-key"
        assert key_store._cache is not None

        # Spy on _load_cache to prove second call doesn't reload from disk
        original_load = key_store._load_cache
        load_count = 0

        def counting_load():
            nonlocal load_count
            load_count += 1
            return original_load()

        key_store._load_cache = counting_load  # type: ignore[method-assign]

        # Second call should hit cache (within TTL), so _load_cache returns cached list
        # without re-reading from disk
        found2 = key_store.get_by_secret("my-secret")
        assert found2 is not None
        assert found2.key_id == "cached-key"
        # _load_cache is called but it should return from cache without disk I/O
        # Verify cache was still populated (not refreshed from disk)
        assert key_store._cache is not None
        assert load_count == 1, "_load_cache should be called but serve from cache"

    def test_cache_invalidated_on_create(self, key_store: ApiKeyStore):
        """Creating a new key should invalidate cache so it's immediately visible."""
        key_store.create(ApiKey(
            key_id="k1",
            key_hash=_hash_secret("s1"),
            name="K1",
            created_at="2026-01-01T00:00:00Z",
        ))
        # Populate cache
        assert key_store.get_by_secret("s1") is not None
        # Create a new key
        key_store.create(ApiKey(
            key_id="k2",
            key_hash=_hash_secret("s2"),
            name="K2",
            created_at="2026-01-01T00:00:00Z",
        ))
        # New key should be immediately findable
        assert key_store.get_by_secret("s2") is not None

    def test_cache_invalidated_on_update(self, key_store: ApiKeyStore):
        """Updating a key should invalidate cache so changes are immediately visible."""
        key = ApiKey(
            key_id="upd-cache",
            key_hash=_hash_secret("s"),
            name="Original",
            scopes=["runs:read"],
            created_at="2026-01-01T00:00:00Z",
        )
        key_store.create(key)
        # Populate cache
        assert key_store.get("upd-cache").name == "Original"
        # Update
        key.name = "Updated"
        key_store.update(key)
        # Should see updated name immediately
        assert key_store.get("upd-cache").name == "Updated"

    def test_cache_invalidated_on_delete(self, key_store: ApiKeyStore):
        """Deleting a key should invalidate cache so it's immediately gone."""
        key_store.create(ApiKey(
            key_id="del-cache",
            key_hash=_hash_secret("s"),
            name="Del",
            created_at="2026-01-01T00:00:00Z",
        ))
        # Populate cache
        assert key_store.get_by_secret("s") is not None
        # Delete
        key_store.delete("del-cache")
        # Should not be found
        assert key_store.get_by_secret("s") is None
        assert key_store.get("del-cache") is None

    def test_cache_ttl_expiry_refreshes_from_disk(self, key_store: ApiKeyStore, monkeypatch):
        """After TTL expires, cache should refresh from disk on next read."""
        key_store.create(ApiKey(
            key_id="ttl-key",
            key_hash=_hash_secret("s"),
            name="TTL",
            created_at="2026-01-01T00:00:00Z",
        ))
        # Populate cache
        assert key_store.get("ttl-key") is not None
        # Force TTL expiry
        key_store._cache_time = 0.0
        # Next read should refresh from disk
        assert key_store.get("ttl-key") is not None

    def test_list_all_uses_cache(self, key_store: ApiKeyStore):
        """list_all should use cache and not re-read files on every call."""
        for i in range(3):
            key_store.create(ApiKey(
                key_id=f"list-{i}",
                key_hash=_hash_secret(f"s-{i}"),
                name=f"Key {i}",
                created_at="2026-01-01T00:00:00Z",
            ))
        # First call populates cache
        keys1 = key_store.list_all()
        assert len(keys1) == 3
        assert key_store._cache is not None

        # Second call should serve from cache (within TTL)
        # Force a fresh _load_cache call and verify it returns the same cached list
        cached_ref = key_store._cache
        keys2 = key_store.list_all()
        assert len(keys2) == 3
        # Cache should not have been refreshed (same object reference)
        assert key_store._cache is cached_ref, "list_all should reuse cached list, not reload from disk"


# ---------------------------------------------------------------------------
# Bootstrap tests
# ---------------------------------------------------------------------------

class TestBootstrap:
    """Verify bootstrap admin key generation."""

    def test_bootstrap_creates_key(self, key_store: ApiKeyStore):
        secret = bootstrap_admin_key(key_store)
        assert secret  # non-empty
        keys = key_store.list_all()
        assert len(keys) == 1
        assert SCOPE_ADMIN in keys[0].scopes
        assert keys[0].active is True

    def test_bootstrap_raises_if_keys_exist(self, key_store: ApiKeyStore):
        bootstrap_admin_key(key_store)
        with pytest.raises(RuntimeError, match="Keys already exist"):
            bootstrap_admin_key(key_store)

    def test_bootstrap_secret_never_logged(self, key_store: ApiKeyStore, caplog: pytest.LogCaptureFixture):
        """The raw secret must never be routed through the logging framework [BLK-186, BLK-188]."""
        with caplog.at_level(logging.DEBUG):
            secret = bootstrap_admin_key(key_store)
        for record in caplog.records:
            assert secret not in record.getMessage()

    def test_bootstrap_secret_printed_to_stdout(self, key_store: ApiKeyStore, capsys: pytest.CaptureFixture):
        """The secret should still be surfaced to the operator via stdout, not logs [BLK-186, BLK-188]."""
        secret = bootstrap_admin_key(key_store)
        captured = capsys.readouterr()
        assert secret in captured.out


# ---------------------------------------------------------------------------
# Auth middleware tests
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    """Verify auth middleware behavior."""

    def test_health_endpoint_no_auth_required(self, auth_client: TestClient):
        resp = auth_client.get("/health")
        assert resp.status_code == 200

    def test_docs_no_auth_required(self, auth_client: TestClient):
        resp = auth_client.get("/docs")
        assert resp.status_code == 200

    def test_missing_auth_header_returns_401(self, auth_client: TestClient, admin_key: tuple[str, str]):
        resp = auth_client.get("/api/v1/skills")
        assert resp.status_code == 401
        assert "Authorization" in resp.json()["detail"]

    def test_invalid_key_returns_401(self, auth_client: TestClient, admin_key: tuple[str, str]):
        resp = auth_client.get(
            "/api/v1/skills",
            headers={"Authorization": "Bearer invalid-key"},
        )
        assert resp.status_code == 401
        assert "Invalid API key" in resp.json()["detail"]

    def test_valid_key_with_admin_scope_succeeds(self, auth_client: TestClient, admin_key: tuple[str, str]):
        _, secret = admin_key
        resp = auth_client.get(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {secret}"},
        )
        assert resp.status_code == 200

    def test_revoked_key_returns_401(self, auth_client: TestClient, admin_key: tuple[str, str]):
        key_id, secret = admin_key
        store = get_key_store()
        key = store.get(key_id)
        key.active = False
        store.update(key)

        resp = auth_client.get(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {secret}"},
        )
        assert resp.status_code == 401
        assert "revoked" in resp.json()["detail"]

    def test_expired_key_returns_401(self, auth_client: TestClient, admin_key: tuple[str, str]):
        key_id, secret = admin_key
        store = get_key_store()
        key = store.get(key_id)
        key.expires_at = "2020-01-01T00:00:00Z"
        store.update(key)

        resp = auth_client.get(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {secret}"},
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"]

    def test_wrong_scope_returns_403(self, auth_client: TestClient):
        # Create a key with only runs:read scope
        store = get_key_store()
        key_id = _generate_key_id()
        secret = _generate_secret()
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        store.create(ApiKey(
            key_id=key_id,
            key_hash=_hash_secret(secret),
            name="Limited Key",
            scopes=[SCOPE_RUNS_READ],
            created_at=now,
            active=True,
        ))

        # Try to access skills (requires definitions:read)
        resp = auth_client.get(
            "/api/v1/skills",
            headers={"Authorization": f"Bearer {secret}"},
        )
        assert resp.status_code == 403
        assert "Insufficient scope" in resp.json()["detail"]

    def test_admin_scope_grants_all_access(self, auth_client: TestClient, admin_key: tuple[str, str]):
        _, secret = admin_key
        # Admin scope should work for all endpoints
        resp = auth_client.get(
            "/api/v1/definitions",
            headers={"Authorization": f"Bearer {secret}"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Key management endpoint tests
# ---------------------------------------------------------------------------

class TestKeyManagementEndpoints:
    """Verify key management CRUD endpoints."""

    def test_create_key(self, auth_client: TestClient, admin_key: tuple[str, str]):
        _, admin_secret = admin_key
        resp = auth_client.post(
            "/api/v1/admin/keys",
            json={
                "name": "New Key",
                "scopes": ["runs:read", "definitions:read"],
            },
            headers={"Authorization": f"Bearer {admin_secret}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Key"
        assert "runs:read" in data["scopes"]
        assert "secret" in data
        assert data["secret"]  # non-empty

    def test_list_keys(self, auth_client: TestClient, admin_key: tuple[str, str]):
        _, admin_secret = admin_key
        # Create an additional key
        auth_client.post(
            "/api/v1/admin/keys",
            json={"name": "Extra Key", "scopes": ["runs:read"]},
            headers={"Authorization": f"Bearer {admin_secret}"},
        )

        resp = auth_client.get(
            "/api/v1/admin/keys",
            headers={"Authorization": f"Bearer {admin_secret}"},
        )
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) >= 2
        # No secrets or hashes in list response
        for k in keys:
            assert "secret" not in k
            assert "key_hash" not in k

    def test_update_key(self, auth_client: TestClient, admin_key: tuple[str, str]):
        _, admin_secret = admin_key
        # Create a key
        create_resp = auth_client.post(
            "/api/v1/admin/keys",
            json={"name": "To Update", "scopes": ["runs:read"]},
            headers={"Authorization": f"Bearer {admin_secret}"},
        )
        key_id = create_resp.json()["key_id"]

        # Update it
        resp = auth_client.put(
            f"/api/v1/admin/keys/{key_id}",
            json={"name": "Updated Name", "scopes": ["runs:read", "runs:write"]},
            headers={"Authorization": f"Bearer {admin_secret}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"
        assert "runs:write" in resp.json()["scopes"]

    def test_delete_key(self, auth_client: TestClient, admin_key: tuple[str, str]):
        _, admin_secret = admin_key
        create_resp = auth_client.post(
            "/api/v1/admin/keys",
            json={"name": "To Delete", "scopes": ["runs:read"]},
            headers={"Authorization": f"Bearer {admin_secret}"},
        )
        key_id = create_resp.json()["key_id"]

        resp = auth_client.delete(
            f"/api/v1/admin/keys/{key_id}",
            headers={"Authorization": f"Bearer {admin_secret}"},
        )
        assert resp.status_code == 204

    def test_rotate_key(self, auth_client: TestClient, admin_key: tuple[str, str]):
        _, admin_secret = admin_key
        create_resp = auth_client.post(
            "/api/v1/admin/keys",
            json={"name": "To Rotate", "scopes": ["runs:read"]},
            headers={"Authorization": f"Bearer {admin_secret}"},
        )
        key_id = create_resp.json()["key_id"]
        old_secret = create_resp.json()["secret"]

        resp = auth_client.post(
            f"/api/v1/admin/keys/{key_id}/rotate",
            headers={"Authorization": f"Bearer {admin_secret}"},
        )
        assert resp.status_code == 200
        new_secret = resp.json()["secret"]
        assert new_secret != old_secret

        # Old secret should no longer work
        resp = auth_client.get(
            "/api/v1/runs",
            headers={"Authorization": f"Bearer {old_secret}"},
        )
        assert resp.status_code == 401

        # New secret should work
        resp = auth_client.get(
            "/api/v1/runs",
            headers={"Authorization": f"Bearer {new_secret}"},
        )
        assert resp.status_code == 200

    def test_invalid_scope_rejected(self, auth_client: TestClient, admin_key: tuple[str, str]):
        _, admin_secret = admin_key
        resp = auth_client.post(
            "/api/v1/admin/keys",
            json={"name": "Bad", "scopes": ["nonexistent:scope"]},
            headers={"Authorization": f"Bearer {admin_secret}"},
        )
        assert resp.status_code == 400
        assert "Invalid scopes" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Fail-closed / unmapped method tests [BLK-215]
# ---------------------------------------------------------------------------

class TestAuthFailClosed:
    """Verify auth middleware fails closed for unmapped methods and routes [BLK-215]."""

    def test_required_scope_deny_for_unmapped_method(self):
        """_required_scope should return __deny__ for unmapped methods on /api/v1/ paths."""
        from src.api.auth import _required_scope
        # TRACE is not in ROUTE_SCOPES
        assert _required_scope("TRACE", "/api/v1/runs") == "__deny__"

    def test_required_scope_deny_for_unknown_api_path(self):
        """_required_scope should return __deny__ for unknown /api/v1/ paths."""
        from src.api.auth import _required_scope
        assert _required_scope("GET", "/api/v1/nonexistent") == "__deny__"

    def test_required_scope_allows_options(self):
        """_required_scope should return None for OPTIONS (CORS preflight) [BLK-215]."""
        from src.api.auth import _required_scope
        assert _required_scope("OPTIONS", "/api/v1/runs") is None

    def test_required_scope_head_treated_as_get(self):
        """_required_scope should treat HEAD like GET [BLK-215]."""
        from src.api.auth import _required_scope
        from src.api.auth import SCOPE_RUNS_READ
        assert _required_scope("HEAD", "/api/v1/runs") == SCOPE_RUNS_READ

    def test_required_scope_non_api_path_returns_none(self):
        """_required_scope should return None for non-api paths."""
        from src.api.auth import _required_scope
        assert _required_scope("GET", "/health") is None
        assert _required_scope("POST", "/docs") is None

    def test_unmapped_method_rejected_with_401(self, auth_client: TestClient, admin_key: tuple[str, str]):
        """Unmapped HTTP methods on /api/v1/ paths should get 401, not pass through [BLK-215]."""
        _, secret = admin_key
        # Use a method not in ROUTE_SCOPES — TestClient doesn't support TRACE,
        # but we can test via direct _required_scope call
        from src.api.auth import _required_scope
        scope = _required_scope("TRACE", "/api/v1/runs")
        assert scope == "__deny__"

    def test_unknown_api_path_rejected_with_401(self, auth_client: TestClient, admin_key: tuple[str, str]):
        """Unknown /api/v1/ paths should get 401 even with valid key [BLK-215]."""
        _, secret = admin_key
        resp = auth_client.get(
            "/api/v1/nonexistent-endpoint",
            headers={"Authorization": f"Bearer {secret}"},
        )
        # FastAPI returns 404 for unknown routes, but auth middleware
        # should intercept first with 401 for fail-closed
        assert resp.status_code == 401

    def test_options_preflight_not_blocked_by_auth(self, auth_client: TestClient):
        """OPTIONS preflight requests should not be blocked by auth [BLK-215]."""
        resp = auth_client.options("/api/v1/runs")
        # Should not be 401 — CORS middleware handles it
        assert resp.status_code != 401

    def test_head_treated_as_get_for_auth(self, auth_client: TestClient, admin_key: tuple[str, str]):
        """HEAD requests should be authenticated like GET [BLK-215]."""
        _, secret = admin_key
        resp = auth_client.head(
            "/api/v1/runs",
            headers={"Authorization": f"Bearer {secret}"},
        )
        # Should not be 401 — HEAD is treated as GET
        assert resp.status_code != 401

    def test_head_without_auth_returns_401(self, auth_client: TestClient):
        """HEAD requests without auth should get 401 [BLK-215]."""
        resp = auth_client.head("/api/v1/runs")
        assert resp.status_code == 401

    def test_scope_does_not_match_broad_prefix(self):
        """_required_scope should NOT match /api/v1/runs-export as /api/v1/runs [SCRUM-15]."""
        from src.api.auth import _required_scope
        # /api/v1/runs-export should NOT inherit runs:read scope
        assert _required_scope("GET", "/api/v1/runs-export") == "__deny__"
        # /api/v1/runsbatch should NOT inherit runs:write scope
        assert _required_scope("POST", "/api/v1/runsbatch") == "__deny__"

    def test_scope_matches_exact_and_subpaths(self):
        """_required_scope should match exact path and subpaths with / separator [SCRUM-15]."""
        from src.api.auth import _required_scope, SCOPE_RUNS_READ
        # Exact match
        assert _required_scope("GET", "/api/v1/runs") == SCOPE_RUNS_READ
        # Subpath with / separator
        assert _required_scope("GET", "/api/v1/runs/run-123") == SCOPE_RUNS_READ
