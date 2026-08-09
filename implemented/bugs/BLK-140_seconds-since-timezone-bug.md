---
id: BLK-140
type: bug
title: "_seconds_since in auth.py uses localtime for UTC timestamp — breaks last_used_at throttling"
priority: medium
status: backlog
phase: 4
owner: backend
created: 2026-08-08T14:45:00+05:30
estimate: S
tags: [backend, bug, auth, timezone]
---

## Problem

`_seconds_since` in `src/api/auth.py` parses a UTC timestamp string
(suffix "Z") with `time.strptime`, then converts to epoch using
`time.mktime` — which interprets the struct_time as **local time**,
not UTC. This produces an incorrect seconds-since value offset by the
machine's timezone offset.

## Evidence

`src/api/auth.py:402-408`:

```python
def _seconds_since(timestamp: str) -> float:
    """Calculate seconds since a UTC timestamp string."""
    try:
        ts = time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        return time.time() - time.mktime(ts)
    except (ValueError, TypeError):
        return float("inf")
```

`time.mktime` treats `ts` as local time. On a machine in UTC+5:30
(e.g., IST), `time.mktime(ts)` returns a value ~5.5 hours *earlier*
than the correct UTC epoch, making `time.time() - time.mktime(ts)`
~19800 seconds *larger* than it should be.

The caller at line 395:
```python
if key.last_used_at is None or _seconds_since(key.last_used_at) > 60:
    key.last_used_at = now_ts
    store.update(key)
```

This means `last_used_at` will be updated on **every request** instead
of being throttled to every 60 seconds, causing an unnecessary file
write per API call.

## Impact

- `last_used_at` is updated on every authenticated request instead of
  every 60 seconds, causing unnecessary disk I/O on the API key store.
- In a deployment with many authenticated requests, this creates
  significant write amplification on the file-based key store.
- `last_used_at` timestamp stored in the key file will be inaccurate
  for audit purposes (updated too frequently).

## Reproduction or reasoning

1. Set `ADE_AUTH_ENABLED=true`
2. Make an authenticated API request
3. Check the API key JSON file — `last_used_at` is updated
4. Make another request within 60 seconds
5. Check again — `last_used_at` is updated again (should not be)
6. On a UTC+5:30 machine, `_seconds_since` returns ~19800+ instead of
   the actual elapsed seconds, so the `> 60` check always passes.

## Proposed resolution

Replace `time.mktime(ts)` with `calendar.timegm(ts)` which interprets
the struct_time as UTC:

```python
import calendar
return time.time() - calendar.timegm(ts)
```

## Acceptance criteria

- [ ] `_seconds_since` uses `calendar.timegm` instead of `time.mktime`
- [ ] `last_used_at` is only updated when >60 seconds have actually elapsed
- [ ] Unit test verifies correct behavior across timezone boundaries

## Validation plan

- Add test that sets `last_used_at` to a recent UTC timestamp and
  verifies `_seconds_since` returns a small value (<60)
- Test with `TZ=Asia/Kolkata` to verify timezone independence

## Related issues

None found.
