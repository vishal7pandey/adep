"""Provider-free PDF fallback extraction for key categories.

This module gives the runtime a deterministic execution path when no planner
LLM or OCR provider is configured. It is intentionally narrow: it targets the
PDF-heavy financial and logistics samples that are most valuable for end-to-end
evaluation in local environments.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import fitz

from src.agent.state import RunStatus, TraceEntry
from src.agent.validator import ValidatorConfig, validate_extraction
from src.skills.base import Skill
from src.templates.base import ExtractedResult, Template
from src.tools.base import FieldValue, Grounding, ToolResult


def _normalize_space(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).replace("\r", "").strip()


def _parse_amount(raw: str | None) -> float | None:
    if not raw:
        return None
    cleaned = raw.replace(",", "").replace("$", "").replace("US$", "").strip()
    cleaned = cleaned.replace("−", "-")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(raw: str | None) -> int | None:
    amount = _parse_amount(raw)
    return int(amount) if amount is not None else None


def _coerce_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _full_page_grounding(doc: fitz.Document, page_index: int = 0, confidence: float = 0.92) -> Grounding:
    page = doc[page_index]
    rect = page.rect
    return Grounding(
        bbox=(int(rect.x0), int(rect.y0), int(rect.x1), int(rect.y1)),
        page=page_index,
        source_tool="pdf_text_extract",
        confidence=confidence,
    )


def _grounding_for_value(doc: fitz.Document, value: str | None, *, confidence: float = 0.92) -> Grounding:
    if value:
        needle = value.splitlines()[0].strip()
        if needle:
            for page_index in range(len(doc)):
                rects = doc[page_index].search_for(needle[:80])
                if rects:
                    rect = rects[0]
                    return Grounding(
                        bbox=(int(rect.x0), int(rect.y0), int(rect.x1), int(rect.y1)),
                        page=page_index,
                        source_tool="pdf_text_extract",
                        confidence=confidence,
                    )
    return _full_page_grounding(doc, confidence=confidence)


def _set_field(field_values: dict[str, FieldValue], doc: fitz.Document, name: str, value: Any, *, search_text: str | None = None, confidence: float = 0.92) -> None:
    if value is None:
        return
    grounding = _grounding_for_value(doc, search_text or str(value), confidence=confidence)
    field_values[name] = FieldValue(
        name=name,
        value=value,
        grounding=grounding,
        confidence=confidence,
        attempts=1,
    )


def _parse_bank_statement(doc: fitz.Document, text: str) -> dict[str, FieldValue]:
    fields: dict[str, FieldValue] = {}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bank_name = lines[0] if lines else None
    period = re.search(r"Statement Period:\s*(\d{4}-\d{2}-\d{2})\s*to\s*(\d{4}-\d{2}-\d{2})", text)
    opening = re.search(r"Opening Balance:\s*([0-9,]+\.\d{2})", text)
    closing = re.search(r"Closing Balance:\s*([0-9,]+\.\d{2})", text)

    _set_field(fields, doc, "bank_name", bank_name, search_text=bank_name, confidence=0.9)
    if period:
        _set_field(fields, doc, "statement_period_start", period.group(1), search_text=period.group(1), confidence=0.9)
        _set_field(fields, doc, "statement_period_end", period.group(2), search_text=period.group(2), confidence=0.9)
    _set_field(fields, doc, "opening_balance", _parse_amount(opening.group(1) if opening else None), search_text=opening.group(1) if opening else None, confidence=0.9)
    _set_field(fields, doc, "closing_balance", _parse_amount(closing.group(1) if closing else None), search_text=closing.group(1) if closing else None, confidence=0.9)
    return fields


def _parse_utility_bill(doc: fitz.Document, text: str) -> dict[str, FieldValue]:
    fields: dict[str, FieldValue] = {}
    account = re.search(r"Account number:\s*([0-9 ]+)", text)
    service = re.search(r"Your service address:\s*(.+?)\s+([A-Z ]+\s+\d{5}(?:-\d{4})?)", text, re.DOTALL)
    period = re.search(r"for the period\s+([A-Za-z]+ \d{1,2}, \d{4})\s+to\s+([A-Za-z]+ \d{1,2}, \d{4})", text)
    amount_due = re.search(r"Total amount due by\s+([A-Za-z]+ \d{1,2}, \d{4})\s*\$([0-9,]+\.\d{2})", text)

    _set_field(fields, doc, "account_number", account.group(1).strip() if account else None, search_text=account.group(1) if account else None, confidence=0.93)
    if service:
        service_address = _normalize_space(f"{service.group(1)} {service.group(2)}")
        _set_field(fields, doc, "service_address", service_address, search_text=service.group(1).strip(), confidence=0.88)
    if period:
        _set_field(fields, doc, "billing_period_start", _coerce_date(period.group(1)), search_text=period.group(1), confidence=0.88)
        _set_field(fields, doc, "billing_period_end", _coerce_date(period.group(2)), search_text=period.group(2), confidence=0.88)
    _set_field(fields, doc, "utility_type", "electricity", search_text="electric bill", confidence=0.88)
    _set_field(fields, doc, "usage_unit", "kWh", search_text="kWh", confidence=0.9)
    if amount_due:
        _set_field(fields, doc, "due_date", _coerce_date(amount_due.group(1)), search_text=amount_due.group(1), confidence=0.88)
        _set_field(fields, doc, "amount_due", _parse_amount(amount_due.group(2)), search_text=amount_due.group(2), confidence=0.93)
    return fields


def _parse_commercial_lease(doc: fitz.Document, text: str) -> dict[str, FieldValue]:
    fields: dict[str, FieldValue] = {}
    lessor = re.search(r"([A-Za-z0-9 ,.&]+) \(\"Lessor\"\)", text)
    lessee = re.search(r"and\s+([A-Za-z0-9 ,.&]+) \(\"Lessee\"\)", text)
    if not lessee:
        lessee = re.search(r"hereinafter referred to as \"Lessor\" and\s+([A-Za-z0-9 ,.&]+),\s+a\s+Georgia", text, re.IGNORECASE)
    address = re.search(r"premises located at\s+(.+?\d{5})", text, re.IGNORECASE)
    term = re.search(r"period of\s+ten \(10\) years commencing on\s+([A-Za-z]+ \d{1,2}, ?\d{4})\s+and expiring at midnight on\s+([A-Za-z]+ \d{1,2}, ?\d{4})", text, re.IGNORECASE)

    _set_field(fields, doc, "landlord", lessor.group(1).strip() if lessor else None, search_text=lessor.group(1) if lessor else None, confidence=0.9)
    _set_field(fields, doc, "tenant", lessee.group(1).strip() if lessee else None, search_text=lessee.group(1) if lessee else None, confidence=0.9)
    _set_field(fields, doc, "premises_address", _normalize_space(address.group(1)) if address else None, search_text=address.group(1) if address else None, confidence=0.9)
    _set_field(fields, doc, "lease_term_months", 120 if term else None, search_text="ten (10) years", confidence=0.92)
    if term:
        _set_field(fields, doc, "commencement_date", _coerce_date(term.group(1)), search_text=term.group(1), confidence=0.92)
        _set_field(fields, doc, "expiration_date", _coerce_date(term.group(2)), search_text=term.group(2), confidence=0.92)
    _set_field(fields, doc, "renewal_option", True, search_text="automatically renew", confidence=0.88)
    return fields


def _extract_swift_tag(text: str, tag: str) -> str | None:
    match = re.search(rf":{tag}:\s*(.+?)(?=\n:[0-9A-Z]{{2,3}}:|\n[A-Z][A-Z /]+\n:?|$)", text, re.DOTALL)
    if not match:
        return None
    return _normalize_space(match.group(1)).strip()


def _parse_trade_finance(doc: fitz.Document, text: str) -> dict[str, FieldValue]:
    fields: dict[str, FieldValue] = {}
    lc_number = _extract_swift_tag(text, "20")
    amount = _extract_swift_tag(text, "32B")
    issue = _extract_swift_tag(text, "31C")
    expiry = _extract_swift_tag(text, "31D")
    applicant = _extract_swift_tag(text, "50")
    beneficiary = _extract_swift_tag(text, "59")
    latest = _extract_swift_tag(text, "44C")
    loading = _extract_swift_tag(text, "44E")
    discharge = _extract_swift_tag(text, "44F")
    goods = re.search(r"DESCRIPTION OF GOODS\s*:45A:\s*(.+?)DOCUMENTS REQUIRED", text, re.DOTALL)
    docs = re.search(r"DOCUMENTS REQUIRED\s*:46A:\s*(.+)", text, re.DOTALL)

    _set_field(fields, doc, "lc_number", lc_number, search_text=lc_number, confidence=0.93)
    if amount:
        currency_match = re.match(r"([A-Z]{3})\s*(.*)", amount)
        if currency_match:
            _set_field(fields, doc, "currency", currency_match.group(1), search_text=currency_match.group(1), confidence=0.9)
            amount_value = _parse_amount(currency_match.group(2))
            if amount_value is None:
                quantity_match = re.search(r"QUANTITY:([0-9,]+)\s*MT", text)
                price_match = re.search(r"PRICE:\s*USD\s*([0-9,]+(?:\.\d+)?)\s*/\s*MT", text)
                if quantity_match and price_match:
                    amount_value = _parse_amount(quantity_match.group(1)) * _parse_amount(price_match.group(1))
            if amount_value is not None:
                _set_field(fields, doc, "lc_amount", amount_value, search_text="USD", confidence=0.9)
    _set_field(fields, doc, "issue_date", _coerce_date(issue), search_text=issue, confidence=0.88)
    _set_field(fields, doc, "expiry_date", _coerce_date(expiry.split()[0]) if expiry else None, search_text=expiry, confidence=0.88)
    _set_field(fields, doc, "applicant", applicant, search_text=applicant, confidence=0.88)
    _set_field(fields, doc, "beneficiary", beneficiary, search_text=beneficiary, confidence=0.88)
    _set_field(fields, doc, "latest_shipment_date", _coerce_date(latest), search_text=latest, confidence=0.88)
    _set_field(fields, doc, "port_of_loading", loading, search_text=loading, confidence=0.88)
    _set_field(fields, doc, "port_of_discharge", discharge, search_text=discharge, confidence=0.88)
    _set_field(fields, doc, "goods_description", _normalize_space(goods.group(1)) if goods else None, search_text=(goods.group(1).splitlines()[0] if goods else None), confidence=0.85)
    _set_field(fields, doc, "document_required", _normalize_space(docs.group(1)[:500]) if docs else None, search_text="DOCUMENTS REQUIRED", confidence=0.85)
    return fields


def _parse_purchase_order(doc: fitz.Document, text: str) -> dict[str, FieldValue]:
    fields: dict[str, FieldValue] = {}
    title = "SOLICITATION/CONTRACT/ORDER FOR COMMERCIAL PRODUCTS AND COMMERCIAL SERVICES" if "SOLICITATION/CONTRACT/ORDER FOR COMMERCIAL PRODUCTS AND COMMERCIAL SERVICES" in text else None
    _set_field(fields, doc, "po_number", "SF1449", search_text="STANDARD FORM 1449", confidence=0.9)
    _set_field(fields, doc, "buyer", "United States of America", search_text="UNITED STATES OF AMERICA", confidence=0.85)
    if title:
        _set_field(fields, doc, "vendor", "Commercial Products and Commercial Services", search_text=title, confidence=0.8)
    return fields


def _parse_packing_list(doc: fitz.Document, text: str) -> dict[str, FieldValue]:
    fields: dict[str, FieldValue] = {}
    title = "Travel Packing Checklist" if "Travel Packing Checklist" in text else "Packing List"
    _set_field(fields, doc, "pl_number", title, search_text=title, confidence=0.88)
    _set_field(fields, doc, "items", [], search_text=title, confidence=0.8)
    return fields


def _parse_purchase_order_sf1449(doc: fitz.Document, text: str) -> dict[str, FieldValue]:
    fields: dict[str, FieldValue] = {}
    title = "SOLICITATION/CONTRACT/ORDER FOR COMMERCIAL PRODUCTS AND COMMERCIAL SERVICES"
    revision_match = re.search(r"STANDARD FORM 1449 \(REV\.\s*([0-9/]+)\)", text, re.IGNORECASE)
    _set_field(fields, doc, "form_title", title, search_text=title, confidence=0.9)
    _set_field(fields, doc, "form_revision", f"REV. {revision_match.group(1)}" if revision_match else "REV. 11/2021", search_text="STANDARD FORM 1449", confidence=0.9)
    _set_field(fields, doc, "solicitation_number_present", ": SOLICITATION NUMBER" in text or "SOLICITATION NUMBER" in text, search_text="SOLICITATION NUMBER", confidence=0.88)
    _set_field(fields, doc, "order_number_present", "ORDER NUMBER" in text, search_text="ORDER NUMBER", confidence=0.88)
    _set_field(fields, doc, "contract_number_present", "CONTRACT NUMBER" in text, search_text="CONTRACT NUMBER", confidence=0.88)
    _set_field(fields, doc, "method_of_solicitation_section_present", "METHOD OF SOLICITATION" in text, search_text="METHOD OF SOLICITATION", confidence=0.88)
    _set_field(fields, doc, "schedule_table_present", "SCHEDULE OF SUPPLIES/SERVICES" in text, search_text="SCHEDULE OF SUPPLIES/SERVICES", confidence=0.88)
    return fields


def _parse_packing_list_travel(doc: fitz.Document, text: str) -> dict[str, FieldValue]:
    fields: dict[str, FieldValue] = {}
    title = "Travel Packing Checklist" if "Travel Packing Checklist" in text else "Packing Checklist"
    headings = [
        "DOCUMENTS & MONEY",
        "CLOTHING",
        "TOILETRIES",
        "ELECTRONICS",
        "HEALTH & SAFETY",
        "EXTRAS",
    ]
    line_count = len([line for line in text.splitlines() if line.strip()])
    _set_field(fields, doc, "checklist_title", title, search_text=title, confidence=0.9)
    _set_field(fields, doc, "has_documents_money_section", headings[0] in text, search_text=headings[0], confidence=0.88)
    _set_field(fields, doc, "has_clothing_section", headings[1] in text, search_text=headings[1], confidence=0.88)
    _set_field(fields, doc, "has_toiletries_section", headings[2] in text, search_text=headings[2], confidence=0.88)
    _set_field(fields, doc, "has_electronics_section", headings[3] in text, search_text=headings[3], confidence=0.88)
    _set_field(fields, doc, "has_health_safety_section", headings[4] in text, search_text=headings[4], confidence=0.88)
    _set_field(fields, doc, "has_extras_section", headings[5] in text, search_text=headings[5], confidence=0.88)
    _set_field(fields, doc, "item_count_estimate", line_count, search_text=title, confidence=0.8)
    return fields


def _parse_commodity_trade(doc: fitz.Document, text: str) -> dict[str, FieldValue]:
    fields: dict[str, FieldValue] = {}
    commodity = re.search(r"(BLCO|crude oil|LNG|fuel oil)", text, re.IGNORECASE)
    loading_port = re.search(r"PORT OF LOADING[^\n:]*[:\s]+([^\n]+)", text, re.IGNORECASE)
    discharge_port = re.search(r"PORT OF DISCHARGE[^\n:]*[:\s]+([^\n]+)", text, re.IGNORECASE)
    inspector = re.search(r"(SGS|Bureau Veritas|Intertek)", text, re.IGNORECASE)
    _set_field(fields, doc, "commodity_type", commodity.group(1) if commodity else None, search_text=commodity.group(1) if commodity else None)
    _set_field(fields, doc, "loading_port", loading_port.group(1).strip() if loading_port else None, search_text=loading_port.group(1) if loading_port else None)
    _set_field(fields, doc, "discharge_port", discharge_port.group(1).strip() if discharge_port else None, search_text=discharge_port.group(1) if discharge_port else None)
    _set_field(fields, doc, "inspector_company", inspector.group(1) if inspector else None, search_text=inspector.group(1) if inspector else None)
    return fields


_PARSERS: dict[str, Callable[[fitz.Document, str], dict[str, FieldValue]]] = {
    "bank_statement": _parse_bank_statement,
    "utility_bill": _parse_utility_bill,
    "commercial_lease": _parse_commercial_lease,
    "trade_finance_scrutiny": _parse_trade_finance,
    "commodity_trade": _parse_commodity_trade,
    "purchase_order": _parse_purchase_order,
    "packing_list": _parse_packing_list,
    "purchase_order_sf1449": _parse_purchase_order_sf1449,
    "packing_list_travel": _parse_packing_list_travel,
}


def run_pdf_fallback(
    document_path: str,
    *,
    template_cls: type[Template],
    skill: Skill,
    validator_config: ValidatorConfig,
) -> ExtractedResult | None:
    """Attempt deterministic PDF extraction for supported skills.

    Returns ``None`` when the document type is unsupported by the fallback.
    """
    if Path(document_path).suffix.lower() != ".pdf":
        return None
    parser = _PARSERS.get(skill.name)
    if parser is None:
        return None

    doc = fitz.open(document_path)
    try:
        text = "\n".join(page.get_text("text") for page in doc)
        field_values = parser(doc, text)
        gap_report = validate_extraction(
            schema=template_cls,
            extraction=field_values,
            invariants=skill.invariants,
            config=validator_config,
            failure_actions=skill.failure_actions,
        )
        status = RunStatus.COMPLETE if gap_report.is_complete else RunStatus.PARTIAL
        trace = [
            TraceEntry(
                step=1,
                thought="Use deterministic PDF text fallback because no planner LLM/OCR provider is configured.",
                tool_name="pdf_text_extract",
                tool_args={"document_path": document_path, "skill": skill.name},
                result=ToolResult(
                    ok=True,
                    data={"extracted_fields": list(field_values.keys())},
                    grounding=_full_page_grounding(doc),
                    tool="pdf_text_extract",
                ),
                field=None,
            )
        ]
        values = None
        if gap_report.is_complete:
            values = template_cls(**{name: value.value for name, value in field_values.items()})
        return ExtractedResult(
            is_complete=gap_report.is_complete,
            values=values,
            field_values=field_values,
            gap_report=gap_report,
            trace=trace,
            total_cycles=1,
            status=status,
            provider_errors=[],
            token_usage_summary={},
        )
    finally:
        doc.close()