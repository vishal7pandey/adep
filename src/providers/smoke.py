"""Repeatable check that a real model call works (ADE-41): `python -m src.providers.smoke`.

Prints a JSON report with booleans, counts, model names and error TYPES only. It never prints a
key, an endpoint, a prompt or an exception message (messages can echo secrets). One tiny chat call
and one tiny vision call: a fraction of a cent.
"""

from __future__ import annotations

import base64
import json
import struct
import sys
import zlib
from typing import Any

from src.config import Settings


def _tiny_red_png() -> str:
    """A 8x8 solid red PNG as a data URI, built without any imaging library."""
    width = height = 8
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    return "data:image/png;base64," + base64.b64encode(png).decode()


def _is_chat_model(model_id: str) -> bool:
    return model_id.startswith(("gpt-", "o1", "o3", "o4", "o5", "o6", "o7", "o8", "o9", "chatgpt"))


def _step(fn: Any) -> dict[str, Any]:
    try:
        return {"ok": True, **fn()}
    except Exception as exc:  # noqa: BLE001 - report the type only, never the message
        return {"ok": False, "error_type": type(exc).__name__}


def check(settings: Settings, client: Any | None) -> dict[str, Any]:
    """Run the checks against `client` and return a secret-free report."""
    provider = settings.active_llm_provider
    key = settings.openai_api_key if provider == "openai" else settings.azure_api_key
    report: dict[str, Any] = {
        "provider": provider,
        "model": settings.chat_model,
        "key_set": bool(key.strip()),
        "configured": settings.is_llm_configured(),
    }
    if client is None or not report["configured"]:
        missing = {"ok": False, "error_type": "NotConfigured"}
        report.update(models=dict(missing), chat=dict(missing), vision=dict(missing))
        return report

    limit = "max_completion_tokens" if provider == "openai" else "max_tokens"

    def models() -> dict[str, Any]:
        ids = sorted(m.id for m in client.models.list().data)
        return {"chat_models": [i for i in ids if _is_chat_model(i)]}

    def chat() -> dict[str, Any]:
        r = client.chat.completions.create(
            model=settings.chat_model,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            **{limit: 16},
        )
        usage = getattr(r, "usage", None)
        return {"tokens": getattr(usage, "total_tokens", None)}

    def vision() -> dict[str, Any]:
        r = client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What single colour fills this image? One word."},
                        {"type": "image_url", "image_url": {"url": _tiny_red_png()}},
                    ],
                }
            ],
            **{limit: 16},
        )
        answer = (r.choices[0].message.content or "").strip().lower()
        usage = getattr(r, "usage", None)
        return {"sees_red": "red" in answer, "tokens": getattr(usage, "total_tokens", None)}

    report["models"] = _step(models)
    report["chat"] = _step(chat)
    report["vision"] = _step(vision)
    return report


def main() -> int:
    from src.config import settings
    from src.providers import vlm_azure

    client = vlm_azure._get_client() if settings.is_llm_configured() else None
    report = check(settings, client)
    print(json.dumps(report, indent=2))
    return 0 if report["chat"]["ok"] and report["vision"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
