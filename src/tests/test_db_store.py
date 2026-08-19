"""Tests for Database-backed Definition Store (v2) [BLK-036]."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.definitions.db_store import DatabaseDefinitionStore
from src.definitions.base import AgentDefinition, AgentConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_store(tmp_path):
    """Create a temporary DB store."""
    return DatabaseDefinitionStore(db_path=tmp_path / "test_store.db")


@pytest.fixture
def file_store(tmp_path):
    """Create a temporary file-based store for migration tests."""
    from src.definitions.store import DefinitionStore
    return DefinitionStore(base_dir=tmp_path / ".adep")


# ---------------------------------------------------------------------------
# Basic CRUD tests
# ---------------------------------------------------------------------------


class TestDatabaseStoreCRUD:
    """Test basic CRUD operations on the database store."""

    def test_create_and_read(self, db_store):
        data = {"id": "test-def", "name": "Test Definition", "version": "1.0.0"}
        db_store.create("definitions", "test-def", data)
        result = db_store.read("definitions", "test-def")
        assert result == data

    def test_create_duplicate_raises(self, db_store):
        data = {"id": "test-def", "name": "Test"}
        db_store.create("definitions", "test-def", data)
        with pytest.raises(FileExistsError, match="already exists"):
            db_store.create("definitions", "test-def", data)

    def test_read_not_found(self, db_store):
        with pytest.raises(FileNotFoundError, match="not found"):
            db_store.read("definitions", "nonexistent")

    def test_update(self, db_store):
        db_store.create("definitions", "test-def", {"id": "test-def", "name": "Old"})
        updated = db_store.update("definitions", "test-def", {"id": "test-def", "name": "New"})
        assert updated["name"] == "New"
        result = db_store.read("definitions", "test-def")
        assert result["name"] == "New"

    def test_update_not_found(self, db_store):
        with pytest.raises(FileNotFoundError, match="not found"):
            db_store.update("definitions", "nonexistent", {"id": "nonexistent"})

    def test_delete(self, db_store):
        db_store.create("definitions", "test-def", {"id": "test-def"})
        db_store.delete("definitions", "test-def")
        assert not db_store.exists("definitions", "test-def")

    def test_delete_not_found(self, db_store):
        with pytest.raises(FileNotFoundError, match="not found"):
            db_store.delete("definitions", "nonexistent")

    def test_list_all(self, db_store):
        db_store.create("definitions", "def-a", {"id": "def-a", "name": "A"})
        db_store.create("definitions", "def-b", {"id": "def-b", "name": "B"})
        db_store.create("skills", "skill-a", {"id": "skill-a"})
        result = db_store.list_all("definitions")
        assert len(result) == 2
        ids = [item["id"] for item in result]
        assert ids == ["def-a", "def-b"]

    def test_list_all_empty(self, db_store):
        result = db_store.list_all("definitions")
        assert result == []

    def test_exists(self, db_store):
        db_store.create("definitions", "test-def", {"id": "test-def"})
        assert db_store.exists("definitions", "test-def")
        assert not db_store.exists("definitions", "nonexistent")

    def test_invalid_entity_id(self, db_store):
        with pytest.raises(ValueError, match="Invalid entity ID"):
            db_store.create("definitions", "../bad", {"id": "bad"})

    def test_invalid_entity_id_path_traversal(self, db_store):
        with pytest.raises(ValueError, match="Invalid entity ID"):
            db_store.read("definitions", "../../etc/passwd")


# ---------------------------------------------------------------------------
# Typed convenience method tests
# ---------------------------------------------------------------------------


class TestDatabaseStoreTypedMethods:
    """Test typed convenience methods."""

    def test_create_and_get_definition(self, db_store):
        defn = AgentDefinition(
            id="def-invoice",
            name="Invoice Extractor",
            skill_id="invoice",
            template_id="invoice",
            tool_names=["ocr", "vlm"],
        )
        db_store.create_definition(defn)
        result = db_store.get_definition("def-invoice")
        assert result["id"] == "def-invoice"
        assert result["name"] == "Invoice Extractor"

    def test_list_definitions(self, db_store):
        defn = AgentDefinition(
            id="def-a",
            name="A",
            skill_id="skill-a",
            template_id="tmpl-a",
        )
        db_store.create_definition(defn)
        result = db_store.list_definitions()
        assert len(result) >= 1
        assert any(d["id"] == "def-a" for d in result)

    def test_update_definition(self, db_store):
        defn = AgentDefinition(
            id="def-a",
            name="Original",
            skill_id="skill-a",
            template_id="tmpl-a",
        )
        db_store.create_definition(defn)
        db_store.update_definition("def-a", {"id": "def-a", "name": "Updated"})
        result = db_store.get_definition("def-a")
        assert result["name"] == "Updated"

    def test_delete_definition(self, db_store):
        defn = AgentDefinition(
            id="def-a",
            name="A",
            skill_id="skill-a",
            template_id="tmpl-a",
        )
        db_store.create_definition(defn)
        db_store.delete_definition("def-a")
        assert not db_store.exists("definitions", "def-a")

    def test_create_and_get_skill(self, db_store):
        db_store.create_skill("my-skill", {"id": "my-skill", "name": "My Skill"})
        result = db_store.get_skill("my-skill")
        assert result["id"] == "my-skill"

    def test_create_and_get_template(self, db_store):
        db_store.create_template("my-tmpl", {"id": "my-tmpl", "fields": []})
        result = db_store.get_template("my-tmpl")
        assert result["id"] == "my-tmpl"

    def test_save_and_get_run(self, db_store):
        db_store.save_run("run-123", {"run_id": "run-123", "status": "completed"})
        result = db_store.get_run("run-123")
        assert result["run_id"] == "run-123"

    def test_update_run_upsert(self, db_store):
        db_store.update_run("run-456", {"run_id": "run-456", "status": "running"})
        db_store.update_run("run-456", {"run_id": "run-456", "status": "completed"})
        result = db_store.get_run("run-456")
        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------


class TestMigration:
    """Test migration from file-based to DB store."""

    def test_migrate_from_file_store(self, file_store, db_store):
        file_store.create("definitions", "def-a", {"id": "def-a", "name": "A"})
        file_store.create("skills", "skill-a", {"id": "skill-a"})
        file_store.create("templates", "tmpl-a", {"id": "tmpl-a"})
        file_store.create("runs", "run-1", {"run_id": "run-1"})

        count = db_store.migrate_from_file_store(file_store)
        assert count == 4

        assert db_store.exists("definitions", "def-a")
        assert db_store.exists("skills", "skill-a")
        assert db_store.exists("templates", "tmpl-a")
        assert db_store.exists("runs", "run-1")

    def test_migrate_skip_existing(self, file_store, db_store):
        file_store.create("definitions", "def-a", {"id": "def-a", "name": "A"})
        db_store.create("definitions", "def-a", {"id": "def-a", "name": "Existing"})

        count = db_store.migrate_from_file_store(file_store)
        assert count == 0
        result = db_store.read("definitions", "def-a")
        assert result["name"] == "Existing"


# ---------------------------------------------------------------------------
# Prebuilt merging tests
# ---------------------------------------------------------------------------


class TestPrebuiltMerging:
    """Test prebuilt content merging with DB store."""

    def test_list_definitions_merges_prebuilt(self, db_store):
        db_store.create("definitions", "def-custom", {"id": "def-custom", "name": "Custom"})
        result = db_store.list_definitions()
        ids = [d["id"] for d in result]
        assert "def-custom" in ids


# ---------------------------------------------------------------------------
# Concurrency tests
# ---------------------------------------------------------------------------


class TestConcurrency:
    """Test concurrent access to the DB store."""

    def test_concurrent_creates_different_ids(self, db_store):
        import threading

        def create_def(def_id):
            db_store.create("definitions", def_id, {"id": def_id})

        threads = [
            threading.Thread(target=create_def, args=(f"def-{i}",))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        result = db_store.list_all("definitions")
        assert len(result) == 10
