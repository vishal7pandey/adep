"""Run engine wiring — connects API layer to Phase 1 engine [BLK-024].

Loads an AgentDefinition from the store, resolves skill + template refs,
builds the ToolRegistry, invokes the ReAct graph, and emits SSE events
for real-time streaming to the frontend Agent Console.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

from pydantic import Field, create_model

from src.agent.graph import CircuitBreaker, build_react_graph
from src.agent.oneflow import build_oneflow_graph
from src.agent.state import AgentState, RunStatus
from src.agent.token_tracking import summarize_token_usage, save_token_usage, update_aggregate_stats
from src.agent.validator import GapType, ValidatorConfig, validate_extraction
from src.agent.webhooks import emit_webhook_event_async, status_to_webhook_event, WebhookEvent
from src.api.sse import SSEEventEmitter
from src.api.status import map_store_status_to_sse, map_status_to_frontend
from src.config import settings
from src.definitions.store import DefinitionStore, get_store
from src.fallback.pdf_runtime import run_pdf_fallback
from src.providers.llm import invoke_llm
from src.run import build_initial_state, build_tool_registry, build_validator_config
from src.skills.base import Skill

if TYPE_CHECKING:
    from src.api.run_executor import RunControl

from src.observability.context import set_context, run_id_var, definition_id_var
from src.observability.tracing import span, mark_error
from src.observability.redaction import hash_prompt
from src.skills.invoice import InvoiceSkill
from src.skills.trade_finance import TradeFinanceScrutinySkill
from src.skills.bill_of_quantities import BillOfQuantitiesSkill
from src.skills.utility_bill import UtilityBillSkill
from src.skills.thermal_receipt import ThermalReceiptSkill
from src.skills.medical_claim import MedicalClaimSkill
from src.skills.compliance_audit import ComplianceAuditSkill
from src.skills.commercial_lease import CommercialLeaseSkill
from src.skills.commodity_trade import CommodityTradeSkill
from src.skills.metallurgical_assay import MetallurgicalAssaySkill
from src.skills.store_audit import StoreAuditSkill
from src.skills.ad_buy import AdBuySkill
from src.skills.bank_statement import BankStatementSkill
from src.skills.purchase_order import PurchaseOrderSkill
from src.skills.purchase_order_sf1449 import PurchaseOrderSF1449Skill
from src.skills.packing_list import PackingListSkill
from src.skills.packing_list_travel import TravelPackingChecklistSkill
from src.skills.w2_tax_form import W2TaxFormSkill
from src.skills.pay_stub import PayStubSkill
from src.skills.insurance_policy import InsurancePolicySkill
from src.skills.pid_diagram import PnIDSkill
from src.templates.base import ExtractedResult, Template
from src.templates.invoice import InvoiceTemplate
from src.templates.trade_finance import TradeFinanceTemplate
from src.templates.bill_of_quantities import BillOfQuantitiesTemplate
from src.templates.utility_bill import UtilityBillTemplate
from src.templates.thermal_receipt import ThermalReceiptTemplate
from src.templates.medical_claim import MedicalClaimTemplate
from src.templates.compliance_audit import ComplianceAuditTemplate
from src.templates.commercial_lease import CommercialLeaseTemplate
from src.templates.commodity_trade import CommodityTradeTemplate
from src.templates.metallurgical_assay import MetallurgicalAssayTemplate
from src.templates.store_audit import StoreAuditTemplate
from src.templates.ad_insertion_order import AdInsertionOrderTemplate
from src.templates.bank_statement import BankStatementTemplate
from src.templates.purchase_order import PurchaseOrderTemplate
from src.templates.purchase_order_sf1449 import PurchaseOrderSF1449Template
from src.templates.packing_list import PackingListTemplate
from src.templates.packing_list_travel import TravelPackingChecklistTemplate
from src.templates.w2_tax_form import W2TaxFormTemplate
from src.templates.pay_stub import PayStubTemplate
from src.templates.insurance_policy import InsurancePolicyTemplate
from src.templates.pid_diagram import PnIDContract

logger = logging.getLogger(__name__)


class _PlannerLLMClient:
    """Adapter exposing the ``invoke`` method expected by graph nodes."""

    def invoke(self, system_prompt: str, user_prompt: str) -> Any:
        return invoke_llm(system_prompt, user_prompt)


def _build_planner_client() -> Any | None:
    """Return an LLM client when Azure planner settings are configured."""
    if settings.azure_api_key and settings.azure_chat_endpoint:
        return _PlannerLLMClient()
    return None

# Skill registry — maps skill IDs to Skill instances [BLK-088]
_SKILL_REGISTRY: dict[str, Skill] = {
    "invoice": InvoiceSkill,
    "sk-invoice-basic": InvoiceSkill,
    "trade_finance_scrutiny": TradeFinanceScrutinySkill,
    "bill_of_quantities": BillOfQuantitiesSkill,
    "utility_bill": UtilityBillSkill,
    "thermal_receipt": ThermalReceiptSkill,
    "medical_claim": MedicalClaimSkill,
    "compliance_audit": ComplianceAuditSkill,
    "commercial_lease": CommercialLeaseSkill,
    "commodity_trade": CommodityTradeSkill,
    "metallurgical_assay": MetallurgicalAssaySkill,
    "store_audit": StoreAuditSkill,
    "ad_buy": AdBuySkill,
    "bank_statement": BankStatementSkill,
    "purchase_order": PurchaseOrderSkill,
    "purchase_order_sf1449": PurchaseOrderSF1449Skill,
    "packing_list": PackingListSkill,
    "packing_list_travel": TravelPackingChecklistSkill,
    "w2_tax_form": W2TaxFormSkill,
    "pay_stub": PayStubSkill,
    "insurance_policy": InsurancePolicySkill,
    "pid_to_dexpi": PnIDSkill,
}

# Template registry — maps template IDs to Template classes [BLK-088]
_TEMPLATE_REGISTRY: dict[str, type[Template]] = {
    "invoice": InvoiceTemplate,
    "tmpl-invoice-standard": InvoiceTemplate,
    "trade_finance_mt700": TradeFinanceTemplate,
    "trade_finance": TradeFinanceTemplate,
    "bill_of_quantities": BillOfQuantitiesTemplate,
    "utility_bill": UtilityBillTemplate,
    "thermal_receipt": ThermalReceiptTemplate,
    "medical_claim_cms1500": MedicalClaimTemplate,
    "medical_claim": MedicalClaimTemplate,
    "compliance_audit_soc2": ComplianceAuditTemplate,
    "compliance_audit": ComplianceAuditTemplate,
    "commercial_lease": CommercialLeaseTemplate,
    "commodity_trade_assay": CommodityTradeTemplate,
    "commodity_trade": CommodityTradeTemplate,
    "metallurgical_assay": MetallurgicalAssayTemplate,
    "store_audit_checklist": StoreAuditTemplate,
    "store_audit": StoreAuditTemplate,
    "ad_insertion_order": AdInsertionOrderTemplate,
    "bank_statement": BankStatementTemplate,
    "purchase_order": PurchaseOrderTemplate,
    "purchase_order_sf1449": PurchaseOrderSF1449Template,
    "packing_list": PackingListTemplate,
    "packing_list_travel": TravelPackingChecklistTemplate,
    "w2_tax_form": W2TaxFormTemplate,
    "pay_stub": PayStubTemplate,
    "insurance_policy": InsurancePolicyTemplate,
    "pid_to_dexpi": PnIDContract,
}


def _parse_failure_actions(raw_actions: dict[str, str] | None) -> dict[GapType, str]:
    """Convert serialized gap type keys into GapType enums."""
    parsed: dict[GapType, str] = {}
    for key, value in (raw_actions or {}).items():
        try:
            parsed[GapType(key)] = value
        except ValueError:
            logger.debug("Ignoring unknown failure action gap type: %s", key)
    return parsed


def _annotation_from_type_name(type_name: str) -> Any:
    """Map stored template field types to Python annotations."""
    mapping: dict[str, Any] = {
        "string": str,
        "float": float,
        "int": int,
        "date": str,
        "boolean": bool,
        "list": list[dict[str, Any]],
    }
    return mapping.get(type_name, str)


def _build_dynamic_skill(skill_ref: str, store: DefinitionStore) -> Skill:
    """Build a runtime Skill from store metadata."""
    skill_data = store.get_skill(skill_ref)
    probe_order: list[tuple[str, str]] = []
    for step in skill_data.get("probe_order", []):
        if isinstance(step, dict):
            probe_order.append((step.get("region_type", "unknown"), step.get("rationale", "")))
        elif isinstance(step, (list, tuple)) and len(step) >= 2:
            probe_order.append((str(step[0]), str(step[1])))

    return Skill(
        name=skill_data.get("id", skill_ref),
        system_prompt=skill_data.get("system_prompt", ""),
        tool_preferences=dict(skill_data.get("tool_preferences", {})),
        probe_order=probe_order,
        invariants=[],
        failure_actions=_parse_failure_actions(skill_data.get("failure_actions")),
        known_failures=skill_data.get("known_failures", ""),
        confidence_overrides=dict(skill_data.get("confidence_overrides", {})),
    )


def _build_dynamic_template(template_ref: str, store: DefinitionStore) -> type[Template]:
    """Build a runtime Pydantic template model from store metadata."""
    template_data = store.get_template(template_ref)
    field_definitions: dict[str, tuple[Any, Any]] = {}
    for field_data in template_data.get("fields", []):
        field_name = field_data.get("name")
        if not field_name:
            continue
        annotation = _annotation_from_type_name(field_data.get("type", "string"))
        required = field_data.get("required", True)
        if not required:
            annotation = annotation | None
        field_definitions[field_name] = (
            annotation,
            Field(
                default=... if required else None,
                description=field_data.get("description", ""),
            ),
        )

    model_name = "".join(part.capitalize() for part in template_ref.replace("-", "_").split("_")) or "DynamicTemplate"
    dynamic_model = create_model(model_name, __base__=Template, **field_definitions)
    dynamic_model.__doc__ = template_data.get("description", "Runtime-generated template")
    return dynamic_model


def _serialize_json_safe(value: Any) -> Any:
    """Convert nested values into JSON-safe primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _serialize_json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_json_safe(item) for item in value]
    return str(value)


def _serialize_grounding(grounding: Any) -> dict[str, Any] | None:
    """Serialize Grounding for persisted verifier payloads."""
    if grounding is None:
        return None
    return {
        "bbox": list(grounding.bbox),
        "page": grounding.page,
        "region_id": grounding.region_id,
        "source_tool": grounding.source_tool,
        "confidence": grounding.confidence,
    }


def _serialize_trace(trace: list[Any]) -> list[dict[str, Any]]:
    """Serialize trace entries for run-scoped verification."""
    serialized: list[dict[str, Any]] = []
    for entry in trace:
        serialized.append({
            "step": entry.step,
            "thought": entry.thought,
            "tool_name": entry.tool_name,
            "tool_args": _serialize_json_safe(entry.tool_args),
            "field": entry.field,
            "result_summary": entry.result_summary,
            "result": {
                "ok": entry.result.ok,
                "error": entry.result.error,
                "tool": entry.result.tool,
                "grounding": _serialize_grounding(entry.result.grounding),
                "cost": _serialize_json_safe(entry.result.cost),
                "data": _serialize_json_safe(entry.result.data),
            },
        })
    return serialized


def _serialize_gap_report_payload(gap_report: Any) -> dict[str, Any]:
    """Serialize GapReport for run-scoped verification."""
    return {
        "total_fields": gap_report.total_fields,
        "is_complete": gap_report.is_complete,
        "satisfied": [{"field": field_name} for field_name in gap_report.satisfied],
        "gaps": [
            {
                "field": gap.field,
                "gap_type": gap.gap_type.value,
                "detail": gap.detail,
                "current_value": _serialize_json_safe(gap.current_value),
                "current_confidence": gap.current_confidence,
                "suggested_action": gap.suggested_action,
                "last_error": gap.last_error,
                "last_tool": gap.last_tool,
            }
            for gap in gap_report.gaps
        ],
    }


def _serialize_extraction_payload(extraction: dict[str, Any]) -> dict[str, Any]:
    """Serialize extracted field values for run-scoped verification."""
    payload: dict[str, Any] = {}
    for name, field_value in extraction.items():
        payload[name] = {
            "value": _serialize_json_safe(field_value.value),
            "confidence": field_value.confidence,
            "attempts": field_value.attempts,
            "grounding": _serialize_grounding(field_value.grounding),
        }
    return payload


def _canonicalize_definition_for_document(
    definition_id: str,
    document_path: str,
    store: DefinitionStore,
) -> str:
    """Select a better-matched definition variant for known document subtypes."""
    name = Path(document_path).name.lower()
    if definition_id == "def-purchase-order" and "sf1449" in name:
        try:
            store.get_definition("def-purchase-order-sf1449")
            return "def-purchase-order-sf1449"
        except FileNotFoundError:
            return definition_id
    if definition_id == "def-packing-list" and "travel" in name:
        try:
            store.get_definition("def-packing-list-travel")
            return "def-packing-list-travel"
        except FileNotFoundError:
            return definition_id
    return definition_id


def resolve_skill(skill_ref: str, store: DefinitionStore | None = None) -> Skill:
    """Resolve a skill reference to a Skill instance.

    Raises:
        ValueError: If the skill is not found.
    """
    skill = _SKILL_REGISTRY.get(skill_ref)
    if skill is None:
        if store is None:
            store = get_store()
        try:
            return _build_dynamic_skill(skill_ref, store)
        except FileNotFoundError as exc:
            raise ValueError(f"Unknown skill: {skill_ref}") from exc
    return skill


def resolve_template(template_ref: str, store: DefinitionStore | None = None) -> type[Template]:
    """Resolve a template reference to a Template class.

    Raises:
        ValueError: If the template is not found.
    """
    template = _TEMPLATE_REGISTRY.get(template_ref)
    if template is None:
        if store is None:
            store = get_store()
        try:
            return _build_dynamic_template(template_ref, store)
        except FileNotFoundError as exc:
            raise ValueError(f"Unknown template: {template_ref}") from exc
    return template


def map_status_to_frontend(status: str) -> str:
    """Map internal RunStatus to frontend ExtractionRun.status [BLK-280].

    Delegates to the canonical mapping in ``src.api.status``.
    """
    from src.api.status import map_status_to_frontend as _map
    return _map(status)


def map_field_status(confidence: float, grounded: bool, is_complete: bool) -> str:
    """Map field confidence/grounding to frontend ExtractedField.status."""
    if not grounded or confidence < 0.5:
        return "failed"
    if confidence < 0.8:
        return "low_confidence"
    return "verified"


def bbox_to_frontend(bbox: tuple[int, int, int, int]) -> dict[str, int]:
    """Convert internal (x1,y1,x2,y2) bbox to frontend {x,y,width,height}."""
    x1, y1, x2, y2 = bbox
    return {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}


def serialize_extraction_result(
    run_id: str,
    definition_id: str,
    document_path: str,
    result: ExtractedResult,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Serialize a RunResult + state to the frontend ExtractionRun shape.

    Handles both FieldExtractionResult and GraphExtractionResult [BLK-169].
    """
    from src.templates.base import GraphExtractionResult

    if isinstance(result, GraphExtractionResult):
        return _serialize_graph_result(run_id, definition_id, document_path, result, state)

    fields = []
    for name, fv in result.field_values.items():
        bbox = None
        page = 0
        if fv.grounding:
            bbox = bbox_to_frontend(fv.grounding.bbox)
            page = fv.grounding.page
        fields.append({
            "id": f"{run_id}_{name}",
            "name": name,
            "value": fv.value,
            "confidence": fv.confidence,
            "bbox": bbox,
            "page": page,
            "status": map_field_status(fv.confidence, fv.grounding is not None, result.is_complete),
        })

    return {
        "id": run_id,
        "definition_id": definition_id,
        "document_url": document_path,
        "status": map_status_to_frontend(result.status),
        "current_cycle": result.total_cycles,
        "total_fields": result.gap_report.total_fields,
        "extracted_fields_count": len(result.gap_report.satisfied),
        "fields": fields,
        "total_cost_usd": result.token_usage_summary.get("total_cost_usd", 0.0),
        "total_tokens": result.token_usage_summary.get("total_tokens", 0),
        "verifier_payload": {
            "trace": _serialize_trace(result.trace),
            "gap_report": _serialize_gap_report_payload(result.gap_report),
            "extraction": _serialize_extraction_payload(result.field_values),
        },
        "task_type": state.get("task_type", "extraction"),
        "execution_mode": "agent",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def _serialize_graph_result(
    run_id: str,
    definition_id: str,
    document_path: str,
    result: GraphExtractionResult,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Serialize a GraphExtractionResult for the frontend [BLK-169]."""
    nodes = result.graph.get("nodes", [])
    edges = result.graph.get("edges", [])

    graph_fields = []
    for node in nodes:
        nid = node.get("id", "")
        bbox = result.node_grounding.get(nid)
        graph_fields.append({
            "id": f"{run_id}_node_{nid}",
            "name": nid,
            "value": node.get("tag") or node.get("type", "unknown"),
            "confidence": node.get("confidence", 0.0),
            "bbox": bbox_to_frontend(bbox) if bbox else None,
            "page": 0,
            "status": "verified" if node.get("confidence", 0) >= 0.8 else "low_confidence",
        })

    return {
        "id": run_id,
        "definition_id": definition_id,
        "document_url": document_path,
        "status": map_status_to_frontend(result.status),
        "current_cycle": result.total_cycles,
        "total_fields": len(nodes),
        "extracted_fields_count": len(nodes),
        "fields": graph_fields,
        "total_cost_usd": result.token_usage_summary.get("total_cost_usd", 0.0),
        "total_tokens": result.token_usage_summary.get("total_tokens", 0),
        "verifier_payload": {
            "trace": _serialize_trace(result.trace),
            "gap_report": _serialize_gap_report_payload(result.gap_report),
            "extraction": {},
        },
        "task_type": "graph_extraction",
        "execution_mode": "agent",
        "graph": {
            "nodes": nodes,
            "edges": edges,
            "node_grounding": {
                nid: list(bbox) if isinstance(bbox, (tuple, list)) else bbox
                for nid, bbox in result.node_grounding.items()
            },
            "edge_grounding": {
                eid: [list(b) if isinstance(b, (tuple, list)) else b for b in path]
                for eid, path in result.edge_grounding.items()
            },
            "serialized_output": result.serialized_output,
            "topology_violations": _extract_topology_violations(result.trace),
        },
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def _extract_topology_violations(trace: list[Any]) -> list[dict[str, Any]]:
    """Extract topology validation results from trace entries [BLK-169]."""
    violations: list[dict[str, Any]] = []
    for entry in trace:
        if not hasattr(entry, "result") or not entry.result or not entry.result.ok:
            continue
        data = entry.result.data
        if isinstance(data, dict) and entry.tool_name == "validate_topology":
            violations = data.get("violations", [])
    return violations


async def execute_run(
    definition_id: str,
    document_path: str,
    emitter: SSEEventEmitter | None = None,
) -> dict[str, Any]:
    """Execute a run synchronously (legacy v1 — kept for backward compat).

    Use execute_run_async for async execution with live SSE and control [BLK-129].
    """
    return await _execute_run_impl(
        definition_id=definition_id,
        document_path=document_path,
        emitter=emitter,
        control=None,
        run_id=None,
        event_buffer=None,
    )


async def execute_run_async(
    run_id: str,
    definition_id: str,
    document_path: str,
    emitter: SSEEventEmitter | None = None,
    control: RunControl | None = None,
    event_buffer: list | None = None,
) -> dict[str, Any]:
    """Execute a run asynchronously with live SSE and cooperative control [BLK-129].

    Runs the LangGraph invoke in a background thread via asyncio.to_thread().
    SSE events are emitted live as graph nodes execute. Cooperative pause/cancel
    flags are checked at cycle boundaries.

    Args:
        run_id: Pre-assigned run ID.
        definition_id: The AgentDefinition ID to use.
        document_path: Path to the document to extract.
        emitter: SSE emitter for live streaming.
        control: RunControl for cooperative pause/cancel.
        event_buffer: Buffer to store events for late subscribers.

    Returns:
        Serialized ExtractionRun dict matching frontend types.
    """
    return await _execute_run_impl(
        definition_id=definition_id,
        document_path=document_path,
        emitter=emitter,
        control=control,
        run_id=run_id,
        event_buffer=event_buffer,
    )


async def _execute_run_impl(
    definition_id: str,
    document_path: str,
    emitter: SSEEventEmitter | None = None,
    control: RunControl | None = None,
    run_id: str | None = None,
    event_buffer: list | None = None,
) -> dict[str, Any]:
    """Internal implementation shared by sync and async execute_run [BLK-129].

    Loads the definition, resolves skill/template, builds the graph,
    invokes it, emits SSE events, and returns the serialized result.

    Args:
        definition_id: The AgentDefinition ID to use.
        document_path: Path to the document to extract.
        emitter: Optional SSE emitter for streaming events.
        control: Optional RunControl for cooperative pause/cancel.
        run_id: Optional pre-assigned run ID.
        event_buffer: Optional buffer for late SSE subscribers.

    Returns:
        Serialized ExtractionRun dict matching frontend types.
    """
    store = get_store()
    if run_id is None:
        run_id = f"run-{uuid.uuid4().hex[:8]}"

    # Set context for structured logging + tracing [BLK-130]
    with set_context(run_id=run_id, definition_id=definition_id), \
         span("run:execute", run_id=run_id, definition_id=definition_id):
        return await _execute_run_inner(
            definition_id=definition_id,
            document_path=document_path,
            emitter=emitter,
            control=control,
            run_id=run_id,
            event_buffer=event_buffer,
            store=store,
        )


async def _execute_run_inner(
    definition_id: str,
    document_path: str,
    emitter: SSEEventEmitter | None = None,
    control: RunControl | None = None,
    run_id: str | None = None,
    event_buffer: list | None = None,
    store: DefinitionStore | None = None,
) -> dict[str, Any]:
    """Inner implementation — called within context + tracing scope [BLK-130]."""
    # BLK-173: Fail fast on partial provider config before doing any work
    settings.validate_provider_config()

    if store is None:
        store = get_store()

    definition_id = _canonicalize_definition_for_document(definition_id, document_path, store)

    # Load definition from store
    try:
        def_data = store.get_definition(definition_id)
    except FileNotFoundError:
        raise ValueError(f"Definition not found: {definition_id}")

    # Resolve skill and template (support both skill_id and skill_ref for backward compat) [BLK-091]
    skill_ref = def_data.get("skill_id", "") or def_data.get("skill_ref", "")
    template_ref = def_data.get("template_id", "") or def_data.get("template_ref", "")
    skill = resolve_skill(skill_ref, store)
    template_cls = resolve_template(template_ref, store)

    # Build state, registry, config
    task_type = def_data.get("task_type", "extraction")
    tool_names = def_data.get("tool_names", [])

    # Apply definition overrides [BLK-094, BLK-284]
    agent_config = def_data.get("agent_config", {})
    max_cycles = agent_config.get("max_cycles_per_document")
    max_cycles_per_field = agent_config.get("max_cycles_per_field")
    confidence_threshold = agent_config.get("confidence_threshold")

    # Resolve page_paths from DocumentStore for multi-page documents [BLK-220]
    page_paths: list[str] | None = None
    try:
        from src.documents.store import get_document_store
        doc_store = get_document_store()
        try:
            doc_meta = doc_store.get_document(document_path)
            page_paths = doc_meta.get("page_paths") or None
            if page_paths:
                document_path = page_paths[0]
        except (FileNotFoundError, ValueError):
            # document_path is a raw file path, not a document ID.
            # Try to find a stored document whose original_filename matches.
            for d in doc_store.list_documents():
                stored_paths = d.get("page_paths", [])
                if stored_paths and Path(stored_paths[0]).resolve() == Path(document_path).resolve():
                    page_paths = stored_paths
                    break
    except Exception:
        logger.debug("DocumentStore lookup failed — treating as single-page [BLK-220]", exc_info=True)

    state = build_initial_state(
        document_path, template_cls, skill,
        task_type=task_type,
        page_paths=page_paths,
        confidence_threshold=confidence_threshold,
    )
    registry = build_tool_registry(tool_names=tool_names if tool_names else None)
    validator_config = build_validator_config(skill)

    # BLK-284: Apply confidence_threshold override to validator_config
    if confidence_threshold is not None:
        validator_config.default_confidence_threshold = confidence_threshold

    # BLK-264: PDF fallback only runs when (a) no LLM provider is configured, or
    # (b) the definition explicitly opts in via use_pdf_fast_path. Previously
    # both branches of an if/else called run_pdf_fallback unconditionally,
    # silently bypassing the ReAct agent for 9 of 22 skills even with Azure configured.
    use_fast_path = agent_config.get("use_pdf_fast_path", False)
    llm_configured = settings.is_llm_configured()
    fallback_result = None
    if not llm_configured or use_fast_path:
        fallback_result = run_pdf_fallback(
            document_path,
            template_cls=template_cls,
            skill=skill,
            validator_config=validator_config,
        )
        if fallback_result is None and not llm_configured:
            raise RuntimeError(
                "No LLM provider configured. Set AZURE_API_KEY and "
                "AZURE_CHAT_ENDPOINT to run agent-based extraction."
            )
    if fallback_result is not None:
        logger.info("Run %s using PDF fallback (execution_mode=fallback)", run_id, extra={"run_id": run_id, "execution_mode": "fallback"})
        serialized = serialize_extraction_result(run_id, definition_id, document_path, fallback_result, {"trace": fallback_result.trace})
        serialized["execution_mode"] = "fallback"
        try:
            existing = store.get_run(run_id)
            existing.update(serialized)
            store.update_run(run_id, existing)
        except FileNotFoundError:
            store.save_run(run_id, serialized)
        if emitter:
            complete_status = "completed" if fallback_result.is_complete else "max_iterations_reached"
            emitter.emit_complete(complete_status, run_id=run_id, execution_mode="fallback")

        # Fire webhook notification (non-blocking) [BLK-242]
        frontend_status = "completed" if fallback_result.is_complete else "max_iterations_reached"
        webhook_event = status_to_webhook_event(frontend_status)
        if webhook_event:
            try:
                await emit_webhook_event_async(webhook_event, {
                    "run_id": run_id,
                    "definition_id": definition_id,
                    "document_url": document_path,
                    "status": frontend_status,
                    "execution_mode": "fallback",
                })
            except Exception as e:
                logger.warning("Webhook emission failed for run %s: %s [BLK-242]", run_id, e)

        return serialized

    planner_client = _build_planner_client()

    # Build graph — wire control and emitter for live SSE + cooperative control [BLK-129]
    breaker = CircuitBreaker(threshold=3)

    # Guardrails: instantiate per-run guardrail components [BLK-079..086, SCRUM-149]
    from src.agent.guardrails.tool_guardrails import ToolCallRateLimiter
    from src.agent.guardrails.loop_detection import LoopDetector
    from src.agent.guardrails.audit_logging import AuditLogger

    rate_limiter = ToolCallRateLimiter()
    loop_detector = LoopDetector(
        max_cycles_per_field=max_cycles_per_field or settings.max_cycles_per_field,
        max_cycles_per_document=max_cycles or settings.max_cycles_per_document,
    )
    audit_logger = AuditLogger(run_id=run_id)

    # Select graph mode: OneFlow (single-agent) or standard ReAct [BLK-074]
    execution_mode = (agent_config.get("execution_mode", "react")
                      if agent_config else "react")
    use_oneflow = execution_mode == "oneflow"

    if use_oneflow:
        logger.info("Run %s using OneFlow single-agent mode [BLK-074]", run_id,
                     extra={"run_id": run_id, "execution_mode": "oneflow"})
        graph = build_oneflow_graph(
            registry=registry,
            skill=skill,
            validator_config=validator_config,
            llm_client=planner_client,
            breaker=breaker,
            control=control,
            emitter=emitter,
            rate_limiter=rate_limiter,
            loop_detector=loop_detector,
            audit_logger=audit_logger,
        )
    else:
        graph = build_react_graph(
            registry=registry,
            skill=skill,
            validator_config=validator_config,
            llm_client=planner_client,
            breaker=breaker,
            control=control,
            emitter=emitter,
            rate_limiter=rate_limiter,
            loop_detector=loop_detector,
            audit_logger=audit_logger,
        )

    # Emit initial progress
    if emitter:
        emitter.emit_progress(0, result_gap_count(state), 0)
        if event_buffer is not None:
            event_buffer.append({"type": "progress", "completed_fields": 0, "total_fields": result_gap_count(state), "failing_fields": 0})

    # Invoke graph [BLK-094] — run in a thread to avoid blocking the event loop [BLK-240]
    recursion_limit = (max_cycles or settings.max_cycles_per_document) + 10
    try:
        final_state = await asyncio.to_thread(
            graph.invoke,
            state,
            config={"recursion_limit": recursion_limit},
        )
    except Exception as e:
        logger.error("Run %s failed: %s", run_id, e, extra={"run_id": run_id, "error": str(e)})
        mark_error(e)
        if emitter:
            emitter.emit_complete("failed", str(e), run_id=run_id)

        # Fire webhook notification (non-blocking) [BLK-242]
        try:
            await emit_webhook_event_async(WebhookEvent.RUN_FAILED, {
                "run_id": run_id,
                "definition_id": definition_id,
                "document_url": document_path,
                "status": "failed",
                "error": str(e),
            })
        except Exception as we:
            logger.warning("Webhook emission failed for run %s: %s [BLK-242]", run_id, we)

        return {
            "id": run_id,
            "definition_id": definition_id,
            "document_url": document_path,
            "status": "failed",
            "current_cycle": 0,
            "total_fields": 0,
            "extracted_fields_count": 0,
            "fields": [],
            "error": str(e),
            "execution_mode": "agent",
        }

    # Build result
    result = final_state.get("result")
    if result is None:
        status = final_state.get("status", RunStatus.PARTIAL)
        # Build token usage summary [BLK-050]
        token_usage_list = final_state.get("token_usage", [])
        token_summary = summarize_token_usage(token_usage_list)

        if task_type == "graph_extraction":
            from src.agent.graph import _build_graph_result
            from src.agent.validator import TaskValidator
            validator = TaskValidator()
            graph_result = _build_graph_result(
                state=final_state,
                is_complete=status == RunStatus.COMPLETE,
                gap_report=None,
                trace=final_state.get("trace", []),
                total_cycles=final_state.get("total_cycles", 0),
                status=status,
                provider_errors=final_state.get("provider_errors", []),
            )
            # Instantiate template if it's a class for Pydantic default_factory access
            contract = template_cls
            if isinstance(template_cls, type):
                try:
                    contract = template_cls()
                except Exception:
                    pass
            gap_report = validator.validate(
                result=graph_result,
                contract=contract,
                invariants=skill.invariants,
                failure_actions=skill.failure_actions,
            )
            graph_result.gap_report = gap_report
            result = graph_result
        else:
            gap_report = validate_extraction(
                schema=template_cls,
                extraction=final_state.get("extraction", {}),
                invariants=skill.invariants,
                config=validator_config,
                failure_actions=skill.failure_actions,
            )
            result = ExtractedResult(
                is_complete=status == RunStatus.COMPLETE,
                values=None,
                field_values=final_state.get("extraction", {}),
                gap_report=gap_report,
                trace=final_state.get("trace", []),
                total_cycles=final_state.get("total_cycles", 0),
                status=status,
                provider_errors=final_state.get("provider_errors", []),
                token_usage_summary=token_summary,
            )

    # Persist token usage [BLK-050]
    token_usage_list = final_state.get("token_usage", [])
    if token_usage_list:
        try:
            save_token_usage(run_id, token_usage_list)
            update_aggregate_stats(run_id, result.token_usage_summary)
        except Exception as e:
            logger.warning("Failed to persist token usage: %s", e)

    # Emit trace events from the final state (only in replay mode — when
    # emitter is provided but control is None, i.e. legacy sync mode).
    # In live mode (control is not None), events were already emitted by
    # the graph nodes during execution [BLK-129].
    if emitter and control is None:
        _emit_trace_events(emitter, final_state.get("trace", []), result)
        # Emit compaction event if compaction occurred during the run [§12.4]
        compaction_summary = final_state.get("compaction_summary", "")
        if compaction_summary:
            emitter.emit_compaction(
                entries_compacted=settings.compaction_threshold,
                summary_length=len(compaction_summary),
            )
        complete_status = map_store_status_to_sse(map_status_to_frontend(result.status))
        complete_msg = "All fields extracted" if result.is_complete else f"Run ended with {len(result.gap_report.gaps)} gaps remaining"
        emitter.emit_complete(
            complete_status,
            complete_msg,
        )
    elif emitter and control is not None:
        # Live mode: emit complete with run_id if not already emitted by terminate_node
        if not emitter._closed:
            # Route through the canonical status contract [BLK-280, BLK-221] so
            # RunStatus.ERROR correctly surfaces as "failed" instead of being
            # collapsed into "max_iterations_reached".
            complete_status = map_store_status_to_sse(map_status_to_frontend(result.status))
            complete_msg = "All fields extracted" if result.is_complete else f"Run ended with {len(result.gap_report.gaps)} gaps remaining"
            emitter.emit_complete(
                complete_status,
                complete_msg,
                run_id=run_id,
            )

    logger.info("Run %s completed via ReAct agent (execution_mode=agent)", run_id, extra={"run_id": run_id, "execution_mode": "agent"})
    # Serialize and persist [BLK-165]
    serialized = serialize_extraction_result(run_id, definition_id, document_path, result, final_state)
    # Merge with existing record to preserve created_at/started_at from executor
    try:
        existing = store.get_run(run_id)
        existing.update(serialized)
        store.update_run(run_id, existing)
    except FileNotFoundError:
        store.save_run(run_id, serialized)

    # Fire webhook notification (non-blocking) [BLK-242]
    frontend_status = map_status_to_frontend(result.status)
    webhook_event = status_to_webhook_event(frontend_status)
    if webhook_event:
        try:
            await emit_webhook_event_async(webhook_event, {
                "run_id": run_id,
                "definition_id": definition_id,
                "document_url": document_path,
                "status": frontend_status,
            })
        except Exception as e:
            logger.warning("Webhook emission failed for run %s: %s [BLK-242]", run_id, e)

    return serialized


def result_gap_count(state: dict[str, Any]) -> int:
    """Get total fields from state for progress emission [BLK-218].

    For field extraction, counts required schema fields.
    For graph extraction, counts expected node types + edge types + output formats.
    """
    template = state.get("template_schema")
    if template is None:
        return 0
    task_type = state.get("task_type", "extraction")
    if task_type == "graph_extraction":
        # template may be a class or instance — instantiate if it's a class
        if isinstance(template, type):
            try:
                template = template()
            except Exception:
                return 0
        node_types = getattr(template, "node_types", [])
        edge_types = getattr(template, "edge_types", [])
        output_formats = getattr(template, "output_formats", [])
        return len(node_types) + len(edge_types) + len(output_formats)
    from src.agent.validator import _required_fields
    return len(_required_fields(template))


def _emit_trace_events(
    emitter: SSEEventEmitter,
    trace: list[TraceEntry],
    result: ExtractedResult,
) -> None:
    """Replay trace entries as SSE events."""
    # Emit initial status_change
    emitter.emit_status_change(status="running", cycle=0, previous_status="idle")

    for entry in trace:
        emitter.emit_thought(entry.step, entry.thought)
        emitter.emit_tool_call(entry.step, entry.tool_name, entry.tool_args)

        crop_thumbnail = None
        if entry.tool_name == "crop" and entry.result.ok and entry.result.data:
            crop_thumbnail = SSEEventEmitter.encode_crop_thumbnail(entry.result.data)

        emitter.emit_tool_result(entry.step, entry.tool_name, entry.result, crop_thumbnail)

    # Emit token_usage events for all LLM calls [BLK-050]
    token_summary = result.token_usage_summary
    if token_summary and token_summary.get("total_tokens", 0) > 0:
        emitter.emit_token_usage(
            node="summary",
            cycle=0,
            input_tokens=0,
            output_tokens=0,
            total_tokens=token_summary["total_tokens"],
            cost_usd=token_summary["total_cost_usd"],
            running_total_tokens=token_summary["total_tokens"],
            running_total_cost=token_summary["total_cost_usd"],
        )

    # Emit field updates for all extracted fields
    total_fields = result.gap_report.total_fields
    extracted_count = len(result.gap_report.satisfied)
    for name, fv in result.field_values.items():
        bbox = None
        page = 0
        if fv.grounding:
            bbox = bbox_to_frontend(fv.grounding.bbox)
            page = fv.grounding.page
        # Determine risk tier [BLK-047]
        from src.agent.hitl import classify_extraction_risk
        risk_tier = classify_extraction_risk(
            confidence=fv.confidence,
            semantic_failed=False,
        ).tier.value
        emitter.emit_field_update(
            field_id=name,
            name=name,
            value=fv.value,
            confidence=fv.confidence,
            bbox=bbox,
            page=page,
            status=map_field_status(fv.confidence, fv.grounding is not None, result.is_complete),
            extracted_fields_count=extracted_count,
            total_fields=total_fields,
            risk_tier=risk_tier,
        )

    # Emit final progress
    emitter.emit_progress(
        completed_fields=extracted_count,
        total_fields=total_fields,
        failing_fields=len(result.gap_report.gaps),
    )

    # Emit final status_change — use canonical status mapping [BLK-281]
    # so max_iterations_reached is NOT collapsed into "failed".
    final_status = map_status_to_frontend(result.status)
    emitter.emit_status_change(status=final_status, cycle=result.total_cycles, previous_status="running")
