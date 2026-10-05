"""Tests for DefinitionStore [BLK-017, TS]."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.definitions.base import AgentDefinition
from src.definitions.store import DefinitionStore


@pytest.fixture
def store(tmp_path: Path) -> DefinitionStore:
    """Create a temporary store for testing."""
    return DefinitionStore(base_dir=tmp_path / ".adep")


class TestDefinitionStore:
    """Verify CRUD operations for all entity types."""

    def test_creates_adep_dir_on_init(self, tmp_path: Path):
        base = tmp_path / ".adep"
        DefinitionStore(base_dir=base)
        assert base.exists()
        assert (base / "definitions").exists()
        assert (base / "skills").exists()
        assert (base / "templates").exists()
        assert (base / "runs").exists()

    def test_create_and_read_definition(self, store: DefinitionStore):
        d = AgentDefinition(
            id="def-test",
            name="Test",
            skill_ref="invoice",
            template_ref="invoice",
        )
        store.create_definition(d)
        result = store.get_definition("def-test")
        assert result["id"] == "def-test"
        assert result["name"] == "Test"

    def test_create_duplicate_raises(self, store: DefinitionStore):
        d = AgentDefinition(id="def-dup", name="Dup", skill_ref="x", template_ref="y")
        store.create_definition(d)
        with pytest.raises(FileExistsError):
            store.create_definition(d)

    def test_read_missing_raises(self, store: DefinitionStore):
        with pytest.raises(FileNotFoundError):
            store.get_definition("nonexistent")

    def test_update_definition(self, store: DefinitionStore):
        d = AgentDefinition(id="def-upd", name="Original", skill_ref="x", template_ref="y")
        store.create_definition(d)
        store.update_definition("def-upd", {"id": "def-upd", "name": "Updated"})
        result = store.get_definition("def-upd")
        assert result["name"] == "Updated"

    def test_delete_definition(self, store: DefinitionStore):
        d = AgentDefinition(id="def-del", name="Delete", skill_ref="x", template_ref="y")
        store.create_definition(d)
        store.delete_definition("def-del")
        assert not store.exists("definitions", "def-del")

    def test_list_definitions_includes_prebuilt(self, store: DefinitionStore):
        for i in range(3):
            d = AgentDefinition(id=f"def-{i}", name=f"Def {i}", skill_ref="x", template_ref="y")
            store.create_definition(d)
        defs = store.list_definitions()
        # 3 user-created + 18 prebuilt [BLK-159]
        assert len(defs) >= 21
        ids = {d["id"] for d in defs}
        assert "def-0" in ids
        assert "def-1" in ids
        assert "def-2" in ids

    def test_create_and_read_skill(self, store: DefinitionStore):
        store.create_skill("sk-test", {"id": "sk-test", "name": "Test Skill"})
        result = store.get_skill("sk-test")
        assert result["name"] == "Test Skill"

    def test_list_skills_includes_prebuilt(self, store: DefinitionStore):
        store.create_skill("sk-1", {"id": "sk-1", "name": "Skill 1"})
        store.create_skill("sk-2", {"id": "sk-2", "name": "Skill 2"})
        skills = store.list_skills()
        # 2 user-created + 19 prebuilt [BLK-159]
        assert len(skills) >= 21
        ids = {s["id"] for s in skills}
        assert "sk-1" in ids
        assert "sk-2" in ids

    def test_create_and_read_template(self, store: DefinitionStore):
        store.create_template(
            "tmpl-test",
            {
                "id": "tmpl-test",
                "name": "Test Template",
                "fields": [{"name": "total", "type": "number", "required": True}],
            },
        )
        result = store.get_template("tmpl-test")
        assert result["name"] == "Test Template"
        assert len(result["fields"]) == 1

    def test_save_and_get_run(self, store: DefinitionStore):
        store.save_run("run-1", {"id": "run-1", "status": "completed"})
        result = store.get_run("run-1")
        assert result["status"] == "completed"

    def test_update_run(self, store: DefinitionStore):
        store.save_run("run-2", {"id": "run-2", "status": "running"})
        store.update_run("run-2", {"id": "run-2", "status": "completed"})
        result = store.get_run("run-2")
        assert result["status"] == "completed"

    def test_list_runs(self, store: DefinitionStore):
        store.save_run("run-a", {"id": "run-a"})
        store.save_run("run-b", {"id": "run-b"})
        runs = store.list_runs()
        assert len(runs) == 2

    def test_delete_skill(self, store: DefinitionStore):
        store.create_skill("sk-del", {"id": "sk-del", "name": "Delete"})
        store.delete_skill("sk-del")
        assert not store.exists("skills", "sk-del")

    def test_delete_template(self, store: DefinitionStore):
        store.create_template("tmpl-del", {"id": "tmpl-del", "name": "Delete"})
        store.delete_template("tmpl-del")
        assert not store.exists("templates", "tmpl-del")
