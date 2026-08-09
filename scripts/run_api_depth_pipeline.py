"""Run the supported sample corpus through the ADE HTTP API.

This script is the thin orchestration layer that the backend was missing:
it discovers sample documents, starts extraction runs via ``/api/v1/runs``,
waits for completion, invokes ``/api/v1/runs/{run_id}/verify``, and writes a
 report with execution and refinement signals.

It intentionally uses the public HTTP API rather than internal Python calls.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_CATEGORY_DEFINITIONS: dict[str, str] = {
    "ad-buy": "def-ad-buy",
    "bank-statements": "def-bank-statement",
    "boq": "def-boq-estimator",
    "commodity-trade": "def-commodity-trade",
    "compliance-audits": "def-compliance-audit",
    "insurance-policy": "def-insurance-policy",
    "invoices": "def-invoice",
    "leases": "def-commercial-lease",
    "medical-claims": "def-medical-claim",
    "metallurgical-assay": "def-metallurgical-assay",
    "packing-list": "def-packing-list",
    "pay-stub": "def-pay-stub",
    "pid-diagrams": "def-pid-to-dexpi",
    "purchase-order": "def-purchase-order",
    "store-audits": "def-store-audit",
    "trade-finance": "def-trade-finance-scrutiny",
    "utility-bills": "def-utility-bill",
    "w2-tax-form": "def-w2-tax-form",
}

PREFERRED_DOCUMENT_PATTERNS: dict[str, tuple[str, ...]] = {
    "commodity-trade": ("blco", "procedures"),
    "packing-list": ("sample-packing-list-02",),
    "purchase-order": ("sf1449",),
    "trade-finance": ("mt700", "lc-sample-agreement"),
    "utility-bills": ("sample-utility-bill-01",),
    "leases": ("sample-lease-02",),
}

DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _api_request(method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    """Issue a JSON HTTP request and return ``(status_code, decoded_body)``."""
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            decoded = json.loads(body) if body else {}
        except json.JSONDecodeError:
            decoded = {"detail": body}
        return exc.code, decoded


def _discover_documents(sample_root: Path, limit_per_category: int) -> dict[str, list[Path]]:
    """Discover supported sample documents under the sample-data root."""
    discovered: dict[str, list[Path]] = {}
    for category in sorted(DEFAULT_CATEGORY_DEFINITIONS):
        category_dir = sample_root / category
        if not category_dir.exists():
            continue
        docs = [
            path for path in sorted(category_dir.iterdir())
            if path.is_file() and path.suffix.lower() in DOCUMENT_EXTENSIONS
        ]
        preferences = PREFERRED_DOCUMENT_PATTERNS.get(category, ())
        if preferences:
            docs = sorted(
                docs,
                key=lambda path: (
                    0 if any(token.lower() in path.name.lower() for token in preferences) else 1,
                    path.name.lower(),
                ),
            )
        if docs:
            discovered[category] = docs[:limit_per_category]
    return discovered


def _wait_for_run(base_url: str, run_id: str, timeout_seconds: int, poll_interval: float) -> tuple[bool, dict[str, Any]]:
    """Poll a run until it reaches a terminal status or times out."""
    deadline = time.time() + timeout_seconds
    last_payload: dict[str, Any] = {}
    while time.time() < deadline:
        status_code, payload = _api_request("GET", f"{base_url}/api/v1/runs/{run_id}")
        last_payload = payload if isinstance(payload, dict) else {}
        if status_code >= 400:
            return False, {"status": "failed", "detail": payload}
        if last_payload.get("status") in TERMINAL_STATUSES:
            return True, last_payload
        time.sleep(poll_interval)
    last_payload.setdefault("status", "timeout")
    return False, last_payload


def _verify_run(base_url: str, run_id: str) -> tuple[int, dict[str, Any]]:
    """Request surrogate verification for a completed run."""
    status_code, payload = _api_request("POST", f"{base_url}/api/v1/runs/{run_id}/verify")
    return status_code, payload if isinstance(payload, dict) else {"detail": payload}


def run_pipeline(
    base_url: str,
    sample_root: Path,
    report_path: Path,
    limit_per_category: int,
    timeout_seconds: int,
    poll_interval: float,
) -> dict[str, Any]:
    """Execute the supported corpus and write a verifier-focused report."""
    discovered = _discover_documents(sample_root, limit_per_category)
    status_code, definitions = _api_request("GET", f"{base_url}/api/v1/definitions")
    if status_code >= 400:
        raise RuntimeError(f"Failed to list definitions: {definitions}")
    available_definition_ids = {item.get("id") for item in definitions if isinstance(item, dict)}

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "sample_root": str(sample_root),
        "categories": [],
    }

    for category, documents in discovered.items():
        definition_id = DEFAULT_CATEGORY_DEFINITIONS[category]
        category_entry: dict[str, Any] = {
            "category": category,
            "definition_id": definition_id,
            "supported": definition_id in available_definition_ids,
            "documents": [],
        }
        if definition_id not in available_definition_ids:
            category_entry["note"] = "Definition not available from API; category skipped."
            report["categories"].append(category_entry)
            continue

        for document_path in documents:
            start_status, start_payload = _api_request(
                "POST",
                f"{base_url}/api/v1/runs",
                {"definition_id": definition_id, "document_url": str(document_path.resolve())},
            )
            document_entry: dict[str, Any] = {
                "document_path": str(document_path),
                "start_status_code": start_status,
            }
            if start_status >= 400:
                document_entry["error"] = start_payload
                category_entry["documents"].append(document_entry)
                continue

            run_id = start_payload.get("id")
            document_entry["run_id"] = run_id
            completed, run_payload = _wait_for_run(base_url, run_id, timeout_seconds, poll_interval)
            document_entry["run_completed"] = completed
            document_entry["run_status"] = run_payload.get("status")
            document_entry["extracted_fields_count"] = run_payload.get("extracted_fields_count")
            document_entry["total_fields"] = run_payload.get("total_fields")
            document_entry["low_confidence_fields"] = [
                field.get("name")
                for field in run_payload.get("fields", [])
                if field.get("status") == "low_confidence"
            ]

            verify_status, verify_payload = _verify_run(base_url, run_id)
            document_entry["verify_status_code"] = verify_status
            if verify_status < 400:
                document_entry["diagnosis_count"] = len(verify_payload.get("diagnoses", []))
                document_entry["high_severity_diagnoses"] = [
                    diagnosis.get("message")
                    for diagnosis in verify_payload.get("diagnoses", [])
                    if diagnosis.get("severity") == "high"
                ]
                document_entry["proposed_tests"] = verify_payload.get("proposed_tests", [])
                document_entry["skill_patch"] = verify_payload.get("skill_patch", {})
            else:
                document_entry["verify_error"] = verify_payload

            category_entry["documents"].append(document_entry)

        report["categories"].append(category_entry)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run supported ADE sample documents through the HTTP API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL for the ADE API server")
    parser.add_argument("--sample-root", default="sample-data", help="Sample data root directory")
    parser.add_argument("--limit-per-category", type=int, default=2, help="Maximum documents to run per supported category")
    parser.add_argument("--timeout-seconds", type=int, default=180, help="Maximum time to wait per run")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval while waiting for runs")
    parser.add_argument("--report-path", default=".adep/reports/api_depth_pipeline.json", help="Where to write the JSON report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        report = run_pipeline(
            base_url=args.base_url.rstrip("/"),
            sample_root=Path(args.sample_root),
            report_path=Path(args.report_path),
            limit_per_category=args.limit_per_category,
            timeout_seconds=args.timeout_seconds,
            poll_interval=args.poll_interval,
        )
    except Exception as exc:
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return 1

    completed = sum(
        1
        for category in report["categories"]
        for document in category.get("documents", [])
        if document.get("run_status") == "completed"
    )
    print(f"Wrote report to {args.report_path}; completed runs: {completed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())