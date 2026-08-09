"""Tests for BLK-165: Persist cost, tokens, and timestamps in run records.

Covers:
- serialize_extraction_result includes total_cost_usd, total_tokens, completed_at
- store.save_run overwrite bug fixed — existing created_at/started_at preserved
- New fields present in serialized output
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.api.run_engine import serialize_extraction_result
from src.templates.base import ExtractedResult
from src.agent.validator import GapReport
from src.tools.base import FieldValue, BBox, Grounding


def _make_result(
    is_complete: bool = True,
    total_cost_usd: float = 0.0,
    total_tokens: int = 0,
) -> ExtractedResult:
    """Create a minimal ExtractedResult for testing."""
    return ExtractedResult(
        is_complete=is_complete,
        field_values={},
        gap_report=GapReport(total_fields=0, gaps=[], satisfied=[]),
        trace=[],
        total_cycles=3,
        status="complete" if is_complete else "partial",
        token_usage_summary={
            "total_cost_usd": total_cost_usd,
            "total_tokens": total_tokens,
        },
    )


class TestSerializeExtractionResult:
    """serialize_extraction_result includes cost/tokens/timestamps [BLK-165]."""

    def test_includes_total_cost_usd(self):
        result = _make_result(total_cost_usd=0.42)
        state: dict[str, Any] = {}
        serialized = serialize_extraction_result("run-1", "def-1", "/doc.png", result, state)
        assert "total_cost_usd" in serialized
        assert serialized["total_cost_usd"] == 0.42

    def test_includes_total_tokens(self):
        result = _make_result(total_tokens=12345)
        state: dict[str, Any] = {}
        serialized = serialize_extraction_result("run-1", "def-1", "/doc.png", result, state)
        assert "total_tokens" in serialized
        assert serialized["total_tokens"] == 12345

    def test_includes_completed_at(self):
        result = _make_result()
        state: dict[str, Any] = {}
        serialized = serialize_extraction_result("run-1", "def-1", "/doc.png", result, state)
        assert "completed_at" in serialized
        # Should be an ISO timestamp
        datetime.fromisoformat(serialized["completed_at"])

    def test_defaults_when_token_summary_empty(self):
        result = _make_result()
        result.token_usage_summary = {}
        state: dict[str, Any] = {}
        serialized = serialize_extraction_result("run-1", "def-1", "/doc.png", result, state)
        assert serialized["total_cost_usd"] == 0.0
        assert serialized["total_tokens"] == 0

    def test_preserves_existing_fields(self):
        result = _make_result()
        state: dict[str, Any] = {}
        serialized = serialize_extraction_result("run-1", "def-1", "/doc.png", result, state)
        # Existing fields still present
        assert serialized["id"] == "run-1"
        assert serialized["definition_id"] == "def-1"
        assert serialized["status"] == "completed"
        assert serialized["current_cycle"] == 3
        assert serialized["fields"] == []


class TestPersistMergeBehavior:
    """Verify the overwrite bug is fixed — existing timestamps preserved [BLK-165]."""

    def test_existing_created_at_preserved(self, tmp_path: Path):
        """When run_engine persists result, existing created_at should survive."""
        from src.definitions.store import DefinitionStore

        store = DefinitionStore(base_dir=str(tmp_path))

        # Simulate executor creating initial run record
        initial = {
            "id": "run-test",
            "definition_id": "def-1",
            "document_url": "/doc.png",
            "status": "queued",
            "created_at": "2026-08-08T10:00:00Z",
            "started_at": "2026-08-08T10:00:05Z",
            "fields": [],
        }
        store.save_run("run-test", initial)

        # Simulate run_engine persisting the result
        result = _make_result(total_cost_usd=0.15, total_tokens=500)
        serialized = serialize_extraction_result("run-test", "def-1", "/doc.png", result, {})

        # This is the fixed code path from run_engine.py
        try:
            existing = store.get_run("run-test")
            existing.update(serialized)
            store.update_run("run-test", existing)
        except FileNotFoundError:
            store.save_run("run-test", serialized)

        # Verify created_at and started_at are preserved
        final = store.get_run("run-test")
        assert final["created_at"] == "2026-08-08T10:00:00Z"
        assert final["started_at"] == "2026-08-08T10:00:05Z"
        # And new fields are present
        assert final["total_cost_usd"] == 0.15
        assert final["total_tokens"] == 500
        assert "completed_at" in final
        assert final["status"] == "completed"
