---
id: BLK-150
type: bug
title: "test_webhook endpoint sends without HMAC signature — secret masked, dead variable"
priority: medium
status: done
started: 2026-08-08T16:30:00+05:30
completed: 2026-08-08T16:45:00+05:30
phase: 4
owner: backend
created: 2026-08-08T14:55:00+05:30
estimate: S
tags: [backend, bug, webhooks, security, dead-code]
---

## Problem

`POST /webhooks/{webhook_id}/test` in `src/api/routes/webhooks.py`
constructs a `WebhookConfig` with `secret=""` (line 127), meaning the
test webhook is dispatched without an HMAC signature. The recipient
cannot verify the payload authenticity. Additionally, `full_data`
(line 123) is assigned but never used — a dead variable.

## Evidence

`src/api/routes/webhooks.py:113-140`:

```python
@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str) -> dict[str, Any]:
    try:
        store = get_webhook_store()
        data = store.get(webhook_id)       # masks secret → "***"
    except FileNotFoundError:
        raise HTTPException(...)

    # Load full config (with secret)
    full_data = store.get(webhook_id)      # ALSO masks secret — dead var
    config = WebhookConfig(
        id=data["id"],
        url=data["url"],
        secret="",                         # ← always empty!
        events=data.get("events", list(WebhookEvent.ALL)),
        active=data.get("active", True),
    )

    result = dispatch_webhook(config, "run.completed", test_payload)
```

`WebhookStore.get()` at `src/agent/webhooks.py:113-121`:
```python
def get(self, hook_id: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["secret"] = "***" if data.get("secret") else ""  # masked!
    return data
```

`dispatch_webhook` at `src/agent/webhooks.py:204-206`:
```python
if config.secret:
    signature = _sign_payload(body, config.secret)
    headers["X-ADEP-Signature"] = signature
```

Since `config.secret` is always `""` in the test endpoint, the
`X-ADEP-Signature` header is never set.

## Impact

- Test webhooks are sent without HMAC signatures, so recipients that
  verify signatures will reject them — making the test feature useless
  for validating webhook configuration.
- Users may incorrectly conclude their webhook is broken when the
  actual issue is the missing signature.
- The dead `full_data` variable suggests the developer intended to
  load the unmasked secret but called `store.get()` (which masks)
  instead of reading the file directly.

## Reproduction or reasoning

1. Create a webhook with a secret: `POST /webhooks` with `secret: "abc123"`.
2. Call `POST /webhooks/{id}/test`.
3. Inspect the received payload — no `X-ADEP-Signature` header.

## Proposed resolution

Read the webhook config file directly to get the unmasked secret, or
add a `get_with_secret()` method to `WebhookStore`:

```python
# In WebhookStore:
def get_raw(self, hook_id: str) -> dict[str, Any]:
    """Get webhook config with unmasked secret (internal use only)."""
    path = self._path(hook_id)
    if not path.exists():
        raise FileNotFoundError(...)
    return json.loads(path.read_text(encoding="utf-8"))

# In test_webhook endpoint:
raw = store.get_raw(webhook_id)
config = WebhookConfig(
    id=raw["id"], url=raw["url"],
    secret=raw.get("secret", ""),
    events=raw.get("events", list(WebhookEvent.ALL)),
    active=raw.get("active", True),
)
```

Remove the dead `full_data` variable.

## Acceptance criteria

- [ ] Test webhook includes `X-ADEP-Signature` header when secret is set
- [ ] Dead `full_data` variable removed
- [ ] No double `store.get()` call
- [ ] Test for `POST /webhooks/{id}/test` endpoint added

## Validation plan

- Create webhook with secret, call test endpoint
- Verify received payload has `X-ADEP-Signature` header
- Verify signature matches HMAC-SHA256 of payload with the secret

## Related issues

BLK-064 (webhook notifications feature)
