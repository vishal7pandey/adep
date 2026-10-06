"""API authentication — API keys, middleware, scope enforcement [BLK-122].

Provides:
- ApiKey model (stored hashed, never plaintext)
- ApiKeyStore (file-based, under .adep/api_keys/)
- Auth middleware (Bearer token validation)
- Scope definitions and route-to-scope mapping
- Bootstrap key generation on first boot with auth enabled
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import calendar
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scope definitions
# ---------------------------------------------------------------------------

SCOPE_RUNS_READ = "runs:read"
SCOPE_RUNS_WRITE = "runs:write"
SCOPE_DEFINITIONS_READ = "definitions:read"
SCOPE_DEFINITIONS_WRITE = "definitions:write"
SCOPE_DOCUMENTS_READ = "documents:read"
SCOPE_DOCUMENTS_WRITE = "documents:write"
SCOPE_ADMIN = "admin"

ALL_SCOPES = [
    SCOPE_RUNS_READ,
    SCOPE_RUNS_WRITE,
    SCOPE_DEFINITIONS_READ,
    SCOPE_DEFINITIONS_WRITE,
    SCOPE_DOCUMENTS_READ,
    SCOPE_DOCUMENTS_WRITE,
    SCOPE_ADMIN,
]

# Routes that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/openapi.json",
    "/api/v1/health",
    "/api/v1/locales",
}

# Route prefix → required scope mapping
# (method, path_prefix) → required_scope
ROUTE_SCOPES: list[tuple[str, str, str]] = [
    # Runs — all methods covered (BLK-215: added DELETE, PATCH)
    ("GET", "/api/v1/runs", SCOPE_RUNS_READ),
    ("POST", "/api/v1/runs", SCOPE_RUNS_WRITE),
    ("DELETE", "/api/v1/runs", SCOPE_RUNS_WRITE),
    ("PATCH", "/api/v1/runs", SCOPE_RUNS_WRITE),
    # Definitions
    ("GET", "/api/v1/definitions", SCOPE_DEFINITIONS_READ),
    ("POST", "/api/v1/definitions", SCOPE_DEFINITIONS_WRITE),
    ("PUT", "/api/v1/definitions", SCOPE_DEFINITIONS_WRITE),
    ("DELETE", "/api/v1/definitions", SCOPE_DEFINITIONS_WRITE),
    # Skills
    ("GET", "/api/v1/skills", SCOPE_DEFINITIONS_READ),
    ("POST", "/api/v1/skills", SCOPE_DEFINITIONS_WRITE),
    ("PUT", "/api/v1/skills", SCOPE_DEFINITIONS_WRITE),
    ("DELETE", "/api/v1/skills", SCOPE_DEFINITIONS_WRITE),
    # Templates
    ("GET", "/api/v1/templates", SCOPE_DEFINITIONS_READ),
    ("POST", "/api/v1/templates", SCOPE_DEFINITIONS_WRITE),
    ("PUT", "/api/v1/templates", SCOPE_DEFINITIONS_WRITE),
    ("DELETE", "/api/v1/templates", SCOPE_DEFINITIONS_WRITE),
    # Documents
    ("GET", "/api/v1/documents", SCOPE_DOCUMENTS_READ),
    ("POST", "/api/v1/documents", SCOPE_DOCUMENTS_WRITE),
    # Admin (keys route is under /api/v1/admin/keys)
    ("GET", "/api/v1/admin", SCOPE_ADMIN),
    ("POST", "/api/v1/admin", SCOPE_ADMIN),
    ("PUT", "/api/v1/admin", SCOPE_ADMIN),
    ("DELETE", "/api/v1/admin", SCOPE_ADMIN),
    # Budget
    ("GET", "/api/v1/budget", SCOPE_ADMIN),
    # Webhooks — all methods covered (BLK-215: added PUT)
    ("GET", "/api/v1/webhooks", SCOPE_ADMIN),
    ("POST", "/api/v1/webhooks", SCOPE_ADMIN),
    ("PUT", "/api/v1/webhooks", SCOPE_ADMIN),
    ("DELETE", "/api/v1/webhooks", SCOPE_ADMIN),
]


def _required_scope(method: str, path: str) -> str | None:
    """Determine the required scope for a given method + path.

    Returns None if the path is a public endpoint (in PUBLIC_PATHS).
    Returns a sentinel "__deny__" scope for any /api/v1/ path that has no
    matching ROUTE_SCOPES entry — this makes the middleware fail closed
    for unknown routes instead of silently passing them through (BLK-215).

    HEAD is treated as GET (RFC 7231 §4.3.2).
    OPTIONS is allowed through (CORS preflight — no credentials sent).

    For non-api paths (e.g. /docs, /health), returns None to let FastAPI
    handle them normally.
    """
    # OPTIONS = CORS preflight — no credentials, let CORS middleware handle it
    if method == "OPTIONS":
        return None
    # HEAD is equivalent to GET for auth purposes (RFC 7231 §4.3.2)
    effective_method = "GET" if method == "HEAD" else method
    for req_method, prefix, scope in ROUTE_SCOPES:
        if effective_method != req_method:
            continue
        # Match on path segment boundaries, not raw startswith, so that
        # a scope for "/api/v1/runs" does NOT match "/api/v1/runs-export"
        # or "/api/v1/runsbatch" [SCRUM-15].
        if path == prefix or path.startswith(prefix + "/"):
            return scope
    # Fail closed: any /api/v1/ path without a matching scope entry is denied
    if path.startswith("/api/v1/"):
        return "__deny__"
    return None


# ---------------------------------------------------------------------------
# API Key model
# ---------------------------------------------------------------------------


@dataclass
class ApiKey:
    """An API key with scopes and optional per-key budgets [BLK-122].

    The raw secret is NEVER stored — only a SHA-256 hash.
    The key_id is a public identifier; the secret is presented once at creation.
    """

    key_id: str
    key_hash: str
    name: str
    scopes: list[str] = field(default_factory=list)
    created_at: str = ""
    last_used_at: str | None = None
    expires_at: str | None = None
    active: bool = True
    budget_daily_tokens: int | None = None
    budget_daily_cost_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Never expose hash in API responses
        d.pop("key_hash", None)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApiKey:
        return cls(
            key_id=data["key_id"],
            key_hash=data["key_hash"],
            name=data.get("name", ""),
            scopes=data.get("scopes", []),
            created_at=data.get("created_at", ""),
            last_used_at=data.get("last_used_at"),
            expires_at=data.get("expires_at"),
            active=data.get("active", True),
            budget_daily_tokens=data.get("budget_daily_tokens"),
            budget_daily_cost_usd=data.get("budget_daily_cost_usd"),
        )


# ---------------------------------------------------------------------------
# Key hashing (SHA-256 with constant-time comparison)
# ---------------------------------------------------------------------------


def _hash_secret(secret: str) -> str:
    """Hash a raw secret using SHA-256."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _verify_secret(secret: str, key_hash: str) -> bool:
    """Verify a secret against a hash using constant-time comparison."""
    return hmac.compare_digest(_hash_secret(secret), key_hash)


def _generate_key_id() -> str:
    """Generate a public key identifier."""
    return f"adep_{secrets.token_hex(8)}"


def _generate_secret() -> str:
    """Generate a cryptographically secure secret."""
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# API Key Store
# ---------------------------------------------------------------------------


class ApiKeyStore:
    """File-based store for API keys under .adep/api_keys/ [BLK-122].

    BLK-254: An in-memory cache with TTL avoids sync file I/O on every request.
    The cache is invalidated on any write (create/update/delete) and refreshes
    lazily after the TTL expires.
    """

    _CACHE_TTL_SECONDS: float = 30.0

    def __init__(self, base_dir: str | Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path.cwd() / ".adep"
        self.base_dir = Path(base_dir) / "api_keys"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._cache: list[ApiKey] | None = None
        self._cache_time: float = 0.0

    def _path_for(self, key_id: str) -> Path:
        return self.base_dir / f"{key_id}.json"

    def _invalidate_cache(self) -> None:
        """Drop the in-memory cache so the next read refreshes from disk."""
        self._cache = None
        self._cache_time = 0.0

    def _load_cache(self) -> list[ApiKey]:
        """Return cached keys, refreshing from disk if stale or empty."""
        now = time.monotonic()
        if self._cache is not None and (now - self._cache_time) < self._CACHE_TTL_SECONDS:
            return self._cache
        keys: list[ApiKey] = []
        for json_file in self.base_dir.glob("*.json"):
            data = json.loads(json_file.read_text(encoding="utf-8"))
            keys.append(ApiKey.from_dict(data))
        self._cache = keys
        self._cache_time = now
        return keys

    def create(self, key: ApiKey) -> ApiKey:
        """Create a new API key. Fails if it already exists."""
        path = self._path_for(key.key_id)
        if path.exists():
            raise FileExistsError(f"API key '{key.key_id}' already exists")
        path.write_text(json.dumps(asdict(key), indent=2), encoding="utf-8")
        self._invalidate_cache()
        logger.info("Created API key: %s", key.key_id)
        return key

    def get(self, key_id: str) -> ApiKey | None:
        """Get an API key by ID. Returns None if not found."""
        for key in self._load_cache():
            if key.key_id == key_id:
                return key
        return None

    def get_by_secret(self, secret: str) -> ApiKey | None:
        """Look up an API key by its raw secret.

        BLK-254: Uses in-memory cache instead of reading files on every call.
        Iterates cached keys and verifies the secret against each hash.
        This is O(n) but n is small (typically < 10 keys) and all in-memory.
        """
        for key in self._load_cache():
            if _verify_secret(secret, key.key_hash):
                return key
        return None

    def list_all(self) -> list[ApiKey]:
        """List all API keys."""
        return sorted(self._load_cache(), key=lambda k: k.key_id)

    def update(self, key: ApiKey) -> ApiKey:
        """Update an existing API key."""
        path = self._path_for(key.key_id)
        if not path.exists():
            raise FileNotFoundError(f"API key '{key.key_id}' not found")
        path.write_text(json.dumps(asdict(key), indent=2), encoding="utf-8")
        self._invalidate_cache()
        return key

    def delete(self, key_id: str) -> None:
        """Delete an API key."""
        # key_id comes from the request URL: resolve the file and require it to stay inside
        # the key directory before it is probed or removed (CodeQL py/path-injection).
        base = os.path.realpath(self.base_dir)
        path = os.path.realpath(os.path.join(base, f"{key_id}.json"))
        if not path.startswith(base + os.sep):
            raise FileNotFoundError(f"API key '{key_id}' not found")
        if not os.path.exists(path):
            raise FileNotFoundError(f"API key '{key_id}' not found")
        os.unlink(path)
        self._invalidate_cache()

    def is_empty(self) -> bool:
        """Check if no keys exist."""
        return len(self._load_cache()) == 0


# ---------------------------------------------------------------------------
# Singleton store
# ---------------------------------------------------------------------------

_key_store: ApiKeyStore | None = None


def get_key_store() -> ApiKeyStore:
    """Get the singleton ApiKeyStore instance."""
    global _key_store
    if _key_store is None:
        _key_store = ApiKeyStore()
    return _key_store


def reset_key_store(base_dir: str | Path | None = None) -> ApiKeyStore:
    """Reset the singleton store (for testing)."""
    global _key_store
    _key_store = ApiKeyStore(base_dir=base_dir)
    return _key_store


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


def bootstrap_admin_key(store: ApiKeyStore) -> str:
    """Create a bootstrap admin key if no keys exist.

    Returns the raw secret (shown once). The secret is never passed through
    the logging framework — logs may be persisted, shipped to aggregators,
    or otherwise retained beyond the operator's console session [BLK-186,
    BLK-188]. Instead, it is printed directly to stdout as a one-time
    banner; only non-sensitive metadata (key_id) is logged.
    """
    if not store.is_empty():
        raise RuntimeError("Keys already exist — cannot bootstrap")

    key_id = _generate_key_id()
    secret = _generate_secret()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    key = ApiKey(
        key_id=key_id,
        key_hash=_hash_secret(secret),
        name="Bootstrap Admin Key",
        scopes=list(ALL_SCOPES),
        created_at=now,
        active=True,
    )
    store.create(key)

    logger.warning(
        "Bootstrap admin key created (key_id: %s) — the secret was printed "
        "to stdout once and is not recoverable from logs.",
        key_id,
    )
    print(
        "\n"
        "==================== BOOTSTRAP ADMIN KEY ====================\n"
        f"  Key ID:  {key_id}\n"
        f"  Secret:  {secret}\n"
        "This secret is shown ONLY ONCE and is never written to logs.\n"
        "Store it securely now — it cannot be recovered later.\n"
        "===============================================================\n",
        flush=True,
    )
    return secret


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------


def install_auth_middleware(app: FastAPI) -> None:
    """Install the auth middleware on the FastAPI app [BLK-122].

    Only active when settings.auth_enabled is True.
    """
    from src.config import settings

    if not settings.auth_enabled:
        return

    # Bootstrap if no keys exist
    store = get_key_store()
    if store.is_empty():
        bootstrap_admin_key(store)

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path

        # Public paths — no auth required
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # Check if auth is enabled
        if not settings.auth_enabled:
            return await call_next(request)

        # Determine required scope
        required_scope = _required_scope(request.method, path)
        if required_scope is None:
            # Public path or non-api path — no auth required
            return await call_next(request)
        if required_scope == "__deny__":
            # BLK-215: fail closed for any /api/v1/ path without a matching scope
            logger.warning("Auth fail-closed: no scope entry for %s %s", request.method, path)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": f"Authentication required for {request.method} {path}"},
            )

        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Missing or invalid Authorization header. Expected: Bearer <key>"
                },
            )

        secret = auth_header[7:]  # Strip "Bearer "

        # Look up key
        store = get_key_store()
        key = store.get_by_secret(secret)
        if key is None:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"},
            )

        if not key.active:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "API key has been revoked"},
            )

        # Check expiry
        if key.expires_at is not None:
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if now > key.expires_at:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "API key has expired"},
                )

        # Check scope
        if required_scope not in key.scopes and SCOPE_ADMIN not in key.scopes:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": f"Insufficient scope. Required: {required_scope}"},
            )

        # Attach resolved key to request state
        request.state.api_key = key

        # Throttled last_used_at update (every 60 seconds)
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if key.last_used_at is None or _seconds_since(key.last_used_at) > 60:
            key.last_used_at = now_ts
            store.update(key)

        return await call_next(request)


def _seconds_since(timestamp: str) -> float:
    """Calculate seconds since a UTC timestamp string."""
    try:
        ts = time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        return time.time() - calendar.timegm(ts)
    except (ValueError, TypeError):
        return float("inf")
