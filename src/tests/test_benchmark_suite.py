"""Tests for the real-world benchmark suite [BLK-174, SCRUM-87].

Tests cover:
- ProviderResult and BenchmarkSuiteReport serialization
- Comparison matrix construction
- Regression detection
- Report save/load round-trip
- API endpoints (POST/GET /admin/benchmarks)
- Provider env var switching
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.eval.benchmark_suite import (
    ProviderResult,
    BenchmarkSuiteReport,
    PROVIDER_CONFIGS,
    DEFAULT_PROVIDERS,
    _build_comparison,
    _detect_regressions,
    save_benchmark_suite_report,
    load_benchmark_suite_reports,
    _set_provider_env,
    _restore_env,
)


# ---------------------------------------------------------------------------
# Unit tests — data structures
# ---------------------------------------------------------------------------

class TestProviderResult:
    """ProviderResult serialization and defaults."""

    def test_default_values(self):
        result = ProviderResult(provider="paddle")
        assert result.provider == "paddle"
        assert result.documents_tested == 0
        assert result.documents_failed == 0
        assert result.overall_accuracy == 0.0
        assert result.per_field == {}
        assert result.failures == []

    def test_to_dict_round_trip(self):
        result = ProviderResult(
            provider="tesseract",
            documents_tested=5,
            documents_failed=1,
            overall_accuracy=0.85,
            overall_grounded_accuracy=0.80,
            overall_anls=0.90,
            overall_smudge=0.75,
            avg_confidence=0.88,
            calibration_error=0.03,
            avg_latency_seconds=12.5,
            avg_tokens=15000,
            avg_cost_usd=0.12,
            per_field={"invoice_number": {"accuracy": 0.95, "total": 5, "correct": 5}},
            failures=[{"field": "total", "correct": 3, "total": 5, "accuracy": 0.6}],
        )
        d = result.to_dict()
        assert d["provider"] == "tesseract"
        assert d["documents_tested"] == 5
        assert d["documents_failed"] == 1
        assert d["overall_accuracy"] == 0.85
        assert d["avg_tokens"] == 15000
        assert "invoice_number" in d["per_field"]
        assert len(d["failures"]) == 1


class TestBenchmarkSuiteReport:
    """BenchmarkSuiteReport serialization."""

    def test_to_dict_with_providers(self):
        report = BenchmarkSuiteReport(
            run_at="2026-01-01T00:00:00Z",
            fixture_dir="sample-data/invoices/",
            baseline_provider="paddle",
            providers=[
                ProviderResult(provider="paddle", overall_accuracy=0.90),
                ProviderResult(provider="tesseract", overall_accuracy=0.85),
            ],
        )
        d = report.to_dict()
        assert d["run_at"] == "2026-01-01T00:00:00Z"
        assert d["baseline_provider"] == "paddle"
        assert len(d["providers"]) == 2
        assert d["providers"][0]["provider"] == "paddle"
        assert d["providers"][1]["provider"] == "tesseract"

    def test_to_json(self):
        report = BenchmarkSuiteReport(run_at="2026-01-01T00:00:00Z")
        j = report.to_json()
        parsed = json.loads(j)
        assert parsed["run_at"] == "2026-01-01T00:00:00Z"

    def test_save_and_load(self, tmp_path: Path):
        report = BenchmarkSuiteReport(
            run_at="2026-01-01T00:00:00Z",
            fixture_dir="sample-data/",
            providers=[ProviderResult(provider="paddle", overall_accuracy=0.9)],
        )
        path = save_benchmark_suite_report(report, reports_dir=tmp_path)
        assert path.exists()

        loaded = load_benchmark_suite_reports(reports_dir=tmp_path)
        assert len(loaded) == 1
        assert loaded[0]["run_at"] == "2026-01-01T00:00:00Z"
        assert loaded[0]["providers"][0]["provider"] == "paddle"

    def test_load_empty_dir(self, tmp_path: Path):
        loaded = load_benchmark_suite_reports(reports_dir=tmp_path / "nonexistent")
        assert loaded == []


# ---------------------------------------------------------------------------
# Unit tests — comparison and regression
# ---------------------------------------------------------------------------

class TestComparisonMatrix:
    """_build_comparison produces correct side-by-side metrics."""

    def test_comparison_includes_all_metrics(self):
        providers = [
            ProviderResult(
                provider="paddle",
                overall_accuracy=0.90,
                overall_grounded_accuracy=0.85,
                calibration_error=0.05,
                avg_latency_seconds=10.0,
                per_field={"invoice_number": {"accuracy": 0.95}, "total": {"accuracy": 0.80}},
            ),
            ProviderResult(
                provider="tesseract",
                overall_accuracy=0.85,
                overall_grounded_accuracy=0.78,
                calibration_error=0.08,
                avg_latency_seconds=15.0,
                per_field={"invoice_number": {"accuracy": 0.90}, "total": {"accuracy": 0.75}},
            ),
        ]
        comparison = _build_comparison(providers)

        assert "overall_accuracy" in comparison
        assert comparison["overall_accuracy"]["paddle"] == 0.9
        assert comparison["overall_accuracy"]["tesseract"] == 0.85
        assert comparison["overall_accuracy"]["best_provider"] == "paddle"

        # Lower is better for calibration_error
        assert comparison["calibration_error"]["best_provider"] == "paddle"

        # Lower is better for latency
        assert comparison["avg_latency_seconds"]["best_provider"] == "paddle"

    def test_per_field_comparison(self):
        providers = [
            ProviderResult(
                provider="paddle",
                per_field={"invoice_number": {"accuracy": 0.95}, "total": {"accuracy": 0.80}},
            ),
            ProviderResult(
                provider="tesseract",
                per_field={"invoice_number": {"accuracy": 0.90}, "total": {"accuracy": 0.85}},
            ),
        ]
        comparison = _build_comparison(providers)
        assert "per_field_accuracy" in comparison
        assert "invoice_number" in comparison["per_field_accuracy"]
        assert comparison["per_field_accuracy"]["invoice_number"]["paddle"] == 0.95
        assert comparison["per_field_accuracy"]["total"]["tesseract"] == 0.85


class TestRegressionDetection:
    """_detect_regressions flags fields with accuracy drops."""

    def test_regression_detected(self):
        providers = [
            ProviderResult(
                provider="paddle",
                per_field={"invoice_number": {"accuracy": 0.95}, "total": {"accuracy": 0.90}},
            ),
            ProviderResult(
                provider="tesseract",
                per_field={"invoice_number": {"accuracy": 0.85}, "total": {"accuracy": 0.88}},
            ),
        ]
        regressions = _detect_regressions(providers, baseline="paddle", threshold=0.05)

        # invoice_number dropped by 0.10 → should be flagged
        assert len(regressions) == 1
        assert regressions[0]["field"] == "invoice_number"
        assert regressions[0]["baseline_provider"] == "paddle"
        assert regressions[0]["provider"] == "tesseract"
        assert regressions[0]["drop"] == 0.1

    def test_no_regression_when_drop_below_threshold(self):
        providers = [
            ProviderResult(
                provider="paddle",
                per_field={"total": {"accuracy": 0.90}},
            ),
            ProviderResult(
                provider="tesseract",
                per_field={"total": {"accuracy": 0.88}},
            ),
        ]
        regressions = _detect_regressions(providers, baseline="paddle", threshold=0.05)
        assert len(regressions) == 0  # 0.02 drop < 0.05 threshold

    def test_no_baseline_returns_empty(self):
        providers = [ProviderResult(provider="paddle")]
        regressions = _detect_regressions(providers, baseline="nonexistent")
        assert regressions == []


# ---------------------------------------------------------------------------
# Unit tests — provider env switching
# ---------------------------------------------------------------------------

class TestProviderEnvSwitching:
    """_set_provider_env and _restore_env manage env vars correctly."""

    def test_set_and_restore(self):
        original = os.environ.get("ADE_OCR_PROVIDER", "")

        old = _set_provider_env("tesseract")
        assert os.environ.get("ADE_OCR_PROVIDER") == "tesseract"

        _restore_env(old)
        if original:
            assert os.environ.get("ADE_OCR_PROVIDER") == original
        else:
            assert "ADE_OCR_PROVIDER" not in os.environ or os.environ.get("ADE_OCR_PROVIDER") == ""

    def test_unknown_provider_no_change(self):
        old = _set_provider_env("unknown_provider")
        _restore_env(old)
        # Should not crash, just no config to set


# ---------------------------------------------------------------------------
# Integration tests — API endpoints
# ---------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Create a FastAPI TestClient with a temporary store."""
    import src.definitions.store as store_module
    import src.config as config_module

    old_store = store_module._store
    old_auth = config_module.settings.auth_enabled
    store_module._store = store_module.DefinitionStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    from src.api.main import create_app
    app = create_app()
    test_client = TestClient(app)

    yield test_client

    config_module.settings.auth_enabled = old_auth
    store_module._store = old_store


class TestBenchmarkAPI:
    """API endpoints for benchmark suite [BLK-174]."""

    def test_get_providers(self, client: TestClient):
        resp = client.get("/api/v1/admin/benchmarks/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert "paddle" in data["providers"]
        assert "tesseract" in data["providers"]
        assert "configs" in data

    def test_list_benchmarks_empty(self, client: TestClient, tmp_path: Path, monkeypatch):
        """GET /admin/benchmarks returns empty list when no reports exist."""
        monkeypatch.chdir(tmp_path)
        resp = client.get("/api/v1/admin/benchmarks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["reports"] == []

    def test_list_benchmarks_with_saved_report(self, client: TestClient, tmp_path: Path, monkeypatch):
        """GET /admin/benchmarks returns saved reports."""
        monkeypatch.chdir(tmp_path)

        # Save a report
        report = BenchmarkSuiteReport(
            run_at="2026-01-01T00:00:00Z",
            fixture_dir="sample-data/",
            providers=[ProviderResult(provider="paddle", overall_accuracy=0.9)],
        )
        save_benchmark_suite_report(report)

        resp = client.get("/api/v1/admin/benchmarks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["reports"][0]["run_at"] == "2026-01-01T00:00:00Z"

    def test_get_latest_benchmark_404(self, client: TestClient, tmp_path: Path, monkeypatch):
        """GET /admin/benchmarks/latest returns 404 when no reports exist."""
        monkeypatch.chdir(tmp_path)
        resp = client.get("/api/v1/admin/benchmarks/latest")
        assert resp.status_code == 404

    def test_get_latest_benchmark(self, client: TestClient, tmp_path: Path, monkeypatch):
        """GET /admin/benchmarks/latest returns the most recent report."""
        monkeypatch.chdir(tmp_path)

        report = BenchmarkSuiteReport(
            run_at="2026-06-01T00:00:00Z",
            fixture_dir="sample-data/",
            providers=[ProviderResult(provider="paddle", overall_accuracy=0.9)],
        )
        save_benchmark_suite_report(report)

        resp = client.get("/api/v1/admin/benchmarks/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_at"] == "2026-06-01T00:00:00Z"

    def test_trigger_benchmark_404_missing_dir(self, client: TestClient):
        """POST /admin/benchmarks returns 404 for nonexistent fixture dir."""
        resp = client.post(
            "/api/v1/admin/benchmarks",
            json={"fixture_dir": "/nonexistent/path/"},
        )
        assert resp.status_code == 404

    def test_trigger_benchmark_400_invalid_provider(self, client: TestClient, tmp_path: Path):
        """POST /admin/benchmarks returns 400 for unknown provider."""
        resp = client.post(
            "/api/v1/admin/benchmarks",
            json={"fixture_dir": str(tmp_path), "providers": ["invalid_provider"]},
        )
        assert resp.status_code == 400
