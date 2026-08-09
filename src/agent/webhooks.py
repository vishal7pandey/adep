"""Webhook notifications — run completion and budget alerts [BLK-064].

Provides:
- ``WebhookConfig``: Webhook configuration model.
- ``WebhookEvent``: Event types that trigger webhooks.
- ``WebhookStore``: File-based webhook config storage.
- ``dispatch_webhook``: Send webhook payload with HMAC signature and retry.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import os
import socket
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds

# BLK-152: SSRF protection — blocked IP ranges
_BLOCKED_IP_PREFIXES = (
    "127.",           # loopback
    "169.254.",       # link-local (includes 169.254.169.254 cloud metadata)
    "10.",            # RFC1918
    "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",  # RFC1918
    "192.168.",       # RFC1918
    "0.",             # current network
    "224.", "225.", "226.", "227.", "228.", "229.", "230.", "231.", "232.", "233.", "234.", "235.", "236.", "237.", "238.", "239.",  # multicast
)

# Allowed URL schemes for webhook targets
_ALLOWED_SCHEMES = frozenset({"https"})
# http allowed only for localhost dev (controlled by env var)
_DEV_HTTP_ALLOWED = os.environ.get("ADE_WEBHOOK_ALLOW_HTTP", "false").lower() in ("true", "1", "yes")


class SSRFError(ValueError):
    """Raised when a webhook URL fails SSRF validation [BLK-152]."""


def _validate_webhook_url(url: str, *, resolve: bool = True) -> None:
    """Validate a webhook URL against SSRF attack vectors [BLK-152].

    Checks:
    1. URL scheme is in the allow-list (https only, http for dev)
    2. Hostname resolves to a non-blocked IP
    3. Blocks loopback, private, link-local, multicast, and cloud metadata IPs

    Args:
        url: The webhook URL to validate.
        resolve: If True, resolve hostname and check IP (prevents DNS rebinding).

    Raises:
        SSRFError: If the URL fails validation.
    """
    parsed = urlparse(url)

    # Scheme allow-list
    if parsed.scheme not in _ALLOWED_SCHEMES:
        if parsed.scheme == "http" and _DEV_HTTP_ALLOWED:
            pass  # Allow http in dev mode
        else:
            raise SSRFError(
                f"Webhook URL scheme '{parsed.scheme}' not allowed. "
                f"Use https{'+ http (dev mode)' if _DEV_HTTP_ALLOWED else ''}."
            )

    if not parsed.hostname:
        raise SSRFError("Webhook URL has no hostname")

    hostname = parsed.hostname

    # Check if hostname is already an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        _check_ip_blocked(ip)
    except ValueError:
        # It's a hostname — resolve it
        if resolve:
            try:
                addrinfos = socket.getaddrinfo(hostname, None)
                for addrinfo in addrinfos:
                    ip = ipaddress.ip_address(addrinfo[4][0])
                    _check_ip_blocked(ip)
            except socket.gaierror:
                raise SSRFError(f"Cannot resolve hostname '{hostname}'")


def _check_ip_blocked(ip: ipaddress.IPAddress) -> None:
    """Check if an IP address is in a blocked range [BLK-152]."""
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved:
        raise SSRFError(
            f"Webhook target IP {ip} is in a blocked range "
            f"(loopback/private/link-local/multicast/reserved)."
        )


def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically [BLK-155].

    Writes to a temp file in the same directory, then os.replace() into place.
    This prevents partial writes from corrupting JSON on crash/kill.
    """
    encoding = "utf-8"
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=path.stem + ".",
        suffix=".tmp",
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class WebhookEvent:
    """Webhook event type constants [BLK-064]."""

    RUN_COMPLETED = "run.completed"
    RUN_PARTIAL = "run.partial"
    RUN_FAILED = "run.failed"
    BUDGET_WARNING = "budget.warning"
    BUDGET_EXCEEDED = "budget.exceeded"

    ALL = frozenset({
        RUN_COMPLETED,
        RUN_PARTIAL,
        RUN_FAILED,
        BUDGET_WARNING,
        BUDGET_EXCEEDED,
    })


@dataclass
class WebhookConfig:
    """Webhook configuration [BLK-064].

    Attributes:
        id: Unique webhook identifier.
        url: Target URL for POST delivery.
        secret: HMAC signing secret (optional).
        events: Set of event types to subscribe to.
        active: Whether this webhook is enabled.
        created_at: ISO 8601 timestamp.
    """

    id: str
    url: str
    secret: str = ""
    events: list[str] = field(default_factory=lambda: list(WebhookEvent.ALL))
    active: bool = True
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON persistence."""
        return {
            "id": self.id,
            "url": self.url,
            "secret": "***" if self.secret else "",
            "events": self.events,
            "active": self.active,
            "created_at": self.created_at,
        }

    def matches_event(self, event: str) -> bool:
        """Check if this webhook subscribes to the given event."""
        return self.active and event in self.events


class WebhookStore:
    """File-based webhook config store [BLK-064].

    Stored under ``.adep/webhooks/{id}.json``.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(".adep")
        self.hooks_dir = self.base_dir / "webhooks"
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, hook_id: str) -> Path:
        return self.hooks_dir / f"{hook_id}.json"

    def create(self, hook_id: str, config: WebhookConfig) -> dict[str, Any]:
        """Create a new webhook config.

        Validates the webhook URL against SSRF rules [BLK-152].
        """
        _validate_webhook_url(config.url)
        path = self._path(hook_id)
        if path.exists():
            raise FileExistsError(f"Webhook '{hook_id}' already exists")
        data = config.to_dict()
        # Store actual secret in file (not masked)
        data["secret"] = config.secret
        _atomic_write(path, json.dumps(data, indent=2))
        return config.to_dict()

    def get(self, hook_id: str) -> dict[str, Any]:
        """Get webhook config by ID (secret masked)."""
        path = self._path(hook_id)
        if not path.exists():
            raise FileNotFoundError(f"Webhook '{hook_id}' not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        # Mask secret in response
        data["secret"] = "***" if data.get("secret") else ""
        return data

    def get_raw(self, hook_id: str) -> dict[str, Any]:
        """Get webhook config by ID with unmasked secret (internal use only).

        Used by the test_webhook endpoint to send signed payloads.
        """
        path = self._path(hook_id)
        if not path.exists():
            raise FileNotFoundError(f"Webhook '{hook_id}' not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        return data

    def list(self) -> list[dict[str, Any]]:
        """List all webhook configs."""
        hooks = []
        for path in sorted(self.hooks_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            data["secret"] = "***" if data.get("secret") else ""
            hooks.append(data)
        return hooks

    def update(self, hook_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a webhook config.

        Validates the webhook URL if it's being changed [BLK-152].
        """
        path = self._path(hook_id)
        if not path.exists():
            raise FileNotFoundError(f"Webhook '{hook_id}' not found")
        existing = json.loads(path.read_text(encoding="utf-8"))
        existing.update(data)
        # Validate URL if it's being changed
        if "url" in data:
            _validate_webhook_url(data["url"])
        _atomic_write(path, json.dumps(existing, indent=2))
        result = existing.copy()
        result["secret"] = "***" if result.get("secret") else ""
        return result

    def delete(self, hook_id: str) -> None:
        """Delete a webhook config."""
        path = self._path(hook_id)
        if not path.exists():
            raise FileNotFoundError(f"Webhook '{hook_id}' not found")
        path.unlink()

    def get_all_for_event(self, event: str) -> list[WebhookConfig]:
        """Get all active webhooks subscribed to an event."""
        configs = []
        for path in self.hooks_dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            config = WebhookConfig(
                id=data["id"],
                url=data["url"],
                secret=data.get("secret", ""),
                events=data.get("events", list(WebhookEvent.ALL)),
                active=data.get("active", True),
                created_at=data.get("created_at", ""),
            )
            if config.matches_event(event):
                configs.append(config)
        return configs


def _sign_payload(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload [BLK-064]."""
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def dispatch_webhook(
    config: WebhookConfig,
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Send webhook payload with HMAC signature and retry [BLK-064].

    Args:
        config: Webhook configuration (URL, secret).
        event: Event type (e.g. "run.completed").
        payload: Webhook payload dict.

    Returns:
        Delivery result dict with status, attempts, and response.
    """
    full_payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    body = json.dumps(full_payload).encode("utf-8")

    # BLK-152: Validate URL at dispatch time (prevents DNS rebinding)
    try:
        _validate_webhook_url(config.url, resolve=True)
    except SSRFError as e:
        logger.warning("Webhook %s blocked by SSRF validation: %s [BLK-152]", config.id, e)
        return {
            "delivered": False,
            "status_code": 0,
            "attempts": 0,
            "error": "URL validation failed",
        }

    headers = {
        "Content-Type": "application/json",
        "X-ADEP-Event": event,
    }
    if config.secret:
        signature = _sign_payload(body, config.secret)
        headers["X-ADEP-Signature"] = signature

    attempts = 0
    last_error = ""

    for attempt in range(MAX_RETRIES):
        attempts += 1
        try:
            req = Request(
                config.url,
                data=body,
                headers=headers,
                method="POST",
            )
            with urlopen(req, timeout=WEBHOOK_TIMEOUT) as resp:
                status_code = resp.status
                if 200 <= status_code < 300:
                    return {
                        "delivered": True,
                        "status_code": status_code,
                        "attempts": attempts,
                    }
                last_error = f"HTTP {status_code}"
        except Exception as e:
            last_error = str(e)

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_BACKOFF_BASE ** attempt)

    logger.warning(
        "Webhook %s failed after %d attempts: %s [BLK-064]",
        config.id, attempts, last_error,
    )
    return {
        "delivered": False,
        "status_code": 0,
        "attempts": attempts,
        "error": last_error,
    }


def emit_webhook_event(
    event: str,
    payload: dict[str, Any],
    store: WebhookStore | None = None,
) -> list[dict[str, Any]]:
    """Emit a webhook event to all subscribed webhooks [BLK-064].

    Args:
        event: Event type (e.g. "run.completed").
        payload: Webhook payload dict.
        store: Webhook store (uses default if None).

    Returns:
        List of delivery results.
    """
    if store is None:
        store = WebhookStore()

    configs = store.get_all_for_event(event)
    results = []

    for config in configs:
        result = dispatch_webhook(config, event, payload)
        result["webhook_id"] = config.id
        results.append(result)

    return results


# Singleton
_store: WebhookStore | None = None


def get_webhook_store() -> WebhookStore:
    """Get the singleton WebhookStore instance."""
    global _store
    if _store is None:
        _store = WebhookStore()
    return _store
