"""Accuracy report writer + confidence calibration [BLK-128].

Produces machine-readable accuracy reports and confidence calibration checks.
Writes reports to `.adep/reports/` for trend tracking.

Wires into the existing BLK-015 evaluation harness rather than duplicating it.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.eval.harness import EvaluationReport, FieldMetric
from src.eval.fixtures import ExpectedFixture, values_match_with_tolerance

logger = logging.getLogger(__name__)

# Calibration bucket boundaries
CALIBRATION_BUCKETS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
CALIBRATION_THRESHOLD = 0.15  # Flag buckets where |reported - actual| > this


@dataclass
class CalibrationBucket:
    """A single confidence calibration bucket [BLK-128].

    Attributes:
        range_low: Lower bound of the confidence range (inclusive).
        range_high: Upper bound of the confidence range (exclusive, except 1.0).
        count: Number of predictions in this bucket.
        correct: Number of correct predictions.
        avg_confidence: Average reported confidence in this bucket.
        actual_accuracy: Fraction of correct predictions.
        calibration_error: |avg_confidence - actual_accuracy|.
        is_failure: True if calibration_error > CALIBRATION_THRESHOLD.
    """

    range_low: float
    range_high: float
    count: int = 0
    correct: int = 0
    avg_confidence: float = 0.0

    @property
    def actual_accuracy(self) -> float:
        return self.correct / self.count if self.count > 0 else 0.0

    @property
    def calibration_error(self) -> float:
        return abs(self.avg_confidence - self.actual_accuracy)

    @property
    def is_failure(self) -> bool:
        return self.count > 0 and self.calibration_error > CALIBRATION_THRESHOLD

    def to_dict(self) -> dict[str, Any]:
        return {
            "range": f"[{self.range_low:.1f}, {self.range_high:.1f})",
            "count": self.count,
            "correct": self.correct,
            "avg_confidence": round(self.avg_confidence, 4),
            "actual_accuracy": round(self.actual_accuracy, 4),
            "calibration_error": round(self.calibration_error, 4),
            "is_failure": self.is_failure,
        }


@dataclass
class AccuracyReport:
    """Full accuracy report for an integration test run [BLK-128].

    Attributes:
        run_at: ISO timestamp of the run.
        documents_tested: Number of documents evaluated.
        field_accuracy: Overall fraction of correct field values.
        exact_match_rate: Fraction of fields with exact string match.
        avg_confidence: Average confidence across all predictions.
        confidence_calibration_error: Expected Calibration Error (ECE).
        avg_cycles: Average extraction cycles per document.
        avg_cost_usd: Average cost per document.
        per_field: Per-field accuracy and confidence stats.
        calibration_buckets: Confidence calibration bucket analysis.
        failures: List of per-field failures with details.
    """

    run_at: str = ""
    documents_tested: int = 0
    field_accuracy: float = 0.0
    exact_match_rate: float = 0.0
    avg_confidence: float = 0.0
    confidence_calibration_error: float = 0.0
    avg_cycles: float = 0.0
    avg_cost_usd: float = 0.0
    per_field: dict[str, dict[str, Any]] = field(default_factory=dict)
    calibration_buckets: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_at": self.run_at,
            "documents_tested": self.documents_tested,
            "field_accuracy": round(self.field_accuracy, 4),
            "exact_match_rate": round(self.exact_match_rate, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "confidence_calibration_error": round(self.confidence_calibration_error, 4),
            "avg_cycles": round(self.avg_cycles, 2),
            "avg_cost_usd": round(self.avg_cost_usd, 4),
            "per_field": self.per_field,
            "calibration_buckets": self.calibration_buckets,
            "failures": self.failures,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, path: str | Path) -> None:
        """Save report to a JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(self.to_json(), encoding="utf-8")
        logger.info("Accuracy report saved to %s", path)


def compute_calibration_buckets(
    confidence_values: list[float],
    correctness: list[float],
) -> list[CalibrationBucket]:
    """Compute confidence calibration buckets [BLK-128].

    Groups predictions into confidence ranges and compares reported confidence
    against actual accuracy per bucket.

    Args:
        confidence_values: List of reported confidence scores.
        correctness: List of 1.0 (correct) or 0.0 (incorrect), aligned with confidence_values.

    Returns:
        List of CalibrationBucket objects.
    """
    buckets: list[CalibrationBucket] = []
    for i in range(len(CALIBRATION_BUCKETS) - 1):
        buckets.append(CalibrationBucket(
            range_low=CALIBRATION_BUCKETS[i],
            range_high=CALIBRATION_BUCKETS[i + 1],
        ))

    for conf, correct in zip(confidence_values, correctness):
        for bucket in buckets:
            if bucket.range_low <= conf < bucket.range_high or (
                bucket.range_high == 1.0 and conf == 1.0
            ):
                bucket.count += 1
                bucket.avg_confidence = (
                    (bucket.avg_confidence * (bucket.count - 1) + conf) / bucket.count
                    if bucket.count > 0 else conf
                )
                if correct >= 1.0:
                    bucket.correct += 1
                break

    return buckets


def compute_expected_calibration_error(
    confidence_values: list[float],
    correctness: list[float],
    n_total: int,
) -> float:
    """Compute Expected Calibration Error (ECE) [BLK-128].

    ECE = sum over buckets of (|bucket|/total) * |avg_confidence - actual_accuracy|

    Args:
        confidence_values: All confidence scores.
        correctness: All correctness labels (1.0/0.0).
        n_total: Total number of predictions.

    Returns:
        ECE score in [0.0, 1.0].
    """
    if n_total == 0:
        return 0.0

    buckets = compute_calibration_buckets(confidence_values, correctness)
    ece = 0.0
    for bucket in buckets:
        if bucket.count == 0:
            continue
        ece += (bucket.count / n_total) * bucket.calibration_error
    return ece


def build_accuracy_report(
    eval_report: EvaluationReport,
    fixtures: list[ExpectedFixture],
    results_data: list[dict[str, Any]] | None = None,
) -> AccuracyReport:
    """Build an AccuracyReport from an EvaluationReport and fixtures [BLK-128].

    Extends the BLK-015 EvaluationReport with calibration buckets, per-field
    stats, and failure details.

    Args:
        eval_report: The EvaluationReport from run_evaluation().
        fixtures: The expected fixtures used for the run.
        results_data: Optional per-run data with cycle counts and costs.

    Returns:
        AccuracyReport with full metrics.
    """
    report = AccuracyReport(
        run_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        documents_tested=eval_report.sample_count,
        field_accuracy=eval_report.overall_accuracy,
        avg_confidence=_safe_mean(
            [m.mean_confidence for m in eval_report.field_metrics.values()]
        ),
    )

    # Per-field stats
    for name, metric in eval_report.field_metrics.items():
        report.per_field[name] = {
            "accuracy": round(metric.accuracy, 4),
            "avg_confidence": round(metric.mean_confidence, 4),
            "correct": metric.correct,
            "total": metric.total,
            "calibration_error": round(metric.calibration_error, 4),
        }

    # Calibration buckets
    all_conf: list[float] = []
    all_correct: list[float] = []
    for metric in eval_report.field_metrics.values():
        all_conf.extend(metric.confidence_values)
        all_correct.extend(metric.correctness)

    buckets = compute_calibration_buckets(all_conf, all_correct)
    report.calibration_buckets = [b.to_dict() for b in buckets]
    report.confidence_calibration_error = compute_expected_calibration_error(
        all_conf, all_correct, len(all_conf),
    )

    # Failures: fields where accuracy < 1.0
    for name, metric in eval_report.field_metrics.items():
        if metric.correct < metric.total:
            report.failures.append({
                "field": name,
                "correct": metric.correct,
                "total": metric.total,
                "accuracy": round(metric.accuracy, 4),
            })

    # Cycle and cost data from results_data
    if results_data:
        cycles = [r.get("current_cycle", 0) for r in results_data]
        costs = [r.get("cost_usd", 0.0) for r in results_data]
        report.avg_cycles = _safe_mean(cycles)
        report.avg_cost_usd = _safe_mean(costs)

    return report


def save_accuracy_report(report: AccuracyReport, reports_dir: str | Path | None = None) -> Path:
    """Save an accuracy report to `.adep/reports/` [BLK-128].

    Args:
        report: The AccuracyReport to save.
        reports_dir: Optional custom directory. Defaults to `.adep/reports/`.

    Returns:
        Path to the saved report file.
    """
    if reports_dir is None:
        reports_dir = Path.cwd() / ".adep" / "reports"
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    filename = f"accuracy_{timestamp}.json"
    path = reports_dir / filename
    report.save(path)
    return path


def _safe_mean(values: list[float]) -> float:
    """Compute mean safely, returning 0.0 for empty lists."""
    return sum(values) / len(values) if values else 0.0
