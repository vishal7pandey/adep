# Project Management Process

> The authoritative process for managing work items in the ADEP project.
> Covers backlog management, item lifecycle, prioritization, and the
> communication cadence that keeps all parties aligned.

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
id: BLK-001                      # unique ID: BLK-<zero-padded number>
type: feature                    # feature | bug | idea | tech-debt
title: "Add table detection tool"
priority: high                   # critical | high | medium | low
status: backlog                  # backlog | in-progress | review | done
phase: 1                         # which vision.md phase (1-4)
owner: backend                   # mgmt | backend | frontend | unassigned
created: 2026-08-07T20:30:00+05:30
started: null                    # ISO timestamp when moved to in-progress
completed: null                  # ISO timestamp when moved to implemented
estimate: null                   # S / M / L / XL (t-shirt sizing)
depends-on: []                   # list of BLK-IDs this item depends on
tags: [tools, perception]
---
```

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

1. **Anyone** may propose a backlog item by creating a `.md` file in the
   appropriate `backlog/<category>/` directory.
2. Use the next available `BLK-NNN` ID (check existing files for the highest
   number).
3. Copy `ITEM-TEMPLATE.md` as a starting point.
4. Set `status: backlog`, `owner: unassigned` (unless the proposer is the
   owner).
5. **Notify** the relevant parties via a comms message (see §5).

### 3.2 Starting Work (backlog → in-progress)

1. **mgmt assigns** the item by setting `owner` and moving the file from
   `backlog/<category>/` to `backlog/in-progress/`.
2. Update `status: in-progress` and set `started` timestamp.
3. The assigned party sends a comms message acknowledging they've picked it up.
4. **If blocked**: set `status: blocked` in frontmatter, add a note to the
   Implementation Log, and send a comms message to `mgmt/inbox/` explaining
   the blocker.

### 3.3 Completing Work (in-progress → implemented)

1. The owner appends a `## Resolution` section to the item.
2. Sets `status: done` and `completed` timestamp.
3. Moves the file from `backlog/in-progress/` to `implemented/<category>/`.
4. Sends a comms message to `mgmt/inbox/` with a summary of what was done.
5. **mgmt reviews** the implementation. If approved, mgmt updates
   `projectmgmt/STATUS.md`. If changes needed, mgmt sends a comms message
   back with feedback — the item stays in `in-progress/` (or returns there
   from review).

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

Items are tagged with a `phase` (1-4) matching the vision.md phases:

| Phase | Focus                  | Primary Owner |
|-------|------------------------|---------------|
| 1     | Engine (extraction)    | backend       |
| 2     | Platform API           | backend       |
| 3     | Frontend UI            | frontend      |
| 4     | Polish & Scale         | both          |

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
| New backlog item created       | Proposer  | Comms message to relevant party's inbox   |
| Item assigned to a party       | mgmt      | Comms message to assignee's inbox         |
| Work started on an item        | Assignee  | Comms message to mgmt/inbox/ acknowledging|
| Blocked on an item             | Assignee  | Comms message to mgmt/inbox/ + blocker's  |
|                               |           | inbox if another party is the blocker     |
| Item completed                 | Assignee  | Comms message to mgmt/inbox/ with summary |
| Item reviewed & approved       | mgmt      | Comms message to assignee's inbox +       |
|                               |           | update STATUS.md                          |
| Item rejected or deferred      | mgmt      | Comms message to proposer's inbox         |
| Phase gate decision            | mgmt      | Comms to both backend + frontend inboxes  |
| Status board updated           | mgmt      | Comms to both inboxes noting what changed |

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

| Action                         | mgmt | backend | frontend |
|-------------------------------|------|---------|----------|
| Create a backlog item          | Yes  | Yes     | Yes      |
| Assign an item                 | Yes  | No      | No       |
| Change priority                | Yes  | No      | No       |
| Start work on assigned item    | Yes* | Yes     | Yes      |
| Move item to implemented/      | Yes* | Yes     | Yes      |
| Approve/reject implementation  | Yes  | No      | No       |
| Update STATUS.md               | Yes  | No      | No       |
| Reject/defer an item           | Yes  | No      | No       |
| Promote idea → feature         | Yes  | No      | No       |

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
