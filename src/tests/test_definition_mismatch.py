"""Tests for definition-document mismatch guardrail [SCRUM-9, BLK-170]."""

from __future__ import annotations

from src.api.run_engine import _check_definition_document_mismatch


class TestDefinitionDocumentMismatch:
    """Verify the lightweight filename-based mismatch guardrail [SCRUM-9]."""

    def test_match_returns_none(self):
        assert _check_definition_document_mismatch("invoice", "/data/invoice_001.pdf") is None

    def test_obvious_mismatch_detected(self):
        msg = _check_definition_document_mismatch("ad_buy", "/data/pid_diagram_01.png")
        assert msg is not None
        assert "ad_buy" in msg
        assert "pid_to_dexpi" in msg

    def test_invoice_on_receipt_file_matches(self):
        assert _check_definition_document_mismatch("invoice", "/data/receipt_scan.jpg") is None

    def test_no_keywords_returns_none(self):
        assert _check_definition_document_mismatch("invoice", "/data/scan_001.pdf") is None

    def test_pid_on_invoice_file_warns(self):
        msg = _check_definition_document_mismatch("pid_to_dexpi", "/data/invoice_acme.pdf")
        assert msg is not None
        assert "pid_to_dexpi" in msg
        assert "invoice" in msg

    def test_bank_statement_on_pid_diagram_warns(self):
        msg = _check_definition_document_mismatch("bank_statement", "/data/p&id_vessel_03.dwg")
        assert msg is not None
        assert "bank_statement" in msg

    def test_case_insensitive_matching(self):
        msg = _check_definition_document_mismatch("ad_buy", "/data/INVOICE_2024.pdf")
        assert msg is not None
        assert "invoice" in msg.lower()
