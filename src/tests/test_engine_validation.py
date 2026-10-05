"""Tests for the new-engine schema and invariant validation (ADE-36).

Replaces ade2's keyword-matching invariant checker with a fixed, structured operator
vocabulary — real field lookups, never a silent pass when a named field is missing.
Hermetic: plain dict fixtures, no network, no LLM.
"""

from __future__ import annotations

import json

from src.engine.validation import validate_invariants, validate_output

# --- AC1: JSON-Schema validation (ported, no behavior change) -------------------------------------

SCHEMA = {
    "type": "object",
    "properties": {
        "header": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
        "items": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["header", "items"],
}


def test_validate_output_schema_conformance():
    good = json.dumps({"header": {"title": "ok"}, "items": [{"a": 1}]})
    result = validate_output(good, SCHEMA)
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_output_reports_missing_nested_required_field():
    bad = json.dumps({"header": {}, "items": []})
    result = validate_output(bad, SCHEMA)
    assert result["valid"] is False
    assert any("header.title" in e for e in result["errors"])


# --- AC2: non_empty -------------------------------------------------------------------------------


def test_non_empty_invariant():
    inv = [{"name": "has_nodes", "check": "non_empty", "fields": ["nodes"]}]

    result = validate_invariants({"nodes": [{"id": 1}]}, inv)
    assert result["checked"] == ["has_nodes"]
    assert result["violated"] == []

    result = validate_invariants({"nodes": []}, inv)
    assert result["checked"] == []
    assert len(result["violated"]) == 1
    assert "nodes" in result["violated"][0]["message"]


# --- AC3: balance_equals --------------------------------------------------------------------------


def test_balance_equals_invariant():
    inv = [
        {
            "name": "balance",
            "check": "balance_equals",
            "fields": ["opening", "deposits", "withdrawals", "closing"],
        }
    ]

    data = {"opening": 100, "deposits": 50, "withdrawals": 30, "closing": 120}
    result = validate_invariants(data, inv)
    assert result["checked"] == ["balance"]

    bad = {**data, "closing": 121}
    result = validate_invariants(bad, inv)
    assert len(result["violated"]) == 1
    msg = result["violated"][0]["message"]
    assert "100" in msg and "121" in msg


# --- AC4: sum_equals ------------------------------------------------------------------------------


def test_sum_equals_invariant():
    inv = [{"name": "totals", "check": "sum_equals", "fields": ["subtotal", "tax", "total"]}]

    result = validate_invariants({"subtotal": 80, "tax": 8, "total": 88}, inv)
    assert result["checked"] == ["totals"]

    result = validate_invariants({"subtotal": 80, "tax": 8, "total": 90}, inv)
    assert len(result["violated"]) == 1


# --- AC5: all_rows_have ---------------------------------------------------------------------------


def test_all_rows_have_invariant():
    inv = [
        {"name": "nodes_tagged", "check": "all_rows_have", "fields": ["nodes"], "require": ["tag"]}
    ]

    good = {"nodes": [{"tag": "T1"}, {"tag": "T2"}]}
    assert validate_invariants(good, inv)["checked"] == ["nodes_tagged"]

    bad = {"nodes": [{"tag": "T1"}, {"tag": ""}]}
    result = validate_invariants(bad, inv)
    assert len(result["violated"]) == 1
    assert "1" in result["violated"][0]["message"]  # names the offending row index


def test_all_rows_have_checks_multiple_required_fields():
    inv = [
        {
            "name": "edges_have_endpoints",
            "check": "all_rows_have",
            "fields": ["edges"],
            "require": ["from_id", "to_id"],
        }
    ]
    bad = {"edges": [{"from_id": "A", "to_id": "B"}, {"from_id": "C"}]}
    result = validate_invariants(bad, inv)
    assert len(result["violated"]) == 1


# --- AC6: tolerance_range -------------------------------------------------------------------------


def test_tolerance_range_invariant():
    inv = [
        {
            "name": "tolerances",
            "check": "tolerance_range",
            "fields": ["characteristics"],
            "min_field": "tolerance_min",
            "max_field": "tolerance_max",
            "value_field": "measured_value",
        }
    ]

    good = {
        "characteristics": [
            {"tolerance_min": 1.0, "tolerance_max": 2.0, "measured_value": 1.5, "result": "PASS"}
        ]
    }
    assert validate_invariants(good, inv)["checked"] == ["tolerances"]

    bad_pass = {
        "characteristics": [
            {"tolerance_min": 1.0, "tolerance_max": 2.0, "measured_value": 5.0, "result": "PASS"}
        ]
    }
    result = validate_invariants(bad_pass, inv)
    assert len(result["violated"]) == 1

    # a FAIL row outside range is expected and not a violation; a PASS row alongside it
    # still gets checked, proving the FAIL row was skipped rather than silently "passing" too
    mixed = {
        "characteristics": [
            {"tolerance_min": 1.0, "tolerance_max": 2.0, "measured_value": 1.5, "result": "PASS"},
            {"tolerance_min": 1.0, "tolerance_max": 2.0, "measured_value": 5.0, "result": "FAIL"},
        ]
    }
    result = validate_invariants(mixed, inv)
    assert result["violated"] == []
    assert result["checked"] == ["tolerances"]


# --- AC7: the ADE-12 false-positive gap, closed ---------------------------------------------------


def test_missing_field_is_could_not_check_not_a_silent_pass():
    inv = [{"name": "ghost", "check": "non_empty", "fields": ["nonexistent_field"]}]

    result = validate_invariants({"nodes": [1]}, inv)
    assert result["could_not_check"] == ["ghost"]
    assert result["checked"] == []
    assert result["violated"] == []


def test_wrong_type_for_operator_is_could_not_check():
    inv = [{"name": "bad_type", "check": "non_empty", "fields": ["name"]}]
    result = validate_invariants({"name": "a string, not a list"}, inv)
    assert result["could_not_check"] == ["bad_type"]


# --- AC8: unknown operator ------------------------------------------------------------------------


def test_unknown_operator_is_could_not_check_not_a_crash():
    inv = [{"name": "mystery", "check": "no_such_operator", "fields": ["x"]}]
    result = validate_invariants({"x": 1}, inv)
    assert result["could_not_check"] == ["mystery"]
