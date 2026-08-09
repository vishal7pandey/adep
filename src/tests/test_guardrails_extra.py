"""Tests for BLK-081, BLK-083, BLK-084, BLK-086 guardrails."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.guardrails.hallucination_detection import (
    GroundingCheckResult,
    check_grounding,
    InvariantCheck,
    check_invariants,
    compute_hallucination_rate,
)
from src.agent.guardrails.pii_redaction import (
    SensitivityLevel,
    PIIDetection,
    detect_pii,
    redact_pii,
    classify_sensitivity,
    is_provider_allowed,
)
from src.agent.guardrails.audit_logging import (
    AuditLogEntry,
    GuardrailDecision,
    AuditLogger,
    hash_prompt,
)
from src.agent.guardrails.exfiltration_prevention import (
    SanitizationResult,
    sanitize_input,
    sanitize_tool_output,
    detect_encoded_data,
    strip_encoded_data,
    check_tool_arg_size,
    check_no_outbound_network,
    build_prompt_isolation,
)


# ---------------------------------------------------------------------------
# BLK-081: Hallucination detection & grounding enforcement
# ---------------------------------------------------------------------------

class TestCheckGrounding:
    """Verify grounding checks [BLK-081]."""

    def test_grounded_field(self):
        result = check_grounding(
            "vendor", "ACME Corp",
            bbox=(10, 20, 100, 50), page=0,
            ocr_text="ACME Corp",
            claimed_confidence=0.95,
        )
        assert result.status == "grounded"
        assert result.confidence == 0.95

    def test_ungrounded_no_bbox(self):
        result = check_grounding(
            "vendor", "ACME Corp",
            bbox=None, page=None,
        )
        assert result.status == "ungrounded"
        assert result.confidence == 0.0

    def test_hallucination_suspected(self):
        result = check_grounding(
            "vendor", "Totally Fake Company Name",
            bbox=(10, 20, 100, 50), page=0,
            ocr_text="ACME Corp",
            claimed_confidence=0.95,
        )
        assert result.status == "hallucination_suspected"
        assert result.confidence <= 0.3

    def test_fuzzy_match_within_threshold(self):
        result = check_grounding(
            "total", "1500.00",
            bbox=(10, 20, 100, 50), page=0,
            ocr_text="1500.0",
            claimed_confidence=0.9,
        )
        assert result.status == "grounded"

    def test_substring_match(self):
        result = check_grounding(
            "vendor", "ACME",
            bbox=(10, 20, 100, 50), page=0,
            ocr_text="ACME Corporation Inc.",
            claimed_confidence=0.9,
        )
        assert result.status == "grounded"

    def test_no_ocr_text_passes(self):
        result = check_grounding(
            "vendor", "ACME",
            bbox=(10, 20, 100, 50), page=0,
            ocr_text=None,
            claimed_confidence=0.9,
        )
        assert result.status == "grounded"


class TestInvariantCheck:
    """Verify cross-field invariant checks [BLK-081]."""

    def test_valid_invariant(self):
        invariant = InvariantCheck(
            name="total_check",
            fields=["subtotal", "tax", "total"],
            check_fn=lambda f: (f["subtotal"] + f["tax"] == f["total"], "OK"),
        )
        violations = check_invariants(
            {"subtotal": 100, "tax": 20, "total": 120},
            [invariant],
        )
        assert len(violations) == 0

    def test_violated_invariant(self):
        invariant = InvariantCheck(
            name="total_check",
            fields=["subtotal", "tax", "total"],
            check_fn=lambda f: (f["subtotal"] + f["tax"] == f["total"], f"Mismatch: {f['subtotal']} + {f['tax']} != {f['total']}"),
        )
        violations = check_invariants(
            {"subtotal": 100, "tax": 20, "total": 150},
            [invariant],
        )
        assert len(violations) == 1
        assert violations[0][0] == "total_check"

    def test_missing_field_skipped(self):
        invariant = InvariantCheck(
            name="total_check",
            fields=["subtotal", "tax", "total"],
            check_fn=lambda f: (True, "OK"),
        )
        violations = check_invariants(
            {"subtotal": 100, "tax": 20},
            [invariant],
        )
        assert len(violations) == 0


class TestHallucinationRate:
    """Verify hallucination rate computation [BLK-081]."""

    def test_no_hallucinations(self):
        fields = [
            {"status": "extracted"},
            {"status": "extracted"},
        ]
        assert compute_hallucination_rate(fields) == 0.0

    def test_some_hallucinations(self):
        fields = [
            {"status": "extracted"},
            {"status": "ungrounded"},
            {"status": "hallucination_suspected"},
            {"status": "extracted"},
        ]
        rate = compute_hallucination_rate(fields)
        assert rate == 50.0

    def test_empty_fields(self):
        assert compute_hallucination_rate([]) == 0.0


# ---------------------------------------------------------------------------
# BLK-083: PII redaction & content filtering
# ---------------------------------------------------------------------------

class TestDetectPII:
    """Verify PII detection [BLK-083]."""

    def test_ssn_detected(self):
        detections = detect_pii("My SSN is 123-45-6789")
        assert any(d.pii_type == "SSN" for d in detections)

    def test_email_detected(self):
        detections = detect_pii("Contact: john@example.com")
        assert any(d.pii_type == "EMAIL" for d in detections)

    def test_phone_detected(self):
        detections = detect_pii("Call +1-555-123-4567")
        assert any(d.pii_type == "PHONE" for d in detections)

    def test_iban_detected(self):
        detections = detect_pii("IBAN: GB29NWBK60161331926819")
        assert any(d.pii_type == "IBAN" for d in detections)

    def test_no_pii(self):
        detections = detect_pii("Just a regular invoice for ACME Corp")
        assert len(detections) == 0


class TestRedactPII:
    """Verify PII redaction [BLK-083]."""

    def test_ssn_redacted(self):
        redacted, detections = redact_pii("SSN: 123-45-6789")
        assert "123-45-6789" not in redacted
        assert "[REDACTED:SSN]" in redacted
        assert any(d.pii_type == "SSN" for d in detections)

    def test_email_redacted(self):
        redacted, _ = redact_pii("Email: john@example.com")
        assert "john@example.com" not in redacted
        assert "[REDACTED:EMAIL]" in redacted

    def test_multiple_types_redacted(self):
        text = "SSN: 123-45-6789, Email: john@example.com"
        redacted, detections = redact_pii(text)
        assert "123-45-6789" not in redacted
        assert "john@example.com" not in redacted
        assert len(detections) == 2

    def test_selective_redaction(self):
        text = "SSN: 123-45-6789, Email: john@example.com"
        redacted, detections = redact_pii(text, types={"SSN"})
        assert "123-45-6789" not in redacted
        assert "john@example.com" in redacted  # Email not redacted
        assert len(detections) == 1


class TestSensitivityClassification:
    """Verify document sensitivity classification [BLK-083]."""

    def test_public_no_pii(self):
        assert classify_sensitivity("Regular invoice for ACME Corp") == SensitivityLevel.PUBLIC

    def test_confidential_email(self):
        assert classify_sensitivity("Contact: john@example.com") == SensitivityLevel.CONFIDENTIAL

    def test_restricted_ssn(self):
        assert classify_sensitivity("SSN: 123-45-6789") == SensitivityLevel.RESTRICTED


class TestProviderRestriction:
    """Verify provider restriction by sensitivity [BLK-083]."""

    def test_public_allows_any(self):
        assert is_provider_allowed(SensitivityLevel.PUBLIC, "azure") is True

    def test_restricted_blocks_external(self):
        assert is_provider_allowed(SensitivityLevel.RESTRICTED, "azure") is False

    def test_restricted_allows_on_prem(self):
        assert is_provider_allowed(SensitivityLevel.RESTRICTED, "local") is True


# ---------------------------------------------------------------------------
# BLK-084: LLM call audit logging & trace integrity
# ---------------------------------------------------------------------------

class TestAuditLogger:
    """Verify audit logging [BLK-084]."""

    def test_log_and_verify_chain(self, tmp_path: Path):
        logger = AuditLogger("test-run", base_dir=tmp_path / ".adep")

        entry1 = AuditLogEntry(
            run_id="test-run", cycle=1, node="plan",
            system_prompt_hash="abc123",
            user_prompt="Extract vendor",
            llm_response='{"vendor": "ACME"}',
            input_tokens=100, output_tokens=50,
            cost_usd=0.005,
        )
        hash1 = logger.log_llm_call(entry1)
        assert hash1 != ""

        entry2 = AuditLogEntry(
            run_id="test-run", cycle=2, node="plan",
            system_prompt_hash="abc123",
            user_prompt="Extract total",
            llm_response='{"total": 1500}',
            input_tokens=120, output_tokens=40,
            cost_usd=0.004,
        )
        hash2 = logger.log_llm_call(entry2)
        assert hash2 != hash1

        # Verify chain integrity
        valid, msg = logger.verify_chain()
        assert valid, f"Chain verification failed: {msg}"

    def test_tamper_detection(self, tmp_path: Path):
        logger = AuditLogger("test-run", base_dir=tmp_path / ".adep")

        entry = AuditLogEntry(
            run_id="test-run", cycle=1, node="plan",
            user_prompt="test",
        )
        logger.log_llm_call(entry)

        # Tamper with the log file
        log_file = logger.log_path
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        tampered = json.loads(lines[0])
        tampered["user_prompt"] = "TAMPERED"
        lines[0] = json.dumps(tampered)
        log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        valid, msg = logger.verify_chain()
        assert not valid
        assert "tampering" in msg.lower() or "mismatch" in msg.lower()

    def test_export_json(self, tmp_path: Path):
        logger = AuditLogger("test-run", base_dir=tmp_path / ".adep")

        entry = AuditLogEntry(
            run_id="test-run", cycle=1, node="plan",
            user_prompt="test",
        )
        logger.log_llm_call(entry)

        exported = logger.export_json()
        data = json.loads(exported)
        assert len(data) == 1
        assert data[0]["run_id"] == "test-run"

    def test_export_csv(self, tmp_path: Path):
        logger = AuditLogger("test-run", base_dir=tmp_path / ".adep")

        entry = AuditLogEntry(
            run_id="test-run", cycle=1, node="plan",
            user_prompt="test",
        )
        logger.log_llm_call(entry)

        exported = logger.export_csv()
        assert "run_id" in exported
        assert "test-run" in exported

    def test_guardrail_decision_logging(self, tmp_path: Path):
        logger = AuditLogger("test-run", base_dir=tmp_path / ".adep")

        decision = GuardrailDecision(
            run_id="test-run",
            guardrail="output_validation",
            action="rejected_malformed_json",
            corrective_action="retry",
        )
        logger.log_guardrail_decision(decision)

        decision_path = logger.log_path.parent / "guardrail_decisions.jsonl"
        assert decision_path.exists()
        lines = decision_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["guardrail"] == "output_validation"

    def test_empty_log_verify(self, tmp_path: Path):
        logger = AuditLogger("test-run", base_dir=tmp_path / ".adep")
        valid, msg = logger.verify_chain()
        assert valid

    def test_hash_prompt(self):
        h = hash_prompt("test prompt")
        assert len(h) == 64  # SHA256 hex


# ---------------------------------------------------------------------------
# BLK-086: Data exfiltration prevention
# ---------------------------------------------------------------------------

class TestSanitizeInput:
    """Verify input sanitization [BLK-086]."""

    def test_clean_text(self):
        result = sanitize_input("Hello World")
        assert result.text == "Hello World"
        assert len(result.actions) == 0

    def test_zero_width_chars_removed(self):
        text = "Hello\u200bWorld"
        result = sanitize_input(text)
        assert "\u200b" not in result.text
        assert "removed_zero_width_chars" in result.actions

    def test_control_chars_removed(self):
        text = "Hello\x07World"
        result = sanitize_input(text)
        assert "\x07" not in result.text
        assert "removed_control_chars" in result.actions

    def test_html_tags_stripped(self):
        text = "<p>Hello</p>World"
        result = sanitize_input(text)
        assert "<" not in result.text
        assert "stripped_html_tags" in result.actions

    def test_long_line_truncated(self):
        text = "x" * 15000
        result = sanitize_input(text)
        assert len(result.text) == 10000
        assert any("truncated" in a for a in result.actions)


class TestSanitizeToolOutput:
    """Verify tool output sanitization [BLK-086]."""

    def test_file_paths_redacted(self):
        result = sanitize_tool_output("File at /etc/passwd contains data")
        assert "/etc/passwd" not in result.text
        assert "[PATH]" in result.text

    def test_env_vars_redacted(self):
        result = sanitize_tool_output("API_KEY=${API_KEY}")
        assert "${API_KEY}" not in result.text
        assert "[ENV]" in result.text


class TestEncodedDataDetection:
    """Verify encoded data detection [BLK-086]."""

    def test_base64_detected(self):
        text = "data: " + "A" * 150
        detections = detect_encoded_data(text)
        assert any(d.encoding_type == "base64" for d in detections)

    def test_hex_detected(self):
        text = "data: " + "a" * 150
        detections = detect_encoded_data(text)
        assert any(d.encoding_type == "hex" for d in detections)

    def test_no_encoded_data(self):
        text = "Just regular text with no encoding"
        detections = detect_encoded_data(text)
        assert len(detections) == 0


class TestStripEncodedData:
    """Verify encoded data stripping [BLK-086]."""

    def test_base64_stripped(self):
        text = "Exfiltrate: " + "A" * 150
        stripped, types = strip_encoded_data(text)
        assert "A" * 150 not in stripped
        assert "base64" in types

    def test_no_encoded_data_unchanged(self):
        text = "Regular text"
        stripped, types = strip_encoded_data(text)
        assert stripped == text
        assert types == []


class TestToolArgSize:
    """Verify tool argument size limits [BLK-086]."""

    def test_within_limit(self):
        args = {"text": "short"}
        ok, _ = check_tool_arg_size(args)
        assert ok

    def test_exceeds_limit(self):
        args = {"data": "x" * 11000}
        ok, reason = check_tool_arg_size(args)
        assert not ok
        assert "exceeds" in reason.lower()


class TestNoOutboundNetwork:
    """Verify outbound network prevention [BLK-086]."""

    def test_localhost_allowed(self):
        assert check_no_outbound_network("http://localhost:8080") is True

    def test_external_url_blocked(self):
        assert check_no_outbound_network("https://evil.com/exfil") is False

    def test_non_url_allowed(self):
        assert check_no_outbound_network("just text") is True


class TestPromptIsolation:
    """Verify prompt isolation [BLK-086]."""

    def test_sections_marked(self):
        prompt = build_prompt_isolation("Extract fields", "Invoice #123")
        assert "DOCUMENT DATA" in prompt
        assert "END DOCUMENT DATA" in prompt
        assert "Extract fields" in prompt
        assert "Invoice #123" in prompt
