"""Benchmark suite for performance measurement [BLK-128].

Measures latency for key operations and persists results to `.adep/reports/`
for trend comparison over time.

All benchmarks are marked `@pytest.mark.integration` and skip cleanly
when credentials are missing.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Benchmark targets (from BLK-128 spec)
BENCHMARK_TARGETS = {
    "single_page_invoice_cold_cache": 30.0,  # seconds
    "single_page_invoice_warm_cache": 3.0,  # seconds
    "ten_page_document": 120.0,  # seconds
    "tool_registry_lookup": 0.001,  # seconds (1 ms)
    "definition_store_list_100": 0.05,  # seconds (50 ms)
    "sse_first_byte": 0.5,  # seconds (500 ms)
}


@dataclass
class BenchmarkResult:
    """A single benchmark measurement [BLK-128].

    Attributes:
        name: Benchmark name.
        duration_seconds: Measured duration.
        target_seconds: Target duration from spec.
        passed: Whether the benchmark met its target.
        metadata: Extra info (cache state, document type, etc.).
    """

    name: str
    duration_seconds: float
    target_seconds: float
    passed: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "duration_seconds": round(self.duration_seconds, 4),
            "target_seconds": round(self.target_seconds, 4),
            "passed": self.passed,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkReport:
    """Full benchmark report [BLK-128].

    Attributes:
        run_at: ISO timestamp.
        benchmarks: List of BenchmarkResult dicts.
        all_passed: Whether all benchmarks met their targets.
    """

    run_at: str = ""
    benchmarks: list[dict[str, Any]] = field(default_factory=list)
    all_passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_at": self.run_at,
            "all_passed": self.all_passed,
            "benchmarks": self.benchmarks,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(self.to_json(), encoding="utf-8")
        logger.info("Benchmark report saved to %s", path)


def save_benchmark_report(report: BenchmarkReport, reports_dir: str | Path | None = None) -> Path:
    """Save a benchmark report to `.adep/reports/` [BLK-128].

    Args:
        report: The BenchmarkReport to save.
        reports_dir: Optional custom directory. Defaults to `.adep/reports/`.

    Returns:
        Path to the saved report file.
    """
    if reports_dir is None:
        reports_dir = Path.cwd() / ".adep" / "reports"
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    filename = f"benchmarks_{timestamp}.json"
    path = reports_dir / filename
    report.save(path)
    return path


def time_operation(func: Any, *args: Any, **kwargs: Any) -> tuple[Any, float]:
    """Time a function call and return (result, duration_seconds) [BLK-128].

    Args:
        func: The function to time.
        *args, **kwargs: Arguments to pass to the function.

    Returns:
        Tuple of (result, duration_in_seconds).
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    duration = time.perf_counter() - start
    return result, duration
