"""Unit tests for the integration test harness itself [BLK-128].

These tests verify the fixture loader, accuracy report writer, confidence
calibration, and benchmark utilities. They are NOT marked `@pytest.mark.integration`
and run in normal CI.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from src.eval.fixtures import (
    ExpectedFixture,
    load_expected_fixtures,
    values_match_with_tolerance,
    check_bbox_in_page_bounds,
)
from src.eval.accuracy import (
    AccuracyReport,
    CalibrationBucket,
    compute_calibration_buckets,
    compute_expected_calibration_error,
    build_accuracy_report,
    save_accuracy_report,
)
from src.eval.benchmarks import (
    BenchmarkResult,
    BenchmarkReport,
    save_benchmark_report,
    time_operation,
    BENCHMARK_TARGETS,
)
from src.eval.harness import (
    EvaluationReport,
    FieldMetric,
    GroundTruthField,
    GroundTruthSample,
    run_evaluation,
)


# ---------------------------------------------------------------------------
# Fixture loader tests
# ---------------------------------------------------------------------------


class TestFixtureLoader:
    """Verify .expected.json fixture loading [BLK-128]."""

    def test_load_expected_fixtures(self, tmp_path: Path):
        fixture_file = tmp_path / "invoice.expected.json"
        fixture_file.write_text(
            json.dumps(
                {
                    "document": "invoice_001.pdf",
                    "definition_id": "def-invoice",
                    "expected": {"invoice_number": "INV-001", "total": 1500.00},
                    "tolerances": {"total": 0.01},
                    "min_confidence": {"invoice_number": 0.85},
                }
            )
        )

        fixtures = load_expected_fixtures(tmp_path)
        assert len(fixtures) == 1
        assert fixtures[0].definition_id == "def-invoice"
        assert fixtures[0].expected["invoice_number"] == "INV-001"
        assert fixtures[0].tolerances["total"] == 0.01
        assert fixtures[0].min_confidence["invoice_number"] == 0.85

    def test_load_fixtures_empty_dir(self, tmp_path: Path):
        fixtures = load_expected_fixtures(tmp_path)
        assert fixtures == []

    def test_load_fixtures_nonexistent_dir(self):
        fixtures = load_expected_fixtures("/nonexistent/path")
        assert fixtures == []

    def test_load_fixtures_multiple(self, tmp_path: Path):
        for i in range(3):
            f = tmp_path / f"doc{i}.expected.json"
            f.write_text(
                json.dumps(
                    {
                        "document": f"doc{i}.pdf",
                        "definition_id": "def-invoice",
                        "expected": {"field": f"value{i}"},
                    }
                )
            )

        fixtures = load_expected_fixtures(tmp_path)
        assert len(fixtures) == 3

    def test_load_fixtures_absolute_document_path(self, tmp_path: Path):
        abs_path = str(tmp_path / "doc.pdf")
        fixture_file = tmp_path / "doc.expected.json"
        fixture_file.write_text(
            json.dumps(
                {
                    "document": abs_path,
                    "definition_id": "def-invoice",
                    "expected": {},
                }
            )
        )

        fixtures = load_expected_fixtures(tmp_path)
        assert fixtures[0].document_path == abs_path


# ---------------------------------------------------------------------------
# Value matching tests
# ---------------------------------------------------------------------------


class TestValuesMatch:
    """Verify values_match_with_tolerance [BLK-128]."""

    def test_exact_string_match(self):
        assert values_match_with_tolerance("INV-001", "INV-001")

    def test_case_insensitive_string_match(self):
        assert values_match_with_tolerance("inv-001", "INV-001")

    def test_string_mismatch(self):
        assert not values_match_with_tolerance("INV-001", "INV-002")

    def test_exact_numeric_match(self):
        assert values_match_with_tolerance(1500.00, 1500.00)

    def test_numeric_within_tolerance(self):
        assert values_match_with_tolerance(1500.005, 1500.00, tolerance=0.01)

    def test_numeric_outside_tolerance(self):
        assert not values_match_with_tolerance(1500.05, 1500.00, tolerance=0.01)

    def test_none_predicted(self):
        assert not values_match_with_tolerance(None, "value")

    def test_type_mismatch(self):
        # String "1500" matches int 1500 via string comparison — this is by design
        assert values_match_with_tolerance("1500", 1500)
        # But "abc" does not match 1500
        assert not values_match_with_tolerance("abc", 1500)


# ---------------------------------------------------------------------------
# BBox validation tests
# ---------------------------------------------------------------------------


class TestBboxValidation:
    """Verify check_bbox_in_page_bounds [BLK-128]."""

    def test_valid_bbox(self):
        assert check_bbox_in_page_bounds((10, 10, 100, 100), 800, 600)

    def test_none_bbox(self):
        assert not check_bbox_in_page_bounds(None, 800, 600)

    def test_zero_area_bbox(self):
        assert not check_bbox_in_page_bounds((10, 10, 10, 10), 800, 600)

    def test_negative_origin(self):
        assert not check_bbox_in_page_bounds((-5, 10, 100, 100), 800, 600)

    def test_exceeds_page_bounds(self):
        assert not check_bbox_in_page_bounds((10, 10, 900, 100), 800, 600)

    def test_exact_page_bounds(self):
        assert check_bbox_in_page_bounds((0, 0, 800, 600), 800, 600)


# ---------------------------------------------------------------------------
# Calibration tests
# ---------------------------------------------------------------------------


class TestCalibration:
    """Verify confidence calibration computation [BLK-128]."""

    def test_perfect_calibration(self):
        confidences = [0.9, 0.9, 0.9, 0.9]
        correctness = [1.0, 1.0, 1.0, 1.0]
        buckets = compute_calibration_buckets(confidences, correctness)
        # All in [0.8, 1.0) bucket
        high_bucket = [b for b in buckets if b.range_low == 0.8][0]
        assert high_bucket.count == 4
        assert high_bucket.actual_accuracy == 1.0
        assert not high_bucket.is_failure

    def test_poor_calibration(self):
        confidences = [0.9, 0.9, 0.9, 0.9]
        correctness = [0.0, 0.0, 0.0, 0.0]
        buckets = compute_calibration_buckets(confidences, correctness)
        high_bucket = [b for b in buckets if b.range_low == 0.8][0]
        assert high_bucket.actual_accuracy == 0.0
        assert high_bucket.calibration_error > 0.15
        assert high_bucket.is_failure

    def test_ece_perfect(self):
        confidences = [0.5, 0.5]
        correctness = [1.0, 0.0]
        ece = compute_expected_calibration_error(confidences, correctness, 2)
        # In [0.4, 0.6) bucket: avg_conf=0.5, accuracy=0.5, error=0
        assert ece == 0.0

    def test_ece_empty(self):
        ece = compute_expected_calibration_error([], [], 0)
        assert ece == 0.0

    def test_calibration_bucket_distribution(self):
        confidences = [0.1, 0.3, 0.5, 0.7, 0.9]
        correctness = [0.0, 0.0, 1.0, 1.0, 1.0]
        buckets = compute_calibration_buckets(confidences, correctness)
        # Each bucket should have exactly 1 entry
        for b in buckets:
            if b.count > 0:
                assert b.count == 1


# ---------------------------------------------------------------------------
# Accuracy report tests
# ---------------------------------------------------------------------------


class TestAccuracyReport:
    """Verify accuracy report generation [BLK-128]."""

    def test_build_accuracy_report(self, tmp_path: Path):
        # Build a minimal EvaluationReport
        report = EvaluationReport(sample_count=2)
        report.field_metrics["invoice_number"] = FieldMetric(name="invoice_number")
        m = report.field_metrics["invoice_number"]
        m.total = 2
        m.correct = 2
        m.confidence_values = [0.9, 0.85]
        m.correctness = [1.0, 1.0]

        fixtures = [
            ExpectedFixture(
                document_path="a.pdf",
                definition_id="def-invoice",
                expected={"invoice_number": "INV-001"},
            ),
            ExpectedFixture(
                document_path="b.pdf",
                definition_id="def-invoice",
                expected={"invoice_number": "INV-002"},
            ),
        ]

        accuracy = build_accuracy_report(report, fixtures)

        assert accuracy.documents_tested == 2
        assert accuracy.field_accuracy == 1.0
        assert len(accuracy.per_field) == 1
        assert accuracy.per_field["invoice_number"]["accuracy"] == 1.0

    def test_save_accuracy_report(self, tmp_path: Path):
        report = AccuracyReport(
            run_at="2026-01-01T00:00:00Z",
            documents_tested=1,
            field_accuracy=0.95,
        )
        path = save_accuracy_report(report, reports_dir=tmp_path / "reports")
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["documents_tested"] == 1
        assert data["field_accuracy"] == 0.95

    def test_accuracy_report_with_failures(self):
        report = EvaluationReport(sample_count=2)
        report.field_metrics["total"] = FieldMetric(name="total")
        m = report.field_metrics["total"]
        m.total = 2
        m.correct = 1
        m.confidence_values = [0.9, 0.3]
        m.correctness = [1.0, 0.0]

        accuracy = build_accuracy_report(report, [])
        assert len(accuracy.failures) == 1
        assert accuracy.failures[0]["field"] == "total"

    def test_accuracy_report_calibration_buckets(self):
        report = EvaluationReport(sample_count=1)
        report.field_metrics["field1"] = FieldMetric(name="field1")
        m = report.field_metrics["field1"]
        m.total = 1
        m.correct = 1
        m.confidence_values = [0.9]
        m.correctness = [1.0]

        accuracy = build_accuracy_report(report, [])
        assert len(accuracy.calibration_buckets) == 5  # 5 buckets
        # Check the [0.8, 1.0) bucket has the entry
        high_bucket = [b for b in accuracy.calibration_buckets if b["range"] == "[0.8, 1.0)"][0]
        assert high_bucket["count"] == 1


# ---------------------------------------------------------------------------
# Benchmark utility tests
# ---------------------------------------------------------------------------


class TestBenchmarkUtils:
    """Verify benchmark utilities [BLK-128]."""

    def test_time_operation(self):
        def slow_func():
            time.sleep(0.01)
            return 42

        result, duration = time_operation(slow_func)
        assert result == 42
        assert duration >= 0.01

    def test_benchmark_result_to_dict(self):
        r = BenchmarkResult(
            name="test",
            duration_seconds=0.5,
            target_seconds=1.0,
            passed=True,
        )
        d = r.to_dict()
        assert d["name"] == "test"
        assert d["passed"] is True

    def test_benchmark_report_save(self, tmp_path: Path):
        report = BenchmarkReport(
            run_at="2026-01-01T00:00:00Z",
            benchmarks=[{"name": "test", "duration_seconds": 0.5}],
            all_passed=True,
        )
        path = save_benchmark_report(report, reports_dir=tmp_path / "reports")
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["all_passed"] is True
        assert len(data["benchmarks"]) == 1

    def test_benchmark_targets_defined(self):
        assert "tool_registry_lookup" in BENCHMARK_TARGETS
        assert "single_page_invoice_cold_cache" in BENCHMARK_TARGETS
        assert "single_page_invoice_warm_cache" in BENCHMARK_TARGETS
        assert "definition_store_list_100" in BENCHMARK_TARGETS
        assert "sse_first_byte" in BENCHMARK_TARGETS

    def test_benchmark_result_failure(self):
        r = BenchmarkResult(
            name="test",
            duration_seconds=2.0,
            target_seconds=1.0,
            passed=False,
        )
        assert not r.passed
        assert not r.to_dict()["passed"]


# ---------------------------------------------------------------------------
# Integration marker tests
# ---------------------------------------------------------------------------


class TestIntegrationMarker:
    """Verify integration tests are properly marked [BLK-128]."""

    def test_integration_marker_registered(self):
        import subprocess

        result = subprocess.run(
            ["uv", "run", "pytest", "--markers"],
            capture_output=True,
            text=True,
            cwd=str(Path.cwd()),
        )
        assert "integration" in result.stdout

    def test_integration_tests_deselected_by_default(self):
        """Integration tests should NOT run in the normal test suite."""
        import subprocess

        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                "--collect-only",
                "-q",
                "-m",
                "not integration",
                "src/tests/test_integration_real.py",
                "src/tests/test_benchmarks.py",
            ],
            capture_output=True,
            text=True,
            cwd=str(Path.cwd()),
        )
        # All items should be deselected
        output = result.stdout + result.stderr
        assert "deselected" in output or "no tests collected" in output.lower()
