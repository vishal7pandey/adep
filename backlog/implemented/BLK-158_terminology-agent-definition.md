---
id: BLK-158
title: Standardize terminology — "Agent Definition" in all user-facing UI labels
status: open
priority: high
estimate: M
assigned_to: frontend
created: 2026-08-08T22:35:00+05:30
tags: [terminology, ux, frontend, consistency]
---

## Problem

The platform has a terminology inconsistency between code and UI.

**Architecture (vision.md) defines:**
- **Agent** = the runtime loop (ReAct + LLM + state model) — one of 4 bricks
- **Agent Definition** = the composed blueprint (skill + template + tools + config)
- **Run Instance** = a live execution of a definition

**Backend is consistent:** `AgentDefinition` model, `/definitions` routes,
`definition_id` fields, `.adep/definitions/` folder. No changes needed.

**Frontend code variables are consistent:** `AgentDefinition` interface,
`fetchDefinitions()`, `createDefinition()`, `definitions` state arrays.

**Frontend UI labels are INCONSISTENT** — they use "Agent" as shorthand
for "Agent Definition" everywhere, creating ambiguity between the
runtime agent and the user-composed blueprint.

## Decision

Standardize all user-facing UI labels to **"Agent Definition"**.

## Evidence — All locations requiring changes

### 1. `frontend/app/definitions/page.tsx`
| Line | Current | Required |
|------|---------|----------|
| 93 | `Choose Agent` | `Choose Agent Definition` |
| 95 | `Select a prebuilt agent or build your own` | `Select a prebuilt agent definition or build your own` |
| 98 | `Build New Agent` | `Build New Agent Definition` |
| 104 | `Failed to load agents:` | `Failed to load agent definitions:` |
| 114 | `Available Agents Grid` (comment) | `Available Agent Definitions` |
| 159 | `Build New Agent` | `Build New Agent Definition` |
| 173 | `Agent Name *` | `Agent Definition Name *` |
| 179 | `Production Invoice Extraction Agent` | `Production Invoice Extraction Agent Definition` |
| 189 | `Agent purpose and scope` | `Agent Definition purpose and scope` |
| 321 | `Review & Create Agent` | `Review & Create Agent Definition` |
| 323 | `Untitled Agent` | `Untitled Agent Definition` |
| 356 | `Create Agent` | `Create Agent Definition` |

### 2. `frontend/components/layout/Sidebar.tsx`
| Line | Current | Required |
|------|---------|----------|
| 266 | `Choose Agent` | `Choose Agent Definition` |

### 3. `frontend/components/workbench/Pane1AgentConsole.tsx`
| Line | Current | Required |
|------|---------|----------|
| 299 | `Select agent manually below` | `Select agent definition manually below` |
| 347 | `Extraction Agent` | `Extraction Agent Definition` |
| 450 | `Agent Definition Selector` (comment) | OK — already correct |
| 454 | `Agent:` | `Agent Definition:` |
| 542 | `suggest the best matching extraction agent` | `suggest the best matching extraction agent definition` |
| 560 | `matching optimal extraction agent` | `matching optimal extraction agent definition` |
| 599 | `Suggested Agent:` | `Suggested Agent Definition:` |
| 607 | `Start Run with Suggested Agent` | `Start Run with Suggested Agent Definition` |

### 4. `frontend/components/workbench/RunComparisonView.tsx`
Check for any "agent" labels and update to "agent definition".

### 5. `frontend/components/ui/OnboardingTour.tsx`
Check tour step labels for "agent" references and update.

## Backend — No code changes needed

Backend terminology is already consistent:
- `AgentDefinition` model class
- `/definitions` API routes
- `definition_id` in run objects
- `suggested_definition_id` in classification results
- `.adep/definitions/` storage folder

**Note:** The endpoint `POST /documents/{id}/suggest-agent` uses
"agent" in the URL path. This is acceptable — it's an API path, not a
user-facing label. Renaming it would be a contract change requiring
coordination. Leave as-is.

## Tests

- Visual review of all pages — no standalone "Agent" in user-facing labels
- Error messages say "agent definitions" not "agents"
- Sidebar navigation says "Choose Agent Definition"
- Onboarding tour updated if it references "agent"
- Build clean with 0 TypeScript errors
