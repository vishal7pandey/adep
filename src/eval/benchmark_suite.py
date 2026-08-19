"""Real-world benchmark suite for extraction quality and provider comparison [BLK-174].

Runs extraction across labeled sample documents for multiple provider configurations
and produces a comparison report with:
- Per-field accuracy, grounded accuracy, ANLS, SMuDGE
- Confidence calibration (ECE)
- Latency and token cost per provider
- Side-by-side provider comparison table
- Regression detection against baseline

Usage:
    from src.eval.benchmark_suite import run_benchmark_suite
    report = run_benchmark_suite(
        fixture_dir="sample-data/invoices/",
        providers=["paddle", "tesseract"],
    )
    print(report.to_json())
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.eval.harness import (
    EvaluationReport,
    FieldMetric,
    GroundTruthSample,
    anls_score,
    bbox_iou,
    evaluate_extraction,
    load_fixtures,
    run_evaluation,
    smudge_evaluate,
    values_match,
)
from src.eval.accuracy import (
    AccuracyReport,
    build_accuracy_report,
    compute_expected_calibration_error,
    save_accuracy_report,
)
from src.eval.fixtures import ExpectedFixture, load_expected_fixtures, values_match_with_tolerance
from src.eval.benchmarks import BenchmarkResult, BenchmarkReport, save_benchmark_report

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider configurations
# ---------------------------------------------------------------------------

PROVIDER_CONFIGS: dict[str, dict[str, str]] = {
    "paddle": {"ADE_OCR_PROVIDER": "paddle"},
    "tesseract": {"ADE_OCR_PROVIDER": "tesseract"},
    "azure": {"ADE_VLM_PROVIDER": "azure"},
}

DEFAULT_PROVIDERS = ["paddle", "tesseract"]


# ---------------------------------------------------------------------------
# Report structures
# ---------------------------------------------------------------------------

@dataclass
class ProviderResult:
    """Extraction quality metrics for a single provider [BLK-174].

    Attributes:
        provider: Provider name (e.g. "paddle", "tesseract").
        documents_tested: Number of documents successfully extracted.
        documents_failed: Number of documents that errored.
        overall_accuracy: Fraction of fields with correct values.
        overall_grounded_accuracy: Fraction with correct value + overlapping bbox.
        overall_anls: Mean ANLS score across all fields.
        overall_smudge: Mean SMuDGE combined score.
        avg_confidence: Average reported confidence.
        calibration_error: Expected Calibration Error (ECE).
        avg_latency_seconds: Mean extraction time per document.
        avg_tokens: Mean tokens consumed per document.
        avg_cost_usd: Mean cost per document.
        per_field: Per-field metrics dict.
        failures: List of per-field failure details.
    """

    provider: str = ""
    documents_tested: int = 0
    documents_failed: int = 0
    overall_accuracy: float = 0.0
    overall_grounded_accuracy: float = 0.0
    overall_anls: float = 0.0
    overall_smudge: float = 0.0
    avg_confidence: float = 0.0
    calibration_error: float = 0.0
    avg_latency_seconds: float = 0.0
    avg_tokens: int = 0
    avg_cost_usd: float = 0.0
    per_field: dict[str, dict[str, Any]] = field(default_factory=dict)
    failures: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "documents_tested": self.documents_tested,
            "documents_failed": self.documents_failed,
            "overall_accuracy": round(self.overall_accuracy, 4),
            "overall_grounded_accuracy": round(self.overall_grounded_accuracy, 4),
            "overall_anls": round(self.overall_anls, 4),
            "overall_smudge": round(self.overall_smudge, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "calibration_error": round(self.calibration_error, 4),
            "avg_latency_seconds": round(self.avg_latency_seconds, 2),
            "avg_tokens": self.avg_tokens,
            "avg_cost_usd": round(self.avg_cost_usd, 4),
            "per_field": self.per_field,
            "failures": self.failures,
        }


@dataclass
class BenchmarkSuiteReport:
    """Full benchmark suite report comparing providers [BLK-174].

    Attributes:
        run_at: ISO timestamp.
        fixture_dir: Path to fixtures used.
        providers: List of ProviderResult, one per provider tested.
        comparison: Side-by-side comparison matrix.
        baseline_provider: Name of the baseline provider for regression checks.
        regressions: List of fields where accuracy dropped vs baseline.
    """

    run_at: str = ""
    fixture_dir: str = ""
    providers: list[ProviderResult] = field(default_factory=list)
    comparison: dict[str, dict[str, Any]] = field(default_factory=dict)
    baseline_provider: str = ""
    regressions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_at": self.run_at,
            "fixture_dir": self.fixture_dir,
            "providers": [p.to_dict() for p in self.providers],
            "comparison": self.comparison,
            "baseline_provider": self.baseline_provider,
            "regressions": self.regressions,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(self.to_json(), encoding="utf-8")
        logger.info("Benchmark suite report saved to %s", path)


# ---------------------------------------------------------------------------
# Suite runner
# ---------------------------------------------------------------------------

def _has_credentials() -> bool:
    return bool(
        os.environ.get("AZURE_OPENAI_API_KEY")
        or os.environ.get("AZURE_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )


def _set_provider_env(provider: str) -> dict[str, str]:
    """Set environment variables for a provider and return the old values."""
    config = PROVIDER_CONFIGS.get(provider, {})
    old_values: dict[str, str] = {}
    for key, val in config.items():
        old_values[key] = os.environ.get(key, "")
        os.environ[key] = val
    return old_values


def _restore_env(old_values: dict[str, str]) -> None:
    """Restore environment variables to their previous values."""
    for key, val in old_values.items():
        if val:
            os.environ[key] = val
        else:
            os.environ.pop(key, None)


def _run_single_provider(
    fixtures: list[ExpectedFixture],
    provider: str,
) -> ProviderResult:
    """Run extraction on all fixtures with a specific provider [BLK-174].

    Args:
        fixtures: List of expected fixtures with ground truth.
        provider: Provider name to configure.

    Returns:
        ProviderResult with aggregated metrics.
    """
    from src.api.run_engine import execute_run

    result = ProviderResult(provider=provider)
    all_results = []
    all_truths: list[GroundTruthSample] = []
    latencies: list[float] = []
    token_counts: list[int] = []
    costs: list[float] = []

    old_env = _set_provider_env(provider)

    try:
        for fixture in fixtures:
            doc_path = Path(fixture.document_path)
            if not doc_path.exists():
                logger.warning("Skipping missing document: %s", doc_path)
                result.documents_failed += 1
                continue

            try:
                start = time.perf_counter()
                run_result = asyncio.get_event_loop().run_until_complete(
                    execute_run(fixture.definition_id, str(doc_path))
                )
                latency = time.perf_counter() - start
                latencies.append(latency)
                result.documents_tested += 1

                # Collect token/cost data
                if hasattr(run_result, "token_usage") and run_result.token_usage:
                    total_tokens = sum(
                        t.get("total_tokens", 0) if isinstance(t, dict) else getattr(t, "total_tokens", 0)
                        for t in run_result.token_usage
                    )
                    token_counts.append(total_tokens)
                if hasattr(run_result, "cost_usd"):
                    costs.append(run_result.cost_usd or 0.0)

                # Build GroundTruthSample from fixture
                truth = GroundTruthSample(
                    document_path=str(doc_path),
                    fields=[
                        # GroundTruthField is created from expected dict
                        _make_gt_field(name, value)
                        for name, value in fixture.expected.items()
                    ],
                )
                all_results.append(run_result)
                all_truths.append(truth)

            except Exception as e:
                logger.error("Extraction failed for %s with %s: %s", doc_path, provider, e)
                result.documents_failed += 1
    finally:
        _restore_env(old_env)

    # Run evaluation
    if all_results and all_truths:
        eval_report = run_evaluation(all_results, all_truths)
        accuracy_report = build_accuracy_report(eval_report, fixtures)

        result.overall_accuracy = eval_report.overall_accuracy
        result.overall_grounded_accuracy = eval_report.overall_grounded_accuracy
        result.overall_anls = eval_report.overall_anls
        result.overall_smudge = eval_report.overall_smudge
        result.avg_confidence = accuracy_report.avg_confidence
        result.calibration_error = accuracy_report.confidence_calibration_error
        result.per_field = accuracy_report.per_field
        result.failures = accuracy_report.failures

    # Aggregate latency/cost
    if latencies:
        result.avg_latency_seconds = sum(latencies) / len(latencies)
    if token_counts:
        result.avg_tokens = sum(token_counts) // len(token_counts)
    if costs:
        result.avg_cost_usd = sum(costs) / len(costs)

    return result


def _make_gt_field(name: str, value: Any):
    """Create a GroundTruthField from a name-value pair."""
    from src.eval.harness import GroundTruthField
    return GroundTruthField(name=name, value=value)


def _build_comparison(providers: list[ProviderResult]) -> dict[str, dict[str, Any]]:
    """Build a side-by-side comparison matrix across providers [BLK-174]."""
    comparison: dict[str, dict[str, Any]] = {}

    metric_keys = [
        "overall_accuracy", "overall_grounded_accuracy", "overall_anls",
        "overall_smudge", "avg_confidence", "calibration_error",
        "avg_latency_seconds", "avg_tokens", "avg_cost_usd",
    ]

    for metric in metric_keys:
        comparison[metric] = {}
        best_provider = None
        best_value = None
        for p in providers:
            val = getattr(p, metric, 0.0)
            comparison[metric][p.provider] = round(val, 4) if isinstance(val, float) else val
            # Track best (for calibration_error and latency, lower is better)
            if best_value is None:
                best_value = val
                best_provider = p.provider
            elif metric in ("calibration_error", "avg_latency_seconds", "avg_cost_usd"):
                if val < best_value:
                    best_value = val
                    best_provider = p.provider
            else:
                if val > best_value:
                    best_value = val
                    best_provider = p.provider
        comparison[metric]["best_provider"] = best_provider

    # Per-field comparison
    all_fields: set[str] = set()
    for p in providers:
        all_fields.update(p.per_field.keys())

    comparison["per_field_accuracy"] = {}
    for field_name in sorted(all_fields):
        comparison["per_field_accuracy"][field_name] = {}
        for p in providers:
            field_data = p.per_field.get(field_name, {})
            comparison["per_field_accuracy"][field_name][p.provider] = field_data.get("accuracy", 0.0)

    return comparison


def _detect_regressions(
    providers: list[ProviderResult],
    baseline: str,
    threshold: float = 0.05,
) -> list[dict[str, Any]]:
    """Detect fields where accuracy dropped vs baseline by more than threshold [BLK-174].

    Args:
        providers: List of provider results.
        baseline: Name of the baseline provider.
        threshold: Minimum accuracy drop to flag as regression.

    Returns:
        List of regression dicts with field, baseline_accuracy, provider, provider_accuracy, drop.
    """
    baseline_result = next((p for p in providers if p.provider == baseline), None)
    if not baseline_result:
        return []

    regressions: list[dict[str, Any]] = []
    for field_name, baseline_data in baseline_result.per_field.items():
        baseline_acc = baseline_data.get("accuracy", 0.0)
        for p in providers:
            if p.provider == baseline:
                continue
            provider_acc = p.per_field.get(field_name, {}).get("accuracy", 0.0)
            drop = baseline_acc - provider_acc
            if drop > threshold:
                regressions.append({
                    "field": field_name,
                    "baseline_provider": baseline,
                    "baseline_accuracy": round(baseline_acc, 4),
                    "provider": p.provider,
                    "provider_accuracy": round(provider_acc, 4),
                    "drop": round(drop, 4),
                })

    return regressions


def run_benchmark_suite(
    fixture_dir: str | Path,
    providers: list[str] | None = None,
    baseline_provider: str | None = None,
) -> BenchmarkSuiteReport:
    """Run the full benchmark suite across providers [BLK-174].

    Args:
        fixture_dir: Path to directory with .expected.json fixtures.
        providers: List of provider names to test. Defaults to ["paddle", "tesseract"].
        baseline_provider: Provider to use as baseline for regression detection.
            Defaults to the first provider.

    Returns:
        BenchmarkSuiteReport with per-provider results and comparison.
    """
    if providers is None:
        providers = DEFAULT_PROVIDERS

    if baseline_provider is None:
        baseline_provider = providers[0]

    fixtures = load_expected_fixtures(fixture_dir)
    if not fixtures:
        logger.warning("No fixtures found in %s", fixture_dir)

    report = BenchmarkSuiteReport(
        run_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        fixture_dir=str(fixture_dir),
        baseline_provider=baseline_provider,
    )

    for provider in providers:
        logger.info("Running benchmark suite with provider: %s", provider)
        provider_result = _run_single_provider(fixtures, provider)
        report.providers.append(provider_result)

    report.comparison = _build_comparison(report.providers)
    report.regressions = _detect_regressions(report.providers, baseline_provider)

    return report


def save_benchmark_suite_report(
    report: BenchmarkSuiteReport,
    reports_dir: str | Path | None = None,
) -> Path:
    """Save a benchmark suite report to `.adep/reports/` [BLK-174].

    Args:
        report: The BenchmarkSuiteReport to save.
        reports_dir: Optional custom directory. Defaults to `.adep/reports/`.

    Returns:
        Path to the saved report file.
    """
    if reports_dir is None:
        reports_dir = Path.cwd() / ".adep" / "reports"
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    filename = f"benchmark_suite_{timestamp}.json"
    path = reports_dir / filename
    report.save(path)
    return path


def load_benchmark_suite_reports(
    reports_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Load all saved benchmark suite reports, sorted newest-first [BLK-174].

    Args:
        reports_dir: Optional custom directory. Defaults to `.adep/reports/`.

    Returns:
        List of report dicts parsed from JSON files.
    """
    if reports_dir is None:
        reports_dir = Path.cwd() / ".adep" / "reports"
    reports_dir = Path(reports_dir)

    if not reports_dir.exists():
        return []

    reports: list[dict[str, Any]] = []
    for path in sorted(reports_dir.glob("benchmark_suite_*.json"), reverse=True):
        try:
            reports.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load benchmark suite report %s: %s", path, e)

    return reports
