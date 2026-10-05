"""Tests for Evaluation Harness [BLK-015, §10, TS].

Tests cover:
- BBox IoU computation
- Value matching with type coercion
- BBox overlap detection
- Per-field metrics (accuracy, grounded accuracy, calibration)
- Full evaluation report across multiple samples
- Fixture loading from JSON
- JSON report serialization
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.eval.harness import (
    EvaluationReport,
    FieldMetric,
    GroundTruthField,
    GroundTruthSample,
    bbox_iou,
    bbox_overlaps,
    evaluate_extraction,
    load_fixtures,
    run_evaluation,
    values_match,
)
from src.templates.base import ExtractedResult
from src.agent.validator import GapReport
from src.tools.base import FieldValue, Grounding


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    field_values: dict[str, FieldValue],
    is_complete: bool = True,
) -> ExtractedResult:
    """Build a minimal ExtractedResult for testing."""
    return ExtractedResult(
        is_complete=is_complete,
        values=None,
        field_values=field_values,
        gap_report=GapReport(
            gaps=[], satisfied=[], is_complete=is_complete, total_fields=len(field_values)
        ),
        trace=[],
        total_cycles=5,
        status="complete" if is_complete else "partial",
        provider_errors=[],
    )


def _make_fv(value, confidence: float, bbox=None) -> FieldValue:
    """Build a FieldValue with optional grounding."""
    grounding = None
    if bbox is not None:
        grounding = Grounding(bbox=bbox, source_tool="ocr", confidence=confidence)
    return FieldValue(name="test", value=value, grounding=grounding, confidence=confidence)


# ---------------------------------------------------------------------------
# BBox IoU tests
# ---------------------------------------------------------------------------


class TestBBoxIoU:
    """Verify IoU computation."""

    def test_identical_boxes(self):
        a = (10, 10, 100, 100)
        assert bbox_iou(a, a) == 1.0

    def test_no_overlap(self):
        a = (0, 0, 50, 50)
        b = (100, 100, 200, 200)
        assert bbox_iou(a, b) == 0.0

    def test_partial_overlap(self):
        a = (0, 0, 100, 100)
        b = (50, 50, 150, 150)
        iou = bbox_iou(a, b)
        assert 0.0 < iou < 1.0
        # Intersection = 50x50 = 2500
        # Union = 10000 + 10000 - 2500 = 17500
        assert abs(iou - 2500 / 17500) < 0.001

    def test_contained_box(self):
        outer = (0, 0, 100, 100)
        inner = (25, 25, 75, 75)
        iou = bbox_iou(outer, inner)
        # Intersection = inner area = 50*50 = 2500
        # Union = outer area = 10000
        assert abs(iou - 2500 / 10000) < 0.001

    def test_zero_area_box(self):
        a = (10, 10, 10, 10)  # zero area
        b = (0, 0, 50, 50)
        assert bbox_iou(a, b) == 0.0


# ---------------------------------------------------------------------------
# Value matching tests
# ---------------------------------------------------------------------------


class TestValuesMatch:
    """Verify value matching with type coercion."""

    def test_exact_string_match(self):
        assert values_match("INV-001", "INV-001") is True

    def test_case_insensitive(self):
        assert values_match("inv-001", "INV-001") is True

    def test_whitespace_trimmed(self):
        assert values_match("  INV-001  ", "INV-001") is True

    def test_float_match(self):
        assert values_match(1500.0, 1500.0) is True

    def test_float_with_tolerance(self):
        assert values_match(1500.004, 1500.0) is True

    def test_float_outside_tolerance(self):
        assert values_match(1500.02, 1500.0) is False

    def test_int_float_match(self):
        assert values_match(1500, 1500.0) is True

    def test_none_predicted(self):
        assert values_match(None, "INV-001") is False

    def test_string_vs_number(self):
        assert values_match("1500", 1500) is True  # string comparison after str()


# ---------------------------------------------------------------------------
# BBox overlap tests
# ---------------------------------------------------------------------------


class TestBBoxOverlaps:
    """Verify bbox overlap detection."""

    def test_overlapping_above_threshold(self):
        a = (0, 0, 100, 100)
        b = (0, 0, 100, 100)
        assert bbox_overlaps(a, b, threshold=0.5) is True

    def test_below_threshold(self):
        a = (0, 0, 100, 100)
        b = (90, 90, 200, 200)
        assert bbox_overlaps(a, b, threshold=0.5) is False

    def test_none_predicted(self):
        assert bbox_overlaps(None, (0, 0, 100, 100)) is False

    def test_none_truth(self):
        assert bbox_overlaps((0, 0, 100, 100), None) is False


# ---------------------------------------------------------------------------
# Evaluate extraction tests
# ---------------------------------------------------------------------------


class TestEvaluateExtraction:
    """Verify single sample evaluation."""

    def test_all_correct(self):
        result = _make_result(
            {
                "invoice_number": _make_fv("INV-001", 0.95, bbox=(10, 10, 200, 50)),
                "total": _make_fv(1500.0, 0.92, bbox=(10, 200, 200, 240)),
            }
        )
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[
                GroundTruthField("invoice_number", "INV-001", bbox=(10, 10, 200, 50)),
                GroundTruthField("total", 1500.0, bbox=(10, 200, 200, 240)),
            ],
        )
        evals = evaluate_extraction(result, truth)
        assert evals["invoice_number"][:3] == (True, True, 0.95)
        assert evals["total"][:3] == (True, True, 0.92)

    def test_value_correct_bbox_wrong(self):
        result = _make_result(
            {
                "invoice_number": _make_fv("INV-001", 0.9, bbox=(10, 10, 200, 50)),
            }
        )
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[
                GroundTruthField("invoice_number", "INV-001", bbox=(500, 500, 700, 550)),
            ],
        )
        evals = evaluate_extraction(result, truth)
        assert evals["invoice_number"][:3] == (True, False, 0.9)

    def test_value_wrong(self):
        result = _make_result(
            {
                "invoice_number": _make_fv("WRONG", 0.7, bbox=(10, 10, 200, 50)),
            }
        )
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[
                GroundTruthField("invoice_number", "INV-001", bbox=(10, 10, 200, 50)),
            ],
        )
        evals = evaluate_extraction(result, truth)
        assert evals["invoice_number"][:3] == (False, False, 0.7)

    def test_missing_field(self):
        result = _make_result({})
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[
                GroundTruthField("invoice_number", "INV-001", bbox=(10, 10, 200, 50)),
            ],
        )
        evals = evaluate_extraction(result, truth)
        assert evals["invoice_number"][:3] == (False, False, 0.0)

    def test_no_grounding_on_truth(self):
        """Ground truth has no bbox — only value accuracy matters."""
        result = _make_result(
            {
                "vendor": _make_fv("ACME Corp", 0.88, bbox=(10, 10, 200, 50)),
            }
        )
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[
                GroundTruthField("vendor", "ACME Corp", bbox=None),
            ],
        )
        evals = evaluate_extraction(result, truth)
        assert evals["vendor"][:3] == (
            True,
            False,
            0.88,
        )  # grounded_correct=False because truth bbox is None


# ---------------------------------------------------------------------------
# Full evaluation report tests
# ---------------------------------------------------------------------------


class TestRunEvaluation:
    """Verify multi-sample evaluation reports."""

    def test_report_accuracy(self):
        results = [
            _make_result(
                {
                    "invoice_number": _make_fv("INV-001", 0.95, bbox=(10, 10, 200, 50)),
                    "total": _make_fv(1500.0, 0.90, bbox=(10, 200, 200, 240)),
                }
            ),
            _make_result(
                {
                    "invoice_number": _make_fv("INV-002", 0.92, bbox=(10, 10, 200, 50)),
                    "total": _make_fv(2000.0, 0.85, bbox=(10, 200, 200, 240)),
                }
            ),
        ]
        truths = [
            GroundTruthSample(
                "test1.png",
                [
                    GroundTruthField("invoice_number", "INV-001", bbox=(10, 10, 200, 50)),
                    GroundTruthField("total", 1500.0, bbox=(10, 200, 200, 240)),
                ],
            ),
            GroundTruthSample(
                "test2.png",
                [
                    GroundTruthField("invoice_number", "INV-002", bbox=(10, 10, 200, 50)),
                    GroundTruthField("total", 2000.0, bbox=(10, 200, 200, 240)),
                ],
            ),
        ]

        report = run_evaluation(results, truths)
        assert report.sample_count == 2
        assert report.overall_accuracy == 1.0
        assert report.overall_grounded_accuracy == 1.0
        assert report.field_metrics["invoice_number"].correct == 2
        assert report.field_metrics["total"].correct == 2

    def test_report_partial_accuracy(self):
        results = [
            _make_result(
                {
                    "invoice_number": _make_fv("INV-001", 0.95, bbox=(10, 10, 200, 50)),
                }
            ),
            _make_result(
                {
                    "invoice_number": _make_fv("WRONG", 0.7, bbox=(10, 10, 200, 50)),
                }
            ),
        ]
        truths = [
            GroundTruthSample(
                "test1.png",
                [
                    GroundTruthField("invoice_number", "INV-001", bbox=(10, 10, 200, 50)),
                ],
            ),
            GroundTruthSample(
                "test2.png",
                [
                    GroundTruthField("invoice_number", "INV-002", bbox=(10, 10, 200, 50)),
                ],
            ),
        ]

        report = run_evaluation(results, truths)
        assert report.overall_accuracy == 0.5
        assert report.field_metrics["invoice_number"].correct == 1
        assert report.field_metrics["invoice_number"].total == 2

    def test_calibration_error(self):
        """High confidence + wrong → high calibration error."""
        results = [
            _make_result(
                {
                    "field": _make_fv("WRONG", 0.95, bbox=(0, 0, 100, 50)),
                }
            ),
        ]
        truths = [
            GroundTruthSample(
                "test.png",
                [
                    GroundTruthField("field", "RIGHT", bbox=(0, 0, 100, 50)),
                ],
            ),
        ]

        report = run_evaluation(results, truths)
        # confidence=0.95, correctness=0.0 → error=0.95
        assert abs(report.overall_calibration_error - 0.95) < 0.001

    def test_perfect_calibration(self):
        """Confidence matches correctness → zero calibration error."""
        results = [
            _make_result(
                {
                    "field": _make_fv("RIGHT", 1.0, bbox=(0, 0, 100, 50)),
                }
            ),
        ]
        truths = [
            GroundTruthSample(
                "test.png",
                [
                    GroundTruthField("field", "RIGHT", bbox=(0, 0, 100, 50)),
                ],
            ),
        ]

        report = run_evaluation(results, truths)
        assert report.overall_calibration_error == 0.0

    def test_empty_results(self):
        report = run_evaluation([], [])
        assert report.sample_count == 0
        assert report.overall_accuracy == 0.0


# ---------------------------------------------------------------------------
# Report serialization tests
# ---------------------------------------------------------------------------


class TestReportSerialization:
    """Verify JSON report output."""

    def test_to_json(self):
        results = [
            _make_result(
                {
                    "invoice_number": _make_fv("INV-001", 0.95, bbox=(10, 10, 200, 50)),
                }
            ),
        ]
        truths = [
            GroundTruthSample(
                "test.png",
                [
                    GroundTruthField("invoice_number", "INV-001", bbox=(10, 10, 200, 50)),
                ],
            ),
        ]
        report = run_evaluation(results, truths)
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["sample_count"] == 1
        assert data["overall_accuracy"] == 1.0
        assert "invoice_number" in data["fields"]
        assert data["fields"]["invoice_number"]["correct"] == 1

    def test_save_to_file(self, tmp_path: Path):
        results = [
            _make_result(
                {
                    "field": _make_fv("val", 0.9, bbox=(0, 0, 100, 50)),
                }
            ),
        ]
        truths = [
            GroundTruthSample(
                "test.png",
                [
                    GroundTruthField("field", "val", bbox=(0, 0, 100, 50)),
                ],
            ),
        ]
        report = run_evaluation(results, truths)
        out_path = tmp_path / "report.json"
        report.save(out_path)
        assert out_path.exists()
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["sample_count"] == 1

    def test_to_dict_structure(self):
        results = [
            _make_result(
                {
                    "f1": _make_fv("v1", 0.9, bbox=(0, 0, 100, 50)),
                    "f2": _make_fv("v2", 0.8, bbox=(0, 0, 100, 50)),
                }
            ),
        ]
        truths = [
            GroundTruthSample(
                "test.png",
                [
                    GroundTruthField("f1", "v1", bbox=(0, 0, 100, 50)),
                    GroundTruthField("f2", "v2", bbox=(0, 0, 100, 50)),
                ],
            ),
        ]
        report = run_evaluation(results, truths)
        d = report.to_dict()
        assert "sample_count" in d
        assert "overall_accuracy" in d
        assert "overall_grounded_accuracy" in d
        assert "overall_calibration_error" in d
        assert "fields" in d
        assert "f1" in d["fields"]
        assert "f2" in d["fields"]
        assert "accuracy" in d["fields"]["f1"]
        assert "grounded_accuracy" in d["fields"]["f1"]
        assert "calibration_error" in d["fields"]["f1"]


# ---------------------------------------------------------------------------
# Fixture loading tests
# ---------------------------------------------------------------------------


class TestLoadFixtures:
    """Verify fixture loading from JSON files."""

    def test_load_single_sample(self, tmp_path: Path):
        gt = {
            "document_path": "invoice_001.png",
            "fields": [
                {"name": "invoice_number", "value": "INV-001", "bbox": [10, 10, 200, 50]},
                {"name": "total", "value": 1500.0, "bbox": [10, 200, 200, 240]},
            ],
        }
        (tmp_path / "ground_truth.json").write_text(json.dumps(gt), encoding="utf-8")

        samples = load_fixtures(tmp_path)
        assert len(samples) == 1
        assert samples[0].fields[0].name == "invoice_number"
        assert samples[0].fields[0].value == "INV-001"
        assert samples[0].fields[0].bbox == (10, 10, 200, 50)

    def test_load_list_of_samples(self, tmp_path: Path):
        gt = [
            {
                "document_path": "invoice_001.png",
                "fields": [{"name": "total", "value": 100.0}],
            },
            {
                "document_path": "invoice_002.png",
                "fields": [{"name": "total", "value": 200.0}],
            },
        ]
        (tmp_path / "ground_truth.json").write_text(json.dumps(gt), encoding="utf-8")

        samples = load_fixtures(tmp_path)
        assert len(samples) == 2

    def test_load_missing_dir(self, tmp_path: Path):
        samples = load_fixtures(tmp_path / "nonexistent")
        assert samples == []

    def test_document_path_resolved_relative(self, tmp_path: Path):
        gt = {
            "document_path": "invoice.png",
            "fields": [{"name": "total", "value": 100.0}],
        }
        (tmp_path / "ground_truth.json").write_text(json.dumps(gt), encoding="utf-8")

        samples = load_fixtures(tmp_path)
        assert str(tmp_path / "invoice.png") in samples[0].document_path

    def test_field_without_bbox(self, tmp_path: Path):
        gt = {
            "document_path": "invoice.png",
            "fields": [{"name": "vendor", "value": "ACME"}],
        }
        (tmp_path / "ground_truth.json").write_text(json.dumps(gt), encoding="utf-8")

        samples = load_fixtures(tmp_path)
        assert samples[0].fields[0].bbox is None
