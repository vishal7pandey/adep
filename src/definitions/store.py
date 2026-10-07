"""File-based Definition Store — CRUD for definitions, skills, templates [BLK-017].

v1 uses a local ``.adep/`` folder on disk with JSON files. Simple,
inspectable, version-controllable, sufficient for single-user v1 [SF].

Folder structure::

    .adep/
      definitions/     # Agent definition JSON files
      skills/          # Skill JSON files
      templates/       # Template JSON files
      runs/            # Run traces and results (JSON)
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from src.definitions.base import AgentDefinition, InvalidEntityIdError

logger = logging.getLogger(__name__)

# Entity types that the store manages
_ENTITY_TYPES = ("definitions", "skills", "templates", "runs")

# Entity types that have prebuilt content merged into read results [BLK-159]
_PREBUILT_ENTITY_TYPES = ("definitions", "skills", "templates")


# Valid entity ID pattern: alphanumeric, dash, underscore (no path separators)
_ENTITY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def _atomic_write(path: str | os.PathLike[str], content: str) -> None:
    """Write content to a file atomically [BLK-155].

    Writes to a temp file in the same directory, then os.replace() into place.
    This prevents partial writes from corrupting JSON on crash/kill.
    """
    target = os.fspath(path)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(target),
        prefix=os.path.splitext(os.path.basename(target))[0] + ".",
        suffix=".tmp",
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _atomic_create(path: str | os.PathLike[str], content: str) -> None:
    """Atomically create a file, failing if it already exists [BLK-155].

    Uses O_CREAT | O_EXCL to prevent TOCTOU race between exists() and write().
    """
    target = os.fspath(path)
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        try:
            os.unlink(target)
        except OSError:
            pass
        raise


class DefinitionStore:
    """File-based CRUD store for definitions, skills, and templates.

    All entities are stored as JSON files under ``.adep/{entity_type}/{id}.json``.
    The ``.adep/`` folder is created on first access if it doesn't exist.

    Attributes:
        base_dir: Root directory for the store (default: ``.adep/``).
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path.cwd() / ".adep"
        self.base_dir = Path(base_dir)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create the .adep/ folder structure if it doesn't exist."""
        for entity_type in _ENTITY_TYPES:
            (self.base_dir / entity_type).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _check_ids(entity_type: str, entity_id: str) -> None:
        """Validate an entity type and id before any path is built from them.

        Raises:
            InvalidEntityIdError: If the type is not a known entity type or the id contains
                path traversal characters (a ``ValueError``).
        """
        if entity_type not in _ENTITY_TYPES:
            raise InvalidEntityIdError(f"Invalid entity type '{entity_type}'")
        if not _ENTITY_ID_PATTERN.match(entity_id):
            raise InvalidEntityIdError(
                f"Invalid entity ID '{entity_id}': must match {_ENTITY_ID_PATTERN.pattern}"
            )

    # ------------------------------------------------------------------
    # Generic CRUD
    #
    # entity_id comes from the request URL or body. Each operation validates the type and id,
    # resolves the target with os.path.realpath and touches it only inside the true branch of an
    # inline ``startswith(root + os.sep)`` guard on the store root (CodeQL py/path-injection,
    # ADE-72). A symlinked file or directory that leaves the store fails the guard.
    # ------------------------------------------------------------------

    def create(self, entity_type: str, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new entity. Fails if it already exists.

        Args:
            entity_type: "definitions", "skills", "templates", or "runs".
            entity_id: Unique identifier for the entity.
            data: Entity data as a dict (will be serialized to JSON).

        Returns:
            The created entity data.

        Raises:
            FileExistsError: If the entity already exists.
        """
        self._check_ids(entity_type, entity_id)
        root = os.path.realpath(self.base_dir)
        real = os.path.realpath(os.path.join(root, entity_type, f"{entity_id}.json"))
        if real.startswith(root + os.sep):
            content = json.dumps(data, indent=2, default=str)
            try:
                _atomic_create(real, content)
            except FileExistsError:
                raise FileExistsError(f"{entity_type}/{entity_id} already exists")
            logger.info("Created %s/%s", entity_type, entity_id)
            return data
        raise InvalidEntityIdError(f"Invalid entity ID '{entity_id}': outside the store")

    def read(self, entity_type: str, entity_id: str) -> dict[str, Any]:
        """Read an entity by ID.

        Raises:
            FileNotFoundError: If the entity doesn't exist.
        """
        self._check_ids(entity_type, entity_id)
        root = os.path.realpath(self.base_dir)
        real = os.path.realpath(os.path.join(root, entity_type, f"{entity_id}.json"))
        if real.startswith(root + os.sep):
            if not os.path.exists(real):
                raise FileNotFoundError(f"{entity_type}/{entity_id} not found")
            with open(real, encoding="utf-8") as f:
                return json.load(f)
        raise InvalidEntityIdError(f"Invalid entity ID '{entity_id}': outside the store")

    def update(self, entity_type: str, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing entity. Fails if it doesn't exist.

        Raises:
            FileNotFoundError: If the entity doesn't exist.
        """
        self._check_ids(entity_type, entity_id)
        root = os.path.realpath(self.base_dir)
        real = os.path.realpath(os.path.join(root, entity_type, f"{entity_id}.json"))
        if real.startswith(root + os.sep):
            if not os.path.exists(real):
                raise FileNotFoundError(f"{entity_type}/{entity_id} not found")
            _atomic_write(real, json.dumps(data, indent=2, default=str))
            logger.info("Updated %s/%s", entity_type, entity_id)
            return data
        raise InvalidEntityIdError(f"Invalid entity ID '{entity_id}': outside the store")

    def delete(self, entity_type: str, entity_id: str) -> None:
        """Delete an entity by ID.

        Raises:
            FileNotFoundError: If the entity doesn't exist.
        """
        self._check_ids(entity_type, entity_id)
        root = os.path.realpath(self.base_dir)
        real = os.path.realpath(os.path.join(root, entity_type, f"{entity_id}.json"))
        if real.startswith(root + os.sep):
            if not os.path.exists(real):
                raise FileNotFoundError(f"{entity_type}/{entity_id} not found")
            os.unlink(real)
            logger.info("Deleted %s/%s", entity_type, entity_id)
            return
        raise InvalidEntityIdError(f"Invalid entity ID '{entity_id}': outside the store")

    def list_all(self, entity_type: str) -> list[dict[str, Any]]:
        """List all entities of a given type.

        Returns:
            List of entity data dicts.
        """
        dir_path = self.base_dir / entity_type
        if not dir_path.exists():
            return []
        results = []
        for json_file in sorted(dir_path.glob("*.json")):
            results.append(json.loads(json_file.read_text(encoding="utf-8")))
        return results

    def exists(self, entity_type: str, entity_id: str) -> bool:
        """Check if an entity exists."""
        self._check_ids(entity_type, entity_id)
        root = os.path.realpath(self.base_dir)
        real = os.path.realpath(os.path.join(root, entity_type, f"{entity_id}.json"))
        if real.startswith(root + os.sep):
            return os.path.exists(real)
        raise InvalidEntityIdError(f"Invalid entity ID '{entity_id}': outside the store")

    # ------------------------------------------------------------------
    # Prebuilt content merging [BLK-159]
    # ------------------------------------------------------------------

    def _merge_with_prebuilt(self, entity_type: str) -> list[dict[str, Any]]:
        """Merge on-disk entities with prebuilt content [BLK-159].

        Disk takes precedence: if an entity with the same ID exists on disk,
        the disk version is used (user edits win). Prebuilt entities not on
        disk are included as-is.

        Args:
            entity_type: "definitions", "skills", or "templates".

        Returns:
            Merged list of entity dicts, sorted by ID.
        """
        disk_items = self.list_all(entity_type)
        prebuilt_items = _get_prebuilt(entity_type)

        disk_ids = {item.get("id") for item in disk_items}
        merged = list(disk_items)
        for prebuilt in prebuilt_items:
            if prebuilt.get("id") not in disk_ids:
                merged.append(prebuilt)

        merged.sort(key=lambda x: x.get("id", ""))
        return merged

    # ------------------------------------------------------------------
    # Typed convenience methods
    # ------------------------------------------------------------------

    def create_definition(self, definition: AgentDefinition) -> dict[str, Any]:
        """Create a definition from an AgentDefinition model."""
        return self.create("definitions", definition.id, definition.model_dump())

    def get_definition(self, definition_id: str) -> dict[str, Any]:
        """Get a definition by ID [BLK-159].

        Checks disk first, falls back to prebuilt definitions.
        """
        try:
            return self.read("definitions", definition_id)
        except FileNotFoundError:
            for prebuilt in _get_prebuilt("definitions"):
                if prebuilt.get("id") == definition_id:
                    return prebuilt
            raise FileNotFoundError(f"definitions/{definition_id} not found")

    def list_definitions(self) -> list[dict[str, Any]]:
        """List all definitions [BLK-159].

        Merges prebuilt definitions with on-disk definitions.
        Disk takes precedence (user edits win).
        """
        return self._merge_with_prebuilt("definitions")

    def update_definition(self, definition_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a definition."""
        return self.update("definitions", definition_id, data)

    def delete_definition(self, definition_id: str) -> None:
        """Delete a definition."""
        self.delete("definitions", definition_id)

    def create_skill(self, skill_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a skill."""
        return self.create("skills", skill_id, data)

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        """Get a skill by ID [BLK-159].

        Checks disk first, falls back to prebuilt skills.
        """
        try:
            return self.read("skills", skill_id)
        except FileNotFoundError:
            for prebuilt in _get_prebuilt("skills"):
                if prebuilt.get("id") == skill_id:
                    return prebuilt
            raise FileNotFoundError(f"skills/{skill_id} not found")

    def list_skills(self) -> list[dict[str, Any]]:
        """List all skills [BLK-159].

        Merges prebuilt skills with on-disk skills.
        Disk takes precedence (user edits win).
        """
        return self._merge_with_prebuilt("skills")

    def update_skill(self, skill_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a skill."""
        return self.update("skills", skill_id, data)

    def delete_skill(self, skill_id: str) -> None:
        """Delete a skill."""
        self.delete("skills", skill_id)

    def create_template(self, template_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a template."""
        return self.create("templates", template_id, data)

    def get_template(self, template_id: str) -> dict[str, Any]:
        """Get a template by ID [BLK-159].

        Checks disk first, falls back to prebuilt templates.
        """
        try:
            return self.read("templates", template_id)
        except FileNotFoundError:
            for prebuilt in _get_prebuilt("templates"):
                if prebuilt.get("id") == template_id:
                    return prebuilt
            raise FileNotFoundError(f"templates/{template_id} not found")

    def list_templates(self) -> list[dict[str, Any]]:
        """List all templates [BLK-159].

        Merges prebuilt templates with on-disk templates.
        Disk takes precedence (user edits win).
        """
        return self._merge_with_prebuilt("templates")

    def update_template(self, template_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a template."""
        return self.update("templates", template_id, data)

    def delete_template(self, template_id: str) -> None:
        """Delete a template."""
        self.delete("templates", template_id)

    def save_run(self, run_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Save a run result/trace."""
        return self.create("runs", run_id, data)

    def get_run(self, run_id: str) -> dict[str, Any]:
        """Get a run by ID."""
        return self.read("runs", run_id)

    def list_runs(self) -> list[dict[str, Any]]:
        """List all runs."""
        return self.list_all("runs")

    def update_run(self, run_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a run (e.g. status change)."""
        if self.exists("runs", run_id):
            return self.update("runs", run_id, data)
        return self.create("runs", run_id, data)

    def delete_run(self, run_id: str) -> None:
        """Delete a run by ID [BLK-077].

        Raises:
            FileNotFoundError: If the run doesn't exist.
        """
        self.delete("runs", run_id)


# Singleton store instance
_store: DefinitionStore | Any = None


def get_store() -> DefinitionStore | Any:
    """Get the singleton store instance.

    Returns a file-based DefinitionStore or a DatabaseDefinitionStore
    depending on the ADE_STORE_BACKEND config setting [BLK-036].
    """
    global _store
    if _store is None:
        from src.config import settings

        backend = settings.store_backend.lower()
        if backend == "sqlite":
            from src.definitions.db_store import DatabaseDefinitionStore

            _store = DatabaseDefinitionStore(db_path=settings.store_db_path)
            logger.info("Using SQLite-backed store at %s", settings.store_db_path)
        else:
            _store = DefinitionStore()
    return _store


# ---------------------------------------------------------------------------
# Prebuilt content merging [BLK-159]
# ---------------------------------------------------------------------------


def _get_prebuilt(entity_type: str) -> list[dict[str, Any]]:
    """Get prebuilt content for an entity type [BLK-159].

    Args:
        entity_type: "definitions", "skills", or "templates".

    Returns:
        List of prebuilt entity dicts, or empty list if none available.
    """
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
