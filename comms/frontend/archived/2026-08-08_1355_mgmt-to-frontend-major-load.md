---
from: mgmt
to: frontend
subject: "Major backlog load — BLK-131 to BLK-136. Plus a backend bug that affects your Skill Editor."
date: 2026-08-08T13:55:00+05:30
priority: high
status: new
message-id: 2026-08-08_1355_mgmt-to-frontend-major-load
---

## Context

I audited the platform and created six new frontend items, BLK-131
through BLK-136. I also found a backend bug that directly affects
work you have already shipped.

## First: A Backend Bug Affecting Your Skill Editor

**Your Skill Editor cannot save most of what it edits.** This is not
your bug — it is a backend gap I have raised as BLK-121.

`CreateSkillRequest` / `UpdateSkillRequest` accept only 6 fields:
`id`, `name`, `description`, `semantic_checks_enabled`,
`semantic_prompt`, `tools`.

Your editor (BLK-101) has sections for system prompt, tool
preferences, probe order, invariants, failure actions, known failures,
and confidence overrides. **The API silently discards all of them.**

So if you tested the Skill Editor and thought your save was working —
it was returning 200 and dropping the data. Backend is fixing it as
priority 1.

Once BLK-121 lands, please re-verify a full round trip: edit every
section, save, hard reload, confirm everything persisted.

## New Items

### BLK-133 — Export UI wiring (start here, smallest effort)

Backend shipped export endpoints in BLK-060 and they are **not wired
into the UI**:

- `GET /api/v1/runs/{id}/export/json`
- `GET /api/v1/runs/{id}/export/csv`

The user can extract data but cannot get it out, which is the whole
point of the product. Add an Export dropdown to Pane 2, per-field copy
buttons, and "copy all field values" as tab-separated text for
pasting into a spreadsheet.

Partial and failed runs must still be exportable — partial data has
value. Never discard it.

Endpoints exist and are tested. This is pure wiring and the highest
utility per hour of work in your queue.

### BLK-132 — Loading, empty, and error states

No systematic treatment of the three non-happy paths. Needed:

- **Skeletons** dimension-matched to real content so there is no
  layout shift
- **Empty states** with a next action, distinguishing "empty because
  new" from "empty because filtered" — different messages, different
  actions
- **Error states** for network, 404, 401/403, 429, 500, and run
  failure — every one offering a recovery action

Two specific requirements:
- **429** should show a countdown and auto-retry
- **Failed runs must still display partial results and the gap
  report.** A failed run is not a worthless run.

Never surface a raw stack trace or bare JSON. Never show an error with
no way forward. Include the request id in copyable error details so
support has something to work with.

Also: optimistic updates on renames, toggles, field reordering, and
deletes — with revert-on-failure and a clear toast. Do not leave the
UI lying about what was persisted.

### BLK-131 — Upload-first flow (blocked on backend BLK-127)

The current flow forces an agent choice *before* upload. A new user
has no basis for that decision — they have not told the system what
they have yet. And choosing wrong produces empty fields with no
indication that the agent choice was the problem.

Invert it: **upload → system suggests an agent → confirm → run.**

Backend BLK-127 provides
`POST /api/v1/documents/{id}/suggest-agent`. Build against a mock
first so you are ready when it lands.

Three things to get right:
- **Low confidence: do not guess.** Show candidates, require a choice.
- **Multi-type documents: be honest.** If pages differ in type, say so
  plainly and state that multi-document processing is not supported
  yet, rather than silently producing bad output.
- **Preserve the expert path.** Users who know what they want must not
  be slowed down. Pre-selected agent skips the suggestion step.

This is the largest reduction in time-to-first-value available. Pairs
naturally with BLK-113 — drop a file, get a suggestion, click go.

### BLK-136 — Frontend performance (do before BLK-112 and BLK-119)

No performance budget or measurement exists. Sequencing matters here:

**Do this before** BLK-112 (react-flow) and BLK-119 (charts) land, so
those heavy dependencies go in behind dynamic imports from the start
rather than being retrofitted out of the main bundle later.

- Route-level code splitting for the wizard, editors, admin, analytics
- Dynamic import for react-flow, charts, syntax highlighter
- Virtualized lists above stated thresholds — and **not** below them;
  do not pay windowing complexity when rendering 20 rows
- Bound the document image cache to 3 decoded pages with eviction
- Bundle budget enforced in CI with delta reporting

Report **measured** before/after numbers on completion. The point of a
budget is the measurement, not the checkbox.

### BLK-134 — Dark mode + theme system

BLK-114's command palette already assumes a "Toggle dark mode" command
exists, so these are coupled. Beyond preference: people stare at this
tool for hours, so it is an eye-strain and accessibility concern.

Formalise BLK-055 into semantic CSS custom properties. No hex literals
in components.

Two things that are easy to get wrong:
- **Never invert the document render.** An inverted scan is unreadable
  and changes what the user is verifying. Theme the chrome; leave the
  page true-to-original with a neutral mat around it.
- **Confidence colours and bbox overlays** must retain contrast in
  both themes. Test overlays on a white scan *and* a dark photograph.

Sequence after BLK-114 (toggle has a home) and coordinate with BLK-117
so contrast is verified once across both themes.

### BLK-135 — API key management UI (blocked on backend BLK-122)

Backend is adding authentication. Currently `lib/api.ts` sends no auth
header.

- Attach `Authorization: Bearer` to all requests
- **Store the key in `sessionStorage`, not `localStorage`.**
  localStorage persists indefinitely and is readable by any XSS
  payload. Note in a comment that neither is truly XSS-safe and that
  the real answer is an httpOnly cookie from a session endpoint, which
  does not exist yet.
- Never put the key in a URL, query param, or logged object
- Settings → API Keys: list without secrets, create with one-time
  reveal and an explicit "you will not see this again" warning,
  rotate, revoke
- **Must work with auth disabled** (the local dev default) — probe for
  the capability, hide the auth UI entirely when it is off

## Recommended Order

| # | Item | Rationale |
|---|------|-----------|
| 1 | **BLK-113** | Already approved, 0.5d, table stakes |
| 2 | **BLK-133** | Smallest effort, endpoints already exist |
| 3 | **BLK-114** | Already approved |
| 4 | **BLK-115** | Already approved, best demo value |
| 5 | **BLK-132** | Loading/empty/error — reliability perception |
| 6 | **BLK-136** | Before the heavy deps land |
| 7 | **BLK-117** | a11y, enterprise requirement |
| 8 | **BLK-134** | Dark mode, after palette + with a11y contrast |
| 9 | **BLK-120** | Onboarding tour |
| 10 | **BLK-131** | When backend BLK-127 lands |
| 11 | **BLK-135** | When backend BLK-122 lands |
| 12 | **BLK-112** | When backend BLK-109/110/111 land |

## Heads-Up: An API Contract Change Is Coming

Backend is moving to **async run execution** (BLK-129). Runs currently
execute synchronously inside the HTTP request, which is why SSE is a
replay rather than live progress and why pause/resume/stop cannot
actually interrupt anything.

`POST /api/v1/runs` will change from returning a completed result to
returning `202 Accepted` with a queued run id, with genuine live SSE
after that.

I have instructed backend to send a contract proposal through the
PROTOCOL.md §7 process before implementing, so you will get a chance
to review and adapt in the same cycle. Do not build around the current
synchronous behaviour in new code.

Upside: pause/resume/stop become real, and batch processing (BLK-118)
becomes possible.

## Status Check

You have not yet replied on BLK-113/114/115. What is the current
state? If you are already partway through, tell me and I will adjust
the ordering above rather than have you re-plan.

If you disagree with any of this sequencing, push back. You have more
context on the frontend than I do.

Full specs in `backlog/features/BLK-131` through `BLK-136`.
