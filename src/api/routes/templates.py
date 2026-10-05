"""REST endpoints for Templates [BLK-021]."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.definitions.store import get_store

router = APIRouter(tags=["templates"])


class TemplateFieldSchema(BaseModel):
    """A single field in a template schema."""

    name: str
    type: str
    description: str = ""
    required: bool = True
    confidence_threshold: float | None = None


class CreateTemplateRequest(BaseModel):
    """Request body for creating a template."""

    id: str = Field(description="Unique template identifier")
    name: str
    description: str = ""
    fields: list[TemplateFieldSchema] = Field(default_factory=list)


class UpdateTemplateRequest(BaseModel):
    """Request body for updating a template."""

    name: str | None = None
    description: str | None = None
    fields: list[TemplateFieldSchema] | None = None


class GenerateTemplateRequest(BaseModel):
    """Request body for AI template generation [BLK-067]."""

    description: str = Field(description="Natural language description of what to extract")


@router.get("/templates")
async def list_templates(
    q: str | None = None,
    field_type: str | None = None,
) -> list[dict[str, Any]]:
    """List all templates with optional search and filters [BLK-061].

    Args:
        q: Search query — case-insensitive substring match on name and description.
        field_type: Filter by field type (checks fields list).
    """
    items = get_store().list_templates()

    if q:
        q_lower = q.lower()
        items = [
            t
            for t in items
            if q_lower in t.get("name", "").lower() or q_lower in t.get("description", "").lower()
        ]

    if field_type:
        items = [t for t in items if any(f.get("type") == field_type for f in t.get("fields", []))]

    return items


@router.get("/templates/{template_id}")
async def get_template(template_id: str) -> dict[str, Any]:
    """Get a single template by ID."""
    try:
        return get_store().get_template(template_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_template(req: CreateTemplateRequest) -> dict[str, Any]:
    """Create a new template."""
    data = req.model_dump()
    try:
        return get_store().create_template(req.id, data)
    except FileExistsError:
        raise HTTPException(status_code=409, detail=f"Template '{req.id}' already exists")


@router.put("/templates/{template_id}")
async def update_template(template_id: str, req: UpdateTemplateRequest) -> dict[str, Any]:
    """Update an existing template."""
    store = get_store()
    try:
        existing = store.get_template(template_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    update_data = req.model_dump(exclude_none=True)
    existing.update(update_data)
    return store.update_template(template_id, existing)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: str) -> Response:
    """Delete a template."""
    try:
        get_store().delete_template(template_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")


@router.post("/templates/generate")
async def generate_template(req: GenerateTemplateRequest) -> dict[str, Any]:
    """Generate a template schema from a natural language description [BLK-067].

    Uses an LLM to convert the description into a structured template with
    field names, types, required flags, and confidence thresholds. The
    generated template is returned for user review — not auto-saved.
    """
    from src.ai.template_composer import generate_template as _generate

    result = _generate(req.description)

    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    return result
