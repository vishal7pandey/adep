"""Tests for BLK-292: BLK-ID Registry prevents duplicate IDs from parallel audits.

Verifies that:
1. next_blk_id() atomically allocates sequential IDs
2. Concurrent calls don't produce duplicates
3. register_existing() bootstraps the registry
4. validate() detects unregistered BLK-IDs
5. Atomic file writes prevent corruption
"""

from __future__ import annotations

import json
import threading
import tempfile
from pathlib import Path

import pytest

from scripts.blk_id_registry import BlkIdRegistry


class TestBlkIdRegistry:
    """BLK-292: Registry must prevent duplicate BLK-ID assignment."""

    @pytest.fixture
    def registry(self, tmp_path: Path) -> BlkIdRegistry:
        """Create a registry with a temp file."""
        return BlkIdRegistry(registry_path=tmp_path / "blk_registry.json")

    def test_next_blk_id_returns_sequential_ids(self, registry: BlkIdRegistry):
        """next_blk_id() must return sequential IDs starting from BLK-001."""
        id1 = registry.next_blk_id("First bug", "src/test.py")
        id2 = registry.next_blk_id("Second bug", "src/test.py")
        id3 = registry.next_blk_id("Third bug", "src/test.py")

        assert id1 == "BLK-001"
        assert id2 == "BLK-002"
        assert id3 == "BLK-003"

    def test_next_blk_id_stores_metadata(self, registry: BlkIdRegistry):
        """next_blk_id() must store description and source_file."""
        blk_id = registry.next_blk_id(
            "Fix provider validation",
            "src/config.py",
            tags=["config", "validation"],
        )

        entry = registry.get(blk_id)
        assert entry is not None
        assert entry["description"] == "Fix provider validation"
        assert entry["source_file"] == "src/config.py"
        assert entry["tags"] == ["config", "validation"]
        assert "assigned_at" in entry

    def test_concurrent_allocation_no_duplicates(self, registry: BlkIdRegistry):
        """Parallel calls to next_blk_id() must not produce duplicate IDs."""
        results: list[str] = []
        results_lock = threading.Lock()

        def allocate():
            blk_id = registry.next_blk_id("Concurrent bug", "src/test.py")
            with results_lock:
                results.append(blk_id)

        threads = [threading.Thread(target=allocate) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        assert len(set(results)) == 20, f"Duplicate IDs found: {results}"

    def test_concurrent_allocation_sequential(self, registry: BlkIdRegistry):
        """Concurrently allocated IDs must cover a contiguous range."""
        results: list[str] = []
        results_lock = threading.Lock()

        def allocate():
            blk_id = registry.next_blk_id("Concurrent bug", "src/test.py")
            with results_lock:
                results.append(blk_id)

        threads = [threading.Thread(target=allocate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        nums = sorted(int(r.split("-")[1]) for r in results)
        assert nums == list(range(1, 11))

    def test_register_existing_advances_next_id(self, registry: BlkIdRegistry):
        """register_existing() must advance next_id past the highest registered ID."""
        registry.register_existing("BLK-084", "Audit logging", "src/agent/guardrails/audit_logging.py")
        registry.register_existing("BLK-150", "Webhook get_raw", "src/agent/webhooks.py")

        next_id = registry.next_blk_id("New bug", "src/test.py")
        assert next_id == "BLK-151"

    def test_register_existing_returns_false_for_duplicate(self, registry: BlkIdRegistry):
        """register_existing() must return False if the ID is already registered."""
        assert registry.register_existing("BLK-084", "First", "src/a.py")
        assert not registry.register_existing("BLK-084", "Second", "src/b.py")

    def test_registry_persists_to_disk(self, registry: BlkIdRegistry, tmp_path: Path):
        """Registry must persist entries to the JSON file."""
        registry.next_blk_id("Test bug", "src/test.py")

        data = json.loads((tmp_path / "blk_registry.json").read_text())
        assert "next_id" in data
        assert "entries" in data
        assert "BLK-001" in data["entries"]

    def test_registry_survives_corrupt_file(self, tmp_path: Path):
        """Registry must handle corrupt JSON gracefully."""
        registry_path = tmp_path / "blk_registry.json"
        registry_path.write_text("CORRUPT{NOT}JSON")

        registry = BlkIdRegistry(registry_path=registry_path)
        blk_id = registry.next_blk_id("After corruption", "src/test.py")
        assert blk_id == "BLK-001"

    def test_validate_detects_unregistered_ids(self, registry: BlkIdRegistry, tmp_path: Path):
        """validate() must flag BLK-IDs in the codebase that aren't registered."""
        # Create a temp file with a BLK-ID
        test_file = tmp_path / "test_code.py"
        test_file.write_text('# BLK-999: Some unregistered bug\n')

        issues = registry.validate(scan_root=str(tmp_path))
        assert len(issues) > 0
        assert any(i["blk_id"] == "BLK-999" for i in issues)

    def test_validate_passes_for_registered_ids(self, registry: BlkIdRegistry, tmp_path: Path):
        """validate() must not flag BLK-IDs that are registered."""
        registry.register_existing("BLK-999", "Registered bug", "test.py")

        test_file = tmp_path / "test_code.py"
        test_file.write_text('# BLK-999: Some registered bug\n')

        issues = registry.validate(scan_root=str(tmp_path))
        assert len(issues) == 0

    def test_atomic_write_does_not_corrupt(self, registry: BlkIdRegistry):
        """Rapid successive writes must not corrupt the registry file."""
        for i in range(50):
            registry.next_blk_id(f"Bulk bug {i}", "src/test.py")

        all_entries = registry.list_all()
        assert len(all_entries) == 50
        # Verify all IDs are unique
        ids = list(all_entries.keys())
        assert len(ids) == len(set(ids))
