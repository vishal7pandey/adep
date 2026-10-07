"""Regression tests for the SonarCloud S2083 findings ADE-56 and ADE-57.

ADE-56: ``save_batch`` (src/api/routes/batches.py) joined a batch id into a path and wrote it
without proving the path stays inside ``.adep/batches``.
ADE-57: ``_encode_image`` (src/providers/vlm_azure.py) opened whatever image path it was handed
(the agent's ``image_path`` tool argument reaches it) without proving the path is a place the
app reads images from: the working directory tree or the system temp directory.
"""

from __future__ import annotations

import os
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.api.routes.batches import load_batch, save_batch
from src.providers import vlm_azure

PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-image-bytes"


# ---------------------------------------------------------------------------
# ADE-56: save_batch
# ---------------------------------------------------------------------------


@pytest.fixture
def batch_cwd(tmp_path, monkeypatch):
    """Run in an empty working directory so `.adep/batches` is under tmp_path."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestSaveBatchContainment:
    def test_relative_traversal_id_is_rejected_and_nothing_is_written(self, batch_cwd):
        with pytest.raises(ValueError):
            save_batch("../escape", {"id": "x"})
        assert not (batch_cwd / ".adep" / "escape.json").exists()

    def test_sibling_dir_sharing_the_batches_name_prefix_is_rejected(self, batch_cwd):
        sibling = batch_cwd / ".adep" / "batches-evil"
        sibling.mkdir(parents=True)
        with pytest.raises(ValueError):
            save_batch("../batches-evil/x", {"id": "x"})
        assert list(sibling.iterdir()) == []

    def test_absolute_id_is_rejected_and_nothing_is_written(self, batch_cwd, tmp_path_factory):
        outside = tmp_path_factory.mktemp("outside")
        target = outside / "victim"
        with pytest.raises(ValueError):
            save_batch(str(target), {"id": "x"})
        assert not (outside / "victim.json").exists()

    def test_legitimate_id_is_saved_inside_the_batches_dir(self, batch_cwd):
        save_batch("batch-ok-123", {"id": "batch-ok-123", "name": "n"})
        saved = batch_cwd / ".adep" / "batches" / "batch-ok-123.json"
        assert saved.is_file()
        assert load_batch("batch-ok-123")["name"] == "n"

    def test_overwriting_an_existing_batch_still_works(self, batch_cwd):
        save_batch("b1", {"id": "b1", "status": "queued"})
        save_batch("b1", {"id": "b1", "status": "cancelled"})
        assert load_batch("b1")["status"] == "cancelled"


# ---------------------------------------------------------------------------
# ADE-57: _encode_image / vlm
# ---------------------------------------------------------------------------


@pytest.fixture
def roots(tmp_path, monkeypatch):
    """Working dir `work/`, system temp dir `systmp/`, and an `outside/` that is neither."""
    work = tmp_path / "work"
    systmp = tmp_path / "systmp"
    outside = tmp_path / "outside"
    for d in (work, systmp, outside):
        d.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(systmp))
    return SimpleNamespace(work=work, systmp=systmp, outside=outside, base=tmp_path)


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="an answer"))]
    )
    monkeypatch.setattr(vlm_azure, "_get_client", lambda: client)
    return client


def _image(path, data=PNG_BYTES):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class TestImagePathContainment:
    def test_absolute_path_outside_both_roots_is_refused(self, roots, fake_client):
        secret = _image(roots.outside / "secret.png")
        result = vlm_azure.vlm(str(secret), "what is this?")
        assert result.ok is False
        fake_client.chat.completions.create.assert_not_called()

    def test_relative_traversal_out_of_the_working_dir_is_refused(self, roots, fake_client):
        _image(roots.outside / "secret.png")
        result = vlm_azure.vlm(os.path.join("..", "outside", "secret.png"), "q")
        assert result.ok is False
        fake_client.chat.completions.create.assert_not_called()

    def test_sibling_dir_sharing_the_working_dir_name_prefix_is_refused(self, roots, fake_client):
        sibling = _image(roots.base / "work-evil" / "secret.png")
        result = vlm_azure.vlm(str(sibling), "q")
        assert result.ok is False
        fake_client.chat.completions.create.assert_not_called()

    def test_encode_image_raises_for_a_path_outside(self, roots):
        secret = _image(roots.outside / "secret.png")
        with pytest.raises(ValueError):
            vlm_azure._encode_image(str(secret))

    def test_refusal_is_immediate_not_retried_with_backoff(self, roots, fake_client):
        secret = _image(roots.outside / "secret.png")
        started = time.monotonic()
        vlm_azure.vlm(str(secret), "q")
        assert time.monotonic() - started < 1.5  # three retries would wait 2s+ each

    def test_symlink_inside_the_working_dir_pointing_outside_is_refused(self, roots, fake_client):
        secret = _image(roots.outside / "secret.png")
        link = roots.work / "link.png"
        try:
            link.symlink_to(secret)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not permitted on this machine")
        result = vlm_azure.vlm(str(link), "q")
        assert result.ok is False
        fake_client.chat.completions.create.assert_not_called()

    def test_image_in_the_working_dir_is_still_read(self, roots, fake_client):
        _image(roots.work / ".adep" / "documents" / "d1" / "page_001.png")
        result = vlm_azure.vlm(os.path.join(".adep", "documents", "d1", "page_001.png"), "q")
        assert result.ok is True
        assert result.data == "an answer"
        url = fake_client.chat.completions.create.call_args.kwargs["messages"][0]["content"][1][
            "image_url"
        ]["url"]
        assert url.startswith("data:image/png;base64,")

    def test_image_in_the_system_temp_dir_is_still_read(self, roots, fake_client):
        crop = _image(roots.systmp / "ade_crop_1.png")
        result = vlm_azure.vlm(str(crop), "q")
        assert result.ok is True
        fake_client.chat.completions.create.assert_called_once()

    def test_jpeg_mime_is_kept_for_non_png(self, roots):
        pic = _image(roots.work / "page.jpg")
        assert vlm_azure._encode_image(str(pic)).startswith("data:image/jpeg;base64,")
