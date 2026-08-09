"""AgentDefinition model — serializable composition of bricks [§3.4, BLK-016].

An AgentDefinition is the "blueprint" that users compose through the UI.
It references a Skill, a Template, a set of tools, and agent config.
The Run Engine instantiates it into a live extraction run.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Runtime configuration for an agent definition.

    Attributes:
        max_cycles_per_field: Override for per-field cycle cap [§2.6].
        max_cycles_per_document: Override for per-document cycle cap [§2.6].
        confidence_threshold: Override for default confidence threshold.
    """

    max_cycles_per_field: int | None = None
    max_cycles_per_document: int | None = None
    confidence_threshold: float | None = None


class AgentDefinition(BaseModel):
    """Serializable composition of skill + template + tools + config [§3.4].

    This is what users compose through the Definition Builder UI and what
    the Run Engine instantiates. Stored as JSON in ``.adep/definitions/``.

    Attributes:
        id: Unique identifier (e.g. "def-invoice-v1").
        name: Human-readable name.
        version: Semantic version string.
        skill_ref: Skill identifier (references a skill in the store).
        template_ref: Template identifier (references a template in the store).
        tool_names: List of tool names enabled for this definition.
        agent_config: Runtime overrides for cycle caps and thresholds.
        system_prompt: Optional override for the skill's system prompt.
    """

    id: str = Field(description="Unique definition identifier")
    name: str = Field(description="Human-readable name")
    version: str = Field(default="1.0.0", description="Semantic version")
    skill_id: str = Field(description="Skill ID to use", alias="skill_ref")
    template_id: str = Field(description="Template ID to use", alias="template_ref")
    tool_names: list[str] = Field(
        default_factory=list,
        description="List of enabled tool names",
    )
    agent_config: AgentConfig = Field(
        default_factory=AgentConfig,
        description="Runtime config overrides",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Optional override for skill's system prompt",
    )
    task_type: str = Field(
        default="extraction",
        description="Task type for this definition (extraction, graph_extraction, etc.)",
    )

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}
