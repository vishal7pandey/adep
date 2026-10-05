"""Budget enforcement — per-run, per-definition, per-global limits [BLK-051, §15].

Provides:
- ``BudgetLevel``: Enum for the three budget levels.
- ``BudgetStatus``: Dataclass for a single budget level's consumption.
- ``BudgetChecker``: Checks budgets and determines if enforcement is needed.
- ``check_run_budget``: Check per-run budget after each LLM call.
- ``check_pre_run_budget``: Check definition/global daily budgets before starting a run.
- ``get_budget_status``: Build budget status dict for API response.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)


class BudgetLevel(str, Enum):
    """Budget enforcement levels."""

    RUN = "run"
    DEFINITION_DAILY = "definition_daily"
    GLOBAL_DAILY = "global_daily"


@dataclass
class BudgetStatus:
    """Consumption status for a single budget level [BLK-051].

    Attributes:
        level: Which budget level.
        consumed_tokens: Tokens consumed so far.
        consumed_cost_usd: Cost consumed so far.
        limit_tokens: Token limit for this level.
        limit_cost_usd: Cost limit for this level.
    """

    level: BudgetLevel
    consumed_tokens: int = 0
    consumed_cost_usd: float = 0.0
    limit_tokens: int = 0
    limit_cost_usd: float = 0.0

    @property
    def percentage(self) -> float:
        """Consumption as percentage of token limit."""
        if self.limit_tokens == 0:
            return 0.0
        return (self.consumed_tokens / self.limit_tokens) * 100

    @property
    def is_exceeded(self) -> bool:
        """Whether either token or cost limit is exceeded."""
        if self.limit_tokens == 0 and self.limit_cost_usd == 0.0:
            return False
        return (self.limit_tokens > 0 and self.consumed_tokens >= self.limit_tokens) or (
            self.limit_cost_usd > 0 and self.consumed_cost_usd >= self.limit_cost_usd
        )

    @property
    def is_warning(self) -> bool:
        """Whether consumption has reached the warning threshold."""
        threshold = settings.budget_warning_threshold
        token_warning = self.consumed_tokens >= self.limit_tokens * threshold
        cost_warning = self.consumed_cost_usd >= self.limit_cost_usd * threshold
        return (token_warning or cost_warning) and not self.is_exceeded

    @property
    def remaining_tokens(self) -> int:
        """Remaining tokens before limit."""
        return max(0, self.limit_tokens - self.consumed_tokens)

    @property
    def remaining_cost_usd(self) -> float:
        """Remaining cost before limit."""
        return round(max(0.0, self.limit_cost_usd - self.consumed_cost_usd), 6)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for API responses."""
        return {
            "tokens": self.consumed_tokens,
            "cost_usd": round(self.consumed_cost_usd, 6),
            "limit_tokens": self.limit_tokens,
            "limit_cost_usd": self.limit_cost_usd,
            "remaining_tokens": self.remaining_tokens,
            "remaining_cost_usd": self.remaining_cost_usd,
            "percentage": round(self.percentage, 1),
        }


def check_run_budget(
    consumed_tokens: int,
    consumed_cost: float,
) -> BudgetStatus:
    """Check per-run budget status [BLK-051].

    Args:
        consumed_tokens: Total tokens consumed in this run so far.
        consumed_cost: Total cost consumed in this run so far.

    Returns:
        BudgetStatus for the run level.
    """
    return BudgetStatus(
        level=BudgetLevel.RUN,
        consumed_tokens=consumed_tokens,
        consumed_cost_usd=consumed_cost,
        limit_tokens=settings.budget_per_run_tokens,
        limit_cost_usd=settings.budget_per_run_cost_usd,
    )


def _load_daily_stats(base_dir: Path | None = None) -> dict[str, Any]:
    """Load aggregate stats for daily budget checks."""
    if base_dir is None:
        base_dir = Path(".adep")
    stats_file = base_dir / "stats" / "aggregate.json"
    if stats_file.exists():
        return json.loads(stats_file.read_text(encoding="utf-8"))
    return {
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "runs_count": 0,
        "by_date": {},
    }


def _get_today_consumption(
    stats: dict[str, Any],
) -> tuple[int, float]:
    """Get today's token and cost consumption from aggregate stats."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_data = stats.get("by_date", {}).get(today, {})
    return (
        today_data.get("tokens", 0),
        today_data.get("cost_usd", 0.0),
    )


def check_pre_run_budget(
    base_dir: Path | None = None,
) -> tuple[BudgetStatus, BudgetStatus]:
    """Check definition and global daily budgets before starting a run [BLK-051].

    Args:
        base_dir: Base directory for .adep/ stats.

    Returns:
        Tuple of (definition_daily_status, global_daily_status).
    """
    stats = _load_daily_stats(base_dir)
    today_tokens, today_cost = _get_today_consumption(stats)

    # Global daily budget
    global_status = BudgetStatus(
        level=BudgetLevel.GLOBAL_DAILY,
        consumed_tokens=today_tokens,
        consumed_cost_usd=today_cost,
        limit_tokens=settings.budget_global_daily_tokens,
        limit_cost_usd=settings.budget_global_daily_cost_usd,
    )

    # Definition daily budget — v1: use global daily consumption as proxy
    # (per-definition tracking requires multi-tenant, BLK-037)
    definition_status = BudgetStatus(
        level=BudgetLevel.DEFINITION_DAILY,
        consumed_tokens=today_tokens,
        consumed_cost_usd=today_cost,
        limit_tokens=settings.budget_per_definition_daily_tokens,
        limit_cost_usd=settings.budget_per_definition_daily_cost_usd,
    )

    return definition_status, global_status


def get_budget_status(
    run_consumed_tokens: int = 0,
    run_consumed_cost: float = 0.0,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Build full budget status dict for API response [BLK-051].

    Args:
        run_consumed_tokens: Tokens consumed in the current run.
        run_consumed_cost: Cost consumed in the current run.
        base_dir: Base directory for .adep/ stats.

    Returns:
        Dict with run, definition_daily, global_daily statuses and warnings list.
    """
    run_status = check_run_budget(run_consumed_tokens, run_consumed_cost)
    def_status, global_status = check_pre_run_budget(base_dir)

    warnings: list[str] = []
    for status in [run_status, def_status, global_status]:
        if status.is_warning:
            warnings.append(
                f"{status.level.value} budget at {status.percentage:.0f}% — "
                f"{status.consumed_tokens}/{status.limit_tokens} tokens consumed"
            )
        if status.is_exceeded:
            warnings.append(
                f"{status.level.value} budget EXCEEDED — "
                f"{status.consumed_tokens}/{status.limit_tokens} tokens"
            )

    return {
        "run": run_status.to_dict(),
        "definition_daily": def_status.to_dict(),
        "global_daily": global_status.to_dict(),
        "warnings": warnings,
    }
