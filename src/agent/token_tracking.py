"""Token tracking utilities — cost calculation, LLM response wrapper [BLK-050, §15].

Provides:
- ``LLMResponse``: Wrapper around LLM response with content + token usage.
- ``calculate_cost``: Compute cost from token counts and pricing config.
- ``estimate_tokens``: Fallback token estimation using len/4 heuristic.
- ``record_token_usage``: Create a TokenUsage entry and update running totals.
- ``summarize_token_usage``: Build a summary dict for ExtractedResult.
- ``save_token_usage``: Persist per-run token_usage.json.
- ``update_aggregate_stats``: Update .adep/stats/aggregate.json.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agent.state import TokenUsage
from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Wrapper for LLM response with content and token usage [BLK-050].

    Attributes:
        content: The LLM response text.
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.
    """

    content: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens for this call."""
        return self.input_tokens + self.output_tokens

    @property
    def has_usage(self) -> bool:
        """Whether token usage was captured from the provider."""
        return self.input_tokens > 0 or self.output_tokens > 0


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    is_vlm: bool = False,
) -> float:
    """Calculate cost in USD from token counts and configured pricing [BLK-050].

    Args:
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        is_vlm: If True, use VLM pricing; otherwise LLM pricing.

    Returns:
        Cost in USD.
    """
    if is_vlm:
        input_rate = settings.vlm_pricing_input_per_1k
        output_rate = settings.vlm_pricing_output_per_1k
    else:
        input_rate = settings.llm_pricing_input_per_1k
        output_rate = settings.llm_pricing_output_per_1k
    return (input_tokens / 1000) * input_rate + (output_tokens / 1000) * output_rate


def estimate_tokens(text: str) -> int:
    """Estimate token count using len/4 heuristic [BLK-050].

    Used as fallback when provider doesn't return token counts.
    Approximately 4 characters per token for English text.
    """
    return max(1, len(text) // 4)


def record_token_usage(
    node: str,
    cycle: int,
    input_tokens: int,
    output_tokens: int,
    is_vlm: bool = False,
) -> TokenUsage:
    """Create a TokenUsage entry with calculated cost [BLK-050].

    Args:
        node: Which graph node made the call.
        cycle: ReAct cycle number.
        input_tokens: Input token count.
        output_tokens: Output token count.
        is_vlm: Whether this was a VLM call (affects pricing).

    Returns:
        TokenUsage dataclass with cost calculated.
    """
    cost = calculate_cost(input_tokens, output_tokens, is_vlm=is_vlm)
    return TokenUsage(
        node=node,
        cycle=cycle,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
    )


def summarize_token_usage(usage_list: list[TokenUsage]) -> dict[str, Any]:
    """Build a token usage summary for ExtractedResult [BLK-050].

    Args:
        usage_list: List of TokenUsage entries from a run.

    Returns:
        Dict with total_tokens, total_cost_usd, and per-node breakdown.
    """
    total_tokens = sum(u.total_tokens for u in usage_list)
    total_cost = sum(u.cost_usd for u in usage_list)

    by_node: dict[str, dict[str, int]] = {}
    for u in usage_list:
        if u.node not in by_node:
            by_node[u.node] = {"calls": 0, "tokens": 0}
        by_node[u.node]["calls"] += 1
        by_node[u.node]["tokens"] += u.total_tokens

    return {
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "by_node": by_node,
    }


def save_token_usage(
    run_id: str,
    usage_list: list[TokenUsage],
    base_dir: Path | None = None,
) -> Path:
    """Persist per-run token usage to .adep/runs/{run_id}/token_usage.json [BLK-050].

    Args:
        run_id: The run ID.
        usage_list: List of TokenUsage entries.
        base_dir: Base directory for .adep/ (defaults to settings path).

    Returns:
        Path to the saved file.
    """
    if base_dir is None:
        base_dir = Path(".adep")

    run_dir = base_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    file_path = run_dir / "token_usage.json"
    data = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entries": [u.to_dict() for u in usage_list],
        "summary": summarize_token_usage(usage_list),
    }
    file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return file_path


# Module-level lock for serializing concurrent aggregate stats writes [SCRUM-53]
_aggregate_lock = threading.Lock()


def update_aggregate_stats(
    run_id: str,
    usage_summary: dict[str, Any],
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Update .adep/stats/aggregate.json with run token/cost data [BLK-050].

    Uses a threading lock + atomic write (temp file + ``os.replace``) to
    prevent corruption under concurrent requests [SCRUM-53, BLK-257].

    Args:
        run_id: The completed run ID.
        usage_summary: Summary dict from summarize_token_usage().
        base_dir: Base directory for .adep/ (defaults to settings path).

    Returns:
        The updated aggregate stats dict.
    """
    if base_dir is None:
        base_dir = Path(".adep")

    stats_dir = base_dir / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)

    stats_file = stats_dir / "aggregate.json"

    with _aggregate_lock:
        if stats_file.exists():
            aggregate = json.loads(stats_file.read_text(encoding="utf-8"))
        else:
            aggregate = {
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "runs_count": 0,
                "avg_tokens_per_run": 0,
                "avg_cost_per_run": 0.0,
                "by_date": {},
            }

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        run_tokens = usage_summary.get("total_tokens", 0)
        run_cost = usage_summary.get("total_cost_usd", 0.0)

        aggregate["total_tokens"] += run_tokens
        aggregate["total_cost_usd"] = round(aggregate["total_cost_usd"] + run_cost, 6)
        aggregate["runs_count"] += 1
        aggregate["avg_tokens_per_run"] = aggregate["total_tokens"] // aggregate["runs_count"]
        aggregate["avg_cost_per_run"] = round(aggregate["total_cost_usd"] / aggregate["runs_count"], 6)

        if today not in aggregate["by_date"]:
            aggregate["by_date"][today] = {
                "tokens": 0,
                "cost_usd": 0.0,
                "runs": 0,
            }
        aggregate["by_date"][today]["tokens"] += run_tokens
        aggregate["by_date"][today]["cost_usd"] = round(aggregate["by_date"][today]["cost_usd"] + run_cost, 6)
        aggregate["by_date"][today]["runs"] += 1

        # Atomic write: temp file + os.replace [SCRUM-53, BLK-257]
        tmp_path = stats_file.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
        tmp_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
        os.replace(tmp_path, stats_file)

    return aggregate
