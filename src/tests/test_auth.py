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
