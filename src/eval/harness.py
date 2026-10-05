"""Evaluation harness — grounded accuracy + confidence calibration [§10, BLK-015].

Runs extraction on a fixture set with ground truth annotations and produces
a report with:
- Per-field accuracy (value correct)
- Grounded accuracy (value correct + bbox overlaps ground truth)
- Confidence calibration (confidence vs actual accuracy)
- JSON report output

Usage:
    from src.eval.harness import run_evaluation
    report = run_evaluation(fixture_dir="tests/fixtures/invoice/")
    print(report.to_json())
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.templates.base import ExtractedResult
from src.tools.base import BBox, FieldValue, Grounding

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ground truth structures
# ---------------------------------------------------------------------------


@dataclass
class GroundTruthField:
    """A single field's ground truth annotation.

    Attributes:
        name: Field path in the template schema (e.g. "invoice_number").
        value: The correct value.
        bbox: Ground truth bounding box (x1, y1, x2, y2) in pixels, or None.
        page: Page number (0-indexed).
    """

    name: str
    value: Any
    bbox: BBox | None = None
    page: int = 0


@dataclass
class GroundTruthSample:
    """A single test sample with ground truth.

    Attributes:
        document_path: Path to the document file.
        fields: List of ground truth field annotations.
    """

    document_path: str
    fields: list[GroundTruthField] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def bbox_iou(a: BBox, b: BBox) -> float:
    """Compute Intersection-over-Union between two bounding boxes.

    Args:
        a: First bbox (x1, y1, x2, y2).
        b: Second bbox (x1, y1, x2, y2).

    Returns:
        IoU score in [0.0, 1.0]. 0.0 means no overlap.
    """
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])

    inter_w = max(0, x2 - x1)
    inter_h = max(0, y2 - y1)
    inter_area = inter_w * inter_h

    a_area = (a[2] - a[0]) * (a[3] - a[1])
    b_area = (b[2] - b[0]) * (b[3] - b[1])
    union_area = a_area + b_area - inter_area

    if union_area == 0:
        return 0.0
    return inter_area / union_area


def values_match(predicted: Any, truth: Any) -> bool:
    """Check if predicted value matches ground truth.

    Handles type coercion for numeric fields (float comparison with tolerance).
    """
    if predicted is None:
        return False
    if isinstance(predicted, (int, float)) and isinstance(truth, (int, float)):
        return abs(float(predicted) - float(truth)) < 0.01
    return str(predicted).strip().lower() == str(truth).strip().lower()


def bbox_overlaps(pred: BBox | None, truth: BBox | None, threshold: float = 0.5) -> bool:
    """Check if predicted bbox overlaps ground truth with IoU >= threshold."""
    if pred is None or truth is None:
        return False
    return bbox_iou(pred, truth) >= threshold


# ---------------------------------------------------------------------------
# ANLS metric — Average Normalized Levenshtein Similarity [BLK-015]
# ---------------------------------------------------------------------------


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def anls_score(predicted: Any, truth: Any) -> float:
    """Compute ANLS (Average Normalized Levenshtein Similarity) for a field [BLK-015].

    ANLS = 1 - (edit_distance / max(len(predicted), len(truth)))

    Returns:
        Score in [0.0, 1.0]. 1.0 = perfect match, 0.0 = completely different.
    """
    s_pred = str(predicted).strip().lower() if predicted is not None else ""
    s_truth = str(truth).strip().lower() if truth is not None else ""
    if not s_pred and not s_truth:
        return 1.0
    if not s_pred or not s_truth:
        return 0.0
    max_len = max(len(s_pred), len(s_truth))
    if max_len == 0:
        return 1.0
    dist = _levenshtein(s_pred, s_truth)
    return 1.0 - (dist / max_len)


# ---------------------------------------------------------------------------
# SMuDGE-style metric — spatial localization + output type [BLK-015]
# ---------------------------------------------------------------------------


@dataclass
class SmudgeScore:
    """SMuDGE-style evaluation score for a single field [BLK-015].

    Combines:
    - Value correctness (ANLS)
    - Spatial localization (IoU with ground truth bbox)
    - Output type check (numeric vs textual)

    Attributes:
        anls: Normalized Levenshtein Similarity score [0, 1].
        spatial_iou: IoU between predicted and ground truth bbox [0, 1].
        type_correct: Whether output type matches expected (numeric vs textual).
        combined: Weighted score: 0.4 * anls + 0.4 * spatial_iou + 0.2 * type_correct.
    """

    anls: float
    spatial_iou: float
    type_correct: bool

    @property
    def combined(self) -> float:
        """Weighted SMuDGE score."""
        return 0.4 * self.anls + 0.4 * self.spatial_iou + 0.2 * (1.0 if self.type_correct else 0.0)


def smudge_evaluate(
    predicted: Any,
    pred_bbox: BBox | None,
    truth: Any,
    truth_bbox: BBox | None,
) -> SmudgeScore:
    """Evaluate a single field using SMuDGE-style metrics [BLK-015].

    Args:
        predicted: The predicted value.
        pred_bbox: Predicted bounding box, or None.
        truth: Ground truth value.
        truth_bbox: Ground truth bounding box, or None.

    Returns:
        SmudgeScore with ANLS, spatial IoU, and type correctness.
    """
    anls = anls_score(predicted, truth)

    if pred_bbox is not None and truth_bbox is not None:
        spatial_iou = bbox_iou(pred_bbox, truth_bbox)
    else:
        spatial_iou = 0.0

    # Type check: both numeric or both textual
    pred_is_numeric = isinstance(predicted, (int, float))
    truth_is_numeric = isinstance(truth, (int, float))
    type_correct = pred_is_numeric == truth_is_numeric

    return SmudgeScore(anls=anls, spatial_iou=spatial_iou, type_correct=type_correct)


# ---------------------------------------------------------------------------
# Report structures
# ---------------------------------------------------------------------------


@dataclass
class FieldMetric:
    """Per-field evaluation metrics.

    Attributes:
        name: Field path.
        correct: Number of correct predictions.
        total: Total samples for this field.
        grounded_correct: Number of predictions with correct value + overlapping bbox.
        confidence_values: List of confidence scores for all predictions.
        correctness: List of booleans (1.0 for correct, 0.0 for incorrect) aligned with confidence_values.
    """

    name: str
    correct: int = 0
    total: int = 0
    grounded_correct: int = 0
    confidence_values: list[float] = field(default_factory=list)
    correctness: list[float] = field(default_factory=list)
    anls_scores: list[float] = field(default_factory=list)
    smudge_scores: list[float] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        """Value accuracy: fraction of predictions with correct value."""
        return self.correct / self.total if self.total > 0 else 0.0

    @property
    def grounded_accuracy(self) -> float:
        """Grounded accuracy: fraction with correct value + overlapping bbox."""
        return self.grounded_correct / self.total if self.total > 0 else 0.0

    @property
    def mean_confidence(self) -> float:
        """Average confidence across all predictions."""
        return (
            sum(self.confidence_values) / len(self.confidence_values)
            if self.confidence_values
            else 0.0
        )

    @property
    def calibration_error(self) -> float:
        """Mean calibration error: |confidence - correctness| averaged.

        0.0 means perfectly calibrated. 1.0 means maximally miscalibrated.
        """
        if not self.confidence_values:
            return 0.0
        errors = [abs(c - r) for c, r in zip(self.confidence_values, self.correctness)]
        return sum(errors) / len(errors)

    @property
    def mean_anls(self) -> float:
        """Mean ANLS score across all predictions [BLK-015]."""
        return sum(self.anls_scores) / len(self.anls_scores) if self.anls_scores else 0.0

    @property
    def mean_smudge(self) -> float:
        """Mean SMuDGE combined score across all predictions [BLK-015]."""
        return sum(self.smudge_scores) / len(self.smudge_scores) if self.smudge_scores else 0.0


@dataclass
class EvaluationReport:
    """Full evaluation report across all samples and fields.

    Attributes:
        sample_count: Number of samples evaluated.
        field_metrics: Per-field metrics keyed by field name.
        overall_accuracy: Mean accuracy across all fields.
        overall_grounded_accuracy: Mean grounded accuracy across all fields.
        overall_calibration_error: Mean calibration error across all fields.
    """

    sample_count: int = 0
    field_metrics: dict[str, FieldMetric] = field(default_factory=dict)

    @property
    def overall_accuracy(self) -> float:
        if not self.field_metrics:
            return 0.0
        total_correct = sum(m.correct for m in self.field_metrics.values())
        total = sum(m.total for m in self.field_metrics.values())
        return total_correct / total if total > 0 else 0.0

    @property
    def overall_grounded_accuracy(self) -> float:
        if not self.field_metrics:
            return 0.0
        total_grounded = sum(m.grounded_correct for m in self.field_metrics.values())
        total = sum(m.total for m in self.field_metrics.values())
        return total_grounded / total if total > 0 else 0.0

    @property
    def overall_calibration_error(self) -> float:
        if not self.field_metrics:
            return 0.0
        all_conf = []
        all_correct = []
        for m in self.field_metrics.values():
            all_conf.extend(m.confidence_values)
            all_correct.extend(m.correctness)
        if not all_conf:
            return 0.0
        errors = [abs(c - r) for c, r in zip(all_conf, all_correct)]
        return sum(errors) / len(errors)

    @property
    def overall_anls(self) -> float:
        """Mean ANLS across all fields [BLK-015]."""
        if not self.field_metrics:
            return 0.0
        all_anls: list[float] = []
        for m in self.field_metrics.values():
            all_anls.extend(m.anls_scores)
        return sum(all_anls) / len(all_anls) if all_anls else 0.0

    @property
    def overall_smudge(self) -> float:
        """Mean SMuDGE combined score across all fields [BLK-015]."""
        if not self.field_metrics:
            return 0.0
        all_smudge: list[float] = []
        for m in self.field_metrics.values():
            all_smudge.extend(m.smudge_scores)
        return sum(all_smudge) / len(all_smudge) if all_smudge else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a dict for JSON output."""
        return {
            "sample_count": self.sample_count,
            "overall_accuracy": round(self.overall_accuracy, 4),
            "overall_grounded_accuracy": round(self.overall_grounded_accuracy, 4),
            "overall_calibration_error": round(self.overall_calibration_error, 4),
            "overall_anls": round(self.overall_anls, 4),
            "overall_smudge": round(self.overall_smudge, 4),
            "fields": {
                name: {
                    "accuracy": round(m.accuracy, 4),
                    "grounded_accuracy": round(m.grounded_accuracy, 4),
                    "mean_confidence": round(m.mean_confidence, 4),
                    "calibration_error": round(m.calibration_error, 4),
                    "mean_anls": round(m.mean_anls, 4),
                    "mean_smudge": round(m.mean_smudge, 4),
                    "correct": m.correct,
                    "total": m.total,
                    "grounded_correct": m.grounded_correct,
                }
                for name, m in self.field_metrics.items()
            },
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize report to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: str | Path) -> None:
        """Save report to a JSON file."""
        Path(path).write_text(self.to_json(), encoding="utf-8")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def evaluate_extraction(
    result: ExtractedResult,
    truth: GroundTruthSample,
) -> dict[str, tuple[bool, bool, float, float, float]]:
    """Evaluate a single extraction result against ground truth.

    Args:
        result: The ExtractedResult from a run.
        truth: Ground truth annotations for this sample.

    Returns:
        Dict mapping field name to (value_correct, grounded_correct, confidence, anls, smudge).
    """
    evaluations: dict[str, tuple[bool, bool, float, float, float]] = {}

    for gt_field in truth.fields:
        fv = result.field_values.get(gt_field.name)
        if fv is None:
            evaluations[gt_field.name] = (False, False, 0.0, 0.0, 0.0)
            continue

        value_correct = values_match(fv.value, gt_field.value)
        pred_bbox = fv.grounding.bbox if fv.grounding else None
        grounded_correct = value_correct and bbox_overlaps(pred_bbox, gt_field.bbox)
        confidence = fv.confidence

        anls = anls_score(fv.value, gt_field.value)
        smudge = smudge_evaluate(fv.value, pred_bbox, gt_field.value, gt_field.bbox).combined

        evaluations[gt_field.name] = (value_correct, grounded_correct, confidence, anls, smudge)

    return evaluations


def run_evaluation(
    results: list[ExtractedResult],
    truths: list[GroundTruthSample],
) -> EvaluationReport:
    """Run evaluation across multiple samples.

    Args:
        results: List of ExtractedResult from running extraction on each sample.
        truths: List of GroundTruthSample aligned with results (same index).

    Returns:
        An EvaluationReport with per-field and overall metrics.
    """
    report = EvaluationReport(sample_count=len(results))

    for result, truth in zip(results, truths):
        evals = evaluate_extraction(result, truth)

        for field_name, (
            value_correct,
            grounded_correct,
            confidence,
            anls,
            smudge,
        ) in evals.items():
            if field_name not in report.field_metrics:
                report.field_metrics[field_name] = FieldMetric(name=field_name)

            metric = report.field_metrics[field_name]
            metric.total += 1
            if value_correct:
                metric.correct += 1
            if grounded_correct:
                metric.grounded_correct += 1
            metric.confidence_values.append(confidence)
            metric.correctness.append(1.0 if value_correct else 0.0)
            metric.anls_scores.append(anls)
            metric.smudge_scores.append(smudge)

    return report


def load_fixtures(fixture_dir: str | Path) -> list[GroundTruthSample]:
    """Load ground truth fixtures from a directory.

    Expects one ``ground_truth.json`` file per sample, or a single
    ``ground_truth.json`` with a list of samples.

    Each sample JSON format:
        {
            "document_path": "invoice_001.png",
            "fields": [
                {"name": "invoice_number", "value": "INV-001", "bbox": [10, 10, 200, 50]},
                {"name": "total", "value": 1500.00, "bbox": [10, 200, 200, 240]}
            ]
        }

    Args:
        fixture_dir: Path to the directory containing fixture files.

    Returns:
        List of GroundTruthSample objects.
    """
    fixture_path = Path(fixture_dir)
    samples: list[GroundTruthSample] = []

    if not fixture_path.exists():
        logger.warning("Fixture directory does not exist: %s", fixture_path)
        return samples

    # Look for ground_truth.json files
    gt_files = list(fixture_path.glob("**/ground_truth.json"))

    for gt_file in gt_files:
        data = json.loads(gt_file.read_text(encoding="utf-8"))

        # Handle both single sample and list of samples
        if isinstance(data, list):
            for item in data:
                samples.append(_parse_sample(item, gt_file.parent))
        else:
            samples.append(_parse_sample(data, gt_file.parent))

    return samples


def _parse_sample(data: dict[str, Any], base_dir: Path) -> GroundTruthSample:
    """Parse a single sample from JSON dict."""
    doc_path = data.get("document_path", "")
    if not Path(doc_path).is_absolute():
        doc_path = str(base_dir / doc_path)

    fields = []
    for f in data.get("fields", []):
        bbox = tuple(f["bbox"]) if f.get("bbox") else None
        fields.append(
            GroundTruthField(
                name=f["name"],
                value=f["value"],
                bbox=bbox,
                page=f.get("page", 0),
            )
        )

    return GroundTruthSample(document_path=doc_path, fields=fields)
