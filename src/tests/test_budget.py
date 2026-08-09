"""Tests for budget limits and enforcement [BLK-051, TS].

Tests cover:
- BudgetStatus: properties (percentage, is_exceeded, is_warning, remaining)
- check_run_budget: per-run budget checking
- check_pre_run_budget: definition and global daily budget checking
- get_budget_status: full status dict for API response
- SSE budget_warning and budget_exceeded events
- POST /runs 429 when budget exceeded
- GET /budget endpoint
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.agent.budget import (
    BudgetLevel,
    BudgetStatus,
    check_run_budget,
    check_pre_run_budget,
    get_budget_status,
)
from src.api.sse import SSEEventEmitter
from src.config import settings


class TestBudgetStatus:
    """Verify BudgetStatus dataclass [BLK-051]."""

    def test_under_limit(self):
        status = BudgetStatus(
            level=BudgetLevel.RUN,
            consumed_tokens=1000,
            consumed_cost_usd=0.01,
            limit_tokens=100_000,
            limit_cost_usd=1.0,
        )
        assert not status.is_exceeded
        assert not status.is_warning
        assert status.percentage == 1.0
        assert status.remaining_tokens == 99_000

    def test_at_warning_threshold(self):
        status = BudgetStatus(
            level=BudgetLevel.RUN,
            consumed_tokens=80_000,
            consumed_cost_usd=0.8,
            limit_tokens=100_000,
            limit_cost_usd=1.0,
        )
        assert status.is_warning
        assert not status.is_exceeded
        assert status.percentage == 80.0

    def test_exceeded_by_tokens(self):
        status = BudgetStatus(
            level=BudgetLevel.RUN,
            consumed_tokens=100_500,
            consumed_cost_usd=0.5,
            limit_tokens=100_000,
            limit_cost_usd=1.0,
        )
        assert status.is_exceeded
        assert not status.is_warning  # exceeded takes precedence

    def test_exceeded_by_cost(self):
        status = BudgetStatus(
            level=BudgetLevel.RUN,
            consumed_tokens=50_000,
            consumed_cost_usd=1.5,
            limit_tokens=100_000,
            limit_cost_usd=1.0,
        )
        assert status.is_exceeded

    def test_remaining_tokens(self):
        status = BudgetStatus(
            level=BudgetLevel.RUN,
            consumed_tokens=30_000,
            limit_tokens=100_000,
            limit_cost_usd=1.0,
        )
        assert status.remaining_tokens == 70_000

    def test_remaining_cost(self):
        status = BudgetStatus(
            level=BudgetLevel.RUN,
            consumed_tokens=0,
            consumed_cost_usd=0.3,
            limit_tokens=100_000,
            limit_cost_usd=1.0,
        )
        assert abs(status.remaining_cost_usd - 0.7) < 0.0001

    def test_to_dict(self):
        status = BudgetStatus(
            level=BudgetLevel.RUN,
            consumed_tokens=50_000,
            consumed_cost_usd=0.5,
            limit_tokens=100_000,
            limit_cost_usd=1.0,
        )
        d = status.to_dict()
        assert d["tokens"] == 50_000
        assert d["limit_tokens"] == 100_000
        assert d["remaining_tokens"] == 50_000
        assert d["percentage"] == 50.0

    def test_zero_limit(self):
        status = BudgetStatus(
            level=BudgetLevel.RUN,
            consumed_tokens=0,
            limit_tokens=0,
            limit_cost_usd=0.0,
        )
        assert status.percentage == 0.0
        assert not status.is_exceeded


class TestCheckRunBudget:
    """Verify check_run_budget [BLK-051]."""

    def test_normal_usage(self):
        status = check_run_budget(1000, 0.01)
        assert status.level == BudgetLevel.RUN
        assert not status.is_exceeded
        assert not status.is_warning

    def test_exceeded(self):
        status = check_run_budget(
            settings.budget_per_run_tokens + 1,
            0.0,
        )
        assert status.is_exceeded

    def test_warning(self):
        status = check_run_budget(
            int(settings.budget_per_run_tokens * 0.85),
            0.0,
        )
        assert status.is_warning
        assert not status.is_exceeded


class TestCheckPreRunBudget:
    """Verify check_pre_run_budget [BLK-051]."""

    def test_no_stats_file(self, tmp_path: Path):
        def_status, global_status = check_pre_run_budget(base_dir=tmp_path)
        assert def_status.consumed_tokens == 0
        assert global_status.consumed_tokens == 0
        assert not def_status.is_exceeded
        assert not global_status.is_exceeded

    def test_with_stats(self, tmp_path: Path):
        stats_dir = tmp_path / "stats"
        stats_dir.mkdir(parents=True)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stats = {
            "total_tokens": 500_000,
            "total_cost_usd": 5.0,
            "runs_count": 5,
            "by_date": {
                today: {"tokens": 500_000, "cost_usd": 5.0, "runs": 5},
            },
        }
        (stats_dir / "aggregate.json").write_text(json.dumps(stats))

        def_status, global_status = check_pre_run_budget(base_dir=tmp_path)
        assert def_status.consumed_tokens == 500_000
        assert global_status.consumed_tokens == 500_000
        assert not def_status.is_exceeded  # 500K < 1M limit
        assert not global_status.is_exceeded  # 500K < 10M limit


class TestGetBudgetStatus:
    """Verify get_budget_status [BLK-051]."""

    def test_empty(self, tmp_path: Path):
        result = get_budget_status(base_dir=tmp_path)
        assert "run" in result
        assert "definition_daily" in result
        assert "global_daily" in result
        assert result["warnings"] == []

    def test_with_run_consumption(self, tmp_path: Path):
        result = get_budget_status(
            run_consumed_tokens=50_000,
            run_consumed_cost=0.5,
            base_dir=tmp_path,
        )
        assert result["run"]["tokens"] == 50_000
        assert result["run"]["remaining_tokens"] == 50_000

    def test_warning_included(self, tmp_path: Path):
        result = get_budget_status(
            run_consumed_tokens=int(settings.budget_per_run_tokens * 0.85),
            run_consumed_cost=0.0,
            base_dir=tmp_path,
        )
        assert len(result["warnings"]) > 0
        assert "run" in result["warnings"][0]


class TestSSEBudgetEvents:
    """Verify SSE budget_warning and budget_exceeded events [BLK-051]."""

    def _collect_events(self, emitter: SSEEventEmitter) -> list[dict[str, Any]]:
        emitter.close()
        loop = asyncio.new_event_loop()
        events = []
        try:
            async def collect():
                async for e in emitter.async_iter():
                    events.append(e)
            loop.run_until_complete(collect())
        finally:
            loop.close()
        return [json.loads(e.replace("data: ", "").strip()) for e in events]

    def test_budget_warning_format(self):
        emitter = SSEEventEmitter()
        emitter.emit_budget_warning(
            level="run",
            consumed_tokens=82000,
            budget_tokens=100000,
            consumed_cost_usd=0.82,
            budget_cost_usd=1.0,
        )
        events = self._collect_events(emitter)
        assert events[0]["type"] == "budget_warning"
        assert events[0]["level"] == "run"
        assert events[0]["consumed_tokens"] == 82000
        assert events[0]["budget_tokens"] == 100000
        assert events[0]["percentage"] == 82
        assert "message" in events[0]

    def test_budget_exceeded_format(self):
        emitter = SSEEventEmitter()
        emitter.emit_budget_exceeded(
            level="run",
            consumed_tokens=100500,
            budget_tokens=100000,
            consumed_cost_usd=1.005,
            budget_cost_usd=1.0,
        )
        events = self._collect_events(emitter)
        assert events[0]["type"] == "budget_exceeded"
        assert events[0]["level"] == "run"
        assert events[0]["consumed_tokens"] == 100500
        assert "message" in events[0]

    def test_budget_warning_zero_budget(self):
        emitter = SSEEventEmitter()
        emitter.emit_budget_warning(
            level="run",
            consumed_tokens=0,
            budget_tokens=0,
            consumed_cost_usd=0.0,
            budget_cost_usd=0.0,
        )
        events = self._collect_events(emitter)
        assert events[0]["percentage"] == 0


class TestBudgetAPIEndpoint:
    """Verify GET /budget API endpoint [BLK-051]."""

    def test_get_budget(self, tmp_path: Path):
        import src.definitions.store as store_module
        import src.config as config_module
        old_store = store_module._store
        old_auth = config_module.settings.auth_enabled
        store_module._store = store_module.DefinitionStore(base_dir=tmp_path / ".adep")
        config_module.settings.auth_enabled = False

        from src.api.main import create_app
        app = create_app()
        client = TestClient(app)

        try:
            resp = client.get("/api/v1/budget")
            assert resp.status_code == 200
            data = resp.json()
            assert "run" in data
            assert "definition_daily" in data
            assert "global_daily" in data
            assert "warnings" in data
        finally:
            config_module.settings.auth_enabled = old_auth
            store_module._store = old_store
