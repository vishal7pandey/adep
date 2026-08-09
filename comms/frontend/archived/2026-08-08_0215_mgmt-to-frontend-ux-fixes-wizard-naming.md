---
from: mgmt
to: frontend
subject: "UX fixes: wizard Next button validation, metadata leaking, naming standardization"
date: 2026-08-08T02:15:00+05:30
priority: high
status: closed
message-id: 2026-08-08_0215_mgmt-to-frontend-ux-fixes-wizard-naming
---

## Three Issues Identified

### Issue 1: Wizard "Next" button not validating mandatory fields

**File:** `frontend/app/definitions/page.tsx:302-305`

The "Next" button in the Agent Definition Builder Wizard is always
active. It should be **disabled** until the current step's mandatory
fields are filled.

```tsx
// Current — always enabled
{step < 7 ? (
  <LttsButton variant="primary" onClick={() => setStep((prev) => Math.min(prev + 1, 7))}>
    Next <ArrowRight className="w-3.5 h-3.5" />
  </LttsButton>
) : (
```

**Fix:** Add per-step validation:

```tsx
const isStepValid = (): boolean => {
  switch (step) {
    case 1: return defName.trim().length > 0; // name required
    case 2: return selectedSkillId.length > 0; // skill required
    case 3: return selectedTemplateId.length > 0; // template required
    case 4: return selectedTools.length > 0; // at least 1 tool
    case 5: return systemPrompt.trim().length > 0; // prompt required
    case 6: return maxIterations > 0 && maxIterations <= 50; // valid range
    case 7: return true; // review step
    default: return false;
  }
};
```

Then disable the Next button:

```tsx
<LttsButton
  variant="primary"
  onClick={() => setStep((prev) => Math.min(prev + 1, 7))}
  disabled={!isStepValid()}
>
  Next <ArrowRight className="w-3.5 h-3.5" />
</LttsButton>
```

Also add a visual hint when disabled — e.g., reduced opacity or a
tooltip "Fill in required fields to continue".

### Issue 2: Internal metadata leaking to UI

**File:** `frontend/app/definitions/page.tsx:67`

```tsx
<p className="text-xs text-muted mt-1">Compose executable agent definitions via 7-step wizard (BLK-031)</p>
```

Users should **never** see backlog item IDs. Remove `(BLK-031)`:

```tsx
<p className="text-xs text-muted mt-1">Compose executable agent definitions via 7-step wizard</p>
```

**Also check** `Sidebar.tsx:112`:

```tsx
<p className="text-[10px] text-[#8FD3E8] font-medium">Session Manager (BLK-077)</p>
```

This was flagged in the previous code review. Change to:

```tsx
<p className="text-[10px] text-[#8FD3E8] font-medium">Local Agentic Extraction</p>
```

**General rule:** Search all frontend files for `BLK-` references in
user-visible text. Remove them all. BLK IDs are for internal tracking
only, never shown to users.

### Issue 3: Naming standardization — "Agents" vs "Definitions"

The terminology is inconsistent across the UI:

| Location | Current Label | Issue |
|----------|--------------|-------|
| Sidebar library | "Agents" → `/definitions` | Page title says "Agent Definition Builder" |
| Definitions page header | "Agent Definition Builder" | Too technical for users |
| Wizard title | "Agent Definition Builder Wizard" | Redundant + technical |
| Save button | "Save Agent Definition" | OK but verbose |
| Sidebar subtitle | "Session Manager (BLK-077)" | Remove BLK ID |

**Standardize to user-friendly language:**

| Location | New Label |
|----------|-----------|
| Sidebar library nav | "Choose Agent" (links to `/definitions`) |
| Definitions page header | "Choose Agent" |
| Page subtitle | "Select a prebuilt agent or build your own" |
| Wizard title | "Build New Agent" |
| Wizard step 1 heading | "Name & Description" (remove "Step 1:") |
| Save button | "Create Agent" |
| Card grid section | "Available Agents" |
| Build button | "Build New Agent" |

**Rationale:** Users think in terms of "choosing an agent" to process
their document. "Definition" is an internal implementation term. The
UI should always say "Agent" in user-facing text.

### Additional: Sidebar nav label change

In `Sidebar.tsx`, the library section currently has:

```tsx
{ href: '/definitions', label: 'Agents', icon: Layers },
```

Change to:

```tsx
{ href: '/definitions', label: 'Choose Agent', icon: Layers },
```

This makes it clear that clicking here lets the user pick an agent for
their extraction session.

## Acceptance Criteria

- [ ] Next button disabled when mandatory fields empty (all 7 steps)
- [ ] No `BLK-` IDs visible anywhere in the UI
- [ ] Sidebar nav says "Choose Agent" (not "Agents")
- [ ] Definitions page header says "Choose Agent" (not "Agent Definition Builder")
- [ ] Wizard title says "Build New Agent" (not "Agent Definition Builder Wizard")
- [ ] Build button says "Build New Agent" (not "Build Definition Wizard")
- [ ] Save button says "Create Agent" (not "Save Agent Definition")
- [ ] Page subtitle says "Select a prebuilt agent or build your own"
- [ ] Sidebar subtitle says "Local Agentic Extraction" (not "Session Manager (BLK-077)")

## Priority

Fix all three issues together. They're all in the same file
(`definitions/page.tsx`) plus one line in `Sidebar.tsx`. Should be
quick.


## Resolution

Processed and implemented UX fixes and stabilization review items. Added wizard per-step validation (isStepValid()) in definitions/page.tsx, stripped all BLK- backlog metadata from user-facing text, standardized library nav label to Choose Agent, updated definitions page headers to Choose Agent, added ApiError class in lib/api.ts (BLK-097), and updated agent definition creation payload schema (BLK-098).
