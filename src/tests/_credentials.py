"""Shared credential detection for integration tests [SCRUM-512].

Provides ``has_real_credentials`` which returns ``True`` only when a real
Azure / OpenAI API key is present in the environment — placeholder values
such as ``your-api-key-here`` are rejected.
"""

from __future__ import annotations

import os
import re

_PLACEHOLDER_PATTERNS = re.compile(
    r"(your[-_]?|placeholder|changeme|dummy|example|test[-_]?key|xxx+|<.+>|YOUR.+HERE)",
    re.IGNORECASE,
)

_ENV_VARS = ("AZURE_API_KEY", "AZURE_OPENAI_API_KEY", "OPENAI_API_KEY")


def _is_placeholder(value: str) -> bool:
    """Return True if *value* looks like a placeholder, not a real key."""
    stripped = value.strip()
    if len(stripped) < 10:
        return True
    return bool(_PLACEHOLDER_PATTERNS.search(stripped))


def has_real_credentials() -> bool:
    """Return True only when a non-placeholder API key is set."""
    for var in _ENV_VARS:
        val = os.environ.get(var, "")
        if val and not _is_placeholder(val):
            return True
    return False
