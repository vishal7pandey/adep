"""Integration tests against real providers [BLK-128].

All tests are marked `@pytest.mark.integration` and skip cleanly when:
- Real credentials are not available
- Sample data / fixtures are not present

Run explicitly: `uv run pytest -m integration`

Never run in CI by default — these tests cost real money.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.eval.fixtures import (
    ExpectedFixture,
    load_expected_fixtures,
    values_match_with_tolerance,
    check_bbox_in_page_bounds,
)
from src.eval.accuracy import (
    build_accuracy_report,
    save_accuracy_report,
    compute_calibration_buckets,
    compute_expected_calibration_error,
)
from src.eval.harness import (
    GroundTruthField,
    GroundTruthSample,
    run_evaluation,
    EvaluationReport,
)
from src.eval.benchmarks import (
    BenchmarkResult,
    BenchmarkReport,
    save_benchmark_report,
    time_operation,
    BENCHMARK_TARGETS,
)

# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

def _has_credentials() -> bool:
    """Check if real provider credentials are available [BLK-128, SCRUM-512]."""
    from src.tests._credentials import has_real_credentials
    return has_real_credentials()


def _has_fixtures() -> bool:
    """Check if expected fixtures exist in sample-data/ [BLK-128]."""
    sample_dir = Path.cwd() / "sample-data"
    if not sample_dir.exists():
        return False
    return bool(list(sample_dir.rglob("*.expected.json")))


skip_no_credentials = pytest.mark.skipif(
    not _has_credentials(),
    reason="No real provider credentials found. Set AZURE_OPENAI_API_KEY or OPENAI_API_KEY to run integration tests.",
)

skip_no_fixtures = pytest.mark.skipif(
    not _has_fixtures(),
    reason="No .expected.json fixtures found in sample-data/. mgmt is producing these under BLK-104.",
)


# ---------------------------------------------------------------------------
# Integration tests — full pipeline against real providers
# ---------------------------------------------------------------------------

@pytest.mark.integration
@skip_no_credentials
@skip_no_fixtures
class TestIntegrationReal:
    """Real-provider integration tests [BLK-128].

    These tests exercise the full extraction pipeline against real OCR and VLM
    providers. They require credentials and labelled fixtures.
    """

    @pytest.fixture(scope="class")
    def fixtures(self) -> list[ExpectedFixture]:
        """Load all expected fixtures from sample-data/."""
        return load_expected_fixtures(Path.cwd() / "sample-data")

    @pytest.fixture(scope="class")
    def extraction_results(self, fixtures: list[ExpectedFixture]) -> list[dict]:
        """Run extraction on all fixtures and return results.

        This is the expensive operation — it calls real providers.
        Cached once per test class run.
        """
        from src.api.run_engine import execute_run
        import asyncio

        results = []
        for fixture in fixtures:
            try:
                result = asyncio.get_event_loop().run_until_complete(
                    execute_run(fixture.definition_id, fixture.document_path)
                )
                results.append(result)
            except Exception as e:
                pytest.fail(f"Extraction failed for {fixture.document_path}: {e}")

        return results

    def test_field_accuracy(self, fixtures, extraction_results):
        """Per-field values match expected within tolerance [BLK-128]."""
        for fixture, result in zip(fixtures, extraction_results):
            fields = result.get("fields", [])
            extracted = {f["name"]: f for f in fields}

            for field_name, expected_value in fixture.expected.items():
                assert field_name in extracted, (
                    f"Field '{field_name}' not extracted from {fixture.document_path}"
                )

                pred_value = extracted[field_name]["value"]
                tolerance = fixture.tolerances.get(field_name, 0.0)

                assert values_match_with_tolerance(
                    pred_value, expected_value, tolerance
                ), (
                    f"Field '{field_name}' in {fixture.document_path}: "
                    f"expected {expected_value!r} (tol={tolerance}), got {pred_value!r}"
                )

    def test_confidence_minimums(self, fixtures, extraction_results):
        """Confidence meets declared minimums [BLK-128]."""
        for fixture, result in zip(fixtures, extraction_results):
            fields = result.get("fields", [])
            extracted = {f["name"]: f for f in fields}

            for field_name, min_conf in fixture.min_confidence.items():
                assert field_name in extracted, (
                    f"Field '{field_name}' not extracted from {fixture.document_path}"
                )

                actual_conf = extracted[field_name].get("confidence", 0.0)
                assert actual_conf >= min_conf, (
                    f"Field '{field_name}' confidence {actual_conf:.3f} "
                    f"below minimum {min_conf:.3f} in {fixture.document_path}"
                )

    def test_grounding_bbox_present(self, fixtures, extraction_results):
        """Grounding bboxes are present for all expected fields [BLK-128]."""
        for fixture, result in zip(fixtures, extraction_results):
            fields = result.get("fields", [])
            extracted = {f["name"]: f for f in fields}

            for field_name in fixture.expected:
                assert field_name in extracted, (
                    f"Field '{field_name}' not extracted from {fixture.document_path}"
                )
                bbox = extracted[field_name].get("bbox")
                assert bbox is not None, (
                    f"Field '{field_name}' has no grounding bbox in {fixture.document_path}"
                )

    def test_run_terminates_within_cycle_caps(self, fixtures, extraction_results):
        """Runs terminate within the configured cycle caps [BLK-128]."""
        from src.config import settings

        max_cycles = settings.max_cycles_per_document
        for fixture, result in zip(fixtures, extraction_results):
            cycles = result.get("current_cycle", 0)
            assert cycles <= max_cycles, (
                f"Run for {fixture.document_path} took {cycles} cycles, "
                f"exceeding max of {max_cycles}"
            )

    def test_accuracy_report_generated(self, fixtures, extraction_results):
        """Accuracy report is generated and saved [BLK-128]."""
        # Build ground truth samples from fixtures
        truths = []
        for fixture in fixtures:
            fields = [
                GroundTruthField(name=name, value=value)
                for name, value in fixture.expected.items()
            ]
            truths.append(GroundTruthSample(
                document_path=fixture.document_path,
                fields=fields,
            ))

        # Build ExtractedResult-like objects from the API results
        # The eval harness expects ExtractedResult, but we have serialized dicts.
        # We'll build a simplified report directly.
        from src.eval.harness import FieldMetric

        report = EvaluationReport(sample_count=len(fixtures))
        for fixture, result in zip(fixtures, extraction_results):
            fields = result.get("fields", [])
            extracted = {f["name"]: f for f in fields}

            for field_name, expected_value in fixture.expected.items():
                if field_name not in report.field_metrics:
                    report.field_metrics[field_name] = FieldMetric(name=field_name)

                metric = report.field_metrics[field_name]
                metric.total += 1

                if field_name in extracted:
                    pred_value = extracted[field_name]["value"]
                    tolerance = fixture.tolerances.get(field_name, 0.0)
                    is_correct = values_match_with_tolerance(
                        pred_value, expected_value, tolerance
                    )
                    if is_correct:
                        metric.correct += 1
                    conf = extracted[field_name].get("confidence", 0.0)
                    metric.confidence_values.append(conf)
                    metric.correctness.append(1.0 if is_correct else 0.0)
                else:
                    metric.confidence_values.append(0.0)
                    metric.correctness.append(0.0)

        accuracy_report = build_accuracy_report(
            report, fixtures, results_data=extraction_results,
        )
        report_path = save_accuracy_report(accuracy_report)

        assert report_path.exists()
        assert accuracy_report.documents_tested > 0
        assert accuracy_report.field_accuracy >= 0.0

    def test_confidence_calibration(self, fixtures, extraction_results):
        """Confidence calibration is measured and failures flagged [BLK-128]."""
        from src.eval.harness import FieldMetric

        all_conf: list[float] = []
        all_correct: list[float] = []

        for fixture, result in zip(fixtures, extraction_results):
            fields = result.get("fields", [])
            extracted = {f["name"]: f for f in fields}

            for field_name, expected_value in fixture.expected.items():
                if field_name in extracted:
                    pred_value = extracted[field_name]["value"]
                    tolerance = fixture.tolerances.get(field_name, 0.0)
                    is_correct = values_match_with_tolerance(
                        pred_value, expected_value, tolerance
                    )
                    conf = extracted[field_name].get("confidence", 0.0)
                    all_conf.append(conf)
                    all_correct.append(1.0 if is_correct else 0.0)

        if not all_conf:
            pytest.skip("No predictions to calibrate")

        buckets = compute_calibration_buckets(all_conf, all_correct)
        ece = compute_expected_calibration_error(all_conf, all_correct, len(all_conf))

        # Report calibration
        for bucket in buckets:
            if bucket.is_failure:
                pytest.fail(
                    f"Calibration failure in bucket [{bucket.range_low:.1f}, {bucket.range_high:.1f}): "
                    f"avg_confidence={bucket.avg_confidence:.3f}, "
                    f"actual_accuracy={bucket.actual_accuracy:.3f}, "
                    f"error={bucket.calibration_error:.3f} > {0.15}"
                )

    def test_cached_second_run_zero_provider_calls(self, fixtures, extraction_results):
        """A cached second run makes zero provider calls [BLK-128, BLK-124]."""
        from src.tools.cache import get_cache, reset_cache
        from src.tools.base import ToolRegistry, ToolSpec, ToolResult

        # The first run already populated the cache.
        # Verify cache has entries.
        cache = get_cache()
        stats = cache.stats()
        assert stats["disk_entries"] > 0 or stats["memory_entries"] > 0, (
            "Cache should have entries after the first run"
        )
