"""Tests for SSE field_update and status_change events [Wave 4/5, BLK-047].

Tests cover:
- field_update event includes extracted_fields_count, total_fields, risk_tier
- status_change event emitted on status transitions
- field_update flat format (field as string, not nested object)
- status_change includes previous_status
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from src.api.sse import SSEEventEmitter


def _collect_events(emitter: SSEEventEmitter) -> list[dict[str, Any]]:
    """Collect all events from an emitter."""
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


class TestFieldUpdateEvent:
    """Verify field_update SSE event format [Wave 4/5]."""

    def test_field_update_has_extracted_fields_count(self):
        emitter = SSEEventEmitter()
        emitter.emit_field_update(
            field_id="total",
            name="total",
            value=1500.0,
            confidence=0.95,
            extracted_fields_count=5,
            total_fields=6,
        )
        events = _collect_events(emitter)
        assert events[0]["type"] == "field_update"
        assert events[0]["extracted_fields_count"] == 5
        assert events[0]["total_fields"] == 6

    def test_field_update_has_risk_tier(self):
        emitter = SSEEventEmitter()
        emitter.emit_field_update(
            field_id="total",
            name="total",
            value=1500.0,
            confidence=0.3,
            risk_tier="high",
        )
        events = _collect_events(emitter)
        assert events[0]["risk_tier"] == "high"

    def test_field_update_flat_format(self):
        """field should be a string (field name), not a nested object [Wave 4/5]."""
        emitter = SSEEventEmitter()
        emitter.emit_field_update(
            field_id="vendor",
            name="vendor",
            value="ACME Corp",
            confidence=0.9,
        )
        events = _collect_events(emitter)
        assert events[0]["field"] == "vendor"
        assert isinstance(events[0]["field"], str)

    def test_field_update_includes_bbox_and_page(self):
        emitter = SSEEventEmitter()
        bbox = {"x": 10, "y": 20, "width": 100, "height": 50}
        emitter.emit_field_update(
            field_id="total",
            name="total",
            value=1500.0,
            confidence=0.95,
            bbox=bbox,
            page=2,
        )
        events = _collect_events(emitter)
        assert events[0]["bbox"] == bbox
        assert events[0]["page"] == 2

    def test_field_update_defaults(self):
        """Default risk_tier should be 'low', counts should be 0."""
        emitter = SSEEventEmitter()
        emitter.emit_field_update(
            field_id="total",
            name="total",
            value=1500.0,
            confidence=0.95,
        )
        events = _collect_events(emitter)
        assert events[0]["risk_tier"] == "low"
        assert events[0]["extracted_fields_count"] == 0
        assert events[0]["total_fields"] == 0


class TestStatusChangeEvent:
    """Verify status_change SSE event [Wave 4/5]."""

    def test_status_change_basic(self):
        emitter = SSEEventEmitter()
        emitter.emit_status_change(status="running", cycle=1, previous_status="idle")
        events = _collect_events(emitter)
        assert events[0]["type"] == "status_change"
        assert events[0]["status"] == "running"
        assert events[0]["cycle"] == 1
        assert events[0]["previous_status"] == "idle"

    def test_status_change_no_previous(self):
        emitter = SSEEventEmitter()
        emitter.emit_status_change(status="running")
        events = _collect_events(emitter)
        assert events[0]["previous_status"] is None

    def test_status_change_paused(self):
        emitter = SSEEventEmitter()
        emitter.emit_status_change(status="paused", cycle=5, previous_status="running")
        events = _collect_events(emitter)
        assert events[0]["status"] == "paused"
        assert events[0]["previous_status"] == "running"

    def test_status_change_completed(self):
        emitter = SSEEventEmitter()
        emitter.emit_status_change(status="completed", cycle=10, previous_status="running")
        events = _collect_events(emitter)
        assert events[0]["status"] == "completed"

    def test_status_change_failed(self):
        emitter = SSEEventEmitter()
        emitter.emit_status_change(status="failed", cycle=3, previous_status="running")
        events = _collect_events(emitter)
        assert events[0]["status"] == "failed"

    def test_multiple_status_changes(self):
        """Verify multiple transitions can be emitted in sequence."""
        emitter = SSEEventEmitter()
        emitter.emit_status_change(status="running", previous_status="idle")
        emitter.emit_status_change(status="paused", cycle=3, previous_status="running")
        emitter.emit_status_change(status="running", cycle=3, previous_status="paused")
        emitter.emit_status_change(status="completed", cycle=10, previous_status="running")
        events = _collect_events(emitter)
        assert len(events) == 4
        assert events[0]["status"] == "running"
        assert events[1]["status"] == "paused"
        assert events[2]["status"] == "running"
        assert events[3]["status"] == "completed"
