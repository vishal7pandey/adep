# ADE-74 — Bootstrap secret clear-text (CodeQL py/clear-text-logging-sensitive-data)

Status: draft · Risk: high · Jira: ADE-74
<!-- Security finding: neutral wording on purpose; this repo is public. -->

One code-scanning alert: 46, rule `py/clear-text-logging-sensitive-data` (high), `src/api/auth.py` lines 373-379, the `print(...)`
call in `bootstrap_admin_key` that shows the one-time bootstrap secret to the operator.

## Repro

Environment: `master` @ feeb9e7.

The code does not log the secret: the `logger.warning` call carries only `key_id`, and `test_bootstrap_secret_never_logged`
proves it. The secret is, by design, written once to stdout as an operator banner (BLK-186, BLK-188) because it cannot be
recovered later. CodeQL models the builtin `print` as a logging sink, so it reports the banner.

Automated repro: `src/tests/test_auth.py::TestBootstrap::test_bootstrap_secret_not_sent_through_print` fails on current code
(`print` is called with the secret). Command: `uv run python -m pytest src/tests/test_auth.py -q`.

Reproducibility: always (CodeQL reports it on every analysis of master).

## Expected

The secret reaches the operator exactly once on stdout, is never passed to a logging call or to `print`, and only the key id is
logged. Behaviour for the operator is identical (same banner text, flushed).

## Actual

The banner is emitted with `print(...)`, which the analyzer treats as logging of sensitive data.

## Root cause (with evidence)

- Where: `src/api/auth.py:372-381`.
- Why it fails: a one-time console banner and a log call are indistinguishable to the analyzer when both use `print`/`logging`.
  The banner is a deliberate, documented exposure; the finding is real in the narrow sense that a `print` goes to whatever stdout
  is attached to (the console, or a container log if stdout is captured).
- Introduced by: BLK-186/BLK-188 (moved the secret from the logger to stdout); always present since.
- Evidence: alert 46 state `open`, `most_recent_instance` lines 373-379, message "This expression logs sensitive data (secret)
  as clear text".

## Blast radius

Single caller path: `install_auth_middleware` -> `bootstrap_admin_key` on first start with auth enabled and no keys. No other
place emits a secret (`ApiKeyStore.create` logs the key id only).

## Regression criterion (AC1)

AC1: The banner (key id and secret) is written to stdout once through `sys.stdout.write` and `flush`, `print` is not called with the
secret, nothing is logged that contains the secret, and the existing tests
(`test_bootstrap_secret_printed_to_stdout`, `test_bootstrap_secret_never_logged`) stay green. The new test
`test_bootstrap_secret_not_sent_through_print` fails on the current code and passes after the fix.

AC2: After the merge and the push scan, `gh api repos/vishal7pandey/adep/code-scanning/alerts/46` reports `fixed`, and the PR
CodeQL result check shows no new alert. If CodeQL still reports the stdout write, no dismissal is applied: a proposal (alert URL,
reason `won't fix` or `false positive`, test evidence) goes to the owner on ADE-74.

## Fix constraints

- Change `bootstrap_admin_key` only. Same banner text, still flushed, still once, secret still returned to the caller.
- Do not log the secret and do not weaken `test_bootstrap_secret_never_logged`.
- Do not add a new place that stores the secret (no file, no env var).

## Risks

Risk high (auth code), diff tiny. The honest limit: writing to stdout is still exposure if stdout is captured by a log shipper;
that is the existing, documented trade-off (operator must see the secret once). Rollback: revert the merge commit.
