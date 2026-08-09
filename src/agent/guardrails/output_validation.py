"""LLM output schema validation & sanitization [BLK-079].

The LLM is a perception engine — its output is untrusted input. No LLM
output reaches tool execution, state mutation, or user display without
passing through this validation layer.

Guardrails:
1. Schema validation via Pydantic
2. Field allowlist (unknown fields dropped + logged)
3. Type coercion safety
4. Output length limits
5. Instruction pattern sanitization
6. No raw LLM output in tool args
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 4096
MAX_OUTPUT_CHARS = MAX_OUTPUT_TOKENS * 4  # ~4 chars per token
MAX_RETRIES = 2

# Instruction-like patterns (shared with BLK-043 input defense)
INSTRUCTION_PATTERNS = [
    re.compile(r"ignore\s+(?:previous|all|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"treat\s+as\s+(?:compliant|approved|verified)", re.IGNORECASE),
    re.compile(r"you\s+are\s+(?:now|actually)\s+(?:an?\s+)?\w+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"do\s+not\s+(?:validate|check|verify)", re.IGNORECASE),
    re.compile(r"override\s+(?:the\s+)?(?:validator|validation|check)", re.IGNORECASE),
]


@dataclass
class ValidationResult:
    """Result of validating LLM output [BLK-079].

    Attributes:
        valid: Whether the output passed validation.
        data: The validated and sanitized data (if valid).
        errors: List of validation error messages.
        warnings: List of non-fatal warnings (e.g. dropped fields).
        retries: Number of retries attempted.
    """

    valid: bool
    data: Any = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    retries: int = 0


def truncate_output(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> tuple[str, bool]:
    """Truncate LLM output to a maximum character count [BLK-079].

    Args:
        text: Raw LLM output text.
        max_chars: Maximum allowed characters.

    Returns:
        Tuple of (truncated_text, was_truncated).
    """
    if len(text) <= max_chars:
        return text, False
    logger.warning("LLM output truncated from %d to %d chars [BLK-079]", len(text), max_chars)
    return text[:max_chars], True


def sanitize_instruction_patterns(text: str) -> tuple[str, list[str]]:
    """Detect and strip instruction-like patterns from LLM output [BLK-079].

    Args:
        text: LLM output text.

    Returns:
        Tuple of (sanitized_text, list_of_detected_patterns).
    """
    detected: list[str] = []
    sanitized = text

    for pattern in INSTRUCTION_PATTERNS:
        matches = pattern.findall(sanitized)
        if matches:
            detected.extend(matches)
            sanitized = pattern.sub("[REDACTED]", sanitized)

    if detected:
        logger.warning(
            "Instruction patterns detected in LLM output: %s [BLK-079]",
            detected,
        )

    return sanitized, detected


def parse_llm_json(raw_text: str) -> dict[str, Any] | None:
    """Parse LLM output as JSON, handling common formatting issues [BLK-079].

    LLMs often wrap JSON in markdown code blocks or add preamble text.
    This function extracts the JSON portion.

    Args:
        raw_text: Raw LLM output text.

    Returns:
        Parsed dict or None if parsing fails.
    """
    text = raw_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON object from surrounding text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


def validate_llm_output(
    raw_text: str,
    schema: type[BaseModel] | None = None,
    allow_extra: bool = False,
) -> ValidationResult:
    """Validate LLM output against a Pydantic schema [BLK-079].

    Pipeline:
    1. Truncate output to max length
    2. Sanitize instruction patterns
    3. Parse as JSON
    4. Validate against schema (if provided)
    5. Drop unknown fields (if not allow_extra)

    Args:
        raw_text: Raw LLM output text.
        schema: Optional Pydantic model to validate against.
        allow_extra: If False, unknown fields are dropped + logged.

    Returns:
        ValidationResult with validated data or errors.
    """
    warnings: list[str] = []

    # 1. Truncate
    text, was_truncated = truncate_output(raw_text)
    if was_truncated:
        warnings.append("Output was truncated to max length")

    # 2. Sanitize instruction patterns
    text, detected_patterns = sanitize_instruction_patterns(text)
    if detected_patterns:
        warnings.append(f"Instruction patterns stripped: {detected_patterns}")

    # 3. Parse JSON
    parsed = parse_llm_json(text)
    if parsed is None:
        return ValidationResult(
            valid=False,
            errors=["Failed to parse LLM output as JSON"],
            warnings=warnings,
        )

    # 4. Validate against schema
    if schema is not None:
        try:
            # 5. Drop unknown fields
            if not allow_extra:
                known_fields = set(schema.model_fields.keys())
                extra_fields = set(parsed.keys()) - known_fields
                if extra_fields:
                    warnings.append(f"Unknown fields dropped: {extra_fields}")
                    parsed = {k: v for k, v in parsed.items() if k in known_fields}

            validated = schema.model_validate(parsed)
            return ValidationResult(
                valid=True,
                data=validated,
                warnings=warnings,
            )
        except ValidationError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Schema validation failed: {e}"],
                warnings=warnings,
            )

    # No schema — return parsed JSON as-is
    return ValidationResult(valid=True, data=parsed, warnings=warnings)


def validate_with_retry(
    raw_text: str,
    schema: type[BaseModel] | None = None,
    retry_prompt: str = "Your previous response was invalid. Please return valid JSON matching the expected schema.",
    max_retries: int = MAX_RETRIES,
) -> ValidationResult:
    """Validate LLM output with retry support [BLK-079].

    On validation failure, returns a ValidationResult with a corrective
    prompt that the caller can send back to the LLM.

    Args:
        raw_text: Raw LLM output text.
        schema: Pydantic model to validate against.
        retry_prompt: Prompt to send on retry.
        max_retries: Maximum retry attempts.

    Returns:
        ValidationResult with retry count and corrective prompt if failed.
    """
    result = validate_llm_output(raw_text, schema)

    if result.valid:
        return result

    # Add retry prompt for the caller to use
    result.errors.append(f"Retry prompt: {retry_prompt}")
    return result


def sanitize_string_arg(value: str) -> str:
    """Sanitize a string argument from LLM output [BLK-079].

    Strips control characters, null bytes, and shell metacharacters.

    Args:
        value: Raw string value from LLM output.

    Returns:
        Sanitized string.
    """
    # Remove null bytes
    sanitized = value.replace("\x00", "")

    # Remove control characters (except newline, tab, carriage return)
    sanitized = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)

    # Strip shell metacharacters that could be dangerous if passed to subprocess
    sanitized = re.sub(r"[;&|`$()]", "", sanitized)

    return sanitized.strip()


def coerce_value(value: Any, target_type: str) -> tuple[Any, bool]:
    """Safely coerce a value to a target type [BLK-079].

    Args:
        value: The value to coerce.
        target_type: One of "str", "int", "float", "bool".

    Returns:
        Tuple of (coerced_value, success). If coercion fails, returns
        (None, False).
    """
    if target_type == "str":
        return str(value), True

    if target_type == "int":
        try:
            return int(value), True
        except (ValueError, TypeError):
            try:
                return int(float(value)), True
            except (ValueError, TypeError):
                return None, False

    if target_type == "float":
        try:
            return float(value), True
        except (ValueError, TypeError):
            return None, False

    if target_type == "bool":
        if isinstance(value, bool):
            return value, True
        if isinstance(value, str):
            lower = value.lower().strip()
            if lower in ("true", "yes", "1"):
                return True, True
            if lower in ("false", "no", "0"):
                return False, True
            return None, False
        if isinstance(value, (int, float)):
            return bool(value), True
        return None, False

    return None, False
