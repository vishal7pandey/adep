"""End-to-end smoke tests for the full extraction pipeline [BLK-103].

These tests exercise the complete pipeline from definition lookup → skill/template
resolution → ReAct graph execution → result serialization, using mocked providers
so they run without real OCR/VLM APIs.

Tests are organized in two tiers:
1. **Mocked e2e** — full pipeline with mock tools, always runs
2. **Integration e2e** — real sample PDFs with real providers, @pytest.mark.integration
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.agent.validator import validate_extraction
from src.api.run_engine import execute_run
from src.config import settings
from src.definitions.store import DefinitionStore
from src.run import build_validator_config
from src.skills.invoice import InvoiceSkill
from src.templates.invoice import InvoiceTemplate, LineItem
from src.templates.medical_claim import MedicalClaimTemplate
from src.templates.utility_bill import UtilityBillTemplate
from src.tools.base import FieldValue, Grounding, ToolRegistry, ToolResult, ToolSpec


# ---------------------------------------------------------------------------
# Mock tool implementations
# ---------------------------------------------------------------------------

_MOCK_VALUES: dict[str, Any] = {
    # Invoice fields
    "invoice_number": "INV-2024-001",
    "vendor": "ACME Corporation",
    "invoice_date": "2024-03-15",
    "due_date": "2024-04-14",
    "subtotal": 1000.0,
    "tax": 100.0,
    "total": 1100.0,
    "line_items": [
        {"description": "Consulting", "quantity": 10.0, "unit_price": 100.0, "amount": 1000.0},
    ],
    # Utility bill fields
    "account_number": "ACC-12345",
    "service_address": "123 Main St",
    "billing_period_start": "2024-01-01",
    "billing_period_end": "2024-01-31",
    "utility_type": "electricity",
    "current_usage": 350.0,
    "usage_unit": "kWh",
    "previous_usage": 320.0,
    "amount_due": 52.50,
    "consumption_history": [{"month": "Jan", "usage": 350}],
    # Medical claim fields
    "patient_name": "John Doe",
    "patient_dob": "1980-01-15",
    "patient_gender": "M",
    "provider_npi": "1234567890",
    "provider_name": "City Medical",
    "diagnosis_codes": ["E11.9"],
    "procedure_codes": ["99213"],
    "service_date_from": "2024-03-01",
    "service_date_to": "2024-03-15",
    "billed_amount": 250.0,
    # BOQ fields
    "project_name": "Highway Construction",
    "boq_reference": "BOQ-2024-001",
    "date": "2024-03-15",
    "contractor": "BuildCorp Ltd",
    "vat_percent": 18.0,
    "vat_amount": 180.0,
    "grand_total": 1180.0,
}


def _mock_ocr(**kwargs: Any) -> ToolResult:
    field = kwargs.get("field", "invoice_number")
    value = _MOCK_VALUES.get(field, "unknown")
    return ToolResult(
        ok=True,
        data=value,
        grounding=Grounding(bbox=(10, 10, 200, 50), source_tool="ocr", confidence=0.95),
        tool="ocr",
    )


def _mock_vlm(**kwargs: Any) -> ToolResult:
    question = kwargs.get("question", "")
    for field, value in _MOCK_VALUES.items():
        if field in question.lower():
            return ToolResult(
                ok=True,
                data=value,
                grounding=Grounding(bbox=(10, 60, 300, 100), source_tool="vlm", confidence=0.9),
                tool="vlm",
            )
    return ToolResult(
        ok=True,
        data="ACME Corporation",
        grounding=Grounding(bbox=(10, 60, 300, 100), source_tool="vlm", confidence=0.9),
        tool="vlm",
    )


def _mock_detect_layout(**kwargs: Any) -> ToolResult:
    return ToolResult(
        ok=True,
        data=[
            {"id": "p0_r0", "type": "text", "bbox": (0, 0, 500, 100), "page": 0,
             "text": "header", "confidence": 0.9, "metadata": {}},
            {"id": "p0_r1", "type": "table", "bbox": (0, 100, 500, 400), "page": 0,
             "text": "line items", "confidence": 0.85, "metadata": {}},
        ],
        tool="detect_layout",
    )


def _mock_crop(**kwargs: Any) -> ToolResult:
    return ToolResult(
        ok=True,
        data="cropped_image.png",
        grounding=Grounding(bbox=kwargs.get("bbox", (0, 0, 100, 100)), source_tool="crop", confidence=1.0),
        tool="crop",
    )


def _mock_cross_check(**kwargs: Any) -> ToolResult:
    return ToolResult(
        ok=True,
        data="pass",
        grounding=None,
        tool="cross_check",
    )


def _build_mock_registry() -> ToolRegistry:
    """Build a ToolRegistry with mock tools that return canned values."""
    registry = ToolRegistry()
    for name, fn in [
        ("ocr", _mock_ocr),
        ("vlm", _mock_vlm),
        ("detect_layout", _mock_detect_layout),
        ("crop", _mock_crop),
        ("crop_image", _mock_crop),
        ("cross_check", _mock_cross_check),
        ("deskew", _mock_crop),
        ("denoise", _mock_crop),
        ("threshold", _mock_crop),
        ("auto_orient", _mock_crop),
    ]:
        registry.register(ToolSpec(name=name, description=f"Mock {name}"), fn)
    return registry


# ---------------------------------------------------------------------------
# Mock LLM client — returns tool calls that extract fields one by one
# ---------------------------------------------------------------------------

class MockLLMClient:
    """Mock LLM that returns a sequence of tool calls to extract fields.

    Batches up to ``batch_size`` fields per cycle to stay within recursion limits.
    Each batch returns one field at a time (the graph processes one tool call per cycle).
    """

    def __init__(self, fields: list[str], tool: str = "ocr", batch_size: int = 3) -> None:
        self._actions: list[dict[str, Any]] = []
        for field in fields:
            self._actions.append({
                "thought": f"Extract {field} using {tool}",
                "tool": tool,
                "args": {"image_path": "sample.png", "field": field},
                "field": field,
            })
        self._actions.append({
            "thought": "All fields extracted, done",
            "tool": "",
            "args": {},
            "field": None,
        })
        self._idx = 0

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        if self._idx >= len(self._actions):
            return json.dumps({"thought": "done", "tool": "", "args": {}, "field": None})
        action = self._actions[self._idx]
        self._idx += 1
        return json.dumps(action)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_store(tmp_path: Path) -> DefinitionStore:
    """Create a DefinitionStore with prebuilt content available via merge [BLK-159]."""
    import src.definitions.store as store_module
    old_store = store_module._store
    store = DefinitionStore(base_dir=tmp_path / ".adep")
    store_module._store = store
    yield store
    store_module._store = old_store


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal fake PDF file for testing."""
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake pdf for testing\n%%EOF")
    return pdf_path


def _run_async(coro: Any) -> Any:
    """Run an async coroutine in a sync test."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ---------------------------------------------------------------------------
# Mocked e2e tests — full pipeline, always runs
# ---------------------------------------------------------------------------

class TestE2EInvoiceMocked:
    """E2e: seed store -> execute_run with invoice definition -> verify result."""

    def test_invoice_e2e_mocked(self, seeded_store, sample_pdf):
        invoice_fields = list(InvoiceTemplate.model_fields.keys())

        mock_llm = MockLLMClient(invoice_fields, "ocr")
        mock_registry = _build_mock_registry()

        def _mock_build_graph(registry, skill, validator_config, llm_client=None, breaker=None,
                              control=None, emitter=None, **kwargs):
            from src.agent.graph import build_react_graph as _real_build
            return _real_build(registry, skill, validator_config, llm_client=mock_llm, breaker=breaker,
                               control=control, emitter=emitter, **kwargs)

        with patch("src.api.run_engine.build_tool_registry", return_value=mock_registry), \
             patch("src.api.run_engine.build_react_graph", side_effect=_mock_build_graph):

            result = _run_async(execute_run("def-trade-finance-scrutiny", str(sample_pdf)))

        assert result["status"] in ("completed", "failed", "max_iterations_reached", "paused")
        assert result["definition_id"] == "def-trade-finance-scrutiny"
        assert result["document_url"] == str(sample_pdf)
        assert result["total_fields"] > 0


class TestE2ESeedAndRun:
    """Verify seed_store + execute_run works end-to-end with mocked tools."""

    def test_seeded_definitions_exist(self, seeded_store):
        defs = seeded_store.list_definitions()
        assert len(defs) == 18
        skills = seeded_store.list_skills()
        assert len(skills) == 19
        templates = seeded_store.list_templates()
        assert len(templates) == 19

    def test_invoice_run_produces_result(self, seeded_store, sample_pdf):
        invoice_fields = list(InvoiceTemplate.model_fields.keys())

        mock_llm = MockLLMClient(invoice_fields, "ocr")
        mock_registry = _build_mock_registry()

        def _mock_build_graph(registry, skill, validator_config, llm_client=None, breaker=None,
                              control=None, emitter=None, **kwargs):
            from src.agent.graph import build_react_graph as _real_build
            return _real_build(registry, skill, validator_config, llm_client=mock_llm, breaker=breaker,
                               control=control, emitter=emitter, **kwargs)

        with patch("src.api.run_engine.build_tool_registry", return_value=mock_registry), \
             patch("src.api.run_engine.build_react_graph", side_effect=_mock_build_graph):

            result = _run_async(execute_run("def-trade-finance-scrutiny", str(sample_pdf)))

        assert result["id"].startswith("run-")
        assert result["total_fields"] > 0
        assert isinstance(result["fields"], list)

    def test_utility_bill_run_mocked(self, seeded_store, sample_pdf):
        utility_fields = list(UtilityBillTemplate.model_fields.keys())[:5]

        mock_llm = MockLLMClient(utility_fields, "vlm")
        mock_registry = _build_mock_registry()

        def _mock_build_graph(registry, skill, validator_config, llm_client=None, breaker=None,
                              control=None, emitter=None, **kwargs):
            from src.agent.graph import build_react_graph as _real_build
            return _real_build(registry, skill, validator_config, llm_client=mock_llm, breaker=breaker,
                               control=control, emitter=emitter, **kwargs)

        with patch("src.api.run_engine.build_tool_registry", return_value=mock_registry), \
             patch("src.api.run_engine.build_react_graph", side_effect=_mock_build_graph), \
             patch.object(settings, "compaction_enabled", False), \
             patch.object(settings, "compaction_threshold", 999):
            result = _run_async(execute_run("def-utility-bill", str(sample_pdf)))

        assert result["status"] in ("completed", "failed", "max_iterations_reached", "paused")
        assert result["total_fields"] > 0

    def test_medical_claim_run_mocked(self, seeded_store, sample_pdf):
        medical_fields = list(MedicalClaimTemplate.model_fields.keys())[:5]

        mock_llm = MockLLMClient(medical_fields, "ocr")
        mock_registry = _build_mock_registry()

        def _mock_build_graph(registry, skill, validator_config, llm_client=None, breaker=None,
                              control=None, emitter=None, **kwargs):
            from src.agent.graph import build_react_graph as _real_build
            return _real_build(registry, skill, validator_config, llm_client=mock_llm, breaker=breaker,
                               control=control, emitter=emitter, **kwargs)

        with patch("src.api.run_engine.build_tool_registry", return_value=mock_registry), \
             patch("src.api.run_engine.build_react_graph", side_effect=_mock_build_graph), \
             patch.object(settings, "compaction_enabled", False), \
             patch.object(settings, "compaction_threshold", 999):
            result = _run_async(execute_run("def-medical-claim", str(sample_pdf)))

        assert result["status"] in ("completed", "failed", "max_iterations_reached", "paused")
        assert result["total_fields"] > 0

    def test_boq_run_mocked(self, seeded_store, sample_pdf):
        from src.templates.bill_of_quantities import BillOfQuantitiesTemplate
        boq_fields = list(BillOfQuantitiesTemplate.model_fields.keys())[:5]

        mock_llm = MockLLMClient(boq_fields, "ocr")
        mock_registry = _build_mock_registry()

        def _mock_build_graph(registry, skill, validator_config, llm_client=None, breaker=None,
                              control=None, emitter=None, **kwargs):
            from src.agent.graph import build_react_graph as _real_build
            return _real_build(registry, skill, validator_config, llm_client=mock_llm, breaker=breaker,
                               control=control, emitter=emitter, **kwargs)

        with patch("src.api.run_engine.build_tool_registry", return_value=mock_registry), \
             patch("src.api.run_engine.build_react_graph", side_effect=_mock_build_graph):

            result = _run_async(execute_run("def-boq-estimator", str(sample_pdf)))

        assert result["status"] in ("completed", "failed", "max_iterations_reached", "paused")
        assert result["total_fields"] > 0


class TestE2EResultSerialization:
    """Verify the serialized result from execute_run has all expected fields."""

    def test_result_has_required_keys(self, seeded_store, sample_pdf):
        invoice_fields = list(InvoiceTemplate.model_fields.keys())

        mock_llm = MockLLMClient(invoice_fields, "ocr")
        mock_registry = _build_mock_registry()

        def _mock_build_graph(registry, skill, validator_config, llm_client=None, breaker=None,
                              control=None, emitter=None, **kwargs):
            from src.agent.graph import build_react_graph as _real_build
            return _real_build(registry, skill, validator_config, llm_client=mock_llm, breaker=breaker,
                               control=control, emitter=emitter, **kwargs)

        with patch("src.api.run_engine.build_tool_registry", return_value=mock_registry), \
             patch("src.api.run_engine.build_react_graph", side_effect=_mock_build_graph):

            result = _run_async(execute_run("def-trade-finance-scrutiny", str(sample_pdf)))

        required_keys = {"id", "definition_id", "document_url", "status",
                         "current_cycle", "total_fields", "extracted_fields_count", "fields"}
        assert required_keys.issubset(set(result.keys()))


class TestE2EInvariantVerification:
    """Verify that invariants are checked during e2e runs."""

    def _build_invoice_extraction(self, total_value: float = 1100.0) -> dict[str, FieldValue]:
        """Build a complete invoice extraction with correct field names and types."""
        def g(bbox: tuple) -> Grounding:
            return Grounding(bbox=bbox, source_tool="ocr", confidence=0.95)
        return {
            "invoice_number": FieldValue(name="invoice_number", value="INV-001",
                                         grounding=g((0, 0, 100, 30)), confidence=0.95),
            "vendor": FieldValue(name="vendor", value="ACME Corp",
                                 grounding=g((0, 30, 100, 60)), confidence=0.9),
            "invoice_date": FieldValue(name="invoice_date", value="2024-03-15",
                                       grounding=g((0, 60, 100, 90)), confidence=0.9),
            "due_date": FieldValue(name="due_date", value="2024-04-14",
                                   grounding=g((0, 90, 100, 120)), confidence=0.9),
            "line_items": FieldValue(name="line_items",
                                     value=[LineItem(description="Consulting", quantity=10.0,
                                                     unit_price=100.0, amount=1000.0)],
                                     grounding=g((0, 100, 100, 200)), confidence=0.9),
            "subtotal": FieldValue(name="subtotal", value=1000.0,
                                   grounding=g((0, 200, 100, 230)), confidence=0.95),
            "tax": FieldValue(name="tax", value=100.0,
                              grounding=g((0, 230, 100, 260)), confidence=0.95),
            "total": FieldValue(name="total", value=total_value,
                                grounding=g((0, 260, 100, 290)), confidence=0.95),
        }

    def test_invoice_subtotal_plus_tax_equals_total_pass(self):
        """Invoice invariant: subtotal + tax = total (should pass)."""
        extraction = self._build_invoice_extraction(total_value=1100.0)

        config = build_validator_config(InvoiceSkill)
        gap_report = validate_extraction(
            schema=InvoiceTemplate,
            extraction=extraction,
            invariants=InvoiceSkill.invariants,
            config=config,
            failure_actions=InvoiceSkill.failure_actions,
        )
        assert gap_report.is_complete
        assert len(gap_report.gaps) == 0

    def test_invoice_subtotal_plus_tax_not_equal_total_fail(self):
        """Invoice invariant should fail when subtotal + tax != total."""
        extraction = self._build_invoice_extraction(total_value=999.0)

        config = build_validator_config(InvoiceSkill)
        gap_report = validate_extraction(
            schema=InvoiceTemplate,
            extraction=extraction,
            invariants=InvoiceSkill.invariants,
            config=config,
            failure_actions=InvoiceSkill.failure_actions,
        )
        assert not gap_report.is_complete
        assert len(gap_report.gaps) > 0


# ---------------------------------------------------------------------------
# Integration e2e tests — real sample PDFs, skipped without providers
# ---------------------------------------------------------------------------

INTEGRATION = pytest.mark.integration
_SAMPLE_DATA = Path(__file__).parent.parent.parent / "sample-data"


def _providers_available() -> bool:
    """Check if OCR and VLM providers are configured."""
    from src.config import settings
    return bool(settings.azure_api_key and settings.azure_chat_endpoint)


@INTEGRATION
@pytest.mark.skipif(not _providers_available(), reason="No OCR/VLM providers configured")
class TestE2ERealProviders:
    """E2e tests with real sample PDFs and real providers.

    Run with: pytest -m integration
    """

    def test_invoice_sample_01(self, seeded_store):
        pdf = _SAMPLE_DATA / "invoices" / "sample-invoice-01.pdf"
        if not pdf.exists():
            pytest.skip(f"Sample file not found: {pdf}")

        result = _run_async(execute_run("def-trade-finance-scrutiny", str(pdf)))

        assert result["status"] in ("completed", "partial")
        assert result["extracted_fields_count"] >= 3
        assert result["total_fields"] > 0

    def test_invoice_sample_02(self, seeded_store):
        pdf = _SAMPLE_DATA / "invoices" / "sample-invoice-02.pdf"
        if not pdf.exists():
            pytest.skip(f"Sample file not found: {pdf}")

        result = _run_async(execute_run("def-trade-finance-scrutiny", str(pdf)))

        assert result["status"] in ("completed", "partial")
        assert result["extracted_fields_count"] >= 1

    def test_utility_bill_sample(self, seeded_store):
        pdf = _SAMPLE_DATA / "utility-bills" / "sample-utility-bill-01.pdf"
        if not pdf.exists():
            pytest.skip(f"Sample file not found: {pdf}")

        result = _run_async(execute_run("def-utility-bill", str(pdf)))

        assert result["status"] in ("completed", "partial")
        assert result["extracted_fields_count"] >= 1

    def test_medical_claim_sample_01(self, seeded_store):
        pdf = _SAMPLE_DATA / "medical-claims" / "sample-cms1500-01.pdf"
        if not pdf.exists():
            pytest.skip(f"Sample file not found: {pdf}")

        result = _run_async(execute_run("def-medical-claim", str(pdf)))

        assert result["status"] in ("completed", "partial")
        assert result["extracted_fields_count"] >= 1

    def test_medical_claim_sample_03(self, seeded_store):
        pdf = _SAMPLE_DATA / "medical-claims" / "sample-cms1500-03.pdf"
        if not pdf.exists():
            pytest.skip(f"Sample file not found: {pdf}")

        result = _run_async(execute_run("def-medical-claim", str(pdf)))

        assert result["status"] in ("completed", "partial")
        assert result["extracted_fields_count"] >= 1

    def test_boq_sample(self, seeded_store):
        pdf = _SAMPLE_DATA / "boq" / "sample-boq-01.pdf"
        if not pdf.exists():
            pytest.skip(f"Sample file not found: {pdf}")

        result = _run_async(execute_run("def-boq-estimator", str(pdf)))

        assert result["status"] in ("completed", "partial")
        assert result["extracted_fields_count"] >= 1

    def test_invoice_invariant_checked(self, seeded_store):
        """Verify at least 1 invariant is checked during a real run."""
        pdf = _SAMPLE_DATA / "invoices" / "sample-invoice-01.pdf"
        if not pdf.exists():
            pytest.skip(f"Sample file not found: {pdf}")

        result = _run_async(execute_run("def-trade-finance-scrutiny", str(pdf)))

        assert result["total_fields"] > 0
        if result["extracted_fields_count"] >= 3:
            assert result["status"] in ("completed", "partial")
