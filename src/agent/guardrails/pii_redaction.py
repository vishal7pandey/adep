"""PII redaction & content filtering [BLK-083].

Scan LLM inputs and outputs for personally identifiable information
(PII) and sensitive content. Redact PII before it enters the LLM prompt,
and filter sensitive content from LLM responses before display.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SensitivityLevel(str, Enum):
    """Document sensitivity classification [BLK-083]."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


# PII patterns [BLK-083]
PII_PATTERNS: dict[str, re.Pattern] = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "CC": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    "EMAIL": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
    "PHONE": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
}

REDACTION_LABELS = {
    "SSN": "[REDACTED:SSN]",
    "CC": "[REDACTED:CC]",
    "EMAIL": "[REDACTED:EMAIL]",
    "PHONE": "[REDACTED:PHONE]",
    "IBAN": "[REDACTED:IBAN]",
}


def _luhn_valid(number: str) -> bool:
    """Validate a number using Luhn algorithm (for credit card detection)."""
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, digit in enumerate(digits):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


@dataclass
class PIIDetection:
    """Result of PII detection [BLK-083].

    Attributes:
        pii_type: Type of PII detected (SSN, CC, EMAIL, etc.).
        original: The original matched text.
        redacted: The redacted replacement text.
        start: Start position in the original text.
        end: End position in the original text.
    """

    pii_type: str
    original: str
    redacted: str
    start: int
    end: int


def detect_pii(text: str) -> list[PIIDetection]:
    """Detect PII patterns in text [BLK-083].

    Args:
        text: Input text to scan.

    Returns:
        List of PIIDetection instances for each match.
    """
    detections: list[PIIDetection] = []

    for pii_type, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            matched_text = match.group()

            # For credit cards, validate with Luhn
            if pii_type == "CC":
                digits_only = re.sub(r"[^\d]", "", matched_text)
                if not _luhn_valid(digits_only):
                    continue

            detections.append(PIIDetection(
                pii_type=pii_type,
                original=matched_text,
                redacted=REDACTION_LABELS[pii_type],
                start=match.start(),
                end=match.end(),
            ))

    return detections


def redact_pii(text: str, types: set[str] | None = None) -> tuple[str, list[PIIDetection]]:
    """Redact PII from text [BLK-083].

    Args:
        text: Input text to redact.
        types: Optional set of PII types to redact. If None, all types are redacted.

    Returns:
        Tuple of (redacted_text, list_of_detections).
    """
    detections = detect_pii(text)

    if types is not None:
        detections = [d for d in detections if d.pii_type in types]

    # Sort by position descending so replacements don't affect earlier positions
    detections.sort(key=lambda d: d.start, reverse=True)

    redacted_text = text
    for detection in detections:
        redacted_text = redacted_text[:detection.start] + detection.redacted + redacted_text[detection.end:]

    if detections:
        logger.info(
            "Redacted %d PII instances: %s [BLK-083]",
            len(detections),
            [d.pii_type for d in detections],
        )

    # Sort detections back by position ascending for the return value
    detections.sort(key=lambda d: d.start)

    return redacted_text, detections


def classify_sensitivity(text: str) -> SensitivityLevel:
    """Classify document sensitivity level based on PII content [BLK-083].

    Args:
        text: Document text sample.

    Returns:
        SensitivityLevel classification.
    """
    detections = detect_pii(text)

    if not detections:
        return SensitivityLevel.PUBLIC

    pii_types = {d.pii_type for d in detections}

    # Restricted: SSN, CC, IBAN
    if pii_types & {"SSN", "CC", "IBAN"}:
        return SensitivityLevel.RESTRICTED

    # Confidential: EMAIL, PHONE
    if pii_types & {"EMAIL", "PHONE"}:
        return SensitivityLevel.CONFIDENTIAL

    return SensitivityLevel.INTERNAL


def is_provider_allowed(
    sensitivity: SensitivityLevel,
    provider: str,
    restricted_providers: set[str] | None = None,
) -> bool:
    """Check if a provider is allowed for a given sensitivity level [BLK-083].

    Args:
        sensitivity: Document sensitivity level.
        provider: Provider name to check.
        restricted_providers: Set of providers allowed for restricted docs.
            If None, defaults to on-prem providers only.

    Returns:
        True if the provider is allowed.
    """
    if restricted_providers is None:
        restricted_providers = {"local", "on-prem", "ollama"}

    if sensitivity == SensitivityLevel.RESTRICTED:
        return provider.lower() in restricted_providers

    return True
