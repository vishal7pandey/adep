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
            cycle=3,
            required_action="approve or reject this field",
        )
        events = self._collect_events(emitter)
        assert events[0]["type"] == "gate_triggered"
        assert events[0]["field"] == "total"
        assert events[0]["risk_tier"] == "high"
        assert events[0]["confidence"] == 0.3
        assert events[0]["cycle"] == 3
        assert events[0]["required_action"] == "approve or reject this field"
        assert "review" in events[0]["reason"].lower()


class TestApproveEndpoint:
    """Verify POST /approve and POST /reject endpoints [BLK-047]."""

    def test_approve_accept(self, client: TestClient):
        _save_run("run-1")
        response = client.post("/api/v1/runs/run-1/approve", json={
            "field": "total",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["field"] == "total"
        assert data["action"] == "accept"
        assert "accept" in data["message"].lower()

    def test_approve_no_body(self, client: TestClient):
        """Approve should work without a body [BLK-047]."""
        _save_run("run-1b")
        response = client.post("/api/v1/runs/run-1b/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "accept"

    def test_reject_field(self, client: TestClient):
        _save_run("run-2")
        response = client.post("/api/v1/runs/run-2/reject", json={
            "field": "subtotal",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "reject"
        assert data["field"] == "subtotal"

    def test_approve_nonexistent_run(self, client: TestClient):
        response = client.post("/api/v1/runs/nonexistent/approve", json={
            "field": "total",
        })
        assert response.status_code == 404

    def test_reject_nonexistent_run(self, client: TestClient):
        response = client.post("/api/v1/runs/nonexistent/reject", json={
            "field": "total",
        })
        assert response.status_code == 404

    def test_approve_resumes_paused_run(self, client: TestClient):
        """Approving a field should resume a paused run [BLK-047]."""
        _save_run("run-4", status="paused")
        response = client.post("/api/v1/runs/run-4/approve", json={
            "field": "total",
        })
        assert response.status_code == 200
        get_response = client.get("/api/v1/runs/run-4")
        assert get_response.json()["status"] == "running"

    def test_reject_resumes_paused_run(self, client: TestClient):
        """Rejecting a field should also resume a paused run [BLK-047]."""
        _save_run("run-4b", status="paused")
        response = client.post("/api/v1/runs/run-4b/reject", json={
            "field": "total",
        })
        assert response.status_code == 200
        get_response = client.get("/api/v1/runs/run-4b")
        assert get_response.json()["status"] == "running"

    def test_approve_records_decision(self, client: TestClient):
        """Approval decisions should be recorded in run data [BLK-047]."""
        _save_run("run-5")
        client.post("/api/v1/runs/run-5/approve", json={
            "field": "total",
        })
        client.post("/api/v1/runs/run-5/reject", json={
            "field": "vendor",
        })
        get_response = client.get("/api/v1/runs/run-5")
        run_data = get_response.json()
        assert "gate_approvals" in run_data
        assert run_data["gate_approvals"]["total"] == "accept"
        assert run_data["gate_approvals"]["vendor"] == "reject"


class TestRunControlGate:
    """Verify RunControl gate synchronization primitives [BLK-047]."""

    def test_gate_event_blocks_until_signaled(self):
        """gate_approval_event.wait() blocks until signal_gate_decision is called."""
        import threading
        from src.api.run_executor import RunControl

        control = RunControl()
        results: list[str] = []

        def waiter():
            control.gate_approval_event.wait()
            results.append(control.gate_decision)

        t = threading.Thread(target=waiter)
        t.start()
        assert results == []  # Still blocked
        control.signal_gate_decision("accept", "total")
        t.join(timeout=2)
        assert results == ["accept"]

    def test_reset_gate_clears_state(self):
        """reset_gate clears the event and decision for the next gate."""
        from src.api.run_executor import RunControl

        control = RunControl()
        control.signal_gate_decision("reject", "subtotal")
        assert control.gate_approval_event.is_set()
        assert control.gate_decision == "reject"
        control.reset_gate()
        assert not control.gate_approval_event.is_set()
        assert control.gate_decision == ""
        assert control.gate_field == ""

    def test_cancel_unblocks_gate_wait(self):
        """SCRUM-483: request_cancel must set gate_approval_event so a
        worker blocked in gate_approval_event.wait() unblocks immediately."""
        import threading
        from src.api.run_executor import RunControl

        control = RunControl()
        unblocked = threading.Event()

        def waiter():
            control.gate_approval_event.wait()
            unblocked.set()

        t = threading.Thread(target=waiter)
        t.start()
        assert not unblocked.is_set()  # Still blocked
        control.request_cancel()
        t.join(timeout=2)
        assert unblocked.is_set()  # Unblocked by cancel
        assert control.cancel_requested is True

    def test_cancel_unblocks_pause_wait(self):
        """SCRUM-483: request_cancel must set resume_event so a worker
        blocked in wait_for_resume() unblocks immediately."""
        import threading
        from src.api.run_executor import RunControl

        control = RunControl()
        control.request_pause()
        unblocked = threading.Event()

        def waiter():
            control.wait_for_resume()
            unblocked.set()

        t = threading.Thread(target=waiter)
        t.start()
        assert not unblocked.is_set()  # Still blocked
        control.request_cancel()
        t.join(timeout=2)
        assert unblocked.is_set()  # Unblocked by cancel
        assert control.cancel_requested is True
