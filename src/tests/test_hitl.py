"""Tests for HITL gate pattern [BLK-047, §13, TS].

Tests cover:
- Risk tier classification: low, medium, high, critical
- Gate decision: requires_gate, timeout, auto_action
- SSE gate_triggered event
- POST /approve endpoint (accept and reject)
- Invalid action handling
- Paused run resumes on approval
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.agent.hitl import (
    GateDecision,
    RiskTier,
    classify_extraction_risk,
)
from src.api.sse import SSEEventEmitter
from src.definitions.store import DefinitionStore


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Create a FastAPI TestClient with a temporary store."""
    import src.definitions.store as store_module
    import src.config as config_module
    old_store = store_module._store
    old_auth = config_module.settings.auth_enabled
    store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    from src.api.main import create_app
    app = create_app()
    test_client = TestClient(app)

    yield test_client

    config_module.settings.auth_enabled = old_auth
    store_module._store = old_store


def _save_run(run_id: str, **overrides: Any) -> None:
    """Save a run to the test store with defaults."""
    import src.definitions.store as store_module
    data = {
        "id": run_id,
        "definition_id": "def-test",
        "document_url": "test.png",
        "status": "running",
        "current_cycle": 5,
        "total_fields": 7,
        "extracted_fields_count": 3,
        "fields": [
            {"id": "invoice_number", "name": "invoice_number", "value": "INV-001", "confidence": 0.95},
        ],
    }
    data.update(overrides)
    store_module._store.save_run(run_id, data)


class TestRiskTierClassification:
    """Verify risk tier classification logic [BLK-047]."""

    def test_high_confidence_is_low_risk(self):
        decision = classify_extraction_risk(confidence=0.9)
        assert decision.tier == RiskTier.LOW
        assert decision.requires_gate is False
        assert decision.auto_timeout_seconds == 0

    def test_medium_confidence_is_medium_risk(self):
        decision = classify_extraction_risk(confidence=0.65)
        assert decision.tier == RiskTier.MEDIUM
        assert decision.requires_gate is False  # Non-blocking
        assert decision.auto_timeout_seconds == 60
        assert decision.auto_action_on_timeout == "accept"

    def test_low_confidence_is_high_risk(self):
        decision = classify_extraction_risk(confidence=0.3)
        assert decision.tier == RiskTier.HIGH
        assert decision.requires_gate is True  # Blocking gate
        assert decision.auto_action_on_timeout == "reject"

    def test_semantic_fail_is_high_risk(self):
        decision = classify_extraction_risk(confidence=0.9, semantic_failed=True)
        assert decision.tier == RiskTier.HIGH
        assert decision.requires_gate is True

    def test_partial_termination_is_critical(self):
        decision = classify_extraction_risk(confidence=0.9, is_partial_termination=True)
        assert decision.tier == RiskTier.CRITICAL
        assert decision.requires_gate is True
        assert decision.auto_action_on_timeout == "reject"

    def test_confidence_at_0_5_boundary_is_medium(self):
        """Confidence exactly 0.5 is medium risk (in [0.5, 0.8))."""
        decision = classify_extraction_risk(confidence=0.5)
        assert decision.tier == RiskTier.MEDIUM

    def test_confidence_at_0_8_boundary_is_low(self):
        """Confidence exactly 0.8 is low risk."""
        decision = classify_extraction_risk(confidence=0.8)
        assert decision.tier == RiskTier.LOW

    def test_confidence_just_below_0_5_is_high(self):
        decision = classify_extraction_risk(confidence=0.49)
        assert decision.tier == RiskTier.HIGH

    def test_confidence_just_below_0_8_is_medium(self):
        decision = classify_extraction_risk(confidence=0.79)
        assert decision.tier == RiskTier.MEDIUM

    def test_critical_overrides_semantic_fail(self):
        """Partial termination is critical even if semantic also failed."""
        decision = classify_extraction_risk(
            confidence=0.3, semantic_failed=True, is_partial_termination=True
        )
        assert decision.tier == RiskTier.CRITICAL

    def test_decision_has_reason(self):
        decision = classify_extraction_risk(confidence=0.3)
        assert len(decision.reason) > 0
        assert "0.30" in decision.reason or "confidence" in decision.reason.lower()


class TestSSEGateEvent:
    """Verify SSE gate_triggered event [BLK-047]."""

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

    def test_emit_gate_triggered(self):
        emitter = SSEEventEmitter()
        emitter.emit_gate_triggered(
            field="total",
            risk_tier="high",
            confidence=0.3,
            reason="Confidence 0.30 < 0.5 — pre-execution review required",
        )
        events = self._collect_events(emitter)
        assert events[0]["type"] == "gate_triggered"
        assert events[0]["field"] == "total"
        assert events[0]["risk_tier"] == "high"
        assert events[0]["confidence"] == 0.3
        assert "review" in events[0]["reason"].lower()


class TestApproveEndpoint:
    """Verify POST /approve endpoint [BLK-047]."""

    def test_approve_accept(self, client: TestClient):
        _save_run("run-1")
        response = client.post("/api/v1/runs/run-1/approve", json={
            "field": "total",
            "action": "accept",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["field"] == "total"
        assert data["action"] == "accept"
        assert "accept" in data["message"].lower()

    def test_approve_reject(self, client: TestClient):
        _save_run("run-2")
        response = client.post("/api/v1/runs/run-2/approve", json={
            "field": "subtotal",
            "action": "reject",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "reject"

    def test_approve_invalid_action(self, client: TestClient):
        _save_run("run-3")
        response = client.post("/api/v1/runs/run-3/approve", json={
            "field": "total",
            "action": "maybe",
        })
        assert response.status_code == 400

    def test_approve_nonexistent_run(self, client: TestClient):
        response = client.post("/api/v1/runs/nonexistent/approve", json={
            "field": "total",
            "action": "accept",
        })
        assert response.status_code == 404

    def test_approve_resumes_paused_run(self, client: TestClient):
        """Approving a field should resume a paused run [BLK-047]."""
        _save_run("run-4", status="paused")
        response = client.post("/api/v1/runs/run-4/approve", json={
            "field": "total",
            "action": "accept",
        })
        assert response.status_code == 200
        get_response = client.get("/api/v1/runs/run-4")
        assert get_response.json()["status"] == "running"

    def test_approve_records_decision(self, client: TestClient):
        """Approval decisions should be recorded in run data [BLK-047]."""
        _save_run("run-5")
        client.post("/api/v1/runs/run-5/approve", json={
            "field": "total",
            "action": "accept",
        })
        client.post("/api/v1/runs/run-5/approve", json={
            "field": "vendor",
            "action": "reject",
        })
        get_response = client.get("/api/v1/runs/run-5")
        run_data = get_response.json()
        assert "gate_approvals" in run_data
        assert run_data["gate_approvals"]["total"] == "accept"
        assert run_data["gate_approvals"]["vendor"] == "reject"
