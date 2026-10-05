"""PII redaction for logs and spans [BLK-130, BLK-083].

Since BLK-083 has not been implemented yet, this module provides a minimal
PII redaction utility that BLK-083 can later extend or replace.

Rules:
- Field **names** are safe to log (e.g. "invoice_number", "vendor")
- Field **values** are NOT safe — redact to "[REDACTED]"
- API keys, endpoints, and credentials are redacted
- Prompts are logged as a hash + token count, never full text
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

# Patterns that indicate sensitive data in log messages
_SENSITIVE_PATTERNS = [
    # API keys (common formats)
    re.compile(r"(?i)(api[_-]?key|secret|token|password|credential)\s*[=:]\s*\S+"),
    # Bearer tokens
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    # Connection strings with embedded credentials
    re.compile(r"(?i)://[^:\s]+:[^@\s]+@"),
]

# Field names that are safe to log (not values, just the names)
# No restriction needed — all field names are safe


def redact_value(value: Any) -> str:
    """Redact a field value for logging.

    Returns "[REDACTED]" for any non-None value. Field names are safe;
    values are not.
    """
    if value is None:
        return "None"
    return "[REDACTED]"


def redact_message(msg: str) -> str:
    """Redact sensitive patterns from a log message string."""
    redacted = msg
    for pattern in _SENSITIVE_PATTERNS:
        redacted = pattern.sub(
            lambda m: (
                m.group(0).split("=")[0].split(":")[0] + "=[REDACTED]"
                if "=" in m.group(0) or ":" in m.group(0)
                else "[REDACTED]"
            ),
            redacted,
        )
    return redacted


def hash_prompt(prompt: str, token_count: int | None = None) -> dict[str, Any]:
    """Hash a prompt for logging — never log full prompt text [BLK-130].

    Returns a dict with:
    - prompt_hash: SHA-256 hash (first 16 chars)
    - prompt_length: character length
    - token_count: if provided
    """
    h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    result: dict[str, Any] = {
        "prompt_hash": h,
        "prompt_length": len(prompt),
    }
    if token_count is not None:
        result["token_count"] = token_count
    return result


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Redact values in a dict while preserving keys.

    Useful for logging structured data where field names are safe but
    values may contain PII.
    """
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            redacted[key] = redact_dict(value)
        elif isinstance(value, list):
            redacted[key] = f"[{len(value)} items]"
        elif key in ("prompt", "system_prompt", "user_prompt"):
            redacted[key] = hash_prompt(str(value))
        elif key in ("api_key", "secret", "token", "password", "credential"):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, str) and len(value) > 200:
            redacted[key] = f"[{len(value)} chars]"
        else:
            redacted[key] = value
    return redacted
