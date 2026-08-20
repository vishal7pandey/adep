"""Performance benchmarks [BLK-128].

All benchmarks are marked `@pytest.mark.integration` and skip cleanly
when credentials or fixtures are missing.

Run explicitly: `uv run pytest -m integration -k benchmark`

Benchmark targets:
| Metric | Target |
|--------|--------|
| Single-page invoice, cold cache | < 30 s |
| Single-page invoice, warm cache | < 3 s |
| 10-page document | < 120 s |
| Tool registry lookup | < 1 ms |
| Definition store list (100 defs) | < 50 ms |
| SSE first byte after run start | < 500 ms |
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from src.eval.benchmarks import (
    BenchmarkResult,
    BenchmarkReport,
    save_benchmark_report,
    time_operation,
    BENCHMARK_TARGETS,
)


def _has_credentials() -> bool:
    from src.tests._credentials import has_real_credentials
    return has_real_credentials()


skip_no_credentials = pytest.mark.skipif(
    not _has_credentials(),
    reason="No real provider credentials found.",
)


# ---------------------------------------------------------------------------
# Non-provider benchmarks (always runnable)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestBenchmarksNoProvider:
    """Benchmarks that don't require real providers [BLK-128].

    These measure internal operations and can run without credentials.
    """

    def test_benchmark_tool_registry_lookup(self, tmp_path: Path):
        """Tool registry lookup < 1 ms [BLK-128]."""
        from src.run import build_tool_registry

        registry = build_tool_registry()
        names = registry.names()
        assert len(names) > 0

        # Time 1000 lookups
        start = time.perf_counter()
        for _ in range(1000):
            for name in names[:10]:
                registry.get(name)
        total = time.perf_counter() - start
        per_lookup = total / (1000 * min(10, len(names)))

        result = BenchmarkResult(
            name="tool_registry_lookup",
            duration_seconds=per_lookup,
            target_seconds=BENCHMARK_TARGETS["tool_registry_lookup"],
            passed=per_lookup <= BENCHMARK_TARGETS["tool_registry_lookup"],
        )

        assert result.passed, (
            f"Tool registry lookup took {per_lookup*1000:.3f} ms, "
            f"target is {BENCHMARK_TARGETS['tool_registry_lookup']*1000:.1f} ms"
        )

    def test_benchmark_definition_store_list(self, tmp_path: Path):
        """Definition store list (100 defs) < 50 ms [BLK-128]."""
        import src.definitions.store as store_module
        old_store = store_module._store

        store = store_module.DefinitionStore(base_dir=tmp_path / ".adep")
        store_module._store = store

        try:
            # Create 100 definitions
            import json
            for i in range(100):
                def_data = {
                    "id": f"def-bench-{i:03d}",
                    "name": f"Benchmark Definition {i}",
                    "skill_id": "invoice",
                    "template_id": "invoice",
                    "tool_names": ["ocr", "vlm"],
                }
                def_path = store.base_dir / "definitions" / f"def-bench-{i:03d}.json"
                def_path.parent.mkdir(parents=True, exist_ok=True)
                def_path.write_text(json.dumps(def_data, indent=2))

            # Time list operation
            start = time.perf_counter()
            store.list_definitions()
            duration = time.perf_counter() - start

            result = BenchmarkResult(
                name="definition_store_list_100",
                duration_seconds=duration,
                target_seconds=BENCHMARK_TARGETS["definition_store_list_100"],
                passed=duration <= BENCHMARK_TARGETS["definition_store_list_100"],
            )

            assert result.passed, (
                f"Definition store list took {duration*1000:.1f} ms, "
                f"target is {BENCHMARK_TARGETS['definition_store_list_100']*1000:.0f} ms"
            )
        finally:
            store_module._store = old_store


# ---------------------------------------------------------------------------
# Provider benchmarks (require credentials + fixtures)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@skip_no_credentials
class TestBenchmarksWithProvider:
    """Benchmarks that require real providers [BLK-128]."""

    def test_benchmark_single_page_cold_cache(self, tmp_path: Path):
        """Single-page invoice, cold cache < 30 s [BLK-128]."""
        from src.tools.cache import reset_cache, get_cache
        from src.api.run_engine import execute_run
        import asyncio

        reset_cache()
        sample = Path.cwd() / "sample-data" / "invoices" / "sample-invoice-01.pdf"
        if not sample.exists():
            pytest.skip("No sample invoice found in sample-data/")

        # Clear cache for cold start
        get_cache().clear()

        start = time.perf_counter()
        result = asyncio.get_event_loop().run_until_complete(
            execute_run("def-invoice", str(sample))
        )
        duration = time.perf_counter() - start

        report_result = BenchmarkResult(
            name="single_page_invoice_cold_cache",
            duration_seconds=duration,
            target_seconds=BENCHMARK_TARGETS["single_page_invoice_cold_cache"],
            passed=duration <= BENCHMARK_TARGETS["single_page_invoice_cold_cache"],
            metadata={"document": str(sample)},
        )

        # Save benchmark report
        report = BenchmarkReport(
            run_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            benchmarks=[report_result.to_dict()],
            all_passed=report_result.passed,
        )
        save_benchmark_report(report)

        assert report_result.passed, (
            f"Cold cache extraction took {duration:.1f} s, "
            f"target is {BENCHMARK_TARGETS['single_page_invoice_cold_cache']} s"
        )

    def test_benchmark_single_page_warm_cache(self, tmp_path: Path):
        """Single-page invoice, warm cache < 3 s [BLK-128]."""
        from src.tools.cache import get_cache
        from src.api.run_engine import execute_run
        import asyncio

        sample = Path.cwd() / "sample-data" / "invoices" / "sample-invoice-01.pdf"
        if not sample.exists():
            pytest.skip("No sample invoice found in sample-data/")

        # First run to warm the cache
        asyncio.get_event_loop().run_until_complete(
            execute_run("def-invoice", str(sample))
        )

        # Second run — should hit cache
        start = time.perf_counter()
        asyncio.get_event_loop().run_until_complete(
            execute_run("def-invoice", str(sample))
        )
        duration = time.perf_counter() - start

        report_result = BenchmarkResult(
            name="single_page_invoice_warm_cache",
            duration_seconds=duration,
            target_seconds=BENCHMARK_TARGETS["single_page_invoice_warm_cache"],
            passed=duration <= BENCHMARK_TARGETS["single_page_invoice_warm_cache"],
            metadata={"document": str(sample)},
        )

        report = BenchmarkReport(
            run_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            benchmarks=[report_result.to_dict()],
            all_passed=report_result.passed,
        )
        save_benchmark_report(report)

        assert report_result.passed, (
            f"Warm cache extraction took {duration:.1f} s, "
            f"target is {BENCHMARK_TARGETS['single_page_invoice_warm_cache']} s"
        )

    def test_benchmark_sse_first_byte(self, tmp_path: Path):
        """SSE first byte after run start < 500 ms [BLK-128]."""
        from src.api.sse import SSEEventEmitter

        sample = Path.cwd() / "sample-data" / "invoices" / "sample-invoice-01.pdf"
        if not sample.exists():
            pytest.skip("No sample invoice found in sample-data/")

        # Measure time to first SSE event
        from src.api.run_engine import execute_run
        import asyncio

        emitter = SSEEventEmitter()

        start = time.perf_counter()
        first_byte_time = None

        original_emit = emitter.emit_progress
        def timed_emit(*args, **kwargs):
            nonlocal first_byte_time
            if first_byte_time is None:
                first_byte_time = time.perf_counter() - start
            return original_emit(*args, **kwargs)

        emitter.emit_progress = timed_emit

        asyncio.get_event_loop().run_until_complete(
            execute_run("def-invoice", str(sample), emitter=emitter)
        )

        if first_byte_time is None:
            pytest.skip("No SSE events emitted")

        result = BenchmarkResult(
            name="sse_first_byte",
            duration_seconds=first_byte_time,
            target_seconds=BENCHMARK_TARGETS["sse_first_byte"],
            passed=first_byte_time <= BENCHMARK_TARGETS["sse_first_byte"],
        )

        assert result.passed, (
            f"SSE first byte took {first_byte_time*1000:.0f} ms, "
            f"target is {BENCHMARK_TARGETS['sse_first_byte']*1000:.0f} ms"
        )
