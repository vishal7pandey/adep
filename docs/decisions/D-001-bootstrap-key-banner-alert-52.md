---
id: D-001
type: dismissal
title: Dismiss CodeQL alert 52, the one-time bootstrap admin key banner (ADE-74)
status: proposed
jira: ADE-74
proposed_by: Claude (agent)
proposed_at: '2026-10-07'
alert: https://github.com/vishal7pandey/adep/security/code-scanning/52
reason: won't fix
options:
- text: "Dismiss the alert in CodeQL as won't fix: the one-time console banner is documented and intended"
  recommended: true
- text: "Do not dismiss; print the secret only when stdout is a terminal, otherwise write it to a mode-0600 file and print the file path"
- text: "Do not dismiss; always write the secret to a mode-0600 file and print only its path"
decision: null
by: null
at: null
delegated: false
---
# Dismiss CodeQL alert 52, the one-time bootstrap admin key banner (ADE-74)

## Context

On first start with no API keys, `bootstrap_admin_key` in `src/api/auth.py` creates an admin key and shows its secret
once to the operator, because the secret cannot be recovered later (only its hash is stored). ADE-74 (PR 40) already
moved the write out of `print` and out of the logging framework, but CodeQL still reports the new line as alert 52.
The owner must choose between accepting this documented exposure and changing how the secret reaches the operator.
Work item: `docs/work/ADE-74-bootstrap-secret-clear-text/` (merged); the successor alert is why ADE-74 is still open.

## Evidence

- Alert: https://github.com/vishal7pandey/adep/security/code-scanning/52, rule `py/clear-text-logging-sensitive-data`,
  high, `src/api/auth.py:375` (`sys.stdout.write(...)` of the banner). The earlier alert 46 was the same banner written
  with `print` and was closed by ADE-74; CodeQL treats a stdout write like `print`.
- The logger never receives the secret: the `logger.warning` call carries only `key_id`; the test
  `test_bootstrap_secret_never_logged` proves it. Only the hash of the secret is stored.
- The banner is the only place the secret appears, once, on the operator's console, and says so ("shown ONLY ONCE").
- ade is a local, single-operator tool (`docs/PROJECT.md` proposal). If stdout is captured (a container log, a service
  manager), the secret reaches that log: that is the real residual exposure behind the alert.

## Options

1. **Dismiss as won't fix (recommended).** No code change. The alert is closed in CodeQL with the reason and a link to
   this record. Cost: the exposure remains for anyone who runs ade with stdout captured, and CodeQL will not warn again
   on this line. Closes off nothing; the code can still be changed later.
2. **Terminal-only print, otherwise a 0600 file.** Print the banner only when `sys.stdout.isatty()`; otherwise write the
   secret to a file created with mode 0600 and print its path. Cost: a small code change and tests (a new bug work
   item), a new file to delete, and a different first-run experience in containers. CodeQL may still flag the
   terminal branch, so the alert might need dismissing anyway.
3. **Always write to a 0600 file.** The secret never touches stdout, only the path does. Cost: the same code change, a
   file that holds a secret in clear text on disk until the operator removes it, and a slower first run for the demo
   path. On Windows the file mode is not enforced the same way.

Accepting option 2 or 3 (`--option 2` or `--option 3`) means the alert is NOT dismissed: an agent then opens a bug work
item for the code change. Only option 1 authorises the dismissal.

## Recommendation

Option 1: the banner is a deliberate one-time disclosure to the person who owns the machine, the secret is not logged or
stored, and a local single-operator tool gains little from a file that holds the same secret in clear text instead.
