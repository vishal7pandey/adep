---
id: BLK-199
type: tech-debt
title: "BLK-067 and BLK-070 are in backlog/features/ but are actually implemented and wired — backlog status drift"
priority: low
status: backlog
phase: 2
owner: devin
created: 2026-08-09T11:30:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [backlog-integrity, ai, adas, process]
---

## Description

`src/ai/template_composer.py` (BLK-067) and `src/ai/surrogate_verifier.py` (BLK-070) are fully implemented AND wired into production:

- `POST /api/v1/templates/generate` calls `generate_template()` from `template_composer.py` (`src/api/routes/templates.py:116-131`)
- `POST /api/v1/skills/{skill_id}/verify` calls `verify_skill()` from `surrogate_verifier.py` (`src/api/routes/skills.py:146-174`)
- The frontend `AiTemplateComposer` component (`frontend/components/templates/AiTemplateComposer.tsx`) calls `generateTemplate()` which hits the backend endpoint

Despite all of this being implemented and wired, the backlog items remain in `backlog/features/` (not `backlog/implemented/`):
- `BLK-067_ai-template-composer.md` — status: feature (not implemented)
- `BLK-070_surrogate-verifier.md` — status: feature (not implemented)

## Problem Statement

- The backlog says these features are "not yet implemented" when they are fully implemented, wired to API endpoints, and have frontend UI
- A developer picking up BLK-067 or BLK-070 would not know the work is already done
- This is a backlog integrity issue, not a code issue — the code is correct

## Acceptance Criteria

- [ ] Move `BLK-067_ai-template-composer.md` from `backlog/features/` to `backlog/implemented/`
- [ ] Move `BLK-070_surrogate-verifier.md` from `backlog/features/` to `backlog/implemented/`
- [ ] Update the status field in both items from `feature` to `implemented`
- [ ] Add implementation log entries noting the API endpoints and frontend component

## Constraints

- No code changes needed — this is purely a backlog process fix

## Dependencies

- `backlog/features/BLK-067_ai-template-composer.md`
- `backlog/features/BLK-070_surrogate-verifier.md`

## Notes

- Initially filed as "unwired dead code" during full-repo audit; corrected after discovering the API endpoints in `templates.py` and `skills.py` and the frontend `AiTemplateComposer` component. The error message in the frontend component ("The backend AI Template Composer endpoint may not be deployed yet") is misleading — the endpoint exists.

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
