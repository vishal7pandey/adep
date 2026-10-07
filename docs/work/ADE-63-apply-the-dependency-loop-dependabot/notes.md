# ADE-63 notes

Date: 2026-10-06

## Dependency status

`factory status` for `vishal7pandey/adep` reported:

| Source | Open |
|---|---:|
| Dependabot alerts | 29 (9 high, 14 medium, 6 low) |
| Code-scanning alerts | 40 (35 high, 5 medium) |
| Secret-scanning alerts | 0 |
| Dependabot PRs | 0 |
| Failed Dependabot Updates runs, last 7 days | 27 |

The summary reports `needs attention` because 44 critical/high alerts and 27 failed update runs
remain. This is a read-only snapshot; no alerts were dismissed.

## Dependabot configuration

`factory sync` (without `--force`) created `.github/dependabot.yml`. `factory sync --check` reports
the repo in sync and `factory verify` reports OK. PyYAML confirms exactly three weekly ecosystems:
`uv` at `/`, `npm` at `/frontend`, and `github-actions` at `/`; each has a `minor-and-patch` group.
There are no `ignore` or `allow` entries.

## PR triage

`gh pr list --author app/dependabot --state open` returned zero open PRs at triage time. No PR was
merged. Recheck after this configuration reaches the default branch, since scheduled version-update
PRs may then appear. Other open PRs are outside this Dependabot-only triage.

## Failed update runs

### npm / `source-map-js`

Runs including `37498178970` fail with `security_update_not_possible`: Dependabot reports latest
resolvable `source-map-js` 1.2.1 versus first fixed 1.2.2, with no conflicting dependencies.
Registry metadata shows the three lockfile parents (`@tailwindcss/node@4.3.3`, `css-tree@3.2.1`,
and `postcss@8.5.23`) each accept `^1.2.1`, and 1.2.2 was published on 2026-09-30. In a scratch
copy of the frontend manifests, `pnpm update source-map-js --lockfile-only` using pnpm 11.22.0
successfully resolved all references to 1.2.2. This points to a Dependabot updater resolution
failure rather than a repository constraint. Filed ADE-64 for the explicit lockfile remediation;
the lockfile fix is not included in ADE-63.

### uv / LangChain, LangGraph, and pydantic-ai

Run `37498178985` reports `security_update_not_possible` for `langgraph-sdk`: latest resolvable
0.1.74 versus first fixed 0.4.4. `pyproject.toml` intentionally caps the legacy stack, including
`langgraph<0.3.0`, `langchain<0.4.0`, `langchain-openai<0.3.0`, and `pydantic-ai<2.0.0` pending
ADE-33. A scratch `uv lock --upgrade-package langgraph-sdk==0.4.4` could not apply the patched
version while satisfying those constraints. This is a project dependency constraint, not a
Dependabot configuration problem. Filed ADE-65; the alert set remains open until the engine
retirement permits compatible upgrades.

No dependency constraints were broadened and no alerts were dismissed as part of ADE-63.

## After the merge (2026-10-07)

PR #25 merged the sync and `dependabot.yml`. Dependabot then opened version-update PRs, which a human
reviewed and merged on 2026-10-06; none was merged by an agent:

| PR | Change | Files | Kind | Under `dependencies.md` |
|---|---|---|---|---|
| #26 | minor-and-patch group, 6 updates (uv) | `pyproject.toml`, `uv.lock` | minor/patch | would qualify (scheduled, manifest and lockfile only) |
| #27 | minor-and-patch group, 13 updates (`/frontend`) | `package.json`, `pnpm-lock.yaml` | minor/patch | would qualify |
| #28 | `paddleocr` 2.10.0 to 3.7.0 | `pyproject.toml`, `uv.lock` | major | not eligible; regression found, ADE-70 |
| #29 | `@types/node` 20.19.43 to 26.6.4 | `package.json`, `pnpm-lock.yaml` | major | not eligible; assessed in ADE-66, no regression |
| #30 | `typescript` 5.9.3 to 6.0.3 | `package.json`, `pnpm-lock.yaml` | major | not eligible; frontend build and tests green, assessed with ADE-66 |

At this writing no Dependabot PR is open. `factory status` on master: Dependabot alerts 22 open (7 high,
12 medium, 3 low; was 29), code scanning 39 open, secret scanning 0, Dependabot PRs 0 open, 28 failed
`Dependabot Updates` runs in 7 days (the ADE-64 and ADE-65 causes remain), needs attention yes.
Merging the majors is the owner's call and the policy does not restrict it; the review of the three
found one real regression (ADE-70: the paddleocr 3.x constructor rejects `show_log`; the unit tests mock
the engine, so green CI did not show it).
