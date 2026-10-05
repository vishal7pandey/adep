"""P&ID scoring (ADE-15): count recall, over-extraction, label precision. No model or network."""

from __future__ import annotations

import json

import pytest

from src.eval.pid_ground_truth import GroundTruth
from src.eval.pid_scoring import CATEGORIES, normalize_tag, score_extraction, tag_parts


def gt(counts: dict[str, int] | None = None, labels: set[str] | None = None) -> GroundTruth:
    base = dict.fromkeys(CATEGORIES, 0)
    base.update(counts or {})
    return GroundTruth(name="t", counts=base, labels={normalize_tag(x) for x in (labels or set())})


def items(*tags: str) -> list[dict]:
    return [{"id": f"i{n}", "tag": t} for n, t in enumerate(tags)]


class TestNormalizeTag:
    def test_case_space_and_separators_are_ignored(self):
        assert normalize_tag("SV 104.01") == normalize_tag("sv104.01") == "SV104.01"
        assert normalize_tag("PI-4712/01") == "PI471201"

    def test_unicode_superscripts_are_folded(self):
        assert normalize_tag("P²-101") == normalize_tag("P2-101")

    def test_empty_and_none(self):
        assert normalize_tag("") == ""
        assert normalize_tag(None) == ""

    def test_different_tags_stay_different(self):
        assert normalize_tag("PI-101") != normalize_tag("PI-102")
        assert normalize_tag("V-1") != normalize_tag("V-10")

    def test_parts_split_letter_and_number_runs(self):
        assert tag_parts("PI 4712.01") == ["PI", "4712.01"]
        assert tag_parts("") == []


class TestCountRecall:
    def test_equal_is_one(self):
        s = score_extraction({"valves": items("V1", "V2")}, gt({"valves": 2}))
        assert s.categories["valves"].recall == 1.0
        assert s.categories["valves"].over_extraction == 0.0

    def test_fewer_found_gives_the_ratio(self):
        s = score_extraction({"valves": items("V1")}, gt({"valves": 4}))
        assert s.categories["valves"].recall == 0.25

    def test_more_found_caps_recall_and_reports_over_extraction(self):
        s = score_extraction({"valves": items("V1", "V2", "V3", "V4")}, gt({"valves": 2}))
        assert s.categories["valves"].recall == 1.0
        assert s.categories["valves"].over_extraction == 1.0

    def test_zero_truth_is_not_applicable_never_one(self):
        s = score_extraction({"instruments": items("PI1")}, gt({"instruments": 0}))
        assert s.categories["instruments"].recall is None
        assert s.categories["instruments"].over_extraction is None

    def test_mean_recall_ignores_not_applicable_categories(self):
        s = score_extraction(
            {"valves": items("V1"), "edges": [{}, {}]},
            gt({"valves": 2, "edges": 2}),
        )
        assert s.mean_count_recall == pytest.approx(0.75)

    def test_missing_and_malformed_categories_count_as_zero_found(self):
        s = score_extraction(
            {"valves": "oops", "nodes": [1, None, "x"]}, gt({"valves": 2, "nodes": 3})
        )
        assert s.categories["valves"].found == 0
        assert s.categories["nodes"].found == 0
        assert s.categories["valves"].recall == 0.0


class TestLabelPrecision:
    def test_all_tags_on_drawing(self):
        s = score_extraction(
            {"nodes": items("P-101"), "valves": items("XV 1")},
            gt(labels={"P-101", "XV1"}),
        )
        assert s.label_precision == 1.0

    def test_invented_tags_lower_precision(self):
        s = score_extraction({"nodes": items("P-101", "GHOST-9")}, gt(labels={"P-101"}))
        assert s.label_precision == 0.5
        assert (s.tags_reported, s.tags_on_drawing) == (2, 1)

    def test_tag_with_parts_printed_separately_counts_as_present(self):
        s = score_extraction({"instruments": items("PI4712.01")}, gt(labels={"PI", "4712.01"}))
        assert s.label_precision == 1.0

    def test_partial_parts_do_not_count(self):
        s = score_extraction({"instruments": items("PI4712.01")}, gt(labels={"PI"}))
        assert s.label_precision == 0.0

    def test_duplicate_tags_count_once_but_still_count_for_recall(self):
        s = score_extraction({"valves": items("V1", "V1", "V1")}, gt({"valves": 3}, {"V1"}))
        assert s.tags_reported == 1
        assert s.categories["valves"].found == 3

    def test_no_tags_is_not_applicable(self):
        s = score_extraction({"valves": [{"id": "x"}]}, gt({"valves": 1}, {"V1"}))
        assert s.label_precision is None


def test_score_serialises_to_json():
    s = score_extraction({"valves": items("V1")}, gt({"valves": 2}, {"V1"}))
    d = s.to_dict()
    json.dumps(d)
    assert d["categories"]["valves"]["recall"] == 0.5
    assert d["label_precision"] == 1.0
