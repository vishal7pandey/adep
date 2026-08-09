"""Tests for trace compaction [§12.3] and State helpers [TS, NFT]."""

from __future__ import annotations

from src.agent.state import TraceEntry, compact_trace
from src.tools.base import ToolResult


def _make_entry(step: int, field: str | None = None) -> TraceEntry:
    """Helper: build a minimal TraceEntry."""
    return TraceEntry(
        step=step,
        thought=f"step {step}",
        tool_name="ocr",
        tool_args={"image": "test.png"},
        result=ToolResult(ok=True, data="text", tool="ocr"),
        field=field,
    )


class TestCompactTrace:
    """Verify the rolling-window trace compaction [§12.3]."""

    def test_window_size_limits_entries(self):
        trace = [_make_entry(i) for i in range(20)]
        compacted = compact_trace(trace, window_size=5, resolved_fields=set())
        assert len(compacted) == 5
        # Should keep the last 5
        assert compacted[0].step == 15
        assert compacted[-1].step == 19

    def test_resolved_fields_pruned(self):
        trace = [
            _make_entry(0, field="total"),
            _make_entry(1, field="tax"),
            _make_entry(2, field="vendor"),
            _make_entry(3, field="total"),
        ]
        compacted = compact_trace(
            trace, window_size=10, resolved_fields={"total"}
        )
        # Entries targeting "total" should be pruned
        assert all(e.field != "total" for e in compacted)
        assert len(compacted) == 2

    def test_empty_trace_stays_empty(self):
        compacted = compact_trace([], window_size=5, resolved_fields=set())
        assert compacted == []

    def test_trace_shorter_than_window_unchanged(self):
        trace = [_make_entry(0), _make_entry(1)]
        compacted = compact_trace(trace, window_size=5, resolved_fields=set())
        assert len(compacted) == 2
