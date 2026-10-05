"""API key management endpoints [BLK-122].

All endpoints require the `admin` scope.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.api.auth import (
    ALL_SCOPES,
    ApiKey,
    _generate_key_id,
    _generate_secret,
    _hash_secret,
    get_key_store,
)

router = APIRouter(tags=["api-keys"])


class CreateKeyRequest(BaseModel):
    """Request body for creating an API key."""

    name: str = Field(description="Human-readable label for the key")
    scopes: list[str] = Field(default_factory=list, description="Scopes granted to this key")
    expires_at: str | None = Field(default=None, description="ISO 8601 expiry timestamp")
    budget_daily_tokens: int | None = Field(default=None, description="Per-key daily token budget")
    budget_daily_cost_usd: float | None = Field(
        default=None, description="Per-key daily cost budget"
    )


class UpdateKeyRequest(BaseModel):
    """Request body for updating an API key."""

    name: str | None = None
    scopes: list[str] | None = None
    expires_at: str | None = None
    active: bool | None = None
    budget_daily_tokens: int | None = None
    budget_daily_cost_usd: float | None = None


class KeyResponse(BaseModel):
    """Response model for an API key (never includes the hash or secret)."""

    key_id: str
    name: str
    scopes: list[str]
    created_at: str
    last_used_at: str | None
    expires_at: str | None
    active: bool
    budget_daily_tokens: int | None
    budget_daily_cost_usd: float | None


class CreateKeyResponse(KeyResponse):
    """Response for key creation — includes the raw secret (shown once)."""

    secret: str = Field(description="Raw API key secret — shown only once")


@router.post("/admin/keys", status_code=status.HTTP_201_CREATED, response_model=CreateKeyResponse)
async def create_key(req: CreateKeyRequest) -> dict[str, Any]:
    """Create a new API key. Returns the raw secret ONCE."""
    # Validate scopes
    invalid = [s for s in req.scopes if s not in ALL_SCOPES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scopes: {invalid}. Valid scopes: {ALL_SCOPES}",
        )

    store = get_key_store()
    key_id = _generate_key_id()
    secret = _generate_secret()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    key = ApiKey(
        key_id=key_id,
        key_hash=_hash_secret(secret),
        name=req.name,
        scopes=req.scopes,
        created_at=now,
        expires_at=req.expires_at,
        active=True,
        budget_daily_tokens=req.budget_daily_tokens,
        budget_daily_cost_usd=req.budget_daily_cost_usd,
    )
    store.create(key)

    resp = key.to_dict()
    resp["secret"] = secret
    return resp


@router.get("/admin/keys", response_model=list[KeyResponse])
async def list_keys() -> list[dict[str, Any]]:
    """List all API keys. Never returns secrets or hashes."""
    store = get_key_store()
    return [key.to_dict() for key in store.list_all()]


@router.put("/admin/keys/{key_id}", response_model=KeyResponse)
async def update_key(key_id: str, req: UpdateKeyRequest) -> dict[str, Any]:
    """Update an existing API key."""
    store = get_key_store()
    key = store.get(key_id)
    if key is None:
        raise HTTPException(status_code=404, detail=f"Key '{key_id}' not found")

    if req.name is not None:
        key.name = req.name
    if req.scopes is not None:
        invalid = [s for s in req.scopes if s not in ALL_SCOPES]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scopes: {invalid}. Valid scopes: {ALL_SCOPES}",
            )
        key.scopes = req.scopes
    if req.expires_at is not None:
        key.expires_at = req.expires_at
    if req.active is not None:
        key.active = req.active
    if req.budget_daily_tokens is not None:
        key.budget_daily_tokens = req.budget_daily_tokens
    if req.budget_daily_cost_usd is not None:
        key.budget_daily_cost_usd = req.budget_daily_cost_usd

    store.update(key)
    return key.to_dict()


@router.delete("/admin/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(key_id: str) -> Response:
    """Revoke an API key by deleting it."""
    store = get_key_store()
    try:
        store.delete(key_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Key '{key_id}' not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/admin/keys/{key_id}/rotate", response_model=CreateKeyResponse)
async def rotate_key(key_id: str) -> dict[str, Any]:
    """Rotate an API key's secret. Returns the new raw secret ONCE."""
    store = get_key_store()
    key = store.get(key_id)
    if key is None:
        raise HTTPException(status_code=404, detail=f"Key '{key_id}' not found")

    new_secret = _generate_secret()
    key.key_hash = _hash_secret(new_secret)
    store.update(key)

    resp = key.to_dict()
    resp["secret"] = new_secret
    return resp
