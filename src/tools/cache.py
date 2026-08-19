"""Content-addressed tool result cache [BLK-124].

Two-level cache: bounded in-memory LRU + file-based store under `.adep/cache/`.

Cache key is derived from:
    sha256(cache_version + tool_name + sha256(image_bytes) + canonical_json(params) + provider)

Critical: hashes the **image region bytes**, not file paths or bbox coordinates.
Two different bboxes that crop to identical pixels hit the same cache entry.

Cache is disable-able via `settings.cache_enabled` for tests that assert
provider call counts.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import settings
from src.tools.base import Grounding, ToolResult

logger = logging.getLogger(__name__)


def _canonical_json(obj: Any) -> str:
    """Serialize to canonical JSON with sorted keys for stable hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _hash_image(image_path: str) -> str:
    """Hash the raw bytes of an image file for content-addressed caching."""
    h = hashlib.sha256()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_cache_key(
    tool_name: str,
    image_path: str | None = None,
    params: dict[str, Any] | None = None,
    provider: str = "",
    image_bytes: bytes | None = None,
) -> str:
    """Compute a content-addressed cache key [BLK-124].

    Args:
        tool_name: Name of the tool.
        image_path: Path to the input image (will be hashed by bytes).
            Mutually exclusive with image_bytes.
        params: Tool parameters dict (canonical JSON hashed).
        provider: Provider name + model version string.
        image_bytes: Raw image bytes (alternative to image_path).

    Returns:
        Hex SHA-256 cache key string.
    """
    if image_path is not None:
        image_hash = _hash_image(image_path)
    elif image_bytes is not None:
        image_hash = hashlib.sha256(image_bytes).hexdigest()
    else:
        image_hash = "no-image"

    params_json = _canonical_json(params or {})
    raw = f"{settings.cache_version}:{tool_name}:{image_hash}:{params_json}:{provider}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class CacheEntry:
    """A single cache entry with metadata.

    Attributes:
        result: The cached ToolResult.
        created_at: Unix timestamp when the entry was created.
        last_used_at: Unix timestamp of last access.
        hit_count: Number of cache hits.
        tool_name: Name of the tool that produced this result.
        size_bytes: Approximate size of the serialized result.
    """

    result: ToolResult
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    hit_count: int = 0
    tool_name: str = ""
    size_bytes: int = 0


class ToolCache:
    """Two-level tool result cache: in-memory LRU + file store [BLK-124].

    Attributes:
        base_dir: Directory for file-based cache storage.
        memory_cache: Bounded LRU OrderedDict for in-memory entries.
        stats: Cache statistics (hits, misses, entries, size).
    """

    def __init__(
        self,
        base_dir: str | Path | None = None,
        max_memory_entries: int | None = None,
        ttl_seconds: int | None = None,
        max_size_bytes: int | None = None,
    ) -> None:
        if base_dir is None:
            base_dir = Path.cwd() / ".adep" / "cache"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.max_memory = max_memory_entries or settings.cache_memory_entries
        self.ttl = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_seconds
        self.max_size = max_size_bytes or settings.cache_max_size_bytes

        self._memory: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def _file_path(self, key: str) -> Path:
        """Get the file path for a cache key (two-level directory)."""
        return self.base_dir / key[:2] / f"{key}.json"

    def _serialize_entry(self, entry: CacheEntry) -> dict[str, Any]:
        """Serialize a CacheEntry to a JSON-compatible dict."""
        tr = entry.result
        grounding = None
        if tr.grounding is not None:
            g = tr.grounding
            grounding = {
                "bbox": list(g.bbox),
                "page": g.page,
                "region_id": g.region_id,
                "source_tool": g.source_tool,
                "confidence": g.confidence,
            }
        return {
            "ok": tr.ok,
            "data": tr.data,
            "error": tr.error,
            "tool": tr.tool,
            "grounding": grounding,
            "cost": tr.cost,
            "created_at": entry.created_at,
            "last_used_at": entry.last_used_at,
            "hit_count": entry.hit_count,
            "tool_name": entry.tool_name,
            "size_bytes": entry.size_bytes,
        }

    def _deserialize_entry(self, data: dict[str, Any]) -> CacheEntry:
        """Deserialize a dict back to a CacheEntry."""
        grounding = None
        g = data.get("grounding")
        if g is not None:
            grounding = Grounding(
                bbox=tuple(g.get("bbox", (0, 0, 0, 0))),
                page=g.get("page", 0),
                region_id=g.get("region_id"),
                source_tool=g.get("source_tool", ""),
                confidence=g.get("confidence", 0.0),
            )
        tr = ToolResult(
            ok=data.get("ok", True),
            data=data.get("data"),
            error=data.get("error", ""),
            tool=data.get("tool", ""),
            grounding=grounding,
            cost=data.get("cost", {}),
        )
        return CacheEntry(
            result=tr,
            created_at=data.get("created_at", time.time()),
            last_used_at=data.get("last_used_at", time.time()),
            hit_count=data.get("hit_count", 0),
            tool_name=data.get("tool_name", ""),
            size_bytes=data.get("size_bytes", 0),
        )

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if a cache entry has expired."""
        return (time.time() - entry.created_at) > self.ttl

    def _evict_memory(self) -> None:
        """Evict LRU entries from memory if over capacity."""
        while len(self._memory) > self.max_memory:
            _, entry = self._memory.popitem(last=False)
            self._stats["evictions"] += 1
            logger.debug("Cache LRU evict: %s", entry.tool_name)

    def _evict_disk(self) -> None:
        """Evict entries from disk if total size exceeds max."""
        total_size = 0
        entries: list[tuple[Path, float, int]] = []
        for shard in self.base_dir.iterdir():
            if not shard.is_dir():
                continue
            for cache_file in shard.glob("*.json"):
                try:
                    stat = cache_file.stat()
                    total_size += stat.st_size
                    entries.append((cache_file, stat.st_mtime, stat.st_size))
                except OSError:
                    continue

        if total_size <= self.max_size:
            return

        # Sort by last_used_at (mtime) ascending — evict oldest first
        entries.sort(key=lambda e: e[1])
        for path, _, size in entries:
            if total_size <= self.max_size:
                break
            try:
                path.unlink()
                total_size -= size
                self._stats["evictions"] += 1
                logger.debug("Cache disk evict: %s", path.name)
            except OSError:
                continue

    def get(self, key: str) -> ToolResult | None:
        """Get a cached result by key.

        Returns None on miss or expiry.
        """
        # Check memory first
        if key in self._memory:
            entry = self._memory[key]
            if self._is_expired(entry):
                del self._memory[key]
                self._stats["misses"] += 1
                logger.debug("Cache miss (expired in memory): %s..", key[:8])
                return None
            # Move to end (most recently used)
            self._memory.move_to_end(key)
            entry.hit_count += 1
            entry.last_used_at = time.time()
            self._stats["hits"] += 1
            logger.debug("Cache hit (memory): %s..", key[:8])
            return entry.result

        # Check disk
        file_path = self._file_path(key)
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                entry = self._deserialize_entry(data)
                if self._is_expired(entry):
                    file_path.unlink(missing_ok=True)
                    self._stats["misses"] += 1
                    logger.debug("Cache miss (expired on disk): %s..", key[:8])
                    return None
                # Promote to memory
                entry.hit_count += 1
                entry.last_used_at = time.time()
                self._memory[key] = entry
                self._evict_memory()
                self._stats["hits"] += 1
                logger.debug("Cache hit (disk): %s..", key[:8])
                return entry.result
            except (json.JSONDecodeError, KeyError, OSError) as e:
                logger.warning("Cache read error for %s..: %s", key[:8], e)

        self._stats["misses"] += 1
        logger.debug("Cache miss: %s..", key[:8])
        return None

    def put(
        self,
        key: str,
        result: ToolResult,
        tool_name: str = "",
        image_path: str | None = None,
    ) -> None:
        """Store a result in the cache.

        Args:
            key: Cache key from compute_cache_key.
            result: The ToolResult to cache.
            tool_name: Name of the tool.
            image_path: Optional image path for size estimation.
        """
        # Estimate size
        size_bytes = 0
        if image_path:
            try:
                size_bytes = os.path.getsize(image_path)
            except OSError:
                pass
        if size_bytes == 0:
            size_bytes = len(_canonical_json(result.data)) if result.data else 0

        entry = CacheEntry(
            result=result,
            tool_name=tool_name,
            size_bytes=size_bytes,
        )

        # Store in memory
        self._memory[key] = entry
        self._evict_memory()

        # Store on disk
        file_path = self._file_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            serialized = self._serialize_entry(entry)
            file_path.write_text(
                json.dumps(serialized, default=str, indent=2),
                encoding="utf-8",
            )
        except (OSError, TypeError) as e:
            logger.warning("Cache write error for %s..: %s", key[:8], e)

        # Check disk size eviction
        self._evict_disk()

    def clear(self) -> int:
        """Clear all cache entries (memory + disk).

        Returns:
            Number of entries cleared.
        """
        count = len(self._memory)
        self._memory.clear()

        cleared = 0
        for shard in self.base_dir.iterdir():
            if not shard.is_dir():
                continue
            for cache_file in shard.glob("*.json"):
                try:
                    cache_file.unlink()
                    cleared += 1
                except OSError:
                    continue

        logger.info("Cache cleared: %d memory, %d disk entries", count, cleared)
        return count + cleared

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, evictions, memory_entries, disk_entries,
            total_size_bytes, hit_rate.
        """
        disk_count = 0
        disk_size = 0
        for shard in self.base_dir.iterdir():
            if not shard.is_dir():
                continue
            for cache_file in shard.glob("*.json"):
                try:
                    stat = cache_file.stat()
                    disk_count += 1
                    disk_size += stat.st_size
                except OSError:
                    continue

        hits = self._stats["hits"]
        misses = self._stats["misses"]
        total = hits + misses
        hit_rate = (hits / total) if total > 0 else 0.0

        return {
            "hits": hits,
            "misses": misses,
            "evictions": self._stats["evictions"],
            "memory_entries": len(self._memory),
            "disk_entries": disk_count,
            "total_size_bytes": disk_size,
            "hit_rate": round(hit_rate, 4),
        }


# Module-level singleton
_cache: ToolCache | None = None


def get_cache() -> ToolCache:
    """Get the singleton ToolCache instance."""
    global _cache
    if _cache is None:
        _cache = ToolCache()
    return _cache


def reset_cache() -> None:
    """Reset the singleton (for testing)."""
    global _cache
    _cache = None
