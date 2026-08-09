"""REST endpoints for Agent Definitions [BLK-019]."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.definitions.base import AgentConfig, AgentDefinition
from src.definitions.store import get_store

router = APIRouter(tags=["definitions"])


class CreateDefinitionRequest(BaseModel):
    """Request body for creating a definition."""
    id: str = Field(description="Unique definition identifier")
    name: str
    skill_id: str
    template_id: str
    tool_names: list[str] = Field(default_factory=list)
    agent_config: AgentConfig = Field(default_factory=AgentConfig)
    system_prompt: str | None = None
    version: str = "1.0.0"
    task_type: str = "extraction"


class UpdateDefinitionRequest(BaseModel):
    """Request body for updating a definition."""
    name: str | None = None
    skill_id: str | None = None
    template_id: str | None = None
    tool_names: list[str] | None = None
    agent_config: AgentConfig | None = None
    system_prompt: str | None = None
    version: str | None = None
    task_type: str | None = None


@router.get("/definitions")
async def list_definitions(
    q: str | None = None,
    skill: str | None = None,
    template: str | None = None,
) -> list[dict[str, Any]]:
    """List all agent definitions with optional search and filters [BLK-061].

    Args:
        q: Search query — case-insensitive substring match on name and description.
        skill: Filter by skill_ref.
        template: Filter by template_ref.
    """
    items = get_store().list_definitions()

    if q:
        q_lower = q.lower()
        items = [
            d for d in items
            if q_lower in d.get("name", "").lower()
            or q_lower in d.get("description", "").lower()
        ]

    if skill:
        items = [d for d in items if d.get("skill_id", d.get("skill_ref")) == skill]

    if template:
        items = [d for d in items if d.get("template_id", d.get("template_ref")) == template]

    return items


@router.get("/definitions/{definition_id}")
async def get_definition(definition_id: str) -> dict[str, Any]:
    """Get a single definition by ID."""
    try:
        return get_store().get_definition(definition_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Definition '{definition_id}' not found")


@router.post("/definitions", status_code=status.HTTP_201_CREATED)
async def create_definition(req: CreateDefinitionRequest) -> dict[str, Any]:
    """Create a new agent definition."""
    definition = AgentDefinition(
        id=req.id,
        name=req.name,
        skill_id=req.skill_id,
        template_id=req.template_id,
        tool_names=req.tool_names,
        agent_config=req.agent_config,
        system_prompt=req.system_prompt,
        version=req.version,
        task_type=req.task_type,
    )
    try:
        return get_store().create_definition(definition)
    except FileExistsError:
        raise HTTPException(status_code=409, detail=f"Definition '{req.id}' already exists")


@router.put("/definitions/{definition_id}")
async def update_definition(definition_id: str, req: UpdateDefinitionRequest) -> dict[str, Any]:
    """Update an existing definition."""
    store = get_store()
    try:
        existing = store.get_definition(definition_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Definition '{definition_id}' not found")

    update_data = req.model_dump(exclude_none=True)
    existing.update(update_data)
    return store.update_definition(definition_id, existing)


@router.delete("/definitions/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_definition(definition_id: str) -> Response:
    """Delete a definition."""
    try:
        get_store().delete_definition(definition_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Definition '{definition_id}' not found")
