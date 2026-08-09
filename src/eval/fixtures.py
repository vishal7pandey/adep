"""Expected-fixture loader for integration tests [BLK-128].

Loads `.expected.json` files that pair sample documents with ground-truth
field values, tolerances, and minimum confidence thresholds.

Schema:
    {
        "document": "sample-data/invoices/acme-invoice-001.pdf",
        "definition_id": "def-invoice",
        "expected": {
            "invoice_number": "INV-2024-0042",
            "total": 1250.00,
            "invoice_date": "2024-03-15"
        },
        "tolerances": {"total": 0.01},
        "min_confidence": {"invoice_number": 0.85}
    }
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExpectedFixture:
    """A single expected-fixture entry for integration testing [BLK-128].

    Attributes:
        document_path: Path to the sample document file.
        definition_id: Agent definition ID to use for extraction.
        expected: Dict of field name → expected value.
        tolerances: Dict of field name → numeric tolerance (for float comparison).
        min_confidence: Dict of field name → minimum required confidence.
    """

    document_path: str
    definition_id: str
    expected: dict[str, Any] = field(default_factory=dict)
    tolerances: dict[str, float] = field(default_factory=dict)
    min_confidence: dict[str, float] = field(default_factory=dict)


def load_expected_fixtures(fixture_dir: str | Path) -> list[ExpectedFixture]:
    """Load all `.expected.json` fixtures from a directory tree [BLK-128].

    Searches recursively for `*.expected.json` files.

    Args:
        fixture_dir: Root directory to search.

    Returns:
        List of ExpectedFixture objects.
    """
    base = Path(fixture_dir)
    fixtures: list[ExpectedFixture] = []

    if not base.exists():
        logger.warning("Fixture directory does not exist: %s", base)
        return fixtures

    for expected_file in base.rglob("*.expected.json"):
        try:
            data = json.loads(expected_file.read_text(encoding="utf-8"))
            doc_path = data.get("document", "")
            if not Path(doc_path).is_absolute():
                doc_path = str(expected_file.parent / doc_path)

            fixtures.append(ExpectedFixture(
                document_path=doc_path,
                definition_id=data.get("definition_id", ""),
                expected=data.get("expected", {}),
                tolerances=data.get("tolerances", {}),
                min_confidence=data.get("min_confidence", {}),
            ))
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to load fixture %s: %s", expected_file, e)

    return fixtures


def values_match_with_tolerance(
    predicted: Any,
    expected: Any,
    tolerance: float = 0.0,
) -> bool:
    """Check if predicted value matches expected, with optional tolerance [BLK-128].

    For numeric values, uses absolute tolerance. For strings, uses case-insensitive
    exact match.

    Args:
        predicted: The predicted value from extraction.
        expected: The expected ground-truth value.
        tolerance: Absolute tolerance for numeric comparison (default 0.0 = exact).

    Returns:
        True if values match within tolerance.
    """
    if predicted is None:
        return False

    if isinstance(predicted, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(predicted) - float(expected)) <= tolerance

    return str(predicted).strip().lower() == str(expected).strip().lower()


def check_bbox_in_page_bounds(
    bbox: tuple[int, int, int, int] | None,
    page_width: int,
    page_height: int,
) -> bool:
    """Check that a bounding box is within page bounds [BLK-128].

    Args:
        bbox: (x1, y1, x2, y2) pixel coordinates, or None.
        page_width: Page width in pixels.
        page_height: Page height in pixels.

    Returns:
        True if bbox is valid and within page bounds.
    """
    if bbox is None:
        return False

    x1, y1, x2, y2 = bbox
    if x2 <= x1 or y2 <= y1:
        return False
    if x1 < 0 or y1 < 0:
        return False
    if x2 > page_width or y2 > page_height:
        return False
    return True
