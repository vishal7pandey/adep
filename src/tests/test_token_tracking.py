"""Tests for token tracking and cost calculation [BLK-050, TS].

Tests cover:
- TokenUsage dataclass: construction, to_dict, __post_init__
- LLMResponse wrapper: content, token counts, has_usage
- calculate_cost: LLM vs VLM pricing, edge cases
- estimate_tokens: heuristic accuracy
- record_token_usage: creates TokenUsage with cost
- summarize_token_usage: per-node breakdown, totals
- save_token_usage: file persistence
- update_aggregate_stats: daily aggregates, running totals
- SSE token_usage event: format and fields
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from src.agent.state import TokenUsage
from src.agent.token_tracking import (
    LLMResponse,
    calculate_cost,
    estimate_tokens,
    record_token_usage,
    summarize_token_usage,
    save_token_usage,
    update_aggregate_stats,
)
from src.api.sse import SSEEventEmitter


class TestTokenUsage:
    """Verify TokenUsage dataclass [BLK-050]."""

    def test_basic_construction(self):
        usage = TokenUsage(node="plan", cycle=1, input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150
        assert usage.cost_usd == 0.0
        assert usage.timestamp != ""

    def test_explicit_total_tokens(self):
        usage = TokenUsage(
            node="plan", cycle=1, input_tokens=100, output_tokens=50, total_tokens=999
        )
        assert usage.total_tokens == 999

    def test_to_dict(self):
        usage = TokenUsage(
            node="compact", cycle=3, input_tokens=200, output_tokens=100, cost_usd=0.005
        )
        d = usage.to_dict()
        assert d["node"] == "compact"
        assert d["cycle"] == 3
        assert d["input_tokens"] == 200
        assert d["output_tokens"] == 100
        assert d["total_tokens"] == 300
        assert d["cost_usd"] == 0.005
        assert "timestamp" in d

    def test_timestamp_auto_generated(self):
        usage = TokenUsage(node="plan", cycle=1, input_tokens=10, output_tokens=5)
        assert usage.timestamp != ""
        assert "T" in usage.timestamp  # ISO format


class TestLLMResponse:
    """Verify LLMResponse wrapper [BLK-050]."""

    def test_basic(self):
        resp = LLMResponse(content="hello", input_tokens=10, output_tokens=5)
        assert resp.content == "hello"
        assert resp.total_tokens == 15
        assert resp.has_usage is True

    def test_no_usage(self):
        resp = LLMResponse(content="hello")
        assert resp.total_tokens == 0
        assert resp.has_usage is False

    def test_total_tokens_property(self):
        resp = LLMResponse(content="test", input_tokens=100, output_tokens=200)
        assert resp.total_tokens == 300


class TestCalculateCost:
    """Verify cost calculation [BLK-050]."""

    def test_llm_pricing(self):
        # input: 1000 tokens * $0.005/1K = $0.005
        # output: 500 tokens * $0.015/1K = $0.0075
        # total: $0.0125
        cost = calculate_cost(input_tokens=1000, output_tokens=500, is_vlm=False)
        assert abs(cost - 0.0125) < 0.0001

    def test_vlm_pricing(self):
        # input: 1000 tokens * $0.01/1K = $0.01
        # output: 500 tokens * $0.03/1K = $0.015
        # total: $0.025
        cost = calculate_cost(input_tokens=1000, output_tokens=500, is_vlm=True)
        assert abs(cost - 0.025) < 0.0001

    def test_zero_tokens(self):
        cost = calculate_cost(input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_large_token_count(self):
        cost = calculate_cost(input_tokens=100_000, output_tokens=50_000)
        # input: 100 * 0.005 = 0.5
        # output: 50 * 0.015 = 0.75
        # total: 1.25
        assert abs(cost - 1.25) < 0.0001


class TestEstimateTokens:
    """Verify token estimation heuristic [BLK-050]."""

    def test_empty_string(self):
        assert estimate_tokens("") == 1

    def test_short_string(self):
        # 20 chars / 4 = 5 tokens
        assert estimate_tokens("a" * 20) == 5

    def test_long_string(self):
        # 400 chars / 4 = 100 tokens
        assert estimate_tokens("a" * 400) == 100

    def test_minimum_one_token(self):
        assert estimate_tokens("ab") == 1  # 2//4 = 0, max(1, 0) = 1


class TestRecordTokenUsage:
    """Verify record_token_usage [BLK-050]."""

    def test_creates_token_usage_with_cost(self):
        usage = record_token_usage(
            node="plan",
            cycle=1,
            input_tokens=1000,
            output_tokens=500,
        )
        assert usage.node == "plan"
        assert usage.cycle == 1
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.total_tokens == 1500
        assert usage.cost_usd > 0

    def test_vlm_cost(self):
        usage = record_token_usage(
            node="vlm",
            cycle=2,
            input_tokens=1000,
            output_tokens=500,
            is_vlm=True,
        )
        # VLM pricing: 0.01 + 0.015 = 0.025
        assert abs(usage.cost_usd - 0.025) < 0.0001


class TestSummarizeTokenUsage:
    """Verify summarize_token_usage [BLK-050]."""

    def test_empty_list(self):
        summary = summarize_token_usage([])
        assert summary["total_tokens"] == 0
        assert summary["total_cost_usd"] == 0.0
        assert summary["by_node"] == {}

    def test_single_entry(self):
        usage = TokenUsage(node="plan", cycle=1, input_tokens=100, output_tokens=50, cost_usd=0.001)
        summary = summarize_token_usage([usage])
        assert summary["total_tokens"] == 150
        assert summary["total_cost_usd"] == 0.001
        assert summary["by_node"]["plan"]["calls"] == 1
        assert summary["by_node"]["plan"]["tokens"] == 150

    def test_multiple_entries_same_node(self):
        u1 = TokenUsage(node="plan", cycle=1, input_tokens=100, output_tokens=50, cost_usd=0.001)
        u2 = TokenUsage(node="plan", cycle=2, input_tokens=200, output_tokens=100, cost_usd=0.002)
        summary = summarize_token_usage([u1, u2])
        assert summary["total_tokens"] == 450
        assert summary["by_node"]["plan"]["calls"] == 2
        assert summary["by_node"]["plan"]["tokens"] == 450

    def test_multiple_nodes(self):
        u1 = TokenUsage(node="plan", cycle=1, input_tokens=100, output_tokens=50, cost_usd=0.001)
        u2 = TokenUsage(
            node="compact", cycle=5, input_tokens=500, output_tokens=200, cost_usd=0.005
        )
        summary = summarize_token_usage([u1, u2])
        assert summary["total_tokens"] == 850
        assert "plan" in summary["by_node"]
        assert "compact" in summary["by_node"]
        assert summary["by_node"]["plan"]["tokens"] == 150
        assert summary["by_node"]["compact"]["tokens"] == 700


class TestSaveTokenUsage:
    """Verify per-run token usage persistence [BLK-050]."""

    def test_save_and_read(self, tmp_path: Path):
        usage_list = [
            TokenUsage(node="plan", cycle=1, input_tokens=100, output_tokens=50),
            TokenUsage(node="compact", cycle=5, input_tokens=200, output_tokens=100),
        ]
        file_path = save_token_usage("run-test", usage_list, base_dir=tmp_path)
        assert file_path.exists()
        data = json.loads(file_path.read_text())
        assert data["run_id"] == "run-test"
        assert len(data["entries"]) == 2
        assert data["summary"]["total_tokens"] == 450

    def test_creates_directory(self, tmp_path: Path):
        usage_list = [TokenUsage(node="plan", cycle=1, input_tokens=10, output_tokens=5)]
        file_path = save_token_usage("run-abc", usage_list, base_dir=tmp_path)
        assert file_path.parent.exists()


class TestUpdateAggregateStats:
    """Verify aggregate stats persistence [BLK-050]."""

    def test_first_run(self, tmp_path: Path):
        summary = {"total_tokens": 1500, "total_cost_usd": 0.01}
        aggregate = update_aggregate_stats("run-1", summary, base_dir=tmp_path)
        assert aggregate["total_tokens"] == 1500
        assert aggregate["runs_count"] == 1
        assert aggregate["avg_tokens_per_run"] == 1500
        assert len(aggregate["by_date"]) == 1

    def test_multiple_runs(self, tmp_path: Path):
        s1 = {"total_tokens": 1000, "total_cost_usd": 0.005}
        s2 = {"total_tokens": 2000, "total_cost_usd": 0.01}
        update_aggregate_stats("run-1", s1, base_dir=tmp_path)
        aggregate = update_aggregate_stats("run-2", s2, base_dir=tmp_path)
        assert aggregate["total_tokens"] == 3000
        assert aggregate["runs_count"] == 2
        assert aggregate["avg_tokens_per_run"] == 1500

    def test_persists_to_file(self, tmp_path: Path):
        summary = {"total_tokens": 500, "total_cost_usd": 0.002}
        update_aggregate_stats("run-1", summary, base_dir=tmp_path)
        stats_file = tmp_path / "stats" / "aggregate.json"
        assert stats_file.exists()
        data = json.loads(stats_file.read_text())
        assert data["total_tokens"] == 500

    def test_concurrent_writes_atomic(self, tmp_path: Path):
        """Concurrent writes should not corrupt the aggregate file [SCRUM-53, BLK-257]."""
        import threading

        num_threads = 10
        tokens_per_run = 100
        barrier = threading.Barrier(num_threads)
        errors: list[Exception] = []

        def worker(idx: int):
            try:
                barrier.wait(timeout=5)
                summary = {"total_tokens": tokens_per_run, "total_cost_usd": 0.001}
                update_aggregate_stats(f"run-{idx}", summary, base_dir=tmp_path)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Workers raised: {errors}"
        stats_file = tmp_path / "stats" / "aggregate.json"
        data = json.loads(stats_file.read_text(encoding="utf-8"))
        assert data["total_tokens"] == num_threads * tokens_per_run
        assert data["runs_count"] == num_threads


class TestSSETokenUsageEvent:
    """Verify SSE token_usage event [BLK-050]."""

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

    def test_token_usage_event_format(self):
        emitter = SSEEventEmitter()
        emitter.emit_token_usage(
            node="plan",
            cycle=5,
            input_tokens=1200,
            output_tokens=150,
            total_tokens=1350,
            cost_usd=0.008,
            running_total_tokens=8500,
            running_total_cost=0.052,
        )
        events = self._collect_events(emitter)
        assert events[0]["type"] == "token_usage"
        assert events[0]["node"] == "plan"
        assert events[0]["cycle"] == 5
        assert events[0]["input_tokens"] == 1200
        assert events[0]["output_tokens"] == 150
        assert events[0]["total_tokens"] == 1350
        assert events[0]["cost_usd"] == 0.008
        assert events[0]["running_total_tokens"] == 8500
        assert events[0]["running_total_cost"] == 0.052

    def test_token_usage_rounding(self):
        emitter = SSEEventEmitter()
        emitter.emit_token_usage(
            node="plan",
            cycle=1,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.000123456,
            running_total_tokens=150,
            running_total_cost=0.000123456,
        )
        events = self._collect_events(emitter)
        # Cost should be rounded to 6 decimal places
        assert events[0]["cost_usd"] == 0.000123
