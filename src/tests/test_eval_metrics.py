"""Tests for ANLS and SMuDGE metrics in eval harness [BLK-015, TS].

Tests cover:
- ANLS: perfect match, near-match, no match, empty strings, None values
- SMuDGE: combined score with value + spatial + type components
- Levenshtein distance computation
- FieldMetric: mean_anls, mean_smudge properties
- EvaluationReport: overall_anls, overall_smudge properties
- to_dict includes ANLS and SMuDGE
- evaluate_extraction returns 5-tuple with ANLS and SMuDGE
- run_evaluation populates ANLS and SMuDGE scores
"""

from __future__ import annotations

from src.eval.harness import (
    EvaluationReport,
    FieldMetric,
    GroundTruthField,
    GroundTruthSample,
    SmudgeScore,
    _levenshtein,
    anls_score,
    bbox_iou,
    evaluate_extraction,
    run_evaluation,
    smudge_evaluate,
    values_match,
)
from src.templates.base import ExtractedResult
from src.tools.base import FieldValue, Grounding


def _fv(value: any, bbox: tuple[int, int, int, int] | None = None, confidence: float = 0.9) -> FieldValue:
    """Build a FieldValue with optional grounding."""
    grounding = Grounding(bbox=bbox, source_tool="ocr", confidence=confidence) if bbox else None
    return FieldValue(name="test", value=value, grounding=grounding, confidence=confidence)


def _result(fields: dict[str, FieldValue]) -> ExtractedResult:
    """Build an ExtractedResult with the given field values."""
    return ExtractedResult(is_complete=True, values={}, field_values=fields)


class TestLevenshtein:
    """Verify Levenshtein distance computation."""

    def test_identical_strings(self):
        assert _levenshtein("hello", "hello") == 0

    def test_one_insertion(self):
        assert _levenshtein("hell", "hello") == 1

    def test_one_deletion(self):
        assert _levenshtein("hello", "hell") == 1

    def test_one_substitution(self):
        assert _levenshtein("hello", "hallo") == 1

    def test_completely_different(self):
        assert _levenshtein("abc", "xyz") == 3

    def test_empty_string(self):
        assert _levenshtein("", "abc") == 3
        assert _levenshtein("abc", "") == 3

    def test_both_empty(self):
        assert _levenshtein("", "") == 0


class TestANLS:
    """Verify ANLS (Normalized Levenshtein Similarity) metric."""

    def test_perfect_match(self):
        assert anls_score("INV-001", "INV-001") == 1.0

    def test_near_match(self):
        score = anls_score("INV-001", "INV-002")
        assert 0.0 < score < 1.0
        assert score > 0.8  # 1 edit out of 7 chars

    def test_no_match(self):
        score = anls_score("abc", "xyz")
        assert score == 0.0

    def test_case_insensitive(self):
        assert anls_score("INV-001", "inv-001") == 1.0

    def test_whitespace_trimmed(self):
        assert anls_score("  INV-001  ", "INV-001") == 1.0

    def test_both_empty(self):
        assert anls_score("", "") == 1.0

    def test_one_empty(self):
        assert anls_score("abc", "") == 0.0
        assert anls_score("", "abc") == 0.0

    def test_none_predicted(self):
        assert anls_score(None, "abc") == 0.0

    def test_none_truth(self):
        assert anls_score("abc", None) == 0.0

    def test_both_none(self):
        assert anls_score(None, None) == 1.0

    def test_numeric_values(self):
        score = anls_score(1500.0, 1500.0)
        assert score == 1.0

    def test_near_numeric(self):
        score = anls_score(1500.0, 1501.0)
        assert 0.0 < score < 1.0


class TestSmudge:
    """Verify SMuDGE-style metric."""

    def test_perfect_value_and_bbox(self):
        bbox = (10, 10, 100, 50)
        score = smudge_evaluate("INV-001", bbox, "INV-001", bbox)
        assert score.anls == 1.0
        assert score.spatial_iou == 1.0
        assert score.type_correct is True
        assert score.combined == 1.0

    def test_correct_value_wrong_bbox(self):
        score = smudge_evaluate("INV-001", (10, 10, 100, 50), "INV-001", (200, 200, 300, 250))
        assert score.anls == 1.0
        assert score.spatial_iou == 0.0
        assert score.combined < 1.0

    def test_wrong_value_correct_bbox(self):
        bbox = (10, 10, 100, 50)
        score = smudge_evaluate("INV-002", bbox, "INV-001", bbox)
        assert score.anls < 1.0
        assert score.spatial_iou == 1.0
        assert score.combined < 1.0

    def test_missing_bbox(self):
        score = smudge_evaluate("INV-001", None, "INV-001", (10, 10, 100, 50))
        assert score.spatial_iou == 0.0
        assert score.combined < 1.0

    def test_both_bbox_missing(self):
        score = smudge_evaluate("INV-001", None, "INV-001", None)
        assert score.spatial_iou == 0.0
        assert score.anls == 1.0
        assert score.type_correct is True

    def test_type_mismatch_numeric_vs_text(self):
        score = smudge_evaluate("1500", (10, 10, 100, 50), 1500.0, (10, 10, 100, 50))
        assert score.type_correct is False

    def test_type_match_both_numeric(self):
        score = smudge_evaluate(1500.0, (10, 10, 100, 50), 1500.0, (10, 10, 100, 50))
        assert score.type_correct is True

    def test_type_match_both_text(self):
        score = smudge_evaluate("INV-001", (10, 10, 100, 50), "INV-001", (10, 10, 100, 50))
        assert score.type_correct is True

    def test_combined_weighting(self):
        """combined = 0.4 * anls + 0.4 * spatial_iou + 0.2 * type_correct."""
        score = SmudgeScore(anls=0.5, spatial_iou=0.5, type_correct=True)
        expected = 0.4 * 0.5 + 0.4 * 0.5 + 0.2 * 1.0
        assert abs(score.combined - expected) < 0.001

    def test_combined_no_type(self):
        score = SmudgeScore(anls=1.0, spatial_iou=1.0, type_correct=False)
        expected = 0.4 * 1.0 + 0.4 * 1.0 + 0.2 * 0.0
        assert abs(score.combined - expected) < 0.001


class TestFieldMetricANLSSmudge:
    """Verify FieldMetric tracks ANLS and SMuDGE scores."""

    def test_mean_anls_empty(self):
        metric = FieldMetric(name="total")
        assert metric.mean_anls == 0.0

    def test_mean_anls_with_scores(self):
        metric = FieldMetric(name="total")
        metric.anls_scores = [1.0, 0.8, 0.6]
        assert abs(metric.mean_anls - 0.8) < 0.001

    def test_mean_smudge_empty(self):
        metric = FieldMetric(name="total")
        assert metric.mean_smudge == 0.0

    def test_mean_smudge_with_scores(self):
        metric = FieldMetric(name="total")
        metric.smudge_scores = [0.9, 0.7, 0.5]
        assert abs(metric.mean_smudge - 0.7) < 0.001


class TestEvaluationReportANLSSmudge:
    """Verify EvaluationReport overall ANLS and SMuDGE."""

    def test_overall_anls_empty(self):
        report = EvaluationReport()
        assert report.overall_anls == 0.0

    def test_overall_anls_with_data(self):
        report = EvaluationReport()
        m1 = FieldMetric(name="total")
        m1.anls_scores = [1.0, 0.8]
        m2 = FieldMetric(name="vendor")
        m2.anls_scores = [0.6, 0.4]
        report.field_metrics = {"total": m1, "vendor": m2}
        expected = (1.0 + 0.8 + 0.6 + 0.4) / 4
        assert abs(report.overall_anls - expected) < 0.001

    def test_overall_smudge_empty(self):
        report = EvaluationReport()
        assert report.overall_smudge == 0.0

    def test_overall_smudge_with_data(self):
        report = EvaluationReport()
        m1 = FieldMetric(name="total")
        m1.smudge_scores = [0.9, 0.7]
        m2 = FieldMetric(name="vendor")
        m2.smudge_scores = [0.5, 0.3]
        report.field_metrics = {"total": m1, "vendor": m2}
        expected = (0.9 + 0.7 + 0.5 + 0.3) / 4
        assert abs(report.overall_smudge - expected) < 0.001

    def test_to_dict_includes_anls_smudge(self):
        report = EvaluationReport()
        m = FieldMetric(name="total")
        m.anls_scores = [1.0]
        m.smudge_scores = [0.8]
        m.total = 1
        m.correct = 1
        report.field_metrics = {"total": m}
        d = report.to_dict()
        assert "overall_anls" in d
        assert "overall_smudge" in d
        assert "mean_anls" in d["fields"]["total"]
        assert "mean_smudge" in d["fields"]["total"]


class TestEvaluateExtractionWithANLSSmudge:
    """Verify evaluate_extraction returns ANLS and SMuDGE."""

    def test_returns_5_tuple(self):
        result = _result({"total": _fv(1500.0, bbox=(10, 10, 100, 50))})
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[GroundTruthField(name="total", value=1500.0, bbox=(10, 10, 100, 50))],
        )
        evals = evaluate_extraction(result, truth)
        assert len(evals["total"]) == 5
        value_correct, grounded_correct, confidence, anls, smudge = evals["total"]
        assert value_correct is True
        assert grounded_correct is True
        assert anls == 1.0
        assert smudge == 1.0

    def test_missing_field_returns_zeros(self):
        result = _result({})
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[GroundTruthField(name="total", value=1500.0, bbox=(10, 10, 100, 50))],
        )
        evals = evaluate_extraction(result, truth)
        value_correct, grounded_correct, confidence, anls, smudge = evals["total"]
        assert value_correct is False
        assert anls == 0.0
        assert smudge == 0.0

    def test_near_match_anls_partial(self):
        result = _result({"invoice_number": _fv("INV-002", bbox=(10, 10, 100, 50))})
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[GroundTruthField(name="invoice_number", value="INV-001", bbox=(10, 10, 100, 50))],
        )
        evals = evaluate_extraction(result, truth)
        _, _, _, anls, _ = evals["invoice_number"]
        assert 0.0 < anls < 1.0


class TestRunEvaluationWithANLSSmudge:
    """Verify run_evaluation populates ANLS and SMuDGE in report."""

    def test_report_has_anls_scores(self):
        result = _result({"total": _fv(1500.0, bbox=(10, 10, 100, 50))})
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[GroundTruthField(name="total", value=1500.0, bbox=(10, 10, 100, 50))],
        )
        report = run_evaluation([result], [truth])
        assert len(report.field_metrics["total"].anls_scores) == 1
        assert report.field_metrics["total"].anls_scores[0] == 1.0

    def test_report_has_smudge_scores(self):
        result = _result({"total": _fv(1500.0, bbox=(10, 10, 100, 50))})
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[GroundTruthField(name="total", value=1500.0, bbox=(10, 10, 100, 50))],
        )
        report = run_evaluation([result], [truth])
        assert len(report.field_metrics["total"].smudge_scores) == 1
        assert report.field_metrics["total"].smudge_scores[0] == 1.0

    def test_report_overall_anls(self):
        result = _result({"total": _fv(1500.0, bbox=(10, 10, 100, 50))})
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[GroundTruthField(name="total", value=1500.0, bbox=(10, 10, 100, 50))],
        )
        report = run_evaluation([result], [truth])
        assert report.overall_anls == 1.0

    def test_report_overall_smudge(self):
        result = _result({"total": _fv(1500.0, bbox=(10, 10, 100, 50))})
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[GroundTruthField(name="total", value=1500.0, bbox=(10, 10, 100, 50))],
        )
        report = run_evaluation([result], [truth])
        assert report.overall_smudge == 1.0

    def test_report_json_output_has_metrics(self):
        result = _result({"total": _fv(1500.0, bbox=(10, 10, 100, 50))})
        truth = GroundTruthSample(
            document_path="test.png",
            fields=[GroundTruthField(name="total", value=1500.0, bbox=(10, 10, 100, 50))],
        )
        report = run_evaluation([result], [truth])
        import json
        d = json.loads(report.to_json())
        assert "overall_anls" in d
        assert "overall_smudge" in d
        assert "mean_anls" in d["fields"]["total"]
        assert "mean_smudge" in d["fields"]["total"]
