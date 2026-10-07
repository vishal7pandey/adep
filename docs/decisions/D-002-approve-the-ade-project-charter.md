---
id: D-002
type: charter
title: Approve the ade project charter
status: proposed
jira: ADE-75
proposed_by: Claude (agent)
proposed_at: '2026-10-07'
options:
- text: Approve the charter in docs/PROJECT.md as written
  recommended: true
decision: null
by: null
at: null
delegated: false
subject: docs/PROJECT.md
---
# Approve the ade project charter

## Context

ADE-75 puts ade on the factory's project charter (FACT-47): a written definition of done, a non-goals list, a parked
list and a stop rule, so scope stops growing by default. The agent drafted `docs/PROJECT.md` from the open Jira tickets
and the scanner alerts as of 2026-10-07. Approving stamps the file's hash; any later edit, including the C1 bar, needs
a new charter decision.

## Evidence

- Purpose: ADEP extracts structured data from engineering documents with a simple agentic engine; first domain P&ID
  digitisation to DEXPI. Mode `active`.
- Done criteria and references (`factory status` shows them once approved; `jira` references show `unknown` until a
  lookup is wired):
  C1 new engine mean count recall at least 0.8 on the three DEXPI reference drawings, variance recorded: metric
  `docs/eval/pid-latest.json` key `mean_count_recall` (now 0.46, spread 0.11, 2026-10-05), ticket ADE-76 (new);
  C2 DEXPI XML export, `jira: ADE-14`; C3 the API can opt into the new engine, `jira: ADE-32`;
  C4 the new engine reports its own token usage, `jira: ADE-42`; C5 the old engine is retired, `jira: ADE-33`
  (see ADE-18 for which old skills survive); C6 no open critical or high security finding, `jira: ADE-78` (new umbrella
  over ADE-74, ADE-65 and ADE-77).
- Non-goals: porting the other 21 document skills (2 or 3 stay as proof of generality), SPICE export, retention cleanup,
  ruff and mypy debt beyond real defects.
- Parked, each labelled `parked` in Jira and left open: ADE-16, ADE-17, ADE-20, ADE-21.
- Open decision that feeds C6: D-001 (alert 52, ADE-74).
- New tickets created for this charter: ADE-76 (C1), ADE-77 (js-yaml high alert 8, found while checking C6), ADE-78 (C6
  umbrella).

## Options

1. **Approve as written (recommended).** ade gets an end (the six criteria) and a stop rule (maintenance mode: only
   security and dependency updates, anything else needs a charter amendment). Approval does not authorise ADE-33: that
   still needs your fresh go-ahead.
2. **Send it back** (`factory decide D-002 --reject --note "..."`): the agent revises `docs/PROJECT.md` and proposes
   again, for example with another bar for C1, other criteria, or a different parked list.

## Recommendation

Approve as written. The one number to check before you answer is the C1 bar of 0.8: if you want another bar, reject
with a note naming it, so it is settled before ADE-76 starts.
