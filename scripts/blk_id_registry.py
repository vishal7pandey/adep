"""BLK-ID Registry — atomic, thread-safe ID assignment [BLK-292].

Problem: Two independent audit passes ran concurrently and both assigned
BLK-IDs from the same sequence starting at BLK-177, producing duplicates.

Solution: A file-based registry (`.adep/blk_registry.json`) that:
1. Tracks all assigned BLK-IDs with metadata (description, file, timestamp).
2. Provides atomic `next_blk_id()` for concurrent-safe allocation.
3. Validates the codebase for duplicate or unregistered BLK-IDs.

Usage:
    from scripts.blk_id_registry import BlkIdRegistry

    registry = BlkIdRegistry()
    new_id = registry.next_blk_id(
        description="Fix provider config validation",
        source_file="src/config.py",
    )
    # => "BLK-293"

    registry.validate()  # Raises on duplicate/unregistered IDs
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BLK_PATTERN = re.compile(r"BLK-(\d{3})")
DEFAULT_REGISTRY_PATH = Path(".adep") / "blk_registry.json"
_LOCK = threading.Lock()


class BlkIdRegistry:
    """Thread-safe BLK-ID registry with atomic allocation [BLK-292].

    The registry file uses a temporary-file-rename pattern for atomic writes,
    preventing race conditions when two processes allocate IDs concurrently.
    """

    def __init__(self, registry_path: Path | str | None = None) -> None:
        self.registry_path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = _LOCK

    def _load(self) -> dict[str, Any]:
        """Load the registry from disk."""
        if not self.registry_path.exists():
            return {"next_id": 1, "entries": {}}
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
            if "next_id" not in data:
                data["next_id"] = 1
            if "entries" not in data:
                data["entries"] = {}
            return data
        except (json.JSONDecodeError, OSError):
            return {"next_id": 1, "entries": {}}

    def _save_atomic(self, data: dict[str, Any]) -> None:
        """Atomically write the registry using temp-file rename."""
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.registry_path.parent),
            suffix=".tmp",
            prefix="blk_registry_",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
                f.write("\n")
            os.replace(tmp_path, str(self.registry_path))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def next_blk_id(
        self,
        description: str,
        source_file: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """Atomically allocate the next BLK-ID [BLK-292].

        Args:
            description: Human-readable description of the bug/issue.
            source_file: File where the BLK-ID will be used.
            tags: Optional tags for categorization.

        Returns:
            The allocated BLK-ID string (e.g. "BLK-293").

        Raises:
            RuntimeError: If the registry cannot be updated after retries.
        """
        tags = tags or []
        max_retries = 3

        with self._lock:
            for attempt in range(max_retries):
                data = self._load()
                next_num = data["next_id"]
                blk_id = f"BLK-{next_num:03d}"

                # Skip if somehow already in entries (corrupt registry)
                if blk_id in data["entries"]:
                    data["next_id"] = next_num + 1
                    continue

                data["entries"][blk_id] = {
                    "description": description,
                    "source_file": source_file,
                    "tags": tags,
                    "assigned_at": datetime.now(timezone.utc).isoformat(),
                }
                data["next_id"] = next_num + 1

                try:
                    self._save_atomic(data)
                    return blk_id
                except OSError:
                    if attempt < max_retries - 1:
                        continue
                    raise RuntimeError(
                        f"Failed to save BLK-ID registry after {max_retries} attempts"
                    )

            raise RuntimeError("Could not allocate a unique BLK-ID")

    def register_existing(
        self,
        blk_id: str,
        description: str,
        source_file: str = "",
        tags: list[str] | None = None,
    ) -> bool:
        """Register an existing BLK-ID in the registry.

        Useful for bootstrapping the registry from an existing codebase.

        Args:
            blk_id: The BLK-ID string (e.g. "BLK-084").
            description: Human-readable description.
            source_file: File where the BLK-ID is used.
            tags: Optional tags.

        Returns:
            True if newly registered, False if already present.
        """
        tags = tags or []
        with self._lock:
            data = self._load()
            if blk_id in data["entries"]:
                return False

            num = int(blk_id.split("-")[1])
            data["entries"][blk_id] = {
                "description": description,
                "source_file": source_file,
                "tags": tags,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
                "imported": True,
            }
            # Advance next_id past the highest registered ID
            if num >= data["next_id"]:
                data["next_id"] = num + 1

            self._save_atomic(data)
            return True

    def get(self, blk_id: str) -> dict[str, Any] | None:
        """Look up a BLK-ID in the registry."""
        data = self._load()
        return data["entries"].get(blk_id)

    def list_all(self) -> dict[str, dict[str, Any]]:
        """List all registered BLK-IDs."""
        data = self._load()
        return data["entries"]

    def validate(self, scan_root: str = ".") -> list[dict[str, Any]]:
        """Scan the codebase for BLK-IDs not in the registry [BLK-292].

        Args:
            scan_root: Root directory to scan.

        Returns:
            List of validation issues (unregistered BLK-IDs).
        """
        from scripts.scan_blk_ids import scan_blk_ids

        scan_result = scan_blk_ids(scan_root)
        registered = set(self._load()["entries"].keys())
        issues = []

        for blk_id, locations in scan_result["file_locations"].items():
            if blk_id not in registered:
                issues.append(
                    {
                        "blk_id": blk_id,
                        "issue": "unregistered",
                        "locations": locations,
                    }
                )

        return issues

    def find_true_duplicates(self, scan_root: str = ".") -> list[dict[str, Any]]:
        """Find BLK-IDs that appear in unrelated files (true duplicates).

        A BLK-ID appearing in an impl file and its test file is expected.
        A BLK-ID appearing in two completely unrelated files is a duplicate.

        Args:
            scan_root: Root directory to scan.

        Returns:
            List of duplicate BLK-IDs with their locations.
        """
        from scripts.scan_blk_ids import scan_blk_ids

        scan_result = scan_blk_ids(scan_root)
        duplicates = []

        for blk_id, locations in scan_result["file_locations"].items():
            # Get unique file paths (ignoring line numbers)
            unique_files = {loc[0] for loc in locations}
            # If the BLK-ID appears in more than 3 unrelated files, flag it
            # (1 impl + 1 test + 1 test docstring = 3 is normal)
            if len(unique_files) > 3:
                duplicates.append(
                    {
                        "blk_id": blk_id,
                        "file_count": len(unique_files),
                        "locations": locations,
                    }
                )

        return duplicates
