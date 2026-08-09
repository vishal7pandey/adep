"""Tests for BLK-159: Store should always include prebuilt content.

Verifies that list_* and get_* methods merge prebuilt content with on-disk
content, with disk taking precedence.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.definitions.base import AgentDefinition
from src.definitions.store import DefinitionStore


@pytest.fixture
def store(tmp_path: Path) -> DefinitionStore:
    """Create a store with a fresh .adep directory (no disk files)."""
    return DefinitionStore(base_dir=tmp_path / ".adep")


class TestPrebuiltMerge:
    """Verify prebuilt content is merged into store read results [BLK-159]."""

    def test_list_definitions_includes_prebuilt(self, store: DefinitionStore):
        """Fresh .adep/ → list_definitions() returns 18 prebuilt definitions."""
        defs = store.list_definitions()
        ids = {d["id"] for d in defs}
        assert "def-trade-finance-scrutiny" in ids
        assert "def-boq-estimator" in ids
        assert "def-pnid-to-dexpi" in ids
        assert len(defs) >= 18

    def test_list_skills_includes_prebuilt(self, store: DefinitionStore):
        """Fresh .adep/ → list_skills() returns 19 prebuilt skills."""
        skills = store.list_skills()
        ids = {s["id"] for s in skills}
        assert "invoice" in ids
        assert "trade_finance_scrutiny" in ids
        assert "pid_to_dexpi" in ids
        assert len(skills) >= 19

    def test_list_templates_includes_prebuilt(self, store: DefinitionStore):
        """Fresh .adep/ → list_templates() returns 19 prebuilt templates."""
        templates = store.list_templates()
        ids = {t["id"] for t in templates}
        assert "invoice" in ids
        assert "trade_finance_mt700" in ids
        assert "pid_to_dexpi" in ids
        assert len(templates) >= 19

    def test_get_definition_prebuilt_fallback(self, store: DefinitionStore):
        """get_definition returns prebuilt when not on disk."""
        result = store.get_definition("def-trade-finance-scrutiny")
        assert result["id"] == "def-trade-finance-scrutiny"
        assert result["name"] == "Trade Finance Scrutiny (MT700)"

    def test_get_skill_prebuilt_fallback(self, store: DefinitionStore):
        """get_skill returns prebuilt when not on disk."""
        result = store.get_skill("invoice")
        assert result["id"] == "invoice"

    def test_get_template_prebuilt_fallback(self, store: DefinitionStore):
        """get_template returns prebuilt when not on disk."""
        result = store.get_template("invoice")
        assert result["id"] == "invoice"

    def test_disk_takes_precedence_over_prebuilt(self, store: DefinitionStore):
        """Disk version of a definition takes precedence over prebuilt."""
        # Write a modified version of a prebuilt definition to disk
        def_path = store.base_dir / "definitions" / "def-trade-finance-scrutiny.json"
        def_path.parent.mkdir(parents=True, exist_ok=True)
        modified = {
            "id": "def-trade-finance-scrutiny",
            "name": "Custom Trade Finance",
            "version": "2.0.0",
            "skill_id": "trade_finance_scrutiny",
            "template_id": "trade_finance_mt700",
            "tool_names": ["ocr"],
            "agent_config": {"max_cycles_per_field": 3},
        }
        def_path.write_text(json.dumps(modified), encoding="utf-8")

        result = store.get_definition("def-trade-finance-scrutiny")
        assert result["name"] == "Custom Trade Finance"
        assert result["version"] == "2.0.0"

        # Also verify in list
        defs = store.list_definitions()
        tf = [d for d in defs if d["id"] == "def-trade-finance-scrutiny"][0]
        assert tf["name"] == "Custom Trade Finance"

    def test_user_created_definition_alongside_prebuilt(self, store: DefinitionStore):
        """User-created definition appears alongside prebuilt ones."""
        d = AgentDefinition(
            id="def-custom-001",
            name="My Custom Definition",
            skill_ref="invoice",
            template_ref="invoice",
        )
        store.create_definition(d)

        defs = store.list_definitions()
        ids = {d["id"] for d in defs}
        assert "def-custom-001" in ids
        assert "def-trade-finance-scrutiny" in ids  # prebuilt still there

    def test_get_nonexistent_definition_raises(self, store: DefinitionStore):
        """get_definition raises FileNotFoundError for truly nonexistent ID."""
        with pytest.raises(FileNotFoundError):
            store.get_definition("def-does-not-exist")

    def test_get_nonexistent_skill_raises(self, store: DefinitionStore):
        """get_skill raises FileNotFoundError for truly nonexistent ID."""
        with pytest.raises(FileNotFoundError):
            store.get_skill("nonexistent-skill")

    def test_get_nonexistent_template_raises(self, store: DefinitionStore):
        """get_template raises FileNotFoundError for truly nonexistent ID."""
        with pytest.raises(FileNotFoundError):
            store.get_template("nonexistent-template")

    def test_list_definitions_sorted_by_id(self, store: DefinitionStore):
        """List results are sorted by ID."""
        defs = store.list_definitions()
        ids = [d["id"] for d in defs]
        assert ids == sorted(ids)

    def test_list_skills_sorted_by_id(self, store: DefinitionStore):
        """List results are sorted by ID."""
        skills = store.list_skills()
        ids = [s["id"] for s in skills]
        assert ids == sorted(ids)

    def test_list_templates_sorted_by_id(self, store: DefinitionStore):
        """List results are sorted by ID."""
        templates = store.list_templates()
        ids = [t["id"] for t in templates]
        assert ids == sorted(ids)

    def test_no_duplicate_ids_in_merged_list(self, store: DefinitionStore):
        """Merged list should not have duplicate IDs."""
        # Create a disk file with same ID as a prebuilt
        d = AgentDefinition(
            id="def-trade-finance-scrutiny",
            name="Disk Version",
            skill_ref="trade_finance_scrutiny",
            template_ref="trade_finance_mt700",
        )
        store.create_definition(d)

        defs = store.list_definitions()
        ids = [d["id"] for d in defs]
        assert len(ids) == len(set(ids)), "Duplicate IDs in merged list"

    def test_prebuilt_count_definitions(self, store: DefinitionStore):
        """Verify exact prebuilt definition count."""
        defs = store.list_definitions()
        assert len(defs) == 21

    def test_prebuilt_count_skills(self, store: DefinitionStore):
        """Verify exact prebuilt skill count."""
        skills = store.list_skills()
        assert len(skills) == 21

    def test_prebuilt_count_templates(self, store: DefinitionStore):
        """Verify exact prebuilt template count."""
        templates = store.list_templates()
        assert len(templates) == 21


class TestSeedStoreRemoved:
    """Verify seed_store and register_prebuilt_definitions are removed [BLK-159]."""

    def test_seed_store_not_importable(self):
        """seed_store should not be importable from prebuilt."""
        from src.definitions import prebuilt
        assert not hasattr(prebuilt, "seed_store")

    def test_register_prebuilt_not_importable(self):
        """register_prebuilt_definitions should not be importable."""
        from src.definitions import prebuilt
        assert not hasattr(prebuilt, "register_prebuilt_definitions")

    def test_scripts_seed_deleted(self):
        """scripts/seed.py should not exist."""
        assert not Path("scripts/seed.py").exists()
