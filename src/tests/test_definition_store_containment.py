"""Regression tests for definition store path containment (ADE-72, CodeQL py/path-injection).

Definition, skill, template and run ids flow into file paths in ``DefinitionStore``. Every public
operation must refuse an id (or entity type) that escapes ``<base>/<entity_type>/``, an invalid id
from a request must be a clean 4xx (never an unhandled ``ValueError``), and legitimate ids,
including the built-in definitions, keep working.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.definitions.store import DefinitionStore

_BAD_IDS = ["../x", "..\\x", "/abs", "C:\\abs", "a/b", "", ".hidden", "x/../y", "a b", "a.b"]
_BAD_URL_IDS = ["..%5Cx", "..%2Fx", "a.b", ".hidden", "a%20b"]


@pytest.fixture
def store(tmp_path: Path) -> DefinitionStore:
    return DefinitionStore(base_dir=tmp_path / ".adep")


@pytest.fixture
def client(store: DefinitionStore):
    import src.api.auth as auth_module
    import src.config as config_module
    import src.definitions.store as store_module

    old = (store_module._store, config_module.settings.auth_enabled, auth_module._key_store)
    store_module._store = store
    config_module.settings.auth_enabled = False

    from src.api.main import create_app

    yield TestClient(create_app())
    store_module._store, config_module.settings.auth_enabled, auth_module._key_store = old


def _symlink_or_skip(link: Path, target: Path) -> None:
    """Symlink, or a directory junction on Windows accounts without the symlink privilege."""
    try:
        os.symlink(target, link, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError):
        if os.name == "nt" and target.is_dir():
            made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)])
            if made.returncode == 0:
                return
        pytest.skip("symlinks are not permitted here")


class TestEveryOperationRejectsABadId:
    @pytest.mark.parametrize("bad", _BAD_IDS)
    def test_create(self, store: DefinitionStore, bad: str):
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.create("skills", bad, {"id": bad})

    @pytest.mark.parametrize("bad", _BAD_IDS)
    def test_read(self, store: DefinitionStore, bad: str):
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.read("skills", bad)

    @pytest.mark.parametrize("bad", _BAD_IDS)
    def test_update(self, store: DefinitionStore, bad: str):
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.update("skills", bad, {"id": bad})

    @pytest.mark.parametrize("bad", _BAD_IDS)
    def test_delete(self, store: DefinitionStore, bad: str):
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.delete("skills", bad)

    @pytest.mark.parametrize("bad", _BAD_IDS)
    def test_exists(self, store: DefinitionStore, bad: str):
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.exists("skills", bad)

    @pytest.mark.parametrize("bad", _BAD_IDS)
    def test_typed_wrappers(self, store: DefinitionStore, bad: str):
        for call in (
            store.get_definition,
            store.get_skill,
            store.get_template,
            store.get_run,
            store.delete_definition,
            store.delete_skill,
            store.delete_template,
            store.delete_run,
        ):
            with pytest.raises(ValueError, match="Invalid entity ID"):
                call(bad)


class TestEntityTypeIsContained:
    @pytest.mark.parametrize("bad_type", ["../outside", "..", "/abs", "a/b", "", "unknown"])
    def test_unknown_entity_type_is_refused_by_every_operation(
        self, store: DefinitionStore, tmp_path: Path, bad_type: str
    ):
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "x.json").write_text('{"id": "x"}')
        with pytest.raises(ValueError):
            store.read(bad_type, "x")
        with pytest.raises(ValueError):
            store.create(bad_type, "y", {"id": "y"})
        with pytest.raises(ValueError):
            store.update(bad_type, "x", {"id": "x"})
        with pytest.raises(ValueError):
            store.delete(bad_type, "x")
        with pytest.raises(ValueError):
            store.exists(bad_type, "x")
        assert (outside / "x.json").exists()
        assert not (outside / "y.json").exists()


class TestSymlinksCannotLeaveTheStore:
    def test_entity_file_symlinked_outside_is_refused(self, store: DefinitionStore, tmp_path):
        secret = tmp_path / "secret.json"
        secret.write_text('{"id": "leak"}')
        _symlink_or_skip(store.base_dir / "skills" / "evil.json", secret)
        with pytest.raises(ValueError):
            store.read("skills", "evil")
        with pytest.raises(ValueError):
            store.update("skills", "evil", {"id": "overwritten"})
        with pytest.raises(ValueError):
            store.delete("skills", "evil")
        assert secret.read_text() == '{"id": "leak"}'

    def test_entity_dir_symlinked_outside_is_refused(self, store: DefinitionStore, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "x.json").write_text('{"id": "x"}')
        (store.base_dir / "templates").rmdir()
        _symlink_or_skip(store.base_dir / "templates", outside)
        with pytest.raises(ValueError):
            store.read("templates", "x")
        with pytest.raises(ValueError):
            store.create("templates", "y", {"id": "y"})
        assert not (outside / "y.json").exists()

    def test_entity_dir_pointing_at_a_sibling_sharing_the_store_name_prefix_is_refused(
        self, store: DefinitionStore, tmp_path: Path
    ):
        evil = tmp_path / ".adep-evil"
        evil.mkdir()
        (evil / "x.json").write_text('{"id": "x"}')
        (store.base_dir / "skills").rmdir()
        _symlink_or_skip(store.base_dir / "skills", evil)
        with pytest.raises(ValueError):
            store.read("skills", "x")
        with pytest.raises(ValueError):
            store.create("skills", "y", {"id": "y"})
        assert not (evil / "y.json").exists()


class TestLegitimateIdsKeepWorking:
    @pytest.mark.parametrize("good", ["a", "my-skill_1", "A1", "def-invoice", "x" * 80])
    def test_full_crud_cycle(self, store: DefinitionStore, good: str):
        assert not store.exists("skills", good)
        assert store.create("skills", good, {"id": good, "v": 1}) == {"id": good, "v": 1}
        assert store.exists("skills", good)
        assert store.read("skills", good)["v"] == 1
        store.update("skills", good, {"id": good, "v": 2})
        assert store.read("skills", good)["v"] == 2
        store.delete("skills", good)
        assert not store.exists("skills", good)

    def test_duplicate_create_still_file_exists(self, store: DefinitionStore):
        store.create("skills", "dup", {"id": "dup"})
        with pytest.raises(FileExistsError):
            store.create("skills", "dup", {"id": "dup"})

    def test_missing_entity_is_file_not_found(self, store: DefinitionStore):
        with pytest.raises(FileNotFoundError):
            store.read("skills", "nope")
        with pytest.raises(FileNotFoundError):
            store.update("skills", "nope", {})
        with pytest.raises(FileNotFoundError):
            store.delete("skills", "nope")

    def test_builtin_definitions_skills_and_templates_resolve(self, store: DefinitionStore):
        from src.definitions.prebuilt import (
            PREBUILT_DEFINITIONS,
            PREBUILT_SKILLS,
            PREBUILT_TEMPLATES,
        )

        assert PREBUILT_DEFINITIONS and PREBUILT_SKILLS and PREBUILT_TEMPLATES
        for item in PREBUILT_DEFINITIONS:
            assert store.get_definition(item["id"])["id"] == item["id"]
        for item in PREBUILT_SKILLS:
            assert store.get_skill(item["id"])["id"] == item["id"]
        for item in PREBUILT_TEMPLATES:
            assert store.get_template(item["id"])["id"] == item["id"]

    def test_runs_and_list_all(self, store: DefinitionStore):
        store.save_run("run-1", {"id": "run-1"})
        store.update_run("run-1", {"id": "run-1", "status": "done"})
        store.update_run("run-2", {"id": "run-2"})
        assert store.get_run("run-1")["status"] == "done"
        assert [r["id"] for r in store.list_runs()] == ["run-1", "run-2"]
        store.delete_run("run-1")
        assert [r["id"] for r in store.list_runs()] == ["run-2"]


class TestRoutesAnswerAnInvalidIdWithA4xx:
    @pytest.mark.parametrize("bad", _BAD_URL_IDS)
    @pytest.mark.parametrize("kind", ["definitions", "skills", "templates"])
    def test_get_put_delete_by_invalid_id(self, client: TestClient, kind: str, bad: str):
        assert client.get(f"/api/v1/{kind}/{bad}").status_code in (400, 404)
        assert client.put(f"/api/v1/{kind}/{bad}", json={"name": "x"}).status_code in (400, 404)
        assert client.delete(f"/api/v1/{kind}/{bad}").status_code in (400, 404)

    @pytest.mark.parametrize("bad", _BAD_URL_IDS)
    def test_runs_by_invalid_id(self, client: TestClient, bad: str):
        assert client.get(f"/api/v1/runs/{bad}").status_code in (400, 404)
        assert client.delete(f"/api/v1/runs/{bad}").status_code in (400, 404)

    def test_create_definition_with_invalid_id_is_400(self, client: TestClient):
        resp = client.post(
            "/api/v1/definitions",
            json={"id": "../evil", "name": "n", "skill_id": "invoice", "template_id": "invoice"},
        )
        assert resp.status_code == 400

    def test_legitimate_routes_still_work(self, client: TestClient):
        assert client.get("/api/v1/definitions/def-invoice").status_code == 200
        created = client.post(
            "/api/v1/definitions",
            json={"id": "my-def", "name": "n", "skill_id": "invoice", "template_id": "invoice"},
        )
        assert created.status_code == 201
        assert client.get("/api/v1/definitions/my-def").json()["name"] == "n"
        assert client.get("/api/v1/definitions/nope").status_code == 404
        assert client.delete("/api/v1/definitions/my-def").status_code == 204
