---
id: BLK-101
type: feature
title: "Redesign Skill Editor — progressive disclosure (Simple + Advanced modes)"
priority: high
status: backlog
phase: 3
owner: frontend
created: 2026-08-08T03:00:00+05:30
estimate: M
depends-on: [BLK-029]
supersedes: [BLK-029]
tags: [frontend, ux, skill-editor, progressive-disclosure, stabilization]
---

## Problem

The current Skill Editor (`frontend/components/skills/SkillEditor.tsx`)
is a 6-section form with a sidebar navigation that exposes every
internal concept at once:

1. Basics & System Prompt
2. Tool Preferences
3. Probe Order
4. Invariants
5. Failure Actions
6. Semantic Checks

**This is too complicated.** Users see terms like "probe order
strategy", "invariant verification rules", and "failure action
actions" without context. The form has hardcoded defaults that don
match any real document type. It's a developer tool, not a user tool.

## Industry Research

### OpenAI GPT Builder (2026)

Two modes:
- **Create** (conversational): User describes what they want in
  natural language. The builder generates the GPT.
- **Configure** (manual): Raw access to system prompt, knowledge
  files, capabilities toggles, and Actions schema.

Key principle: **beginners use Create, experts use Configure.**
The simple path is always one click away.

### Flowise (2026)

Three tiers:
- **Assistant** (simplest): Guided setup, preconfigured structure,
  plug-and-play. No code required.
- **Chatflow** (intermediate): Visual canvas with nodes.
- **Agentflow** (advanced): Multi-agent orchestration, tool usage,
  autonomous reasoning.

Key principle: **progressive disclosure.** Users start simple and
graduate to more complex builders as needed.

### CrewAI (2026)

Skills are `SKILL.md` files with YAML frontmatter:
```yaml
name: my-skill
description: When to use this skill
allowed-tools: [tool1, tool2]
```
The skill body is just markdown instructions. No probe order, no
invariants, no failure actions in the UI — those are code-level
concerns.

Key principle: **skills are instructions + metadata, not
engineering configurations.**

### Langflow (2026)

Visual canvas. Tools are drag-and-drop components connected to an
Agent node. Tool actions have editable labels and descriptions.
Advanced settings are per-component, not global.

Key principle: **visual composition over form-filling.**

## Proposed Design

### Two-Mode Editor

**Simple Mode (default):**

```
┌─────────────────────────────────────────────────────┐
│  Build Skill                          [Simple|Advanced] │
├─────────────────────────────────────────────────────┤
│                                                       │
│  Skill Name: [________________________]              │
│  Description: [________________________]             │
│                                                       │
│  Document Type: [Invoice ▾]                          │
│  (dropdown: Invoice, Receipt, Contract, Bill,        │
│   Lease, Claim, Audit, Custom...)                    │
│                                                       │
│  ── System Prompt ──                                 │
│  ┌─────────────────────────────────────────────┐    │
│  │  (auto-filled based on document type,        │    │
│  │   editable textarea)                         │    │
│  │                                              │    │
│  └─────────────────────────────────────────────┘    │
│  ✨ Auto-generate from description (BLK-068 preview) │
│                                                       │
│  ── Tools ──                                         │
│  [✓] OCR (text extraction)                           │
│  [✓] Layout Detection                                │
│  [ ] Table Reader                                    │
│  [✓] Image Crop                                      │
│  [ ] VLM (vision model)                              │
│  [ ] Deskew                                          │
│                                                       │
│  ── Validation ──                                    │
│  [✓] Verify math (sums, totals)                     │
│  [✓] Verify dates (format, range)                   │
│  [ ] Semantic check (LLM verification)              │
│                                                       │
│              [Clone]  [Save Skill]                    │
└─────────────────────────────────────────────────────┘
```

**Advanced Mode (collapsible, hidden by default):**

```
┌─────────────────────────────────────────────────────┐
│  Build Skill                          [Simple|Advanced] │
├─────────────────────────────────────────────────────┤
│  (all Simple fields above)                           │
│                                                       │
│  ▼ Advanced Settings                                  │
│  ┌─────────────────────────────────────────────┐    │
│  │                                               │    │
│  │  ── Probe Order ──                           │    │
│  │  1. [Scan full page    ] [▼]                 │    │
│  │  2. [Inspect low-conf  ] [▼]                 │    │
│  │  [+ Add Step]                                │    │
│  │                                               │    │
│  │  ── Invariants ──                            │    │
│  │  • total = subtotal + tax   [✕]              │    │
│  │  • date <= today            [✕]              │    │
│  │  [+ Add Rule]                                │    │
│  │                                               │    │
│  │  ── Failure Actions ──                       │    │
│  │  • confidence < 0.6 → VLM escalation [✕]    │    │
│  │  • OCR error → deskew             [✕]       │    │
│  │  [+ Add Action]                              │    │
│  │                                               │    │
│  │  ── Semantic Checks ──                       │    │
│  │  [ ] Enable LLM semantic verification       │    │
│  │  Prompt: [________________________]          │    │
│  │                                               │    │
│  └─────────────────────────────────────────────┘    │
│                                                       │
│              [Clone]  [Save Skill]                    │
└─────────────────────────────────────────────────────┘
```

### Design Principles

1. **Progressive disclosure** — Simple mode shows 4 concepts
   (name, document type, prompt, tools). Advanced mode adds 4 more
   (probe order, invariants, failure actions, semantic checks).
   Users never see advanced settings unless they opt in.

2. **Document type presets** — Selecting "Invoice" auto-fills:
   - System prompt with invoice-specific instructions
   - Tool preferences (OCR, layout, crop, table reader)
   - Invariants (subtotal + tax = total)
   - Failure actions (low confidence → VLM, OCR error → deskew)
   - Probe order (scan page → inspect table → verify totals)
   
   User can then tweak or override. This replaces the empty-form
   problem.

3. **Human-readable labels** — No jargon:
   - "Probe Order Strategy" → "Extraction Steps"
   - "Invariants Verification Rules" → "Validation Rules"
   - "Failure Action Actions" → "Fallback Behavior"
   - "Pragmatic Semantic Checks" → "AI Verification"

4. **Toggle-based tools** — Tools are checkboxes with descriptions,
   not a chip selector with raw tool names. "OCR (text extraction)"
   not "paddle_ocr".

5. **AI assist placeholder** — The "Auto-generate from description"
   button is a placeholder for BLK-068 (AI Skill Composer). In v1,
   it could pre-fill from document type selection. In Phase 5, it
   becomes a full NL → skill generator.

6. **Remove BLK-029 from header** — No backlog IDs in the UI (same
   as BLK-097/previous comms).

### Document Type Presets

```typescript
const SKILL_PRESETS: Record<string, SkillPreset> = {
  invoice: {
    systemPrompt: "Extract vendor name, invoice number, dates, line items, and totals from invoice documents. Verify subtotal + tax = total.",
    tools: ['paddle_ocr', 'detect_layout', 'crop_image', 'read_table', 'outcome_validator'],
    invariants: [
      { field: 'total_amount', type: 'sum_check', params: 'subtotal + tax == total_amount' },
    ],
    failureActions: [
      { condition: 'confidence < 0.6', action: 'vlm_escalation' },
      { condition: 'ocr_error', action: 'deskew' },
    ],
    probeOrder: [
      { rationale: 'Scan full page for text', action: 'Run OCR on page 1' },
      { rationale: 'Extract line items from table', action: 'Run read_table on table region' },
      { rationale: 'Verify totals', action: 'Run outcome_validator' },
    ],
  },
  receipt: { ... },
  contract: { ... },
  bill: { ... },
  lease: { ... },
  claim: { ... },
  audit: { ... },
  custom: {
    systemPrompt: '',
    tools: [],
    invariants: [],
    failureActions: [],
    probeOrder: [],
  },
};
```

### Toggle Component

```tsx
// Simple mode: tools as toggles with descriptions
const TOOL_OPTIONS = [
  { id: 'paddle_ocr', label: 'OCR (text extraction)', description: 'Extract text from document images' },
  { id: 'detect_layout', label: 'Layout Detection', description: 'Identify text, table, and figure regions' },
  { id: 'crop_image', label: 'Image Crop', description: 'Zoom into specific regions for closer inspection' },
  { id: 'read_table', label: 'Table Reader', description: 'Extract structured data from tables' },
  { id: 'azure_vlm', label: 'Vision Model (VLM)', description: 'Use AI vision for complex or degraded documents' },
  { id: 'deskew', label: 'Deskew', description: 'Straighten tilted document scans' },
  { id: 'outcome_validator', label: 'Validation', description: 'Verify extracted values against rules' },
];

// Render as toggle list, not chips
{TOOL_OPTIONS.map(tool => (
  <label key={tool.id} className="flex items-start gap-2 p-2 rounded hover:bg-black/5">
    <input type="checkbox" checked={selectedTools.includes(tool.id)} onChange={() => toggleTool(tool.id)} />
    <div>
      <div className="font-semibold">{tool.label}</div>
      <div className="text-muted text-xs">{tool.description}</div>
    </div>
  </label>
))}
```

## Acceptance Criteria

- [ ] Simple mode shows: name, description, document type dropdown,
      system prompt, tool toggles, validation checkboxes
- [ ] Advanced mode (collapsible) shows: probe order, invariants,
      failure actions, semantic checks
- [ ] Default mode is Simple
- [ ] Selecting a document type preset auto-fills all fields
- [ ] "Custom" document type starts with empty fields
- [ ] Tool labels are human-readable (not raw tool IDs)
- [ ] No BLK- IDs visible in the UI
- [ ] Section labels use plain English (not jargon)
- [ ] Save button disabled until name + document type are filled
- [ ] Advanced settings preserved when toggling between modes
- [ ] Clone button works in both modes

## Files to Modify

- `frontend/components/skills/SkillEditor.tsx` — full redesign
- `frontend/app/skills/page.tsx` — update header/title

## References

- OpenAI GPT Builder: Create vs Configure tabs
- Flowise: Assistant → Chatflow → Agentflow progressive disclosure
- CrewAI: SKILL.md = instructions + metadata (not engineering config)
- Langflow: Visual tool connection, editable action descriptions
- BLK-068: AI Skill Composer (Phase 5 — future NL generation)
