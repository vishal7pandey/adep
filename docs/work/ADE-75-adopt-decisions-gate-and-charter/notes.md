# ADE-75 notes

## `factory doctor .` after the sync (2026-10-07, before the records existed)

```
OK    managed files                34 tracked, all present, unmodified
OK    skills .claude/skills        10 present
OK    skills .github/skills        10 present
OK    factory_version              0.1.0
OK    git                          repository found
OK    repo: secret scanning + push protection ok
OK    repo: dependabot alerts      ok
OK    repo: dependabot security updates ok
OK    repo: codeql default setup   ok
OK    sonar: properties            no placeholder left
OK    sonar: SONAR_TOKEN           present (name only; its value is never read)
WARN  deps: dependabot alerts      19 open (high 6, medium 10, low 3)
WARN  deps: code-scanning alerts   6 open (high 1, medium 5)
OK    deps: secret-scanning alerts 0 open
OK    deps: dependabot PRs         0 open
WARN  deps: dependabot updates     29 failed run(s) in the last 7 days
WARN  deps: needs attention        yes (7 critical/high alert(s) open; 29 failed Dependabot Updates run(s))
WARN  charter                      no approved charter: docs/PROJECT.md is still the template
doctor: 0 failure(s), 5 warning(s)
```

After the records were written the charter line reads `no approved charter: decision D-002 is waiting for the owner`
and two new `WARN decision` lines list D-001 and D-002 as waiting for the owner.

## Decisions made on the way

- Alert 52 is a `dismissal` record (option 1 is the subject); options 2 and 3 are the alternatives, and the record says an
  `--option 2|3` answer does not dismiss the alert.
- C6 points at a new umbrella ticket (ADE-78) because three groups of high alerts are open (CodeQL 52 / ADE-74, the LangChain
  stack / ADE-65, js-yaml alert 8 / new ADE-77) and a criterion takes exactly one reference.
- Found: Dependabot alert 8 (js-yaml, high) had no ticket: filed as ADE-77.
- `docs/eval/pid-latest.json` holds the baseline numbers as reported for 2026-10-05 (0.46, spread 0.11); it is not a new run.
- `factory status` in this repo still shows ADE-26 and ADE-55 as `in-review` on master although their PRs merged earlier; not
  changed here (out of scope), worth a small status-fix chore.
