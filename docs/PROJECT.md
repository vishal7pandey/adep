---
# The charter of ade, a proposal for the owner. It is approved only through decision record D-002
# (`factory decide D-002 --accept`, run by the owner); until then `factory doctor` says "no approved charter".
# The recall bar in C1 (0.8) is the agent's proposal: it is the owner's number to change.
purpose: "ADEP extracts structured data from engineering documents with a simple agentic engine (a loop that calls a model with tools and a skill). The first domain is P&ID digitisation to DEXPI."
mode: active
decision: D-002
done:
  - id: C1
    text: "The new engine's mean count recall on the three DEXPI reference P&IDs is at least 0.8, with the variance recorded (ADE-76)"
    check: {metric: {file: docs/eval/pid-latest.json, key: mean_count_recall, min: 0.8}}
  - id: C2
    text: "A P&ID extraction can be exported as DEXPI XML (ADE-14)"
    check: {jira: ADE-14}
  - id: C3
    text: "The API can opt into the new engine through a setting (ADE-32)"
    check: {jira: ADE-32}
  - id: C4
    text: "The new engine reports its own token usage correctly on a real run (ADE-42)"
    check: {jira: ADE-42}
  - id: C5
    text: "The old engine is retired, after the owner decides which old skills survive (ADE-33, ADE-18)"
    check: {jira: ADE-33}
  - id: C6
    text: "No critical or high security finding is open (umbrella ADE-78: ADE-74, ADE-65, ADE-77)"
    check: {jira: ADE-78}
non_goals:
  - "Porting the other 21 old document skills; 2 or 3 stay as proof that the engine is general"
  - "SPICE netlist export (ADE-16)"
  - "Retention cleanup of run data and uploaded documents (ADE-17)"
  - "Clearing the ruff and mypy backlog beyond real defects (ADE-20, ADE-21)"
parked:
  - {item: "SPICE netlist exporter and schematic-to-spice skill", jira: ADE-16}
  - {item: "Retention cleanup for run data and uploaded documents", jira: ADE-17}
  - {item: "1043 ruff errors in src/ (only the real defects among them are worked)", jira: ADE-20}
  - {item: "183 mypy errors in src/ (only the real defects among them are worked)", jira: ADE-21}
---
# The ade charter

ade is finished as a first version when the six criteria above are met: the new engine reaches the agreed P&ID
recall bar (C1), exports DEXPI (C2), is reachable from the API (C3) and accounts for its own tokens (C4), the old
engine is gone (C5), and no critical or high security finding is open (C6). C1 to C5 are the work; C6 is the
condition under which it may be called done.

Two things in this proposal are the owner's to decide and are flagged on purpose:

* The bar in C1, 0.8 mean count recall, is a proposal. The baseline is 0.46 with a spread of 0.11 (2026-10-05, three
  reference drawings). Change it with a new charter decision before ADE-76 starts, not after a run.
* C5 needs the owner's fresh go-ahead for ADE-33 (deleting the old engine and the Python skill classes), and a choice
  of which old skills survive (ADE-18). The charter does not give either; it only says they must happen.

The `jira` references (C2 to C6) are read by `factory status` only when a Jira lookup is wired; until then they show
`unknown`, not met. The parked list is what the owner has deliberately not asked for; each ticket carries the label
`parked` and stays open.

## Maintenance mode

When every done criterion is met the project enters maintenance mode (`mode: maintenance`, approved through a new
charter decision). In maintenance mode only security and dependency updates are made, through the findings and
dependency loops (`factory-findings`, `factory-dependencies`). Any other change needs a charter amendment: a new
charter decision the owner accepts. `factory feature start` warns, but does not block, so the owner can proceed
deliberately.
