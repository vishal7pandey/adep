"""Tests for runtime API-defined artifacts and run-scoped verification."""

from __future__ import annotations

import json
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.definitions.store as store_module
from src.agent.token_tracking import LLMResponse
from src.api.run_engine import resolve_skill, resolve_template
from src.definitions.store import DefinitionStore


def test_resolve_dynamic_skill(tmp_path):
    store = DefinitionStore(base_dir=tmp_path / ".adep")
    store.create_skill(
        "dyn-skill",
        {
            "id": "dyn-skill",
            "name": "Dynamic Skill",
            "system_prompt": "Extract key fields carefully.",
            "tool_preferences": {"header": "ocr"},
            "probe_order": [
                {"region_type": "header", "rationale": "IDs are usually in the header"}
            ],
            "failure_actions": {"missing": "retry_ocr"},
            "known_failures": "Low contrast scans can hide IDs.",
            "confidence_overrides": {"invoice_number": 0.9},
        },
    )

    skill = resolve_skill("dyn-skill", store)
    assert skill.name == "dyn-skill"
    assert skill.system_prompt == "Extract key fields carefully."
    assert skill.probe_order == [("header", "IDs are usually in the header")]
    assert skill.tool_preferences["header"] == "ocr"
    assert skill.known_failures.startswith("Low contrast")


def test_resolve_dynamic_template(tmp_path):
    store = DefinitionStore(base_dir=tmp_path / ".adep")
    store.create_template(
        "dyn-template",
        {
            "id": "dyn-template",
            "name": "Dynamic Template",
            "description": "Runtime-built template",
            "fields": [
                {
                    "name": "invoice_number",
                    "type": "string",
                    "description": "Invoice identifier",
                    "required": True,
                },
                {
                    "name": "total_amount",
                    "type": "float",
                    "description": "Total due",
                    "required": False,
                },
            ],
        },
    )

    template_cls = resolve_template("dyn-template", store)
    assert "invoice_number" in template_cls.model_fields
    assert template_cls.model_fields["invoice_number"].is_required()
    assert not template_cls.model_fields["total_amount"].is_required()


def _build_runs_app(tmp_path) -> TestClient:
    old_store = store_module._store
    store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")

    store = store_module._store
    store.create_skill(
        "dyn-skill",
        {
            "id": "dyn-skill",
            "name": "Dynamic Skill",
            "system_prompt": "Extract fields",
            "tools": ["ocr", "vlm"],
        },
    )
    store.create(
        "definitions",
        "def-dyn",
        {
            "id": "def-dyn",
            "name": "Dynamic Definition",
            "skill_id": "dyn-skill",
            "template_id": "invoice",
            "tool_names": ["ocr", "vlm"],
            "agent_config": {},
            "version": "1.0.0",
            "task_type": "extraction",
        },
    )
    store.save_run(
        "run-1",
        {
            "id": "run-1",
            "definition_id": "def-dyn",
            "status": "completed",
            "verifier_payload": {
                "trace": [
                    {
                        "step": 1,
                        "thought": "Read the header first",
                        "tool_name": "ocr",
                        "tool_args": {"page": 0},
                        "result_summary": "ok: invoice number found",
                        "result": {"ok": True},
                    }
                ],
                "gap_report": {
                    "total_fields": 2,
                    "satisfied": [{"field": "invoice_number"}],
                    "gaps": [{"field": "total_amount", "gap_type": "missing"}],
                },
                "extraction": {
                    "invoice_number": {"value": "INV-001", "confidence": 0.94},
                },
            },
        },
    )

    app = FastAPI()
    from src.api.routes.runs import router

    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)
    client._old_store = old_store  # type: ignore[attr-defined]
    return client


@patch("src.ai.surrogate_verifier.invoke_llm")
def test_verify_run_endpoint_success(mock_invoke, tmp_path):
    mock_invoke.return_value = LLMResponse(
        content=json.dumps(
            {
                "diagnoses": [
                    {
                        "type": "tool_selection",
                        "severity": "medium",
                        "message": "Use VLM after OCR for totals",
                    }
                ],
                "proposed_tests": [
                    {"assertion": "total_amount should be extracted", "reason": "required field"}
                ],
                "skill_patch": {
                    "probe_order_adjustments": [
                        {
                            "region_type": "table",
                            "rationale": "Totals often appear near summary rows",
                            "position": "after:header",
                        }
                    ]
                },
            }
        ),
        input_tokens=100,
        output_tokens=150,
    )
    client = _build_runs_app(tmp_path)
    try:
        resp = client.post("/api/v1/runs/run-1/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["diagnoses"][0]["type"] == "tool_selection"
        assert data["proposed_tests"][0]["assertion"].startswith("total_amount")
    finally:
        store_module._store = client._old_store  # type: ignore[attr-defined]


def test_verify_run_endpoint_requires_payload(tmp_path):
    old_store = store_module._store
    store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
    try:
        store_module._store.create_skill(
            "dyn-skill",
            {
                "id": "dyn-skill",
                "name": "Dynamic Skill",
                "system_prompt": "Extract fields",
            },
        )
        store_module._store.create(
            "definitions",
            "def-dyn",
            {
                "id": "def-dyn",
                "name": "Dynamic Definition",
                "skill_id": "dyn-skill",
                "template_id": "invoice",
                "tool_names": [],
                "agent_config": {},
                "version": "1.0.0",
                "task_type": "extraction",
            },
        )
        store_module._store.save_run(
            "run-2",
            {
                "id": "run-2",
                "definition_id": "def-dyn",
                "status": "completed",
            },
        )
        app = FastAPI()
        from src.api.routes.runs import router

        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)
        resp = client.post("/api/v1/runs/run-2/verify")
        assert resp.status_code == 409
    finally:
        store_module._store = old_store
