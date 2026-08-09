"""Tool call guardrails — argument validation, allowlist, sandboxing [BLK-080].

The LLM proposes tool calls, but the execution layer must validate every
tool call before execution. Tools are on a strict allowlist, arguments
are validated against ToolSpec schemas, and dangerous operations are
sandboxed.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from src.tools.base import ToolRegistry, ToolResult

logger = logging.getLogger(__name__)

# Default per-tool rate limits
DEFAULT_MAX_CALLS_PER_CYCLE = 5
DEFAULT_MAX_CALLS_PER_RUN = 50


@dataclass
class ToolCallDecision:
    """Result of evaluating a proposed tool call [BLK-080].

    Attributes:
        allowed: Whether the tool call is allowed to proceed.
        tool_name: Name of the requested tool.
        args: Sanitized and validated arguments (if allowed).
        reason: Why the call was rejected (if not allowed).
        logged: Whether this decision was logged to the trace.
    """

    allowed: bool
    tool_name: str
    args: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    logged: bool = False


@dataclass
class ToolCallRateLimiter:
    """Per-tool rate limiter for a single run [BLK-080].

    Tracks call counts per tool and enforces max-calls-per-cycle and
    max-calls-per-run limits.

    Attributes:
        _call_counts: Maps tool name -> total call count.
        _cycle_counts: Maps tool name -> current cycle call count.
        max_per_cycle: Max calls per tool per cycle.
        max_per_run: Max calls per tool per run.
    """

    max_per_cycle: int = DEFAULT_MAX_CALLS_PER_CYCLE
    max_per_run: int = DEFAULT_MAX_CALLS_PER_RUN
    _call_counts: dict[str, int] = field(default_factory=dict)
    _cycle_counts: dict[str, int] = field(default_factory=dict)

    def check(self, tool_name: str) -> tuple[bool, str]:
        """Check if a tool call is within rate limits.

        Returns:
            Tuple of (allowed, reason_if_denied).
        """
        run_count = self._call_counts.get(tool_name, 0)
        cycle_count = self._cycle_counts.get(tool_name, 0)

        if run_count >= self.max_per_run:
            return False, f"Tool '{tool_name}' exceeded max calls per run ({self.max_per_run})"
        if cycle_count >= self.max_per_cycle:
            return False, f"Tool '{tool_name}' exceeded max calls per cycle ({self.max_per_cycle})"
        return True, ""

    def record(self, tool_name: str) -> None:
        """Record a successful tool call."""
        self._call_counts[tool_name] = self._call_counts.get(tool_name, 0) + 1
        self._cycle_counts[tool_name] = self._cycle_counts.get(tool_name, 0) + 1

    def reset_cycle(self) -> None:
        """Reset per-cycle counters at the start of a new cycle."""
        self._cycle_counts.clear()


def sanitize_tool_args(args: dict[str, Any]) -> dict[str, Any]:
    """Sanitize tool call arguments [BLK-080].

    - Strips control characters and null bytes from string arguments
    - Removes shell metacharacters
    - Validates path arguments for traversal attempts

    Args:
        args: Raw tool arguments from LLM.

    Returns:
        Sanitized arguments dict.
    """
    sanitized: dict[str, Any] = {}

    for key, value in args.items():
        if isinstance(value, str):
            # Remove null bytes
            cleaned = value.replace("\x00", "")
            # Remove control characters
            cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
            # Strip shell metacharacters
            cleaned = re.sub(r"[;&|`$()]", "", cleaned)
            sanitized[key] = cleaned.strip()
        elif isinstance(value, dict):
            sanitized[key] = sanitize_tool_args(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_tool_args(item) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def check_path_traversal(path_str: str, allowed_base: str | None = None) -> bool:
    """Check if a path contains traversal attempts [BLK-080].

    Args:
        path_str: File path to check.
        allowed_base: If provided, path must resolve under this base directory.

    Returns:
        True if the path is safe, False if traversal detected.
    """
    # Check for explicit traversal patterns
    if ".." in path_str:
        logger.warning("Path traversal attempt detected: %s [BLK-080]", path_str)
        return False

    # Check for absolute paths that escape allowed base
    if allowed_base:
        try:
            base = Path(allowed_base).resolve()
            target = Path(path_str).resolve()
            if not str(target).startswith(str(base)):
                logger.warning("Path escapes allowed base: %s [BLK-080]", path_str)
                return False
        except Exception:
            return False

    return True


def validate_page_number(page: int, total_pages: int) -> bool:
    """Validate a page number against document page count [BLK-080].

    Args:
        page: Requested page number (0-indexed).
        total_pages: Total pages in the document.

    Returns:
        True if the page number is valid.
    """
    if page < 0 or page >= total_pages:
        logger.warning("Out-of-bounds page number: %d (total: %d) [BLK-080]", page, total_pages)
        return False
    return True


def evaluate_tool_call(
    tool_name: str,
    args: dict[str, Any],
    registry: ToolRegistry,
    rate_limiter: ToolCallRateLimiter | None = None,
    document_pages: int | None = None,
    allowed_base_dir: str | None = None,
) -> ToolCallDecision:
    """Evaluate a proposed tool call against all guardrails [BLK-080].

    Checks:
    1. Tool is in the registry (allowlist)
    2. Arguments are sanitized
    3. Arguments are valid against tool spec (if Pydantic schema)
    4. Path arguments are sandboxed
    5. Page numbers are in bounds
    6. Rate limits are not exceeded

    Args:
        tool_name: Name of the requested tool.
        args: Raw arguments from the LLM.
        registry: The tool registry (allowlist).
        rate_limiter: Optional rate limiter for the run.
        document_pages: Total pages in the document (for page validation).
        allowed_base_dir: Base directory for path sandboxing.

    Returns:
        ToolCallDecision indicating whether to proceed.
    """
    # 1. Tool allowlist check
    if tool_name not in registry.names():
        logger.warning("Rejected tool call: '%s' not in registry [BLK-080]", tool_name)
        return ToolCallDecision(
            allowed=False,
            tool_name=tool_name,
            reason=f"Tool '{tool_name}' is not registered",
            logged=True,
        )

    # 2. Sanitize arguments
    sanitized_args = sanitize_tool_args(args)

    # 3. Validate against tool spec schema (if available)
    spec, _ = registry.get(tool_name)
    arg_schema = spec.arg_schema

    if arg_schema is not None and isinstance(arg_schema, type) and issubclass(arg_schema, BaseModel):
        try:
            validated = arg_schema.model_validate(sanitized_args)
            sanitized_args = validated.model_dump()
        except ValidationError as e:
            logger.warning("Rejected tool call: invalid args for '%s': %s [BLK-080]", tool_name, e)
            return ToolCallDecision(
                allowed=False,
                tool_name=tool_name,
                reason=f"Invalid arguments: {e}",
                logged=True,
            )

    # 4. Path sandboxing — check any argument that looks like a file path
    for key, value in sanitized_args.items():
        if isinstance(value, str) and ("/" in value or "\\" in value):
            if not check_path_traversal(value, allowed_base_dir):
                return ToolCallDecision(
                    allowed=False,
                    tool_name=tool_name,
                    reason=f"Path traversal detected in argument '{key}'",
                    logged=True,
                )

    # 5. Page number validation
    if document_pages is not None:
        for key, value in sanitized_args.items():
            if "page" in key.lower() and isinstance(value, int):
                if not validate_page_number(value, document_pages):
                    return ToolCallDecision(
                        allowed=False,
                        tool_name=tool_name,
                        reason=f"Page {value} out of bounds (document has {document_pages} pages)",
                        logged=True,
                    )

    # 6. Rate limiting
    if rate_limiter is not None:
        allowed, reason = rate_limiter.check(tool_name)
        if not allowed:
            logger.warning("Rate limited tool call: %s [BLK-080]", reason)
            return ToolCallDecision(
                allowed=False,
                tool_name=tool_name,
                reason=reason,
                logged=True,
            )

    return ToolCallDecision(
        allowed=True,
        tool_name=tool_name,
        args=sanitized_args,
        logged=True,
    )


def safe_tool_call(
    tool_name: str,
    args: dict[str, Any],
    registry: ToolRegistry,
    rate_limiter: ToolCallRateLimiter | None = None,
    document_pages: int | None = None,
    allowed_base_dir: str | None = None,
) -> ToolResult:
    """Execute a tool call with all guardrails applied [BLK-080].

    This is the safe entry point for executing LLM-proposed tool calls.
    It validates the call, sanitizes arguments, and only executes if
    all guardrails pass.

    Args:
        tool_name: Name of the tool to call.
        args: Arguments from the LLM.
        registry: Tool registry (allowlist).
        rate_limiter: Optional rate limiter.
        document_pages: Total document pages for page validation.
        allowed_base_dir: Base directory for path sandboxing.

    Returns:
        ToolResult from the tool, or an error result if guardrails rejected the call.
    """
    decision = evaluate_tool_call(
        tool_name, args, registry, rate_limiter, document_pages, allowed_base_dir
    )

    if not decision.allowed:
        return ToolResult(
            ok=False,
            error=f"Tool call rejected: {decision.reason}",
            tool=tool_name,
        )

    # Record in rate limiter
    if rate_limiter is not None:
        rate_limiter.record(tool_name)

    # Execute
    return registry.call(tool_name, **decision.args)
