"""REST endpoints for Skills [BLK-020]."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.definitions.store import get_store

router = APIRouter(tags=["skills"])


class ProbeStep(BaseModel):
    """A single probe step in a skill's probe order."""
    region_type: str = Field(description="Region type to probe")
    rationale: str = Field(description="Why this region is probed")


class InvariantSpec(BaseModel):
    """Declarative invariant specification (metadata only, not executable)."""
    name: str = Field(description="Invariant name")
    fields: list[str] = Field(default_factory=list, description="Field paths this invariant depends on")
    description: str = Field(default="", description="What this invariant checks")


class CreateSkillRequest(BaseModel):
    """Request body for creating a skill [BLK-121]."""
    id: str = Field(description="Unique skill identifier")
    name: str
    description: str = ""
    system_prompt: str = ""
    tool_preferences: dict[str, str] = Field(default_factory=dict)
    probe_order: list[ProbeStep] = Field(default_factory=list)
    invariants: list[InvariantSpec] = Field(default_factory=list)
    failure_actions: dict[str, str] = Field(default_factory=dict)
    known_failures: str = ""
    confidence_overrides: dict[str, float] = Field(default_factory=dict)
    semantic_checks_enabled: bool = False
    semantic_prompt: str | None = None
    tools: list[str] = Field(default_factory=list)


class UpdateSkillRequest(BaseModel):
    """Request body for updating a skill [BLK-121].

    All fields optional — only provided fields are updated.
    Fields not in the request are preserved.
    """
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    tool_preferences: dict[str, str] | None = None
    probe_order: list[ProbeStep] | None = None
    invariants: list[InvariantSpec] | None = None
    failure_actions: dict[str, str] | None = None
    known_failures: str | None = None
    confidence_overrides: dict[str, float] | None = None
    semantic_checks_enabled: bool | None = None
    semantic_prompt: str | None = None
    tools: list[str] | None = None


@router.get("/skills")
async def list_skills(
    q: str | None = None,
    tool: str | None = None,
    semantic: bool | None = None,
) -> list[dict[str, Any]]:
    """List all skills with optional search and filters [BLK-061].

    Args:
        q: Search query — case-insensitive substring match on name and description.
        tool: Filter by tool name (checks tools list).
        semantic: Filter by semantic_checks_enabled flag.
    """
    items = get_store().list_skills()

    if q:
        q_lower = q.lower()
        items = [
            s for s in items
            if q_lower in s.get("name", "").lower()
            or q_lower in s.get("description", "").lower()
        ]

    if tool:
        items = [s for s in items if tool in s.get("tools", [])]

    if semantic is not None:
        items = [s for s in items if s.get("semantic_checks_enabled") == semantic]

    return items


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str) -> dict[str, Any]:
    """Get a single skill by ID."""
    try:
        return get_store().get_skill(skill_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")


@router.post("/skills", status_code=status.HTTP_201_CREATED)
async def create_skill(req: CreateSkillRequest) -> dict[str, Any]:
    """Create a new skill."""
    data = req.model_dump()
    try:
        return get_store().create_skill(req.id, data)
    except FileExistsError:
        raise HTTPException(status_code=409, detail=f"Skill '{req.id}' already exists")


@router.put("/skills/{skill_id}")
async def update_skill(skill_id: str, req: UpdateSkillRequest) -> dict[str, Any]:
    """Update an existing skill."""
    store = get_store()
    try:
        existing = store.get_skill(skill_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    update_data = req.model_dump(exclude_none=True)
    existing.update(update_data)
    return store.update_skill(skill_id, existing)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(skill_id: str) -> Response:
    """Delete a skill."""
    try:
        get_store().delete_skill(skill_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")


class VerifySkillRequest(BaseModel):
    """Request body for Surrogate Verifier [BLK-070]."""
    trace: list[dict[str, Any]] = Field(default_factory=list, description="Execution trace entries")
    gap_report: dict[str, Any] = Field(default_factory=dict, description="Gap report from the run")
    extraction: dict[str, Any] = Field(default_factory=dict, description="Extracted field values")


@router.post("/skills/{skill_id}/verify")
async def verify_skill(skill_id: str, req: VerifySkillRequest) -> dict[str, Any]:
    """Run the Surrogate Verifier on a skill [BLK-070].

    Analyzes the skill's execution trace without ground truth and returns
    diagnoses, proposed tests, and skill patches.

    The skill is loaded from the store. The trace, gap_report, and extraction
    are provided by the caller (from a sample run).
    """
    from src.ai.surrogate_verifier import verify_skill as _verify

    store = get_store()
    try:
        skill = store.get_skill(skill_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    result = _verify(
        skill=skill,
        trace=req.trace,
        gap_report=req.gap_report,
        extraction=req.extraction,
    )

    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    return result
