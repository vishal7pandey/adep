"""Tests for document upload validation [BLK-256].

Verifies magic-byte checks, streamed size cap, and decompression-bomb guard.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.documents.validation import validate_magic_bytes, MAGIC_BYTE_READ_SIZE
from src.documents.store import MAX_FILE_SIZE_BYTES, _MAX_IMAGE_PIXELS


# ---------------------------------------------------------------------------
# Magic-byte validation unit tests
# ---------------------------------------------------------------------------


class TestValidateMagicBytes:
    """Verify magic-byte detection for each supported format."""

    def test_pdf_magic_bytes(self):
        assert validate_magic_bytes(b"%PDF-1.4\n", ".pdf") is True

    def test_png_magic_bytes(self):
        assert validate_magic_bytes(b"\x89PNG\r\n\x1a\n\x00\x00", ".png") is True

    def test_jpeg_magic_bytes(self):
        assert validate_magic_bytes(b"\xff\xd8\xff\xe0\x00", ".jpg") is True
        assert validate_magic_bytes(b"\xff\xd8\xff\xe1\x00", ".jpeg") is True

    def test_tiff_magic_bytes_little_endian(self):
        assert validate_magic_bytes(b"II*\x00\x08\x00", ".tiff") is True
        assert validate_magic_bytes(b"II*\x00\x08\x00", ".tif") is True

    def test_tiff_magic_bytes_big_endian(self):
        assert validate_magic_bytes(b"MM\x00*\x00\x08", ".tiff") is True

    def test_bmp_magic_bytes(self):
        assert validate_magic_bytes(b"BM\x00\x00\x00\x00", ".bmp") is True

    def test_wrong_content_rejected(self):
        """A file with wrong magic bytes should be rejected."""
        assert validate_magic_bytes(b"NOTAPDF-1.4\n", ".pdf") is False
        assert validate_magic_bytes(b"\x00\x00\x00\x00", ".png") is False
        assert validate_magic_bytes(b"PK\x03\x04", ".pdf") is False  # ZIP header

    def test_empty_header_rejected(self):
        assert validate_magic_bytes(b"", ".pdf") is False

    def test_unknown_extension_rejected(self):
        assert validate_magic_bytes(b"%PDF-1.4\n", ".exe") is False

    def test_short_header_still_works(self):
        """Headers shorter than MAGIC_BYTE_READ_SIZE should still validate."""
        assert validate_magic_bytes(b"%PDF-", ".pdf") is True
        assert validate_magic_bytes(b"BM", ".bmp") is True


# ---------------------------------------------------------------------------
# Integration tests via API endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def upload_client(tmp_path: Path) -> TestClient:
    """Create a FastAPI TestClient with auth enabled and a temp key store."""
    import src.api.auth as auth_module
    import src.config as config_module
    import src.definitions.store as store_module
    from src.documents import store as doc_store_mod

    # Reset stores to temp dir
    old_store = store_module._store
    old_key_store = auth_module._key_store
    old_doc_store = doc_store_mod._store
    store_module._store = store_module.DefinitionStore(base_dir=tmp_path / ".adep")
    auth_module._key_store = auth_module.ApiKeyStore(base_dir=tmp_path / ".adep")
    doc_store_mod._store = None

    # Enable auth
    old_auth = config_module.settings.auth_enabled
    config_module.settings.auth_enabled = True

    # Capture the bootstrap secret from stdout during create_app()
    import contextlib

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        from src.api.main import create_app

        app = create_app()
    client = TestClient(app)

    # Parse the secret from the bootstrap output
    out = captured.getvalue()
    secret = ""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Secret:") and "shown ONLY ONCE" not in line:
            secret = line.split("Secret:", 1)[1].strip()
            break
    assert secret, f"Could not extract bootstrap secret from stdout: {out!r}"
    client._admin_secret = secret  # type: ignore[attr-defined]

    yield client

    # Restore
    config_module.settings.auth_enabled = old_auth
    store_module._store = old_store
    auth_module._key_store = old_key_store
    doc_store_mod._store = old_doc_store


def _make_upload(content: bytes, filename: str):
    """Create a file upload payload."""
    return {"file": (filename, io.BytesIO(content), "application/octet-stream")}


def _auth_headers(client: TestClient) -> dict[str, str]:
    """Get auth headers from the client's admin secret."""
    return {"Authorization": f"Bearer {client._admin_secret}"}  # type: ignore[attr-defined]


class TestUploadValidation:
    """Verify upload endpoint rejects invalid files [BLK-256]."""

    def test_valid_png_accepted(self, upload_client: TestClient):
        """A real PNG file should be accepted."""
        from PIL import Image

        img = Image.new("RGB", (1, 1), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
        resp = upload_client.post(
            "/api/v1/documents",
            files=_make_upload(png_bytes, "test.png"),
            headers=_auth_headers(upload_client),
        )
        assert resp.status_code == 201

    def test_spoofed_extension_rejected(self, upload_client: TestClient):
        """A non-PNG file with .png extension should be rejected with 415."""
        fake_content = b"THIS_IS_NOT_A_PNG_FILE_CONTENT_HERE"
        resp = upload_client.post(
            "/api/v1/documents",
            files=_make_upload(fake_content, "fake.png"),
            headers=_auth_headers(upload_client),
        )
        assert resp.status_code == 415
        assert "does not match" in resp.json()["detail"].lower()

    def test_spoofed_pdf_rejected(self, upload_client: TestClient):
        """A non-PDF file with .pdf extension should be rejected with 415."""
        fake_content = b"PK\x03\x04" + b"\x00" * 100  # ZIP header, not PDF
        resp = upload_client.post(
            "/api/v1/documents",
            files=_make_upload(fake_content, "fake.pdf"),
            headers=_auth_headers(upload_client),
        )
        assert resp.status_code == 415

    def test_oversized_file_rejected_during_streaming(self, upload_client: TestClient):
        """A file exceeding MAX_FILE_SIZE_BYTES should be rejected with 413."""
        # Create content just over the limit
        oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (MAX_FILE_SIZE_BYTES + 1)
        resp = upload_client.post(
            "/api/v1/documents",
            files=_make_upload(oversized, "big.png"),
            headers=_auth_headers(upload_client),
        )
        assert resp.status_code == 413
        assert "exceeds" in resp.json()["detail"].lower()

    def test_unsupported_extension_rejected(self, upload_client: TestClient):
        """Files with unsupported extensions should be rejected with 400."""
        resp = upload_client.post(
            "/api/v1/documents",
            files=_make_upload(b"content", "file.exe"),
            headers=_auth_headers(upload_client),
        )
        assert resp.status_code == 400
        assert "unsupported" in resp.json()["detail"].lower()

    def test_empty_file_rejected(self, upload_client: TestClient):
        """An empty file should be rejected by magic-byte validation."""
        resp = upload_client.post(
            "/api/v1/documents",
            files=_make_upload(b"", "empty.png"),
            headers=_auth_headers(upload_client),
        )
        assert resp.status_code == 415


# ---------------------------------------------------------------------------
# Decompression-bomb guard tests
# ---------------------------------------------------------------------------


class TestDecompressionBombGuard:
    """Verify PIL decompression-bomb protection is active."""

    def test_max_image_pixels_set(self):
        """Verify that _MAX_IMAGE_PIXELS is defined and reasonable."""
        assert _MAX_IMAGE_PIXELS > 0
        assert _MAX_IMAGE_PIXELS <= 200_000_000  # Not unreasonably high

    def test_pil_max_image_pixels_enforced(self):
        """Verify that PIL.Image.MAX_IMAGE_PIXELS is set when processing images."""
        from PIL import Image
        from src.documents.store import DocumentStore

        # Before calling _process_image, MAX_IMAGE_PIXELS may be unset
        # After calling it (even if it fails), it should be set
        original = Image.MAX_IMAGE_PIXELS
        try:
            # Create a minimal valid PNG to trigger _process_image
            png_bytes = (
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
                b"\x00\x00\x00\x90wS\xde"
                b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01"
                b"\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(png_bytes)
                tmp_path = Path(tmp.name)

            store = DocumentStore(base_dir=Path(tempfile.mkdtemp()))
            try:
                store._process_image(tmp_path, store.docs_dir / "test", "test", "test.png", ".png")
            except Exception:
                pass  # May fail for various reasons, that's OK
            finally:
                tmp_path.unlink(missing_ok=True)

            assert Image.MAX_IMAGE_PIXELS == _MAX_IMAGE_PIXELS
        finally:
            Image.MAX_IMAGE_PIXELS = original
