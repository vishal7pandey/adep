# BLK-152: SSRF via unvalidated webhook URL

**ID:** BLK-152
**Source:** REV-001 (independent reviewer)
**Severity:** Critical
**Category:** Security
**Status:** Done
**Assigned to:** Backend
**Estimate:** M

## Problem

The webhook subsystem accepts arbitrary, unvalidated URLs from the API
caller and performs an outbound HTTP POST to that URL with no scheme,
host, or IP-range restriction. This is a server-side request forgery
(SSRF) vulnerability.

An attacker can register a webhook pointing at internal infrastructure
(127.0.0.1, 169.254.169.254, RFC1918 ranges, internal admin panels)
and use `POST /webhooks/{id}/test` as a blind or semi-blind SSRF oracle.
The `test_webhook` response leaks `delivered`, `status_code`, and
`error`, enabling internal port/service enumeration.

Compounded by REV-002 (auth disabled by default) — the endpoint requires
no credentials in the shipped default configuration.

## Evidence

- `src/api/routes/webhooks.py` `create_webhook` accepts free-text `url`
  with no validation beyond Pydantic string typing.
- `src/agent/webhooks.py:231` — `urlopen(req, timeout=WEBHOOK_TIMEOUT)`
  with no allow-list, no private IP blocking, no scheme restriction.
- `src/api/routes/webhooks.py:113` — `test_webhook` calls
  `dispatch_webhook` synchronously, returning delivery status.

## Resolution

1. URL scheme allow-list: `https` only (optionally `http` for explicit
   local dev with a warning).
2. Resolve hostname and block private/loopback/link-local/multicast IP
   ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16,
   169.254.0.0/16, 0.0.0.0/8, ::1, fc00::/7, fe80::/10).
3. Block common metadata endpoints (169.254.169.254).
4. Validate at both registration time AND dispatch time (prevent DNS
   rebinding).
5. Redesign `test_webhook` response to not leak granular connectivity
   info for blocked targets.

## Tests

- Register webhook pointing at 127.0.0.1 → rejected
- Register webhook pointing at 169.254.169.254 → rejected
- Register webhook pointing at RFC1918 address → rejected
- Register webhook with `file://` scheme → rejected
- Register webhook with DNS name resolving to private IP → rejected
- Valid HTTPS URL → accepted
- `test_webhook` on blocked URL → generic error, no status code leak
