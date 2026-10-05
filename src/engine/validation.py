"""Schema and invariant validation for the new engine (ADE-36).

Two halves, deliberately built differently:

- JSON-Schema validation (validate_output) is a direct, close-to-verbatim port of ade2's
  src/ade2/schema.py — recursive type/required-field checking with no keyword-matching
  problem.

- Invariant validation (validate_invariants) is NOT a port: ade2's own invariant checker
  matches a free-text description against hardcoded keyword patterns to guess which
  sub-checker to run, then regexes the same free text for field names. When the keyword
  matches but the regex misses, the invariant is reported as checked-and-passed even
  though nothing was verified — a silent false positive (ADE-12 flags this explicitly).

  Here, invariants are structured dicts naming real fields and a fixed operator from a
  small vocabulary (non_empty, balance_equals, sum_equals, all_rows_have, tolerance_range).
  Every result is one of three disjoint states — checked (passed), violated, or
  could_not_check (a named field is missing or the wrong type) — and "could not check" is
  never silently folded into "passed".
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_FLOAT_TOLERANCE = 0.01

# --- JSON-Schema validation (ported from ade2's schema.py; no behavior change) --------------------


def validate_output(answer: str, schema: dict) -> dict[str, Any]:
    """Validate agent output (a JSON string) against a full JSON schema, recursively.

    Returns {"valid": bool, "errors": [...], "parsed": the parsed JSON or None}.
    """
    cleaned = _strip_code_fence(answer)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("Output validation failed: invalid JSON (%s)", exc)
        return {"valid": False, "errors": [f"Invalid JSON: {exc}"], "parsed": None}

    errors: list[str] = []
    _validate_node(parsed, schema, "", errors)

    if errors:
        logger.warning("Output validation failed: %d error(s)", len(errors))
    else:
        logger.debug("Output validation passed")

    return {"valid": len(errors) == 0, "errors": errors, "parsed": parsed}


def _validate_node(value: Any, schema: dict, path: str, errors: list[str]) -> None:
    expected_type = schema.get("type")
    if expected_type and not _check_type(value, expected_type):
        errors.append(
            f"Field '{path or 'root'}' should be {expected_type}, got {type(value).__name__}"
        )
        return

    if expected_type == "object":
        props = schema.get("properties", {})
        required = schema.get("required", [])

        for field_name in required:
            if field_name not in value:
                full = f"{path}.{field_name}" if path else field_name
                errors.append(f"Missing required field: {full}")

        for field_name, field_value in value.items():
            if field_name in props:
                child_path = f"{path}.{field_name}" if path else field_name
                _validate_node(field_value, props[field_name], child_path, errors)

    elif expected_type == "array" and "items" in schema:
        items_schema = schema["items"]
        for i, item in enumerate(value):
            _validate_node(item, items_schema, f"{path}[{i}]", errors)


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    return cleaned


def _check_type(value: Any, expected: str) -> bool:
    type_map: dict[str, Any] = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    py_type = type_map.get(expected)
    if py_type is None:
        return True
    if expected in ("number", "integer") and isinstance(value, bool):
        return False
    return isinstance(value, py_type)


# --- Invariant validation: structured operators, not keyword matching -----------------------------

CHECKED = "checked"
VIOLATED = "violated"
COULD_NOT_CHECK = "could_not_check"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_non_empty(data: dict, inv: dict) -> tuple[str, str | None]:
    field = inv["fields"][0]
    value = data.get(field)
    if not isinstance(value, list):
        return COULD_NOT_CHECK, f"field '{field}' is not a list"
    if len(value) == 0:
        return VIOLATED, f"'{field}' is empty but must be non-empty"
    return CHECKED, None


def _check_balance_equals(data: dict, inv: dict) -> tuple[str, str | None]:
    start_f, inc_f, dec_f, end_f = inv["fields"]
    values = [data.get(f) for f in (start_f, inc_f, dec_f, end_f)]
    if not all(_is_number(v) for v in values):
        return COULD_NOT_CHECK, "one or more fields are missing or non-numeric"
    start, inc, dec, end = values
    computed = start + inc - dec
    if abs(computed - end) > _FLOAT_TOLERANCE:
        return (
            VIOLATED,
            f"{start_f}({start}) + {inc_f}({inc}) - {dec_f}({dec}) = {computed} != {end_f}({end})",
        )
    return CHECKED, None


def _check_sum_equals(data: dict, inv: dict) -> tuple[str, str | None]:
    fields = inv["fields"]
    values = [data.get(f) for f in fields]
    if not all(_is_number(v) for v in values):
        return COULD_NOT_CHECK, "one or more fields are missing or non-numeric"
    *addends, total_value = values
    computed = sum(addends)
    if abs(computed - total_value) > _FLOAT_TOLERANCE:
        parts = " + ".join(f"{f}({v})" for f, v in zip(fields[:-1], addends))
        return VIOLATED, f"{parts} = {computed} != {fields[-1]}({total_value})"
    return CHECKED, None


def _check_all_rows_have(data: dict, inv: dict) -> tuple[str, str | None]:
    field = inv["fields"][0]
    require = inv.get("require", [])
    rows = data.get(field)
    if not isinstance(rows, list) or not rows:
        return COULD_NOT_CHECK, f"field '{field}' is missing, not a list, or empty"
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            return COULD_NOT_CHECK, f"row {i} of '{field}' is not an object"
        for key in require:
            if not row.get(key):
                return VIOLATED, f"row {i} of '{field}' is missing '{key}'"
    return CHECKED, None


def _check_tolerance_range(data: dict, inv: dict) -> tuple[str, str | None]:
    field = inv["fields"][0]
    min_f = inv.get("min_field", "tolerance_min")
    max_f = inv.get("max_field", "tolerance_max")
    value_f = inv.get("value_field", "measured_value")
    result_f = inv.get("result_field", "result")

    rows = data.get(field)
    if not isinstance(rows, list) or not rows:
        return COULD_NOT_CHECK, f"field '{field}' is missing, not a list, or empty"

    checked_any = False
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if str(row.get(result_f, "")).upper() != "PASS":
            continue
        mn, mx, measured = row.get(min_f), row.get(max_f), row.get(value_f)
        if not all(_is_number(v) for v in (mn, mx, measured)):
            continue
        checked_any = True
        if not (mn <= measured <= mx):
            return VIOLATED, f"row {i}: measured({measured}) outside [{mn}, {mx}] but marked PASS"
    if not checked_any:
        return COULD_NOT_CHECK, f"no PASS row in '{field}' had usable {min_f}/{max_f}/{value_f}"
    return CHECKED, None


_OPERATORS = {
    "non_empty": _check_non_empty,
    "balance_equals": _check_balance_equals,
    "sum_equals": _check_sum_equals,
    "all_rows_have": _check_all_rows_have,
    "tolerance_range": _check_tolerance_range,
}


def validate_invariants(data: dict, invariants: list[dict]) -> dict[str, Any]:
    """Evaluate structured invariants against real data.

    Returns {"checked": [...names...], "violated": [{"name", "message"}, ...],
    "could_not_check": [...names...]} — three disjoint lists. A field an invariant names
    that is absent or the wrong type always lands in could_not_check, never in checked.
    """
    checked: list[str] = []
    violated: list[dict[str, str]] = []
    could_not_check: list[str] = []

    for inv in invariants:
        name = inv.get("name", "unnamed")
        operator = _OPERATORS.get(inv.get("check", ""))
        if operator is None:
            could_not_check.append(name)
            logger.debug("Invariant '%s': unknown check operator %r", name, inv.get("check"))
            continue

        outcome, message = operator(data, inv)
        if outcome == CHECKED:
            checked.append(name)
        elif outcome == VIOLATED:
            violated.append({"name": name, "message": message or ""})
            logger.warning("Invariant '%s' violated: %s", name, message)
        else:
            could_not_check.append(name)
            logger.debug("Invariant '%s' could not be checked: %s", name, message)

    return {"checked": checked, "violated": violated, "could_not_check": could_not_check}
