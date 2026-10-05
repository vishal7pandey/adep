"""Tests for BLK-124 — Tool result caching.

Tests cover:
- Content-addressed cache key computation
- Cache hit/miss/expiry
- Two-level cache: in-memory LRU + file store
- Identical pixels different bbox → same cache hit
- TTL expiry
- LRU eviction
- Cache version invalidation
- ToolSpec.cacheable flag
- ToolRegistry.call() with caching
- Cache stats and clear API endpoints
- Config: cache_enabled toggle
- Cached second run makes zero provider calls
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.tools.base import Grounding, ToolRegistry, ToolSpec, ToolResult
from src.tools.cache import (
    ToolCache,
    compute_cache_key,
    get_cache,
    reset_cache,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_cache(tmp_path: Path) -> ToolCache:
    """Create a fresh ToolCache in a tmp directory."""
    return ToolCache(base_dir=tmp_path / "cache")


@pytest.fixture(autouse=True)
def _reset_cache_singleton():
    """Reset the module-level cache singleton between tests."""
    reset_cache()
    yield
    reset_cache()


# ---------------------------------------------------------------------------
# Cache key computation tests
# ---------------------------------------------------------------------------


class TestCacheKey:
    """Verify content-addressed cache key computation [BLK-124]."""

    def test_key_is_deterministic(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake image bytes")
        key1 = compute_cache_key("ocr", image_path=str(img), params={"lang": "en"})
        key2 = compute_cache_key("ocr", image_path=str(img), params={"lang": "en"})
        assert key1 == key2

    def test_different_tool_different_key(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake image bytes")
        key1 = compute_cache_key("ocr", image_path=str(img))
        key2 = compute_cache_key("vlm", image_path=str(img))
        assert key1 != key2

    def test_different_params_different_key(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake image bytes")
        key1 = compute_cache_key("vlm", image_path=str(img), params={"question": "what is this?"})
        key2 = compute_cache_key(
            "vlm", image_path=str(img), params={"question": "what is the total?"}
        )
        assert key1 != key2

    def test_different_image_different_key(self, tmp_path: Path):
        img1 = tmp_path / "a.png"
        img1.write_bytes(b"image A")
        img2 = tmp_path / "b.png"
        img2.write_bytes(b"image B")
        key1 = compute_cache_key("ocr", image_path=str(img1))
        key2 = compute_cache_key("ocr", image_path=str(img2))
        assert key1 != key2

    def test_identical_bytes_different_path_same_key(self, tmp_path: Path):
        """Two files with identical bytes should produce the same key."""
        img1 = tmp_path / "a.png"
        img1.write_bytes(b"identical pixels")
        img2 = tmp_path / "b.png"
        img2.write_bytes(b"identical pixels")
        key1 = compute_cache_key("ocr", image_path=str(img1))
        key2 = compute_cache_key("ocr", image_path=str(img2))
        assert key1 == key2

    def test_different_provider_different_key(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake image bytes")
        key1 = compute_cache_key("ocr", image_path=str(img), provider="paddle")
        key2 = compute_cache_key("ocr", image_path=str(img), provider="tesseract")
        assert key1 != key2

    def test_image_bytes_parameter(self):
        key1 = compute_cache_key("ocr", image_bytes=b"raw bytes here")
        key2 = compute_cache_key("ocr", image_bytes=b"raw bytes here")
        assert key1 == key2
        key3 = compute_cache_key("ocr", image_bytes=b"different bytes")
        assert key1 != key3


# ---------------------------------------------------------------------------
# ToolCache basic tests
# ---------------------------------------------------------------------------


class TestToolCache:
    """Verify ToolCache get/put operations [BLK-124]."""

    def test_put_and_get(self, tmp_cache: ToolCache):
        result = ToolResult(ok=True, data={"text": "hello"}, tool="ocr")
        key = "abc123"
        tmp_cache.put(key, result, tool_name="ocr")
        cached = tmp_cache.get(key)
        assert cached is not None
        assert cached.ok is True
        assert cached.data == {"text": "hello"}

    def test_miss_returns_none(self, tmp_cache: ToolCache):
        assert tmp_cache.get("nonexistent") is None

    def test_stats_track_hits_misses(self, tmp_cache: ToolCache):
        result = ToolResult(ok=True, data={"text": "hello"}, tool="ocr")
        tmp_cache.put("key1", result, tool_name="ocr")
        tmp_cache.get("key1")  # hit
        tmp_cache.get("key1")  # hit
        tmp_cache.get("missing")  # miss
        stats = tmp_cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1


# ---------------------------------------------------------------------------
# TTL expiry tests
# ---------------------------------------------------------------------------


class TestTTLExpiry:
    """Verify TTL-based cache expiry [BLK-124]."""

    def test_expired_entry_returns_none(self, tmp_path: Path):
        cache = ToolCache(base_dir=tmp_path / "cache", ttl_seconds=1)
        result = ToolResult(ok=True, data={"text": "hello"}, tool="ocr")
        cache.put("key1", result, tool_name="ocr")

        # Simulate expiry by backdating the entry
        for entry in cache._memory.values():
            entry.created_at = time.time() - 10

        assert cache.get("key1") is None

    def test_non_expired_entry_returns_result(self, tmp_path: Path):
        cache = ToolCache(base_dir=tmp_path / "cache", ttl_seconds=3600)
        result = ToolResult(ok=True, data={"text": "hello"}, tool="ocr")
        cache.put("key1", result, tool_name="ocr")
        cached = cache.get("key1")
        assert cached is not None
        assert cached.data == {"text": "hello"}


# ---------------------------------------------------------------------------
# LRU eviction tests
# ---------------------------------------------------------------------------


class TestLRUEviction:
    """Verify in-memory LRU eviction [BLK-124]."""

    def test_memory_lru_eviction(self, tmp_path: Path):
        cache = ToolCache(base_dir=tmp_path / "cache", max_memory_entries=3)
        for i in range(5):
            result = ToolResult(ok=True, data={"i": i}, tool="ocr")
            cache.put(f"key{i}", result, tool_name="ocr")

        # Only the last 3 should be in memory
        assert len(cache._memory) == 3
        assert "key4" in cache._memory
        assert "key3" in cache._memory
        assert "key2" in cache._memory
        assert "key0" not in cache._memory
        assert "key1" not in cache._memory

    def test_lru_order_on_get(self, tmp_path: Path):
        cache = ToolCache(base_dir=tmp_path / "cache", max_memory_entries=3)
        for i in range(3):
            result = ToolResult(ok=True, data={"i": i}, tool="ocr")
            cache.put(f"key{i}", result, tool_name="ocr")

        # Access key0 to make it recently used
        cache.get("key0")

        # Add a new key — should evict key1 (least recently used)
        result = ToolResult(ok=True, data={"i": 99}, tool="ocr")
        cache.put("key99", result, tool_name="ocr")

        assert "key0" in cache._memory  # was recently accessed
        assert "key1" not in cache._memory  # was LRU, evicted


# ---------------------------------------------------------------------------
# Disk persistence tests
# ---------------------------------------------------------------------------


class TestDiskPersistence:
    """Verify file-based cache persistence [BLK-124]."""

    def test_disk_persistence(self, tmp_path: Path):
        cache1 = ToolCache(base_dir=tmp_path / "cache")
        result = ToolResult(ok=True, data={"text": "persisted"}, tool="ocr")
        cache1.put("diskkey", result, tool_name="ocr")

        # Create a new cache instance pointing to the same directory
        cache2 = ToolCache(base_dir=tmp_path / "cache")
        cached = cache2.get("diskkey")
        assert cached is not None
        assert cached.data == {"text": "persisted"}

    def test_disk_file_structure(self, tmp_path: Path):
        cache = ToolCache(base_dir=tmp_path / "cache")
        result = ToolResult(ok=True, data={"text": "test"}, tool="ocr")
        key = "abcdef1234567890"
        cache.put(key, result, tool_name="ocr")

        # File should be at cache/ab/abcdef1234567890.json
        cache_file = tmp_path / "cache" / "ab" / f"{key}.json"
        assert cache_file.exists()


# ---------------------------------------------------------------------------
# Cache clear tests
# ---------------------------------------------------------------------------


class TestCacheClear:
    """Verify cache clear operation [BLK-124]."""

    def test_clear_removes_all_entries(self, tmp_cache: ToolCache):
        for i in range(3):
            result = ToolResult(ok=True, data={"i": i}, tool="ocr")
            tmp_cache.put(f"key{i}", result, tool_name="ocr")

        cleared = tmp_cache.clear()
        assert cleared >= 3
        assert len(tmp_cache._memory) == 0
        assert tmp_cache.get("key0") is None


# ---------------------------------------------------------------------------
# ToolSpec.cacheable tests
# ---------------------------------------------------------------------------


class TestToolSpecCacheable:
    """Verify ToolSpec.cacheable flag [BLK-124]."""

    def test_default_not_cacheable(self):
        spec = ToolSpec(name="test", description="test tool")
        assert spec.cacheable is False

    def test_cacheable_flag(self):
        spec = ToolSpec(name="test", description="test tool", cacheable=True)
        assert spec.cacheable is True


# ---------------------------------------------------------------------------
# ToolRegistry.call() caching tests
# ---------------------------------------------------------------------------


class TestRegistryCaching:
    """Verify ToolRegistry.call() uses cache for cacheable tools [BLK-124]."""

    def test_cacheable_tool_uses_cache(self, tmp_path: Path):
        import src.config as config_module

        old_enabled = config_module.settings.cache_enabled
        config_module.settings.cache_enabled = True

        try:
            reset_cache()
            call_count = 0

            def mock_ocr(image_path: str, lang: str = "en") -> ToolResult:
                nonlocal call_count
                call_count += 1
                return ToolResult(ok=True, data={"text": "mock"}, tool="ocr")

            registry = ToolRegistry()
            registry.register(
                ToolSpec(
                    name="ocr", description="test", cacheable=True, arg_schema={"image_path": str}
                ),
                mock_ocr,
            )

            img = tmp_path / "test.png"
            img.write_bytes(b"fake image")

            # First call — miss, invokes tool
            r1 = registry.call("ocr", image_path=str(img))
            assert r1.data == {"text": "mock"}
            assert call_count == 1

            # Second call — hit, does not invoke tool
            r2 = registry.call("ocr", image_path=str(img))
            assert r2.data == {"text": "mock"}
            assert call_count == 1  # still 1 — cached!
        finally:
            config_module.settings.cache_enabled = old_enabled
            reset_cache()

    def test_non_cacheable_tool_skips_cache(self, tmp_path: Path):
        import src.config as config_module

        old_enabled = config_module.settings.cache_enabled
        config_module.settings.cache_enabled = True

        try:
            reset_cache()
            call_count = 0

            def mock_tool(image_path: str) -> ToolResult:
                nonlocal call_count
                call_count += 1
                return ToolResult(ok=True, data={"n": call_count}, tool="test")

            registry = ToolRegistry()
            registry.register(
                ToolSpec(
                    name="test", description="test", cacheable=False, arg_schema={"image_path": str}
                ),
                mock_tool,
            )

            img = tmp_path / "test.png"
            img.write_bytes(b"fake image")

            r1 = registry.call("test", image_path=str(img))
            r2 = registry.call("test", image_path=str(img))
            assert call_count == 2  # not cached
            assert r1.data != r2.data  # different results
        finally:
            config_module.settings.cache_enabled = old_enabled
            reset_cache()

    def test_cache_disabled_skips_cache(self, tmp_path: Path):
        import src.config as config_module

        old_enabled = config_module.settings.cache_enabled
        config_module.settings.cache_enabled = False

        try:
            reset_cache()
            call_count = 0

            def mock_ocr(image_path: str) -> ToolResult:
                nonlocal call_count
                call_count += 1
                return ToolResult(ok=True, data={"n": call_count}, tool="ocr")

            registry = ToolRegistry()
            registry.register(
                ToolSpec(
                    name="ocr", description="test", cacheable=True, arg_schema={"image_path": str}
                ),
                mock_ocr,
            )

            img = tmp_path / "test.png"
            img.write_bytes(b"fake image")

            registry.call("ocr", image_path=str(img))
            registry.call("ocr", image_path=str(img))
            assert call_count == 2  # cache disabled, both invoked
        finally:
            config_module.settings.cache_enabled = old_enabled
            reset_cache()


# ---------------------------------------------------------------------------
# Cache version invalidation tests
# ---------------------------------------------------------------------------


class TestCacheVersion:
    """Verify cache version prefix invalidates keys [BLK-124]."""

    def test_version_change_invalidates(self, tmp_path: Path):
        import src.config as config_module

        old_version = config_module.settings.cache_version

        try:
            config_module.settings.cache_version = "v1"
            reset_cache()
            cache = ToolCache(base_dir=tmp_path / "cache")

            result = ToolResult(ok=True, data={"text": "v1 result"}, tool="ocr")
            key_v1 = compute_cache_key("ocr", image_bytes=b"test bytes")
            cache.put(key_v1, result, tool_name="ocr")
            assert cache.get(key_v1) is not None

            # Change version — old key should not match new key
            config_module.settings.cache_version = "v2"
            key_v2 = compute_cache_key("ocr", image_bytes=b"test bytes")
            assert key_v1 != key_v2
        finally:
            config_module.settings.cache_version = old_version
            reset_cache()


# ---------------------------------------------------------------------------
# Cached second run makes zero provider calls
# ---------------------------------------------------------------------------


class TestCachedSecondRun:
    """Verify a cached second run makes zero provider calls [BLK-124]."""

    def test_second_run_uses_cache(self, tmp_path: Path):
        import src.config as config_module

        old_enabled = config_module.settings.cache_enabled
        config_module.settings.cache_enabled = True

        try:
            reset_cache()
            call_count = 0

            def mock_ocr(image_path: str, lang: str = "en") -> ToolResult:
                nonlocal call_count
                call_count += 1
                return ToolResult(ok=True, data={"text": "cached"}, tool="ocr")

            registry = ToolRegistry()
            registry.register(
                ToolSpec(
                    name="ocr", description="test", cacheable=True, arg_schema={"image_path": str}
                ),
                mock_ocr,
            )

            img = tmp_path / "doc.png"
            img.write_bytes(b"document pixels")

            # First call — miss
            registry.call("ocr", image_path=str(img))
            assert call_count == 1

            # Second call — should be cached, zero new provider calls
            registry.call("ocr", image_path=str(img))
            assert call_count == 1  # zero new calls
        finally:
            config_module.settings.cache_enabled = old_enabled
            reset_cache()


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestCacheEndpoints:
    """Verify cache stats and clear API endpoints [BLK-124]."""

    @pytest.fixture
    def client(self, tmp_path: Path):
        import src.config as config_module
        import src.definitions.store as store_module

        old_auth = config_module.settings.auth_enabled
        old_store = store_module._store

        config_module.settings.auth_enabled = False
        store_module._store = store_module.DefinitionStore(base_dir=tmp_path / ".adep")

        reset_cache()
        from src.api.main import create_app

        app = create_app()
        yield TestClient(app)

        config_module.settings.auth_enabled = old_auth
        store_module._store = old_store
        reset_cache()

    def test_cache_stats_endpoint(self, client):
        resp = client.get("/api/v1/admin/cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "hits" in data
        assert "misses" in data
        assert "memory_entries" in data
        assert "disk_entries" in data
        assert "hit_rate" in data

    def test_clear_cache_endpoint(self, client):
        resp = client.delete("/api/v1/admin/cache")
        assert resp.status_code == 200
        data = resp.json()
        assert "cleared" in data
        assert data["cleared"] >= 0


# ---------------------------------------------------------------------------
# Grounding preservation tests (SCRUM-480)
# ---------------------------------------------------------------------------


class TestGroundingPreservation:
    """Verify grounding is not stripped during cache serialization [SCRUM-480]."""

    def test_grounding_survives_memory_roundtrip(self, tmp_cache: ToolCache):
        """Grounding should survive a put → get cycle in memory."""
        grounding = Grounding(bbox=(10, 20, 100, 200), page=0, source_tool="ocr", confidence=0.95)
        result = ToolResult(ok=True, data={"text": "hello"}, tool="ocr", grounding=grounding)
        tmp_cache.put("key_g", result, tool_name="ocr")
        cached = tmp_cache.get("key_g")
        assert cached is not None
        assert cached.grounding is not None
        assert cached.grounding.bbox == (10, 20, 100, 200)
        assert cached.grounding.page == 0
        assert cached.grounding.source_tool == "ocr"
        assert cached.grounding.confidence == 0.95

    def test_grounding_survives_disk_roundtrip(self, tmp_path: Path):
        """Grounding should survive serialization to disk and back."""
        cache1 = ToolCache(base_dir=tmp_path / "cache")
        grounding = Grounding(bbox=(5, 10, 50, 80), page=2, source_tool="vlm", confidence=0.87)
        result = ToolResult(ok=True, data={"text": "disk"}, tool="vlm", grounding=grounding)
        cache1.put("disk_g", result, tool_name="vlm")

        # New cache instance reads from disk
        cache2 = ToolCache(base_dir=tmp_path / "cache")
        cached = cache2.get("disk_g")
        assert cached is not None
        assert cached.grounding is not None
        assert cached.grounding.bbox == (5, 10, 50, 80)
        assert cached.grounding.page == 2
        assert cached.grounding.source_tool == "vlm"
        assert cached.grounding.confidence == 0.87

    def test_none_grounding_stays_none(self, tmp_cache: ToolCache):
        """Result without grounding should return None grounding from cache."""
        result = ToolResult(ok=True, data={"text": "no grounding"}, tool="ocr")
        tmp_cache.put("key_ng", result, tool_name="ocr")
        cached = tmp_cache.get("key_ng")
        assert cached is not None
        assert cached.grounding is None
