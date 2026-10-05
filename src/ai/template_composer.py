"""AI Template Composer — generate extraction schemas from NL [BLK-067].

Converts a natural language description of desired extraction output into
a Pydantic-based Template schema with field names, types, required flags,
confidence thresholds, and descriptions.

Uses Azure OpenAI (GPT-5.4) with a structured system prompt. Generated
schema is returned for user review — not auto-saved.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.providers.llm import invoke_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an AI assistant that generates document extraction template schemas from natural language descriptions.

Given a description of what fields to extract from a document, produce a JSON schema with this exact structure:

{
  "name": "Human-readable schema name",
  "description": "Brief description of what this template extracts",
  "fields": [
    {
      "name": "snake_case_field_name",
      "type": "string|float|int|date|boolean|list",
      "description": "What this field represents",
      "required": true,
      "threshold": 0.8,
      "sub_fields": []
    }
  ]
}

Rules:
- Field names MUST be snake_case (lowercase with underscores)
- Supported types: string, float, int, date, boolean, list
- For list types, include sub_fields for the items in the list
- Confidence thresholds: 0.85 for critical fields (amounts, IDs, dates), 0.8 for standard fields, 0.75 for optional fields
- Include 5-15 fields for a typical template
- Make field descriptions specific enough for an extraction agent to understand
- Return ONLY the JSON, no markdown or explanation"""

_SUPPORTED_TYPES = {"string", "float", "int", "date", "boolean", "list"}


def _normalize_field_name(name: str) -> str:
    """Normalize a field name to snake_case."""
    s = re.sub(r"[^\w\s]", "", name.lower().strip())
    s = re.sub(r"[\s]+", "_", s)
    s = s.strip("_")
    return s


def _validate_field(field: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a single field from LLM output."""
    name = _normalize_field_name(field.get("name", "unknown"))
    field_type = field.get("type", "string")
    if field_type not in _SUPPORTED_TYPES:
        field_type = "string"

    threshold = field.get("threshold")
    if (
        threshold is None
        or not isinstance(threshold, (int, float))
        or threshold < 0
        or threshold > 1
    ):
        # Default thresholds by type
        if field_type in ("float", "int"):
            threshold = 0.85
        elif field_type == "date":
            threshold = 0.85
        elif field_type == "boolean":
            threshold = 0.75
        else:
            threshold = 0.8

    result: dict[str, Any] = {
        "name": name,
        "type": field_type,
        "description": field.get("description", ""),
        "required": bool(field.get("required", True)),
        "confidence_threshold": float(threshold),
    }

    # Handle sub_fields for list types
    sub_fields = field.get("sub_fields", [])
    if sub_fields and field_type == "list":
        result["sub_fields"] = [_validate_field(sf) for sf in sub_fields if isinstance(sf, dict)]
    else:
        result["sub_fields"] = []

    return result


def generate_template(description: str) -> dict[str, Any]:
    """Generate a template schema from a natural language description [BLK-067].

    Args:
        description: Natural language description of what to extract.

    Returns:
        Generated template dict with name, description, and fields.
        Fields are validated: snake_case names, supported types, thresholds.
    """
    if not description or not description.strip():
        return {
            "name": "",
            "description": "",
            "fields": [],
            "error": "Description is required",
        }

    response = invoke_llm(_SYSTEM_PROMPT, description, max_tokens=3000)

    if not response.content:
        return {
            "name": "",
            "description": "",
            "fields": [],
            "error": "LLM call failed — check Azure API key and endpoint configuration",
        }

    # Parse JSON from LLM response
    content = response.content.strip()
    try:
        # Find JSON in response (LLM may wrap in markdown)
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == 0:
            return {
                "name": "",
                "description": "",
                "fields": [],
                "error": "LLM did not return valid JSON",
            }
        raw = json.loads(content[start:end])
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "name": "",
            "description": "",
            "fields": [],
            "error": f"Failed to parse LLM response: {e}",
        }

    # Validate and normalize
    fields = []
    for field in raw.get("fields", []):
        if isinstance(field, dict):
            fields.append(_validate_field(field))

    return {
        "name": raw.get("name", "Generated Template"),
        "description": raw.get("description", ""),
        "fields": fields,
        "_token_usage": {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "total_tokens": response.total_tokens,
        },
    }
