"""Magic-byte validation for uploaded documents [BLK-256].

Prevents content-type spoofing by checking the actual file header bytes
against the claimed extension. This stops attackers from uploading
malicious files (e.g. executables, scripts) with a .pdf or .png extension.
"""

from __future__ import annotations

# Number of bytes to read from the start of the file for magic-byte checks.
# PDF needs 5 bytes, PNG needs 8, JPEG needs 3, TIFF needs 4, BMP needs 2.
MAGIC_BYTE_READ_SIZE = 12

# Magic-byte signatures for each supported format.
# Each entry maps an extension to a list of acceptable byte prefixes.
_MAGIC_BYTES: dict[str, list[bytes]] = {
    ".pdf": [b"%PDF-"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".tiff": [b"II*\x00", b"MM\x00*"],
    ".tif": [b"II*\x00", b"MM\x00*"],
    ".bmp": [b"BM"],
}


def validate_magic_bytes(header: bytes, ext: str) -> bool:
    """Check whether the file header matches the expected magic bytes for the extension.

    Args:
        header: The first ``MAGIC_BYTE_READ_SIZE`` bytes of the file.
        ext: The file extension including the leading dot (e.g. ``.pdf``).

    Returns:
        True if the header starts with any of the known magic-byte signatures
        for the given extension. False otherwise (including unknown extensions).
    """
    signatures = _MAGIC_BYTES.get(ext.lower())
    if signatures is None:
        return False
    return any(header.startswith(sig) for sig in signatures)
