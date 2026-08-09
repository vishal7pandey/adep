"""Run grounded evaluation against the ADE HTTP API using labeled fixtures."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.harness import GroundTruthField, GroundTruthSample, run_evaluation
from src.templates.base import ExtractedResult
from src.tools.base import FieldValue, Grounding

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _api_request(method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
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
        return exc.code, json.loads(body) if body else {}


def _wait_for_run(base_url: str, run_id: str, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_payload: dict[str, Any] = {}
    while time.time() < deadline:
        status_code, payload = _api_request("GET", f"{base_url}/api/v1/runs/{run_id}")
        if status_code >= 400:
            raise RuntimeError(f"Failed to fetch run {run_id}: {payload}")
        last_payload = payload
        if last_payload.get("status") in TERMINAL_STATUSES:
            return last_payload
        time.sleep(1.0)
    raise TimeoutError(f"Run {run_id} did not finish within {timeout_seconds}s")


def _load_ground_truth_samples(fixtures_root: Path) -> list[tuple[str, GroundTruthSample]]:
    loaded: list[tuple[str, GroundTruthSample]] = []
    for gt_file in sorted(fixtures_root.glob("**/ground_truth.json")):
        data = json.loads(gt_file.read_text(encoding="utf-8"))
        doc_path = data["document_path"]
        if not Path(doc_path).is_absolute():
            doc_path = str((gt_file.parent / doc_path).resolve())
        truth = GroundTruthSample(
            document_path=doc_path,
            fields=[
                GroundTruthField(
                    name=field["name"],
                    value=field["value"],
                    bbox=tuple(field["bbox"]) if field.get("bbox") else None,
                    page=field.get("page", 0),
                )
                for field in data.get("fields", [])
            ],
        )
        loaded.append((data["definition_id"], truth))
    return loaded


def _result_from_run(run_data: dict[str, Any]) -> ExtractedResult:
    field_values: dict[str, FieldValue] = {}
    for field in run_data.get("fields", []):
        bbox = field.get("bbox")
        grounding = None
        if bbox:
            grounding = Grounding(
                bbox=(bbox["x"], bbox["y"], bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]),
                page=field.get("page", 0),
                source_tool="api_run",
                confidence=field.get("confidence", 0.0),
            )
        field_values[field["name"]] = FieldValue(
            name=field["name"],
            value=field.get("value"),
            grounding=grounding,
            confidence=field.get("confidence", 0.0),
            attempts=1,
        )
    return ExtractedResult(
        is_complete=run_data.get("status") == "completed",
        field_values=field_values,
        gap_report=None,
        trace=[],
        total_cycles=run_data.get("current_cycle", 0),
        status=run_data.get("status", "completed"),
    )


def run_eval(base_url: str, fixtures_root: Path, timeout_seconds: int, report_path: Path) -> dict[str, Any]:
    loaded = _load_ground_truth_samples(fixtures_root)
    results: list[ExtractedResult] = []
    truths: list[GroundTruthSample] = []
    run_rows: list[dict[str, Any]] = []

    for definition_id, truth in loaded:
        status_code, start_payload = _api_request(
            "POST",
            f"{base_url}/api/v1/runs",
            {"definition_id": definition_id, "document_url": truth.document_path},
        )
        if status_code >= 400:
            raise RuntimeError(f"Failed to start run for {truth.document_path}: {start_payload}")
        run_data = _wait_for_run(base_url, start_payload["id"], timeout_seconds)
        results.append(_result_from_run(run_data))
        truths.append(truth)
        run_rows.append({
            "definition_id": definition_id,
            "document_path": truth.document_path,
            "run_id": start_payload["id"],
            "status": run_data.get("status"),
        })

    report = run_evaluation(results, truths)
    payload = report.to_dict()
    payload["runs"] = run_rows
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run grounded ADE evaluation against the HTTP API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--fixtures-root", default="src/tests/fixtures/high_value")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--report-path", default=".adep/reports/api_grounded_eval.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        payload = run_eval(args.base_url.rstrip("/"), Path(args.fixtures_root), args.timeout_seconds, Path(args.report_path))
    except Exception as exc:
        print(f"Grounded eval failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote grounded eval report to {args.report_path}; overall_accuracy={payload['overall_accuracy']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())