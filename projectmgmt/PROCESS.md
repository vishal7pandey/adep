# Project Management Process

> The authoritative process for managing work items in the ADEP project.
> Covers backlog management, item lifecycle, prioritization, and the
> communication cadence that keeps all parties aligned.
>
> **v2 (2026-08-09).** Rewritten for the 5-party structure (mgmt, devin,
> antigravity, cline, opencode) — see `comms/PROTOCOL.md` for the full
> rationale and `REMEDIATION_PLAN.md` for the current work plan. The
> single most important change: **status is no longer self-reported.**
> An item is not `done` until independently verified by someone other
> than the implementer (PROTOCOL §7.1). Treat every pre-2026-08-09
> `implemented/` item as **unverified-but-plausible**, not confirmed —
> see REMEDIATION_PLAN.md §0 for the retroactive verification sweep.
>
> **v2.1 (2026-08-09, 16:00).** cline's dedicated verification-gate
> mandate is suspended (it overclaimed a test result and stalled
> verifying nothing in its queue — see STATUS.md). Verification is now
> **cross-team**: devin verifies antigravity's work, antigravity verifies
> devin's, with mgmt spot-checks as a compensating control. Every
> "cline" reference below describing the verification step now means
> "the other implementing team" — left in place where it illustrates the
> mechanism rather than the specific party.

---

## 1. Directory Structure

```
backlog/
  features/         ← new capabilities (e.g., "Add table detection tool")
  bugs/             ← defects in shipped code
  ideas/            ← exploratory proposals, not yet committed to
  tech-debt/        ← refactoring, cleanup, architecture improvements
  in-progress/      ← items currently being worked on (moved from any category)
implemented/
  features/
  bugs/
  ideas/
  tech-debt/
projectmgmt/
  PROCESS.md        ← this file
  ITEM-TEMPLATE.md  ← copy this when creating a new backlog item
  STATUS.md         ← live status board: what's in-progress, what's next
```

---

## 2. Backlog Item Format

Every backlog item is a `.md` file with YAML frontmatter + a structured body.
Copy `ITEM-TEMPLATE.md` to start a new item.

### 2.1 Frontmatter Schema

```yaml
---
id: BLK-001                      # unique ID: BLK-<number>. mgmt-issued only (PROTOCOL §7.3)
type: feature                    # feature | bug | idea | tech-debt
title: "Add table detection tool"
priority: high                   # critical | high | medium | low
status: backlog                  # backlog | in-progress | verifying | done
phase: 1                         # vision.md phase, or "remediation"
owner: devin                     # mgmt | devin | antigravity | opencode | unassigned (cline suspended, v2.1)
verified-by: null                # set to the verifying team's name (+ date) once independently verified
created: 2026-08-07T20:30:00+05:30
started: null                    # ISO timestamp when moved to in-progress
completed: null                  # ISO timestamp when the verifying team closes and moves to implemented
estimate: null                   # S / M / L / XL (t-shirt sizing)
depends-on: []                   # list of BLK-IDs this item depends on
tags: [tools, perception]
---
```

`status: verifying` is new: the implementing party sets this (not `done`)
when it believes the work is complete and has handed it to the *other*
implementing team (devin↔antigravity, v2.1). Only the verifying team may
change `verifying` → `done`, and never for its own item.

### 2.2 Body Structure

```markdown
## Description
<What and why. Concrete and actionable.>

## Acceptance Criteria
- [ ] <Criterion 1>
- [ ] <Criterion 2>

## Constraints
<Deadlines, technical constraints, things to avoid.>

## Dependencies
<Other BLK-IDs that must be done first, or external dependencies.>

## Notes
<References, links, additional context.>

## Implementation Log
<Appended as work progresses. Each entry: timestamp + author + update.>
```

### 2.3 Resolution Section (added before moving to implemented/)

```markdown
## Resolution
<What was done. Outcome. Files changed. Follow-up items spawned.>
```

---

## 3. Item Lifecycle

```
backlog/<category>/  →  backlog/in-progress/  →  implemented/<category>/
     (pending)             (being worked on)          (done)
```

### 3.1 Creating an Item

1. **Anyone may propose** an item, but **only mgmt creates the file and
   assigns the ID** (PROTOCOL §7.3 — this is the fix for the 30 BLK-ID
   collisions the 2026-08-09 audit found from uncoordinated parallel
   filing). Send the proposal to `mgmt/inbox/`; do not create the file
   yourself.
2. mgmt uses the next available `BLK-NNN` ID (checked against the whole
   `backlog/` tree, including `implemented/`, not just the target category).
3. mgmt copies `ITEM-TEMPLATE.md`, sets `status: backlog`, `owner:` to the
   likely team (or `unassigned`), and notifies the relevant parties.

### 3.2 Starting Work (backlog → in-progress)

1. **mgmt assigns** the item by setting `owner` and moving the file from
   `backlog/<category>/` to `backlog/in-progress/`.
2. Update `status: in-progress` and set `started` timestamp.
3. The assigned party sends a comms message acknowledging they've picked it up.
4. **If blocked**: set `status: blocked` in frontmatter, add a note to the
   Implementation Log, and send a comms message to `mgmt/inbox/` explaining
   the blocker.

### 3.3 Completing Work (in-progress → verified → implemented)

**Revised 2026-08-09 16:00 (v2.1).** This step originally routed through
a dedicated verification party (cline). That mandate is suspended — it
overclaimed a test result and stalled without verifying anything in its
queue — so verification is now **cross-team**: the implementing party's
peer (the *other* implementing team) verifies instead of a third party.
The mandatory hop itself is unchanged; only who performs it changed.

1. The owner appends `## Resolution` **and** `## Evidence` (PROTOCOL §7.2 —
   exact test/curl output or file:line references, not prose claims).
2. Sets `status: verifying` (**not** `done` — the implementer cannot mark
   its own item done) and sends the item to the **other** implementing
   team's inbox: devin → antigravity's items, antigravity → devin's.
3. **The verifying party independently reproduces** the acceptance
   criteria — runs the test, hits the endpoint, reads the diff. It does
   not accept the Resolution text as evidence of itself.
4. If the item is tagged `security`, the verifier also routes it to
   `opencode/inbox/` for the mandatory co-sign (PROTOCOL §7.4) before it
   can close.
5. On success: the verifier sets `status: done`, `completed` timestamp,
   `verified-by: <team> (date)`, appends `## Verified by <team>`
   describing what it independently confirmed, and moves the file to
   `implemented/<category>/`.
6. On failure: the verifier sets `status: in-progress`, replies to the
   implementer's comms message with exactly what didn't hold up, and the
   item returns to step 1.
7. The verifier notifies `mgmt/inbox/` either way; mgmt updates
   `projectmgmt/STATUS.md` only from verified completions, and performs
   its own periodic spot-checks on top (the compensating control for
   cross-team verification being weaker than a dedicated gate — see
   PROTOCOL §7.1).

### 3.4 Rejecting or Deferring an Item

1. **mgmt** may reject or defer a backlog item.
2. To reject: append a `## Resolution` section stating "Rejected: <reason>",
   set `status: done`, move to `implemented/<category>/`.
3. To defer: change `priority: low` and add a note in the Notes section.
   The item stays in `backlog/<category>/`.

---

## 4. Prioritization

mgmt owns the priority of every backlog item. Priorities are:

| Priority  | Meaning                                                    |
|-----------|------------------------------------------------------------|
| critical  | Blocking all other work. Drop everything.                  |
| high      | Required for the current phase. Do next.                   |
| medium    | Valuable for the current phase but not blocking.           |
| low       | Nice-to-have. Deferred to a later phase.                   |

### 4.1 Phase Alignment

Items are tagged with a `phase` (1-4, or `remediation` for the current
work — see `REMEDIATION_PLAN.md`) matching the vision.md phases:

| Phase | Focus                  | Primary Owner(s) |
|-------|------------------------|-------------------|
| remediation | Fix the house of cards (current) | devin, antigravity, cline, opencode |
| 1     | Engine (extraction)    | devin       |
| 2     | Platform API           | devin       |
| 3     | Frontend UI            | antigravity |
| 4     | Polish & Scale         | all four    |
| 5     | ADAS / Agentic Builder | **frozen** (PROTOCOL §7.8) until remediation P0/P1 clears |

mgmt sequences phases. Phase 2 items are not started until Phase 1 is
signed off (see RACI.md §Phase Gate Authority). Exceptions require mgmt
approval via comms.

---

## 5. Communication Cadence ("Overcommunicate")

### 5.1 The Rule

**Everyone overcommunicates.** Silence is the enemy. If you're working on
something, say so. If you're blocked, say so. If you finished something,
say so. If you have an idea, write it up. If you disagree, speak up.

### 5.2 Required Communications

| Event                          | Who       | Action                                    |
|-------------------------------|-----------|-------------------------------------------|
| New item proposed              | Proposer  | Comms message to `mgmt/inbox/` (mgmt files it, §3.1) |
| Item assigned to a party       | mgmt      | Comms message to assignee's inbox         |
| Work started on an item        | Assignee  | Comms message to mgmt/inbox/ acknowledging|
| Blocked on an item             | Assignee  | Comms message to mgmt/inbox/ + blocker's  |
|                               |           | inbox if another party is the blocker     |
| Item marked `verifying`        | Assignee  | Comms message to the *other* implementing team's inbox with Resolution + Evidence |
| Item tagged `security` reaches `verifying` | Verifier | Comms message to `opencode/inbox/` for co-sign |
| Item verified & closed         | Verifier  | Comms to implementer + `mgmt/inbox/`; mgmt updates STATUS.md |
| Item bounced back              | Verifier  | Comms to implementer explaining exactly what didn't hold up |
| Item rejected or deferred      | mgmt      | Comms message to proposer's inbox         |
| Phase gate decision            | mgmt      | Comms to all active team inboxes          |
| Status board updated           | mgmt      | Comms to all active inboxes noting what changed |

### 5.3 Status Board

`projectmgmt/STATUS.md` is the live dashboard. mgmt updates it whenever:
- An item is assigned, started, completed, or blocked.
- A phase gate is passed.
- Priorities change.

All parties should read STATUS.md at the start of each work session.

### 5.4 Weekly Summary (or per-session)

At the end of each work session or significant milestone, the working party
sends a comms message to `mgmt/inbox/` with:
- What was accomplished (BLK-IDs completed or progressed).
- What's in progress (BLK-IDs still being worked on).
- Blockers or concerns.
- Next planned items.

---

## 6. Backlog Categories

| Category    | When to use                                              |
|------------|----------------------------------------------------------|
| features   | New capabilities the platform will gain.                 |
| bugs       | Defects in code that has been shipped or is in use.      |
| ideas      | Proposals that haven't been committed to. Exploratory.   |
| tech-debt  | Refactoring, cleanup, architecture improvements.         |

### 6.1 Ideas → Features

An `idea` may be promoted to a `feature` by mgmt:
1. mgmt reviews the idea and decides to commit.
2. Move the file from `backlog/ideas/` to `backlog/features/`.
3. Update `type: feature` in frontmatter.
4. Assign a priority and phase.
5. Send comms to the proposer and relevant team.

---

## 7. Who Can Do What

**Revised 2026-08-09 16:00 (v2.1) — cline suspended, verification is now cross-team (§3.3).**

| Action                         | mgmt | devin | antigravity | opencode |
|---------------------------------|------|-------|-------------|----------|
| Propose a backlog item          | Yes  | Yes   | Yes         | Yes      |
| Create the file / assign BLK-ID | Yes  | No    | No          | No       |
| Assign an item's owner          | Yes  | No    | No          | No       |
| Change priority                 | Yes  | No    | No          | No       |
| Start work on assigned item     | Yes* | Yes   | Yes         | Yes      |
| Mark an item `verifying`        | No   | Yes (own items) | Yes (own items) | Yes (own items) |
| Verify the *other* team's `verifying` item | No | Yes (antigravity's) | Yes (devin's) | No |
| Mark an item `done` / move to `implemented/` | No | Yes (as verifier of antigravity's item) | Yes (as verifier of devin's item) | No |
| Co-sign a `security` item       | No   | No    | No          | Yes (only) |
| Update STATUS.md                | Yes  | No    | No          | No       |
| Reject/defer an item            | Yes  | No    | No          | No       |
| Promote idea → feature          | Yes  | No    | No          | No       |

\* *mgmt may do implementation work on mgmt-owned regions only.*

---

## 8. Naming Convention

Backlog item files:

```
BLK-NNN_short-kebab-case-slug.md
```

Examples:
- `BLK-001_tool-interface-contracts.md`
- `BLK-002_paddleocr-provider.md`
- `BLK-015_chat-interface-scaffold.md`

---

## 9. Integration with comms/

The comms system and the backlog system are complementary:

- **comms/** is for *communication* — messages between parties.
- **backlog/** is for *work items* — what needs to be done.

**Every backlog item lifecycle event triggers a comms message** (see §5.2).
The comms message should reference the BLK-NNN ID so parties can cross-reference.

When a comms message results in a decision to do work, mgmt creates a backlog
item and references the comms message-id in the item's Notes section.

When a backlog item generates discussion, parties send comms messages and
reference the BLK-NNN ID in the subject or body.
