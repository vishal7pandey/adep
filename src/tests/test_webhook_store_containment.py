"""Regression tests for webhook store path containment (ADE-71, CodeQL py/path-injection).

A webhook id from the URL or request body flows into ``.adep/webhooks/<id>.json``. Every operation
(create, get, get_raw, update, delete, and the list and event scans) must refuse an id that escapes
the webhooks directory, an invalid id from a request must be a clean 4xx (never an unhandled error),
and legitimate ids keep working.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.agent.webhooks import WebhookConfig, WebhookStore

_BAD_IDS = ["../x", "..\\x", "/abs", "C:\\abs", "a/b", "", ".hidden", "x/../y", "a b", "a.b"]
_BAD_URL_IDS = ["..%5Cx", "..%2Fx", "a.b", ".hidden", "a%20b"]
_URL = "https://example.com/hook"


@pytest.fixture
def store(tmp_path: Path) -> WebhookStore:
    return WebhookStore(base_dir=tmp_path / ".adep")


@pytest.fixture
def client(store: WebhookStore):
    import src.agent.webhooks as webhooks_module
    import src.api.auth as auth_module
    import src.config as config_module

    old = (webhooks_module._store, config_module.settings.auth_enabled, auth_module._key_store)
    webhooks_module._store = store
    config_module.settings.auth_enabled = False

    from src.api.main import create_app

    with patch("src.agent.webhooks._validate_webhook_url"):
        yield TestClient(create_app())
    webhooks_module._store, config_module.settings.auth_enabled, auth_module._key_store = old


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
    def test_create(self, store: WebhookStore, tmp_path: Path, bad: str):
        with pytest.raises(ValueError, match="Invalid webhook ID"):
            store.create(bad, WebhookConfig(id=bad, url=_URL))
        assert not (tmp_path / ".adep" / "x.json").exists()
        assert list(store.hooks_dir.glob("*")) == []

    @pytest.mark.parametrize("bad", _BAD_IDS)
    def test_get(self, store: WebhookStore, bad: str):
        with pytest.raises(ValueError, match="Invalid webhook ID"):
            store.get(bad)

    @pytest.mark.parametrize("bad", _BAD_IDS)
    def test_get_raw(self, store: WebhookStore, bad: str):
        with pytest.raises(ValueError, match="Invalid webhook ID"):
            store.get_raw(bad)

    @pytest.mark.parametrize("bad", _BAD_IDS)
    def test_update(self, store: WebhookStore, bad: str):
        with pytest.raises(ValueError, match="Invalid webhook ID"):
            store.update(bad, {"active": False})

    @pytest.mark.parametrize("bad", _BAD_IDS)
    def test_delete(self, store: WebhookStore, bad: str):
        with pytest.raises(ValueError, match="Invalid webhook ID"):
            store.delete(bad)

    def test_traversal_never_touches_a_file_outside_the_webhooks_dir(
        self, store: WebhookStore, tmp_path: Path
    ):
        outside = tmp_path / ".adep" / "outside.json"
        outside.write_text('{"id": "outside", "url": "https://example.com", "secret": "s"}')
        for call in (
            lambda: store.get("../outside"),
            lambda: store.get_raw("../outside"),
            lambda: store.update("../outside", {"active": False}),
            lambda: store.delete("../outside"),
        ):
            with pytest.raises(ValueError):
                call()
        assert outside.exists()
        assert '"active"' not in outside.read_text()


class TestSymlinksCannotLeaveTheStore:
    def test_hook_file_symlinked_outside_is_refused(self, store: WebhookStore, tmp_path: Path):
        secret = tmp_path / "secret.json"
        secret.write_text('{"id": "leak", "url": "https://example.com", "secret": "s3"}')
        _symlink_or_skip(store.hooks_dir / "evil.json", secret)
        with pytest.raises(ValueError):
            store.get_raw("evil")
        with pytest.raises(ValueError):
            store.update("evil", {"active": False})
        with pytest.raises(ValueError):
            store.delete("evil")
        assert "active" not in secret.read_text()

    def test_hooks_dir_pointing_at_a_sibling_sharing_the_store_name_prefix_is_refused(
        self, tmp_path: Path
    ):
        base = tmp_path / ".adep"
        base.mkdir()
        evil = tmp_path / ".adep-evil"
        evil.mkdir()
        (evil / "x.json").write_text('{"id": "x", "url": "https://example.com"}')
        _symlink_or_skip(base / "webhooks", evil)
        store = WebhookStore(base_dir=base)
        with pytest.raises(ValueError):
            store.get("x")
        with pytest.raises(ValueError):
            store.create("y", WebhookConfig(id="y", url=_URL))
        assert not (evil / "y.json").exists()


class TestLegitimateIdsKeepWorking:
    @pytest.mark.parametrize("good", ["h1", "my-hook_1", "A1", "x" * 80])
    def test_full_crud_cycle(self, store: WebhookStore, good: str):
        created = store.create(good, WebhookConfig(id=good, url=_URL, secret="s"))
        assert created["id"] == good and created["secret"] == "***"
        assert store.get(good)["secret"] == "***"
        assert store.get_raw(good)["secret"] == "s"
        assert store.update(good, {"active": False})["active"] is False
        assert [h["id"] for h in store.list()] == [good]
        store.delete(good)
        assert store.list() == []

    def test_duplicate_create_still_file_exists(self, store: WebhookStore):
        store.create("dup", WebhookConfig(id="dup", url=_URL))
        with pytest.raises(FileExistsError):
            store.create("dup", WebhookConfig(id="dup", url=_URL))

    def test_missing_hook_is_file_not_found(self, store: WebhookStore):
        with pytest.raises(FileNotFoundError):
            store.get("nope")
        with pytest.raises(FileNotFoundError):
            store.get_raw("nope")
        with pytest.raises(FileNotFoundError):
            store.update("nope", {})
        with pytest.raises(FileNotFoundError):
            store.delete("nope")

    def test_event_scan_still_finds_active_hooks(self, store: WebhookStore):
        store.create("h1", WebhookConfig(id="h1", url=_URL, events=["run.completed"]))
        assert [c.id for c in store.get_all_for_event("run.completed")] == ["h1"]
        assert store.get_all_for_event("run.failed") == []


class TestRoutesAnswerAnInvalidIdWithA4xx:
    @pytest.mark.parametrize("bad", _BAD_URL_IDS)
    def test_get_put_delete_test_by_invalid_id(self, client: TestClient, bad: str):
        assert client.get(f"/api/v1/webhooks/{bad}").status_code in (400, 404)
        assert client.put(f"/api/v1/webhooks/{bad}", json={"active": False}).status_code in (
            400,
            404,
        )
        assert client.delete(f"/api/v1/webhooks/{bad}").status_code in (400, 404)
        assert client.post(f"/api/v1/webhooks/{bad}/test").status_code in (400, 404)

    def test_create_with_a_traversal_id_is_400_and_writes_nothing(
        self, client: TestClient, store: WebhookStore, tmp_path: Path
    ):
        resp = client.post("/api/v1/webhooks", json={"id": "../escaped", "url": _URL})
        assert resp.status_code == 400
        assert not (tmp_path / ".adep" / "escaped.json").exists()

    def test_legitimate_routes_still_work(self, client: TestClient):
        created = client.post("/api/v1/webhooks", json={"id": "hook-1", "url": _URL})
        assert created.status_code == 201
        assert client.get("/api/v1/webhooks/hook-1").json()["id"] == "hook-1"
        assert client.get("/api/v1/webhooks/nope").status_code == 404
        assert client.put("/api/v1/webhooks/hook-1", json={"active": False}).status_code == 200
        assert client.delete("/api/v1/webhooks/hook-1").status_code == 204
