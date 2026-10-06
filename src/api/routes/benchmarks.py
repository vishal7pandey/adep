"""REST endpoints for benchmark suite [BLK-174]."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.eval.benchmark_suite import (
    run_benchmark_suite,
    save_benchmark_suite_report,
    load_benchmark_suite_reports,
    DEFAULT_PROVIDERS,
    PROVIDER_CONFIGS,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["benchmarks"])


class BenchmarkRequest(BaseModel):
    """Request body for POST /admin/benchmarks [BLK-174]."""

    fixture_dir: str = Field(
        default="sample-data/",
        description="Path to directory with .expected.json fixtures.",
    )
    providers: list[str] = Field(
        default_factory=lambda: list(DEFAULT_PROVIDERS),
        description="Provider names to test (e.g. ['paddle', 'tesseract']).",
    )
    baseline_provider: str | None = Field(
        default=None,
        description="Provider to use as baseline for regression detection. Defaults to first provider.",
    )


class BenchmarkResponse(BaseModel):
    """Response for POST /admin/benchmarks [BLK-174]."""

    report: dict[str, Any]
    saved_path: str | None = None


@router.post("/admin/benchmarks", response_model=BenchmarkResponse)
def trigger_benchmark(req: BenchmarkRequest) -> BenchmarkResponse:
    """Run the benchmark suite across providers [BLK-174].

    Runs extraction on labeled fixtures for each provider, produces a comparison
    report, and persists it to `.adep/reports/`.
    """
    # Validate provider names
    invalid = [p for p in req.providers if p not in PROVIDER_CONFIGS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown providers: {invalid}. Available: {list(PROVIDER_CONFIGS.keys())}",
        )

    # fixture_dir comes from the request body: resolve it and require it to stay inside the
    # working directory before it is probed (CodeQL py/path-injection). An absolute value
    # replaces the base in os.path.join and is checked the same way. Anything outside gets the
    # same 404 as a missing directory.
    base = os.path.realpath(os.getcwd())
    fixture_path = os.path.realpath(os.path.join(base, req.fixture_dir))
    if fixture_path != base and not fixture_path.startswith(base + os.sep):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fixture directory not found: {req.fixture_dir}",
        )

    if not os.path.exists(fixture_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fixture directory not found: {fixture_path}",
        )

    try:
        report = run_benchmark_suite(
            fixture_dir=fixture_path,
            providers=req.providers,
            baseline_provider=req.baseline_provider,
        )
    except Exception as e:
        logger.error("Benchmark suite failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark suite failed: {e}",
        )

    saved_path = save_benchmark_suite_report(report)

    return BenchmarkResponse(
        report=report.to_dict(),
        saved_path=str(saved_path),
    )


@router.get("/admin/benchmarks")
def list_benchmark_reports() -> dict[str, Any]:
    """List all saved benchmark suite reports [BLK-174].

    Returns reports sorted newest-first.
    """
    reports = load_benchmark_suite_reports()
    return {
        "count": len(reports),
        "reports": reports,
    }


@router.get("/admin/benchmarks/latest")
def get_latest_benchmark() -> dict[str, Any]:
    """Get the most recent benchmark suite report [BLK-174]."""
    reports = load_benchmark_suite_reports()
    if not reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No benchmark suite reports found.",
        )
    return reports[0]


@router.get("/admin/benchmarks/providers")
def list_available_providers() -> dict[str, Any]:
    """List all available provider configurations [BLK-174]."""
    return {
        "providers": list(PROVIDER_CONFIGS.keys()),
        "configs": PROVIDER_CONFIGS,
    }
