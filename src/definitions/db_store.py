"""Database-backed Definition Store (v2) — SQLite CRUD for definitions, skills, templates, runs [BLK-036].

Migrates the file-based store to SQLite for better scalability, concurrent
access, and query support. Uses Python's built-in sqlite3 module — no new
dependencies required.

The DB schema uses a single `entities` table with:
- entity_type: "definitions" | "skills" | "templates" | "runs"
- entity_id: unique identifier within the entity type
- data: JSON blob containing the full entity
- created_at: ISO timestamp
- updated_at: ISO timestamp

A unique constraint on (entity_type, entity_id) prevents duplicates.
Prebuilt content is merged on read (disk/DB takes precedence) [BLK-159].

The store is backward-compatible with DefinitionStore — same method signatures.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.definitions.base import AgentDefinition, InvalidEntityIdError

logger = logging.getLogger(__name__)

_ENTITY_TYPES = ("definitions", "skills", "templates", "runs")
_PREBUILT_ENTITY_TYPES = ("definitions", "skills", "templates")
_ENTITY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    entity_type TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    data        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
"""


class DatabaseDefinitionStore:
    """SQLite-backed CRUD store for definitions, skills, templates, and runs.

    Drop-in replacement for DefinitionStore with identical method signatures.
    Uses SQLite for persistence, enabling concurrent access and query support.

    Attributes:
        db_path: Path to the SQLite database file. Use ":memory:" for in-memory.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path.cwd() / ".adep" / "store.db"
        self.db_path = str(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        db_path = Path(self.db_path)
        if db_path.parent and not db_path.parent.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def _validate_id(self, entity_id: str) -> None:
        if not _ENTITY_ID_PATTERN.match(entity_id):
            raise InvalidEntityIdError(
                f"Invalid entity ID '{entity_id}': must match {_ENTITY_ID_PATTERN.pattern}"
            )

    # ------------------------------------------------------------------
    # Generic CRUD
    # ------------------------------------------------------------------

    def create(self, entity_type: str, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new entity. Fails if it already exists."""
        self._validate_id(entity_id)
        now = datetime.now(timezone.utc).isoformat()
        content = json.dumps(data, indent=2, default=str)
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO entities (entity_type, entity_id, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (entity_type, entity_id, content, now, now),
            )
            conn.commit()
            logger.info("Created %s/%s", entity_type, entity_id)
            return data
        except sqlite3.IntegrityError:
            raise FileExistsError(f"{entity_type}/{entity_id} already exists")
        finally:
            conn.close()

    def read(self, entity_type: str, entity_id: str) -> dict[str, Any]:
        """Read an entity by ID."""
        self._validate_id(entity_id)
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT data FROM entities WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            ).fetchone()
            if row is None:
                raise FileNotFoundError(f"{entity_type}/{entity_id} not found")
            return json.loads(row["data"])
        finally:
            conn.close()

    def update(self, entity_type: str, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing entity. Fails if it doesn't exist."""
        self._validate_id(entity_id)
        now = datetime.now(timezone.utc).isoformat()
        content = json.dumps(data, indent=2, default=str)
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "UPDATE entities SET data = ?, updated_at = ? WHERE entity_type = ? AND entity_id = ?",
                (content, now, entity_type, entity_id),
            )
            if cursor.rowcount == 0:
                raise FileNotFoundError(f"{entity_type}/{entity_id} not found")
            conn.commit()
            logger.info("Updated %s/%s", entity_type, entity_id)
            return data
        finally:
            conn.close()

    def delete(self, entity_type: str, entity_id: str) -> None:
        """Delete an entity by ID."""
        self._validate_id(entity_id)
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM entities WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            )
            if cursor.rowcount == 0:
                raise FileNotFoundError(f"{entity_type}/{entity_id} not found")
            conn.commit()
            logger.info("Deleted %s/%s", entity_type, entity_id)
        finally:
            conn.close()

    def list_all(self, entity_type: str) -> list[dict[str, Any]]:
        """List all entities of a given type."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT data FROM entities WHERE entity_type = ? ORDER BY entity_id",
                (entity_type,),
            ).fetchall()
            return [json.loads(row["data"]) for row in rows]
        finally:
            conn.close()

    def exists(self, entity_type: str, entity_id: str) -> bool:
        """Check if an entity exists."""
        self._validate_id(entity_id)
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM entities WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Prebuilt content merging [BLK-159]
    # ------------------------------------------------------------------

    def _merge_with_prebuilt(self, entity_type: str) -> list[dict[str, Any]]:
        """Merge DB entities with prebuilt content [BLK-159]."""
        db_items = self.list_all(entity_type)
        prebuilt_items = _get_prebuilt(entity_type)
        db_ids = {item.get("id") for item in db_items}
        merged = list(db_items)
        for prebuilt in prebuilt_items:
            if prebuilt.get("id") not in db_ids:
                merged.append(prebuilt)
        merged.sort(key=lambda x: x.get("id", ""))
        return merged

    # ------------------------------------------------------------------
    # Typed convenience methods
    # ------------------------------------------------------------------

    def create_definition(self, definition: AgentDefinition) -> dict[str, Any]:
        return self.create("definitions", definition.id, definition.model_dump())

    def get_definition(self, definition_id: str) -> dict[str, Any]:
        try:
            return self.read("definitions", definition_id)
        except FileNotFoundError:
            for prebuilt in _get_prebuilt("definitions"):
                if prebuilt.get("id") == definition_id:
                    return prebuilt
            raise FileNotFoundError(f"definitions/{definition_id} not found")

    def list_definitions(self) -> list[dict[str, Any]]:
        return self._merge_with_prebuilt("definitions")

    def update_definition(self, definition_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self.update("definitions", definition_id, data)

    def delete_definition(self, definition_id: str) -> None:
        self.delete("definitions", definition_id)

    def create_skill(self, skill_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self.create("skills", skill_id, data)

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        try:
            return self.read("skills", skill_id)
        except FileNotFoundError:
            for prebuilt in _get_prebuilt("skills"):
                if prebuilt.get("id") == skill_id:
                    return prebuilt
            raise FileNotFoundError(f"skills/{skill_id} not found")

    def list_skills(self) -> list[dict[str, Any]]:
        return self._merge_with_prebuilt("skills")

    def update_skill(self, skill_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self.update("skills", skill_id, data)

    def delete_skill(self, skill_id: str) -> None:
        self.delete("skills", skill_id)

    def create_template(self, template_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self.create("templates", template_id, data)

    def get_template(self, template_id: str) -> dict[str, Any]:
        try:
            return self.read("templates", template_id)
        except FileNotFoundError:
            for prebuilt in _get_prebuilt("templates"):
                if prebuilt.get("id") == template_id:
                    return prebuilt
            raise FileNotFoundError(f"templates/{template_id} not found")

    def list_templates(self) -> list[dict[str, Any]]:
        return self._merge_with_prebuilt("templates")

    def update_template(self, template_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self.update("templates", template_id, data)

    def delete_template(self, template_id: str) -> None:
        self.delete("templates", template_id)

    def save_run(self, run_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self.create("runs", run_id, data)

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self.read("runs", run_id)

    def list_runs(self) -> list[dict[str, Any]]:
        return self.list_all("runs")

    def update_run(self, run_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if self.exists("runs", run_id):
            return self.update("runs", run_id, data)
        return self.create("runs", run_id, data)

    def delete_run(self, run_id: str) -> None:
        self.delete("runs", run_id)

    # ------------------------------------------------------------------
    # Migration helper
    # ------------------------------------------------------------------

    def migrate_from_file_store(self, file_store: Any) -> int:
        """Migrate entities from a file-based DefinitionStore to this DB store.

        Args:
            file_store: A DefinitionStore instance to read from.

        Returns:
            Number of entities migrated.
        """
        count = 0
        for entity_type in _ENTITY_TYPES:
            items = file_store.list_all(entity_type)
            for item in items:
                entity_id = item.get("id") or item.get("run_id", "")
                if not entity_id:
                    continue
                if not self.exists(entity_type, entity_id):
                    self.create(entity_type, entity_id, item)
                    count += 1
        logger.info("Migrated %d entities from file store to DB", count)
        return count


def _get_prebuilt(entity_type: str) -> list[dict[str, Any]]:
    """Get prebuilt content for an entity type [BLK-159]."""
    try:
        from src.definitions.prebuilt import (
            PREBUILT_DEFINITIONS,
            PREBUILT_SKILLS,
            PREBUILT_TEMPLATES,
        )
    except Exception:
        return []

    if entity_type == "definitions":
        return PREBUILT_DEFINITIONS
    if entity_type == "skills":
        return PREBUILT_SKILLS
    if entity_type == "templates":
        return PREBUILT_TEMPLATES
    return []
