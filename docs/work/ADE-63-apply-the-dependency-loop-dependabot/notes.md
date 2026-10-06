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
