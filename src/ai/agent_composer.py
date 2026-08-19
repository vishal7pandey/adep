"""AI Agent Composer — generate full Agent Definition from natural language [BLK-069].

A meta-agent that takes a natural language request and produces a complete
Agent Definition by orchestrating:

1. Template Composer (BLK-067) → generates Pydantic template schema
2. Skill Composer (BLK-068) → generates skill playbook
3. Agent Composer (this module) → binds skill + template + tools + config

The result is a candidate AgentDefinition dict ready for review or storage.
Optionally saves the generated skill, template, and definition to the store.

Uses Azure OpenAI (GPT-5.4) via the Template Composer and Skill Composer.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src.ai.skill_composer import generate_skill
from src.ai.template_composer import generate_template
from src.providers.llm import invoke_llm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt — for the orchestrator LLM that decides the definition structure
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are an AI assistant that generates agent definition configurations from natural language descriptions.

Given a description of a document extraction task, produce a JSON object with the agent-level configuration:

{
  "name": "Human-readable definition name",
  "definition_id": "def-snake-case-id",
  "task_type": "extraction",
  "max_cycles_per_field": 5,
  "max_cycles_per_document": 20,
  "confidence_threshold": 0.85,
  "system_prompt_override": null
}

Rules:
- definition_id MUST be snake_case with "def-" prefix (e.g. "def-invoice", "def-custom-doc")
- task_type: "extraction" for standard extraction, "graph_extraction" for graph/P&ID diagrams
- max_cycles_per_field: 3-8 (default 5, higher for complex documents)
- max_cycles_per_document: 15-40 (default 20, higher for multi-page documents)
- confidence_threshold: 0.75-0.95 (default 0.85, higher for high-stakes fields)
- system_prompt_override: null (use skill's prompt) or a custom string
- Return ONLY the JSON, no markdown or explanation"""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _normalize_definition_id(raw_id: str) -> str:
    """Normalize a definition ID to def-snake_case."""
    s = raw_id.lower().strip()
    # Preserve hyphens but replace other non-alphanumeric with underscore
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s]+", "_", s)
    s = s.strip("_-")
    if not s.startswith("def-"):
        s = f"def-{s}"
    return s


def _validate_agent_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize agent config values."""
    config = {
        "max_cycles_per_field": 5,
        "max_cycles_per_document": 20,
        "confidence_threshold": 0.85,
        "use_pdf_fast_path": False,
    }
    if "max_cycles_per_field" in raw:
        try:
            val = int(raw["max_cycles_per_field"])
            if 1 <= val <= 20:
                config["max_cycles_per_field"] = val
        except (TypeError, ValueError):
            pass
    if "max_cycles_per_document" in raw:
        try:
            val = int(raw["max_cycles_per_document"])
            if 5 <= val <= 100:
                config["max_cycles_per_document"] = val
        except (TypeError, ValueError):
            pass
    if "confidence_threshold" in raw:
        try:
            val = float(raw["confidence_threshold"])
            if 0.0 <= val <= 1.0:
                config["confidence_threshold"] = val
        except (TypeError, ValueError):
            pass
    if "use_pdf_fast_path" in raw:
        config["use_pdf_fast_path"] = bool(raw["use_pdf_fast_path"])
    return config


def _derive_tool_names(skill: dict[str, Any], template: dict[str, Any]) -> list[str]:
    """Derive the tool set from skill tool_preferences and template field types.

    Always includes detect_layout and crop as baseline tools.
    """
    tools: set[str] = {"detect_layout", "crop"}

    # Add tools from skill tool_preferences
    for tool in skill.get("tool_preferences", {}).values():
        tool_lower = str(tool).lower().strip()
        if tool_lower and tool_lower not in ("detect_layout", "crop"):
            tools.add(tool_lower)

    # Add read_table if template has list fields (tables)
    for f in template.get("fields", []):
        if f.get("type") == "list":
            tools.add("read_table")
            break

    # Always include ocr and vlm as fallback tools
    tools.add("ocr")
    tools.add("vlm")

    return sorted(tools)


def _derive_confidence_threshold(skill: dict[str, Any], template: dict[str, Any]) -> float:
    """Derive a sensible default confidence threshold from skill and template."""
    overrides = skill.get("confidence_overrides", {})
    if overrides:
        values = list(overrides.values())
        if values:
            return min(values)  # Use the most lenient threshold as the document-level default

    # Check template field thresholds
    thresholds = [f.get("confidence_threshold", 0.8) for f in template.get("fields", [])]
    if thresholds:
        return min(thresholds)

    return 0.85


# ---------------------------------------------------------------------------
# Heuristic fallback (no LLM available)
# ---------------------------------------------------------------------------

def _heuristic_definition_config(description: str) -> dict[str, Any]:
    """Generate a basic agent config without an LLM call."""
    name = description.strip().split("\n")[0][:80] if description else "Custom Definition"
    def_id = _normalize_definition_id(
        "_".join(description.lower().split()[:3]) if description else "custom"
    )

    # Heuristics for complexity
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in ("multi-page", "multiple pages", "complex", "lease", "audit")):
        max_cycles_doc = 30
    else:
        max_cycles_doc = 20

    if any(kw in desc_lower for kw in ("graph", "pid", "p&id", "diagram")):
        task_type = "graph_extraction"
    else:
        task_type = "extraction"

    return {
        "name": name,
        "definition_id": def_id,
        "task_type": task_type,
        "max_cycles_per_field": 5,
        "max_cycles_per_document": max_cycles_doc,
        "confidence_threshold": 0.85,
        "system_prompt_override": None,
        "_heuristic": True,
    }


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgentComposerResult:
    """Result of the Agent Composer pipeline [BLK-069].

    Attributes:
        definition: The generated AgentDefinition dict.
        skill: The generated skill dict.
        template: The generated template dict.
        token_usage: Total token usage across all LLM calls.
        errors: List of non-fatal errors/warnings during generation.
    """
    definition: dict[str, Any] = field(default_factory=dict)
    skill: dict[str, Any] = field(default_factory=dict)
    template: dict[str, Any] = field(default_factory=dict)
    token_usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition": self.definition,
            "skill": self.skill,
            "template": self.template,
            "token_usage": self.token_usage,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_agent(
    description: str,
    *,
    sample_document_summary: str | None = None,
    save_to_store: bool = False,
) -> AgentComposerResult:
    """Generate a complete Agent Definition from natural language [BLK-069].

    Orchestrates:
    1. Template Composer → generates template schema
    2. Skill Composer → generates skill playbook
    3. Agent Composer → binds them into an AgentDefinition

    Args:
        description: Natural language description of the document type and
            what to extract (e.g. "Extract invoice number, date, vendor,
            line items, and totals from commercial invoices").
        sample_document_summary: Optional summary of a sample document.
        save_to_store: If True, saves generated skill, template, and
            definition to the DefinitionStore. Default is False (review only).

    Returns:
        AgentComposerResult with definition, skill, template, and metadata.
    """
    result = AgentComposerResult()

    if not description or not description.strip():
        result.errors.append("Description is required")
        return result

    # Step 1: Generate template schema via Template Composer
    template = generate_template(description)
    if template.get("error"):
        result.errors.append(f"Template Composer error: {template['error']}")

    # Accumulate token usage
    tu = template.pop("_token_usage", {})
    result.token_usage["input_tokens"] += tu.get("input_tokens", 0)
    result.token_usage["output_tokens"] += tu.get("output_tokens", 0)
    result.token_usage["total_tokens"] += tu.get("total_tokens", 0)

    # Extract field names for the skill composer
    sample_fields = [f["name"] for f in template.get("fields", []) if f.get("name")]

    # Step 2: Generate skill playbook via Skill Composer
    skill = generate_skill(
        description=description,
        sample_fields=sample_fields,
        sample_document_summary=sample_document_summary,
    )

    # Accumulate token usage
    tu = skill.pop("_token_usage", {})
    result.token_usage["input_tokens"] += tu.get("input_tokens", 0)
    result.token_usage["output_tokens"] += tu.get("output_tokens", 0)
    result.token_usage["total_tokens"] += tu.get("total_tokens", 0)

    # Step 3: Generate agent-level config via LLM
    config_response = invoke_llm(_SYSTEM_PROMPT, description, max_tokens=1000)
    if config_response.content:
        try:
            content = config_response.content.strip()
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > 0:
                raw_config = json.loads(content[start:end])
            else:
                raise ValueError("No JSON found")
        except (json.JSONDecodeError, ValueError):
            raw_config = _heuristic_definition_config(description)
    else:
        raw_config = _heuristic_definition_config(description)

    # Accumulate token usage from config LLM call
    result.token_usage["input_tokens"] += config_response.input_tokens
    result.token_usage["output_tokens"] += config_response.output_tokens
    result.token_usage["total_tokens"] += config_response.total_tokens

    # Step 4: Validate and bind everything together
    def_id = _normalize_definition_id(raw_config.get("definition_id", "def-custom"))
    def_name = raw_config.get("name", description.strip().split("\n")[0][:80])
    task_type = raw_config.get("task_type", "extraction")

    agent_config = _validate_agent_config({
        "max_cycles_per_field": raw_config.get("max_cycles_per_field", 5),
        "max_cycles_per_document": raw_config.get("max_cycles_per_document", 20),
        "confidence_threshold": raw_config.get("confidence_threshold",
                                                 _derive_confidence_threshold(skill, template)),
    })

    # Derive tool names from skill and template
    tool_names = _derive_tool_names(skill, template)

    # Use skill name as skill_id, template name as template_id
    skill_id = skill.get("name", "custom")
    template_id = template.get("name", "custom").lower().replace(" ", "_") if template.get("name") else "custom"

    # System prompt override
    system_prompt_override = raw_config.get("system_prompt_override")
    if system_prompt_override and not isinstance(system_prompt_override, str):
        system_prompt_override = None

    definition = {
        "id": def_id,
        "name": def_name,
        "version": "1.0.0",
        "skill_id": skill_id,
        "template_id": template_id,
        "tool_names": tool_names,
        "agent_config": agent_config,
        "system_prompt": system_prompt_override,
        "task_type": task_type,
    }

    result.definition = definition
    result.skill = skill
    result.template = template

    # Step 5: Optionally save to store
    if save_to_store:
        _save_to_store(result)

    return result


def _save_to_store(result: AgentComposerResult) -> None:
    """Save generated skill, template, and definition to the DefinitionStore."""
    from src.definitions.base import AgentConfig, AgentDefinition
    from src.definitions.store import get_store

    store = get_store()
    defn = result.definition
    skill = result.skill
    tmpl = result.template

    # Save skill
    try:
        skill_id = defn["skill_id"]
        store.create_skill(skill_id, skill)
        logger.info("Saved generated skill '%s' to store", skill_id)
    except FileExistsError:
        logger.warning("Skill '%s' already exists in store — skipping", skill_id)
        result.errors.append(f"Skill '{skill_id}' already exists in store")
    except Exception as e:
        result.errors.append(f"Failed to save skill: {e}")

    # Save template
    try:
        template_id = defn["template_id"]
        store.create_template(template_id, tmpl)
        logger.info("Saved generated template '%s' to store", template_id)
    except FileExistsError:
        logger.warning("Template '%s' already exists in store — skipping", template_id)
        result.errors.append(f"Template '{template_id}' already exists in store")
    except Exception as e:
        result.errors.append(f"Failed to save template: {e}")

    # Save definition
    try:
        config = defn.get("agent_config", {})
        agent_config = AgentConfig(
            max_cycles_per_field=config.get("max_cycles_per_field"),
            max_cycles_per_document=config.get("max_cycles_per_document"),
            confidence_threshold=config.get("confidence_threshold"),
            use_pdf_fast_path=config.get("use_pdf_fast_path", False),
        )
        definition = AgentDefinition(
            id=defn["id"],
            name=defn["name"],
            skill_id=defn["skill_id"],
            template_id=defn["template_id"],
            tool_names=defn.get("tool_names", []),
            agent_config=agent_config,
            system_prompt=defn.get("system_prompt"),
            version=defn.get("version", "1.0.0"),
            task_type=defn.get("task_type", "extraction"),
        )
        store.create_definition(definition)
        logger.info("Saved generated definition '%s' to store", defn["id"])
    except FileExistsError:
        logger.warning("Definition '%s' already exists in store — skipping", defn["id"])
        result.errors.append(f"Definition '{defn['id']}' already exists in store")
    except Exception as e:
        result.errors.append(f"Failed to save definition: {e}")
