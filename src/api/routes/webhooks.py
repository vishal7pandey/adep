"""REST endpoints for webhook management [BLK-064]."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.agent.webhooks import (
    WebhookConfig,
    WebhookEvent,
    WebhookStore,
    dispatch_webhook,
    get_webhook_store,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


class CreateWebhookRequest(BaseModel):
    """Request body for creating a webhook [BLK-064]."""

    id: str = Field(description="Unique webhook identifier")
    url: str = Field(description="Target URL for POST delivery")
    secret: str = Field(default="", description="HMAC signing secret (optional)")
    events: list[str] = Field(
        default_factory=lambda: list(WebhookEvent.ALL),
        description="Event types to subscribe to",
    )
    active: bool = True


class UpdateWebhookRequest(BaseModel):
    """Request body for updating a webhook [BLK-064]."""

    url: str | None = None
    secret: str | None = None
    events: list[str] | None = None
    active: bool | None = None


@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
async def create_webhook(req: CreateWebhookRequest) -> dict[str, Any]:
    """Create a new webhook [BLK-064]."""
    # Validate events
    for event in req.events:
        if event not in WebhookEvent.ALL:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event '{event}'. Valid events: {', '.join(sorted(WebhookEvent.ALL))}",
            )

    config = WebhookConfig(
        id=req.id,
        url=req.url,
        secret=req.secret,
        events=req.events,
        active=req.active,
    )
    try:
        return get_webhook_store().create(req.id, config)
    except FileExistsError:
        raise HTTPException(status_code=409, detail=f"Webhook '{req.id}' already exists")


@router.get("/webhooks")
async def list_webhooks() -> list[dict[str, Any]]:
    """List all webhooks [BLK-064]."""
    return get_webhook_store().list()


@router.get("/webhooks/{webhook_id}")
async def get_webhook(webhook_id: str) -> dict[str, Any]:
    """Get a webhook by ID [BLK-064]."""
    try:
        return get_webhook_store().get(webhook_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found")


@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, req: UpdateWebhookRequest) -> dict[str, Any]:
    """Update a webhook [BLK-064]."""
    update_data = req.model_dump(exclude_none=True)
    if "events" in update_data:
        for event in update_data["events"]:
            if event not in WebhookEvent.ALL:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid event '{event}'",
                )
    try:
        return get_webhook_store().update(webhook_id, update_data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found")


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(webhook_id: str) -> Response:
    """Delete a webhook [BLK-064]."""
    try:
        get_webhook_store().delete(webhook_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found")
    return Response(status_code=204)


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str) -> dict[str, Any]:
    """Send a test payload to a webhook [BLK-064]."""
    try:
        store = get_webhook_store()
        raw_data = store.get_raw(webhook_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found")

    config = WebhookConfig(
        id=raw_data["id"],
        url=raw_data["url"],
        secret=raw_data.get("secret", ""),
        events=raw_data.get("events", list(WebhookEvent.ALL)),
        active=raw_data.get("active", True),
    )

    test_payload = {
        "run_id": "test-run",
        "definition_id": "test-def",
        "status": "test",
        "message": "This is a test webhook delivery from ADEP",
    }

    import asyncio

    result = await asyncio.to_thread(dispatch_webhook, config, "run.completed", test_payload)
    return {"webhook_id": webhook_id, "delivery": result}
