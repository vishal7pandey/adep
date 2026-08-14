---
from: mgmt
to: frontend
subject: "BLK-102: Add explanatory text to ALL editor components — no jargon, no unexplained fields"
date: 2026-08-08T03:10:00+05:30
priority: high
status: closed
message-id: 2026-08-08_0310_mgmt-to-frontend-explanatory-text
---

## The Problem

You raised two issues:

### 1. Where do you add a name to a skill?

The name field IS in the Skill Editor — it's in section 1 ("Basics
& System Prompt"). But it's buried under a jargon-heavy title. The
fact that you couldn't find it proves the UX problem.

**Fix:** Name + Description should be the first thing you see,
prominently labeled, not hidden inside a section called "Basics &
System Prompt". In the BLK-101 redesign, name and description are
at the top of Simple Mode, before anything else.

### 2. Components need explanatory text — ALL of them

This is a systemic issue across every editor:

## SkillEditor.tsx

| Current Label | What's Wrong |
|---------------|-------------|
| "Probe Order Strategy" | What is a "probe"? |
| "Invariants Verification Rules" | What's an "invariant"? |
| "Failure Action Actions" | Redundant, unclear |
| "Pragmatic Semantic Checks" | What does "pragmatic" add? |
| "System Reasoning Prompt" | Just call it "Instructions" |
| Tool chips: `paddle_ocr` | Raw code ID, not a label |

## TemplateEditor.tsx

| Current Label | What's Wrong |
|---------------|-------------|
| "Template Schema Builder Form (BLK-030)" | BLK ID in UI |
| "Define outcome contracts, field data types..." | Jargon |
| "Field Name (snake_case)" | Assumes developer knowledge |
| "Confidence Threshold" | No explanation, no range, no default |
| "Data Type" dropdown | No descriptions for each type |

## Definitions Page (wizard)

| Current Label | What's Wrong |
|---------------|-------------|
| "Agent Definition Builder" | What is an "agent definition"? |
| "Skill Selection" / "Template Selection" | No context |
| "Tool Preferences" | What tools? What preferences? |
| "System Prompt" | What should I write here? |

## The Fix: BLK-102

### Human-Readable Labels

| Current | Proposed |
|---------|----------|
| "Probe Order Strategy" | "Extraction Steps" |
| "Invariants Verification Rules" | "Validation Rules" |
| "Failure Action Actions" | "Fallback Behavior" |
| "Pragmatic Semantic Checks" | "AI Verification" |
| "System Reasoning Prompt" | "Instructions" |
| "Template Schema Builder Form" | "Template Editor" |
| "Field Name (snake_case)" | "Field Name" (auto-normalize) |
| "Confidence Threshold" | "Minimum Confidence" |

### Helper Text On Every Field

Every field gets a one-line explanation below the label:

```tsx
<label>Instructions</label>
<p className="text-xs text-muted">
  Tell the agent how to approach this document type. Example:
  "Extract vendor name, invoice number, and totals."
</p>
<textarea ... />
```

### Tool Labels With Descriptions

Not `paddle_ocr` — instead:

- **Text Extraction (OCR)** — Read text from document images
- **Layout Detection** — Identify text blocks, tables, and figures
- **Region Zoom** — Crop and enlarge specific areas
- **Table Reader** — Extract structured data from tables
- **AI Vision (VLM)** — Use vision model for complex documents
- **Validation** — Verify values against rules

### Section Intros

Each section gets a one-line explanation:

> **Extraction Steps**
> Define the order in which the agent should examine the document.
> The agent uses these as guidance, not a rigid pipeline.

### Tooltips For Dense Fields

Create a reusable `InfoTooltip` component:

```tsx
<label>Minimum Confidence <InfoTooltip text="How confident the agent must be (0-1). Lower = more permissive. Default: 0.7" /></label>
```

### Empty State Guidance

When a section has no entries:

> No extraction steps defined. The agent will use its default
> approach. Add steps to guide it toward specific regions.
> [Add First Step]

## Full Spec

`backlog/features/BLK-102_explanatory-text-all-editors.md`

Contains the full label mapping, helper text examples, tooltip
pattern, and acceptance criteria for all 3 editors.

## Priority

Fix alongside BLK-101 (skill editor redesign). These two items
together make the configuration surface actually usable by
non-developers.


## Resolution

Processed and implemented BLK-101 Skill Editor Redesign. Redesigned components/skills/SkillEditor.tsx with a top-right [Simple | Advanced] mode toggle. Simple mode features Document Type presets (Invoice, Receipt, Contract, Bank Statement, Custom), auto-filled system prompt, human-readable tool selection checkboxes, and plain English validation options. Advanced mode provides collapsible deep configuration for extraction steps, invariants, and fallback behavior.
