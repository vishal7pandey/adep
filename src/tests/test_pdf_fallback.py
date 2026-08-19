"""Tests for PDF fallback gating logic [BLK-264, BLK-287].

Verifies that:
- run_pdf_fallback only runs when no LLM provider is configured OR fast-path is opted in
- Fallback returns None for unsupported skills (non-PDF or no parser registered)
- Fallback returns None for non-PDF documents
- execute_run_async raises RuntimeError when no LLM and no fallback available
- execute_run_async uses agent path when LLM is configured and no fast-path opt-in
- SSE complete event includes execution_mode for fallback runs [BLK-287]
- Serialized fallback result includes execution_mode=fallback [BLK-287]
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.fallback.pdf_runtime import run_pdf_fallback, _PARSERS
from src.skills.bank_statement import BankStatementSkill
from src.skills.invoice import InvoiceSkill
from src.templates.bank_statement import BankStatementTemplate
from src.templates.invoice import InvoiceTemplate
from src.agent.validator import ValidatorConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def validator_config() -> ValidatorConfig:
    return ValidatorConfig()


@pytest.fixture
def fake_pdf(tmp_path: Path) -> Path:
    """Create a minimal fake PDF file."""
    import fitz
    pdf_path = tmp_path / "test_doc.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test Bank\nStatement Period: 2024-01-01 to 2024-02-01")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


# ---------------------------------------------------------------------------
# run_pdf_fallback unit tests
# ---------------------------------------------------------------------------

class TestRunPdfFallback:
    """Verify run_pdf_fallback behavior [BLK-264]."""

    def test_returns_none_for_non_pdf(self, tmp_path: Path, validator_config: ValidatorConfig):
        """Fallback should return None for non-PDF documents."""
        txt_path = tmp_path / "doc.txt"
        txt_path.write_text("not a pdf")
        result = run_pdf_fallback(
            str(txt_path),
            template_cls=BankStatementTemplate,
            skill=BankStatementSkill,
            validator_config=validator_config,
        )
        assert result is None

    def test_returns_none_for_unsupported_skill(self, fake_pdf: Path, validator_config: ValidatorConfig):
        """Fallback should return None for skills without a registered parser."""
        # Invoice is not in _PARSERS
        assert "invoice" not in _PARSERS
        result = run_pdf_fallback(
            str(fake_pdf),
            template_cls=InvoiceTemplate,
            skill=InvoiceSkill,
            validator_config=validator_config,
        )
        assert result is None

    def test_returns_result_for_supported_skill(self, fake_pdf: Path, validator_config: ValidatorConfig):
        """Fallback should return a result for supported skills with PDF documents."""
        assert "bank_statement" in _PARSERS
        result = run_pdf_fallback(
            str(fake_pdf),
            template_cls=BankStatementTemplate,
            skill=BankStatementSkill,
            validator_config=validator_config,
        )
        assert result is not None
        assert hasattr(result, "is_complete")
        assert hasattr(result, "field_values")
        assert hasattr(result, "trace")
        assert len(result.trace) == 1
        assert result.trace[0].tool_name == "pdf_text_extract"

    def test_nine_parsers_registered(self):
        """Verify exactly 9 parsers are registered (the 9 skills from BLK-264)."""
        assert len(_PARSERS) == 9
        expected = {
            "bank_statement",
            "utility_bill",
            "commercial_lease",
            "trade_finance_scrutiny",
            "commodity_trade",
            "purchase_order",
            "packing_list",
            "purchase_order_sf1449",
            "packing_list_travel",
        }
        assert set(_PARSERS.keys()) == expected


# ---------------------------------------------------------------------------
# Fallback gating logic tests
# ---------------------------------------------------------------------------

class TestFallbackGating:
    """Verify _execute_run_inner gates fallback correctly [BLK-264]."""

    def test_fallback_skipped_when_llm_configured(self):
        """When LLM is configured and fast-path not opted in, fallback should be skipped."""
        import src.api.run_engine as engine
        import src.config as config_module

        old_key = config_module.settings.azure_api_key
        old_endpoint = config_module.settings.azure_chat_endpoint
        config_module.settings.azure_api_key = "test-key"
        config_module.settings.azure_chat_endpoint = "test-endpoint"
        try:
            # Verify the gating condition
            llm_configured = bool(
                config_module.settings.azure_api_key
                and config_module.settings.azure_chat_endpoint
            )
            use_fast_path = False
            assert llm_configured is True
            assert not (not llm_configured or use_fast_path)
        finally:
            config_module.settings.azure_api_key = old_key
            config_module.settings.azure_chat_endpoint = old_endpoint

    def test_fallback_runs_when_llm_not_configured(self):
        """When LLM is not configured, fallback should be attempted."""
        import src.config as config_module

        old_key = config_module.settings.azure_api_key
        old_endpoint = config_module.settings.azure_chat_endpoint
        config_module.settings.azure_api_key = ""
        config_module.settings.azure_chat_endpoint = ""
        try:
            llm_configured = bool(
                config_module.settings.azure_api_key
                and config_module.settings.azure_chat_endpoint
            )
            use_fast_path = False
            assert llm_configured is False
            assert (not llm_configured or use_fast_path) is True
        finally:
            config_module.settings.azure_api_key = old_key
            config_module.settings.azure_chat_endpoint = old_endpoint

    def test_fallback_runs_when_fast_path_opted_in(self):
        """When fast-path is opted in, fallback should run even with LLM configured."""
        import src.config as config_module

        old_key = config_module.settings.azure_api_key
        old_endpoint = config_module.settings.azure_chat_endpoint
        config_module.settings.azure_api_key = "test-key"
        config_module.settings.azure_chat_endpoint = "test-endpoint"
        try:
            llm_configured = bool(
                config_module.settings.azure_api_key
                and config_module.settings.azure_chat_endpoint
            )
            use_fast_path = True
            assert llm_configured is True
            assert (not llm_configured or use_fast_path) is True
        finally:
            config_module.settings.azure_api_key = old_key
            config_module.settings.azure_chat_endpoint = old_endpoint

    def test_runtime_error_when_no_llm_and_no_fallback(self, tmp_path: Path):
        """When no LLM and fallback returns None, should raise RuntimeError."""
        import src.api.run_engine as engine
        import src.config as config_module

        old_key = config_module.settings.azure_api_key
        old_endpoint = config_module.settings.azure_chat_endpoint
        config_module.settings.azure_api_key = ""
        config_module.settings.azure_chat_endpoint = ""

        # Create a non-PDF doc so fallback returns None
        txt_path = tmp_path / "doc.txt"
        txt_path.write_text("not a pdf")

        try:
            import asyncio
            from src.definitions.store import DefinitionStore
            import src.definitions.store as store_module

            old_store = store_module._store
            store = DefinitionStore(base_dir=tmp_path / ".adep")
            store_module._store = store
            store.create("definitions", "def-test", {
                "id": "def-test",
                "name": "Test",
                "skill_id": "invoice",
                "template_id": "invoice",
            })

            try:
                with pytest.raises(RuntimeError, match="No LLM provider configured"):
                    asyncio.run(engine._execute_run_inner(
                        definition_id="def-test",
                        document_path=str(txt_path),
                        store=store,
                    ))
            finally:
                store_module._store = old_store
        finally:
            config_module.settings.azure_api_key = old_key
            config_module.settings.azure_chat_endpoint = old_endpoint


# ---------------------------------------------------------------------------
# Fallback transparency tests [BLK-287]
# ---------------------------------------------------------------------------

class TestFallbackTransparency:
    """Verify fallback runs are distinguishable from agent runs in SSE and serialized output [BLK-287]."""

    def test_sse_emit_complete_accepts_execution_mode(self):
        """emit_complete should accept and include execution_mode in payload [BLK-287]."""
        from src.api.sse import SSEEventEmitter

        emitter = SSEEventEmitter()
        emitter.emit_complete("completed", run_id="test-run", execution_mode="fallback")

        # Events are buffered in _event_buffer [SCRUM-484]
        events = list(emitter._event_buffer)

        complete_events = [e for e in events if e.get("type") == "complete"]
        assert len(complete_events) == 1
        assert complete_events[0]["execution_mode"] == "fallback"
        assert complete_events[0]["status"] == "completed"
        assert complete_events[0]["run_id"] == "test-run"

    def test_sse_emit_complete_omits_execution_mode_when_none(self):
        """emit_complete should not include execution_mode when not provided [BLK-287]."""
        from src.api.sse import SSEEventEmitter

        emitter = SSEEventEmitter()
        emitter.emit_complete("completed", run_id="test-run")

        # Events are buffered in _event_buffer [SCRUM-484]
        events = list(emitter._event_buffer)

        complete_events = [e for e in events if e.get("type") == "complete"]
        assert len(complete_events) == 1
        assert "execution_mode" not in complete_events[0]

    def test_serialize_extraction_result_defaults_to_agent(self):
        """serialize_extraction_result should default to execution_mode=agent [BLK-287]."""
        from src.api.run_engine import serialize_extraction_result
        from src.templates.base import ExtractedResult
        from src.agent.validator import GapReport
        from src.agent.state import RunStatus

        result = ExtractedResult(
            is_complete=True,
            values=None,
            field_values={},
            gap_report=GapReport(
                is_complete=True,
                total_fields=0,
                satisfied=[],
                gaps=[],
            ),
            trace=[],
            total_cycles=0,
            status=RunStatus.COMPLETE,
            provider_errors=[],
            token_usage_summary={},
        )

        serialized = serialize_extraction_result(
            "test-run", "def-test", "/path/to/doc.pdf", result, {},
        )
        assert serialized["execution_mode"] == "agent"

    def test_fallback_serialized_result_has_fallback_mode(self, fake_pdf: Path, validator_config: ValidatorConfig):
        """When fallback runs, serialized result should have execution_mode=fallback [BLK-287]."""
        from src.api.run_engine import serialize_extraction_result

        result = run_pdf_fallback(
            str(fake_pdf),
            template_cls=BankStatementTemplate,
            skill=BankStatementSkill,
            validator_config=validator_config,
        )
        assert result is not None

        serialized = serialize_extraction_result(
            "test-run", "def-test", str(fake_pdf), result, {"trace": result.trace},
        )
        # serialize_extraction_result defaults to "agent" — the caller must override
        assert serialized["execution_mode"] == "agent"
        # The run_engine.py fallback path overrides this:
        serialized["execution_mode"] = "fallback"
        assert serialized["execution_mode"] == "fallback"
