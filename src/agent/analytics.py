"""Advanced analytics — per-skill, per-template, per-document-type insights [BLK-066].

Aggregates run data from `.adep/runs/` files to compute metrics.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_all_runs(base_dir: Path | None = None) -> list[dict[str, Any]]:
    """Load all run data from the store."""
    if base_dir is None:
        base_dir = Path(".adep")
    runs_dir = base_dir / "runs"
    if not runs_dir.exists():
        return []
    runs = []
    for path in sorted(runs_dir.glob("*.json")):
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception as e:
            logger.warning("Failed to load run %s: %s", path, e)
    return runs


def get_skill_analytics(base_dir: Path | None = None) -> list[dict[str, Any]]:
    """Compute per-skill analytics [BLK-066].

    Returns:
        List of skill analytics dicts with:
        - skill_id, total_runs, success_rate, avg_confidence,
          avg_tokens, avg_cost, top_failing_fields
    """
    runs = _load_all_runs(base_dir)

    by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        def_id = run.get("definition_id", "unknown")
        by_skill[def_id].append(run)

    results = []
    for skill_id, skill_runs in by_skill.items():
        total = len(skill_runs)
        completed = sum(1 for r in skill_runs if r.get("status") == "completed")
        success_rate = (completed / total * 100) if total > 0 else 0.0

        confidences = [
            f.get("confidence", 0.0)
            for r in skill_runs
            for f in r.get("fields", [])
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        token_usage = [
            r.get("token_usage_summary", {})
            for r in skill_runs
        ]
        total_tokens = sum(t.get("total_tokens", 0) for t in token_usage)
        total_cost = sum(t.get("total_cost_usd", 0.0) for t in token_usage)
        avg_tokens = total_tokens / total if total > 0 else 0
        avg_cost = total_cost / total if total > 0 else 0.0

        # Top failing fields
        failing_fields: dict[str, int] = defaultdict(int)
        for r in skill_runs:
            for f in r.get("fields", []):
                if f.get("status") not in ("extracted", "complete"):
                    failing_fields[f.get("name", f.get("id", "unknown"))] += 1

        top_failing = sorted(
            failing_fields.items(), key=lambda x: x[1], reverse=True
        )[:5]

        results.append({
            "skill_id": skill_id,
            "total_runs": total,
            "success_rate": round(success_rate, 1),
            "avg_confidence": round(avg_confidence, 3),
            "avg_tokens": int(avg_tokens),
            "avg_cost_usd": round(avg_cost, 6),
            "top_failing_fields": [
                {"field": f, "failures": c} for f, c in top_failing
            ],
        })

    return results


def get_template_analytics(base_dir: Path | None = None) -> list[dict[str, Any]]:
    """Compute per-template analytics [BLK-066].

    Returns:
        List of template analytics dicts with:
        - template_id, total_runs, required_coverage, optional_coverage,
          avg_confidence_per_field, most_missing_fields
    """
    runs = _load_all_runs(base_dir)

    by_template: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        # Templates are referenced via definitions; use definition_id as proxy
        tmpl_id = run.get("definition_id", "unknown")
        by_template[tmpl_id].append(run)

    results = []
    for template_id, tmpl_runs in by_template.items():
        total = len(tmpl_runs)
        total_fields = sum(r.get("total_fields", 0) for r in tmpl_runs)
        extracted = sum(r.get("extracted_fields_count", 0) for r in tmpl_runs)

        coverage = (extracted / total_fields * 100) if total_fields > 0 else 0.0

        # Per-field confidence
        field_confidences: dict[str, list[float]] = defaultdict(list)
        for r in tmpl_runs:
            for f in r.get("fields", []):
                name = f.get("name", f.get("id", "unknown"))
                field_confidences[name].append(f.get("confidence", 0.0))

        avg_per_field = {
            name: round(sum(c) / len(c), 3)
            for name, c in field_confidences.items()
        }

        # Most missing fields
        missing: dict[str, int] = defaultdict(int)
        for r in tmpl_runs:
            extracted_names = {
                f.get("name", f.get("id", ""))
                for f in r.get("fields", [])
                if f.get("status") in ("extracted", "complete")
            }
            # We don't know the full template schema from run data alone
            # Use fields with non-extracted status as proxy
            for f in r.get("fields", []):
                if f.get("status") not in ("extracted", "complete"):
                    missing[f.get("name", f.get("id", "unknown"))] += 1

        most_missing = sorted(missing.items(), key=lambda x: x[1], reverse=True)[:5]

        results.append({
            "template_id": template_id,
            "total_runs": total,
            "field_coverage": round(coverage, 1),
            "avg_confidence_per_field": avg_per_field,
            "most_missing_fields": [
                {"field": f, "count": c} for f, c in most_missing
            ],
        })

    return results


def get_document_analytics(base_dir: Path | None = None) -> dict[str, Any]:
    """Compute per-document-type analytics [BLK-066].

    Returns:
        Dict with volume by definition, avg extraction time, error rate, cost.
    """
    runs = _load_all_runs(base_dir)

    total = len(runs)
    completed = sum(1 for r in runs if r.get("status") == "completed")
    failed = sum(1 for r in runs if r.get("status") == "failed")

    by_def: dict[str, int] = defaultdict(int)
    for r in runs:
        by_def[r.get("definition_id", "unknown")] += 1

    token_usage = [r.get("token_usage_summary", {}) for r in runs]
    total_tokens = sum(t.get("total_tokens", 0) for t in token_usage)
    total_cost = sum(t.get("total_cost_usd", 0.0) for t in token_usage)

    return {
        "total_runs": total,
        "completed": completed,
        "failed": failed,
        "error_rate": round((failed / total * 100) if total > 0 else 0.0, 1),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "volume_by_definition": dict(by_def),
    }


def get_failure_analytics(base_dir: Path | None = None) -> dict[str, Any]:
    """Compute failure analysis [BLK-066].

    Returns:
        Dict with most common gap types, most failing fields, retry frequency.
    """
    runs = _load_all_runs(base_dir)

    failing_fields: dict[str, int] = defaultdict(int)
    failed_runs = 0

    for r in runs:
        if r.get("status") in ("failed", "partial"):
            failed_runs += 1
        for f in r.get("fields", []):
            if f.get("status") not in ("extracted", "complete"):
                failing_fields[f.get("name", f.get("id", "unknown"))] += 1

    top_failing = sorted(failing_fields.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_failed_or_partial": failed_runs,
        "top_failing_fields": [
            {"field": f, "count": c} for f, c in top_failing
        ],
    }
