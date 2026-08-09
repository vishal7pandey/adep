---
id: BLK-102
type: feature
title: "Add explanatory text and tooltips to all editor components"
priority: high
status: backlog
phase: 3
owner: frontend
created: 2026-08-08T03:10:00+05:30
estimate: M
depends-on: [BLK-101]
tags: [frontend, ux, explanatory-text, tooltips, onboarding, stabilization]
---

## Problem

Every editor component in the app uses jargon-heavy labels with
zero explanatory text. Users don't know what "Probe Order",
"Invariants", "Confidence Threshold", or "snake_case" mean. No
tooltips, no help text, no "what is this?" anywhere.

### SkillEditor.tsx

| Current Label | Problem |
|---------------|---------|
| "Basics & System Prompt" | Buries the skill name field |
| "Probe Order Strategy" | What is a "probe"? |
| "Invariants Verification Rules" | What's an "invariant"? |
| "Failure Action Actions" | Redundant naming, unclear |
| "Pragmatic Semantic Checks" | What does "pragmatic" add? |
| "System Reasoning Prompt" | Just call it "Instructions" |
| Tool chips: `paddle_ocr`, `outcome_validator` | Raw code IDs |

### TemplateEditor.tsx

| Current Label | Problem |
|---------------|---------|
| "Template Schema Builder Form (BLK-030)" | BLK ID in UI |
| "Define outcome contracts, field data types..." | Jargon subtitle |
| "Field Name (snake_case)" | Assumes dev knowledge |
| "Confidence Threshold" | No explanation, no range guidance |
| "Data Type" options: string, number, date... | No descriptions |
| "Description" placeholder: "Extraction prompt guidance for agent" | Unclear |

### Definitions Page (wizard)

| Current Label | Problem |
|---------------|---------|
| "Agent Definition Builder" | What is an "agent definition"? |
| Step labels: "Skill Selection", "Template Selection" | No context |
| "Tool Preferences" | What tools? What preferences? |
| "System Prompt" | What should I write here? |

## Fix

### 1. Human-Readable Labels

| Current | Proposed | Explanation |
|---------|----------|-------------|
| "Basics & System Prompt" | "Name & Description" | First section is just identity |
| "Probe Order Strategy" | "Extraction Steps" | Ordered steps the agent follows |
| "Invariants Verification Rules" | "Validation Rules" | Math/logic checks on extracted data |
| "Failure Action Actions" | "Fallback Behavior" | What to do when extraction fails |
| "Pragmatic Semantic Checks" | "AI Verification" | Optional LLM-based sanity check |
| "System Reasoning Prompt" | "Instructions" | Tell the agent how to approach this document |
| "Template Schema Builder Form" | "Template Editor" | Simple, clear |
| "Define outcome contracts..." | "Define what fields to extract from this document type" | Plain English |
| "Field Name (snake_case)" | "Field Name" + helper text | Don't expose naming convention |
| "Confidence Threshold" | "Minimum Confidence" + helper | "How confident the agent must be (0-1). Default: 0.7" |

### 2. Helper Text Pattern

Every field gets a one-line helper text below the label:

```tsx
<div>
  <label className="block font-semibold mb-1">Instructions</label>
  <p className="text-xs text-muted mb-2">
    Tell the agent how to approach this document type. Example:
    "Extract vendor name, invoice number, and totals. Verify
    subtotal + tax = total."
  </p>
  <textarea ... />
</div>
```

### 3. Tooltip Component

For advanced/dense fields, add info tooltips:

```tsx
<label className="flex items-center gap-1">
  Minimum Confidence
  <InfoTooltip text="How confident the agent must be (0-1) before
  accepting a value. Lower = more permissive, higher = stricter.
  Default: 0.7" />
</label>
<input type="number" step="0.05" min="0" max="1" ... />
```

### 4. Tool Labels with Descriptions

Replace raw tool IDs with labeled toggles:

```tsx
const TOOL_OPTIONS = [
  { id: 'paddle_ocr', label: 'Text Extraction (OCR)',
    description: 'Read text from document images' },
  { id: 'detect_layout', label: 'Layout Detection',
    description: 'Identify text blocks, tables, and figures' },
  { id: 'crop_image', label: 'Region Zoom',
    description: 'Crop and enlarge specific areas for closer inspection' },
  { id: 'read_table', label: 'Table Reader',
    description: 'Extract structured data from tables' },
  { id: 'azure_vlm', label: 'AI Vision (VLM)',
    description: 'Use a vision language model for complex or degraded documents' },
  { id: 'deskew', label: 'Deskew',
    description: 'Straighten tilted document scans before OCR' },
  { id: 'outcome_validator', label: 'Validation',
    description: 'Verify extracted values against rules (sums, dates, formats)' },
];
```

### 5. Section Intros

Each section in the editors gets a one-line intro:

```tsx
{activeSection === 'probe' && (
  <div className="space-y-4">
    <div>
      <h3 className="font-bold text-sm">Extraction Steps</h3>
      <p className="text-xs text-muted mt-1">
        Define the order in which the agent should examine the document.
        The agent uses these as guidance, not a rigid pipeline.
      </p>
    </div>
    {/* ... existing form fields ... */}
  </div>
)}
```

### 6. Empty State Guidance

When a section has no entries, show a helpful empty state:

```tsx
{probeSteps.length === 0 && (
  <div className="text-center py-8 text-muted">
    <p>No extraction steps defined.</p>
    <p className="text-xs mt-1">
      The agent will use its default approach. Add steps to guide
      it toward specific regions or tools.
    </p>
    <AdeButton variant="secondary" size="sm" onClick={addProbeStep}>
      <Plus className="w-3.5 h-3.5" /> Add First Step
    </AdeButton>
  </div>
)}
```

## Files to Modify

- `frontend/components/skills/SkillEditor.tsx` — labels, helper text, tooltips
- `frontend/components/templates/TemplateEditor.tsx` — labels, helper text, tooltips
- `frontend/app/definitions/page.tsx` — wizard step descriptions, helper text
- Create `frontend/components/ui/InfoTooltip.tsx` — reusable tooltip component

## Acceptance Criteria

- [ ] No jargon in any editor label (no "invariant", "probe", "pragmatic")
- [ ] Every field has a one-line helper text or tooltip
- [ ] Tool names are human-readable with descriptions
- [ ] Each editor section has a one-line intro explaining what it does
- [ ] Empty states have guidance text
- [ ] No BLK IDs visible anywhere in the UI
- [ ] InfoTooltip component created and reusable
- [ ] "Confidence Threshold" shows range and default in helper text
- [ ] "Field Name" doesn't mention snake_case (auto-normalize instead)

## References

- OpenAI GPT Builder: every field has helper text and examples
- Flowise: tool descriptions are editable and human-readable
- Langflow: tool actions have descriptions that help the agent decide
