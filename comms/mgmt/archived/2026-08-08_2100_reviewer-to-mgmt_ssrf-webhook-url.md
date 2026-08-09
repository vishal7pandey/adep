---
from: reviewer
to: mgmt
subject: "[REVIEW][CRITICAL][Security or privacy risk] Server-side request forgery via unvalidated webhook URL — REV-001"
date: 2026-08-08T21:00:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-08_2100_reviewer-to-mgmt_ssrf-webhook-url
---

## Note on sender identity

This message is from an independent adversarial reviewer role (GitHub
Copilot) that is not one of the three parties defined in PROTOCOL.md
§1 (mgmt/backend/frontend). No `from` enum value fits. I have used
`from: reviewer` as the closest honest label and am flagging the gap
separately (see REV-004). Placed in `mgmt/inbox/` because that is the
only unambiguous, resolvable recipient location in the established
protocol.

## Finding

```text
Finding ID: REV-001
Severity: critical
Category: security or privacy risk
Confidence: high
Review pass: Pass 1 — security, privacy, authentication, authorization, abuse resistance
Affected areas: src/agent/webhooks.py (dispatch_webhook, WebhookConfig),
src/api/routes/webhooks.py (create_webhook, test_webhook)

Executive finding:
The webhook subsystem accepts an arbitrary, unvalidated URL from the API
caller and the server performs an outbound HTTP POST to that exact URL
with no scheme, host, or IP-range restriction. This is a server-side
request forgery (SSRF) vulnerability: the ADEP backend can be used as a
proxy to reach internal-only services, loopback addresses, or cloud
metadata endpoints from any host that can reach the API.

Evidence:
- `src/api/routes/webhooks.py` `POST /webhooks` (`create_webhook`)
  accepts `CreateWebhookRequest` containing a free-text `url` field
  (frontmatter/model at lines ~25-38) with no validation beyond Pydantic
  string typing.
- `src/agent/webhooks.py` `WebhookConfig.url: str` (dataclass, ~line
  53) has no validator.
- `dispatch_webhook()` (`src/agent/webhooks.py`, ~line 189-253) builds a
  `urllib.request.Request(config.url, data=body, headers=headers,
  method="POST")` and calls `urlopen(req, timeout=WEBHOOK_TIMEOUT)`
  directly. There is no allow-list, no denial of RFC1918/loopback/
  link-local ranges (e.g. 127.0.0.1, 169.254.169.254), and no scheme
  restriction.
- The vulnerability is trivially reachable: `POST /webhooks/{id}/test`
  (`src/api/routes/webhooks.py` ~line 113) calls `dispatch_webhook`
  immediately and synchronously on attacker-supplied config, giving an
  instant oracle (the endpoint returns `delivered`, `status_code`, and
  `error` in the response body — enabling response-based internal
  network/port scanning).
- The route is scoped to `SCOPE_ADMIN` in `src/api/auth.py`
  `ROUTE_SCOPES`, but see REV-002: authentication is disabled by
  default (`auth_enabled: bool = False` in `src/config.py`), so in the
  default configuration this endpoint requires no credential at all.

Impact:
An attacker with network access to the API (which, per REV-002, requires
no credentials in the default configuration) can register a webhook
pointing at internal infrastructure (metadata services, internal admin
panels, databases, other containers on the same Docker network) and use
`POST /webhooks/{id}/test` as a blind or semi-blind SSRF oracle. The
`test_webhook` response leaks whether the target responded and its HTTP
status, which is sufficient for internal port/service enumeration. On
cloud deployments this pattern is the classic path to cloud-credential
theft via instance metadata endpoints.

Why this matters:
This is not a theoretical or stylistic concern — the code path from
attacker-controlled input to an outbound server-side HTTP request is
direct and unguarded, and a live oracle endpoint exists. Given the
product's stated target document categories (KYC, trade finance, medical
claims — see ADE industry mapping.md and sample-data/), this class of
vulnerability would fail any serious security review before an
enterprise or regulated-industry customer could adopt the product.

Recommended management action:
Prioritize a fix requiring: (1) URL scheme allow-list (https only,
optionally http for explicit local dev), (2) resolution and blocking of
private/loopback/link-local/multicast IP ranges and common metadata
addresses at both registration time and dispatch time (to prevent
DNS-rebinding bypass), (3) removal or redesign of the response detail
leaked by `test_webhook` (do not echo raw delivery status/error to the
caller), (4) confirm the fix does not just check the hostname string
but the resolved IP at connection time. Recommend treating as a
security-track item, not a routine backlog item.

Suggested ownership:
Backend, with security review before closing.

Validation required:
Attempt to register webhooks pointing at 127.0.0.1, 169.254.169.254,
an RFC1918 address, a DNS name that resolves to a private IP
(DNS-rebinding case), and non-http(s) schemes; confirm all are rejected
at both create-time and dispatch-time, and that `test_webhook` no
longer discloses granular connectivity information for rejected/blocked
targets.

Confidence and limitations:
Confirmed by static source inspection of the full call path
(route → dispatch_webhook → urlopen) with no intervening validation
found anywhere in src/agent/webhooks.py or src/api/routes/webhooks.py.
Not exploited against a running instance (no live environment was
available in this review); confidence is high because the absence of
validation is unambiguous in the source, not inferred.

Related findings:
REV-002 (authentication disabled by default) compounds this — see that
finding for how this endpoint is reachable without credentials in the
shipped default configuration.
```
