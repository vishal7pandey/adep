---
id: BLK-053
type: feature
title: "Token usage display in workbench — per-run consumption in Pane 1"
priority: medium
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T23:30:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-028, BLK-050]
tags: [frontend, tokens, consumption, workbench, pane1, observability]
---

## Description

Surface token consumption in the workbench during extraction runs.
Shows running token count and cost in Pane 1, with detailed breakdown
in progressive disclosure Level 3 (expert mode).

## Motivation

Users running extractions need to see what they're spending in real time.
This is the in-flight view — the admin panel (BLK-052) is the historical
view. Together they provide complete cost visibility.

## Design

### Pane 1 Header — Compact Token Display

In the Pane 1 header bar (next to Compact button and progress bar):

```
┌─────────────────────────────────────────────────────────┐
│ Extraction Agent  ⏸ ▶ ⏹ ↩   🧠 8.5K tokens · $0.05  │
│ ████████████░░░░░░ 4/7 Fields   [Compact]              │
└─────────────────────────────────────────────────────────┘
```

- Token icon (🧠 or lucide `Brain`) + running total: `8.5K tokens`
- Cost: `$0.05` (formatted to 2 decimal places)
- Updates in real time via SSE `token_usage` events
- Color: neutral (Neutral Light `#E1E1E1`) when under budget, Tech Yellow
  `#F2E500` when >80% of run budget, Coral `#F47C6D` when exceeded

### Pane 1 — Budget Warning Banner

When SSE `budget_warning` event fires (80% of run budget):

```
┌─────────────────────────────────────────────────────────┐
│ ⚠ Approaching budget limit — 82% consumed (82K / 100K) │
└─────────────────────────────────────────────────────────┘
```

- Tech Yellow `#F2E500` background, dark text
- Dismissible (× button) — but reappears if percentage increases by 5%+
- Shows consumed / limit in tokens

### Pane 1 — Budget Exceeded Banner

When SSE `budget_exceeded` event fires:

```
┌─────────────────────────────────────────────────────────┐
│ ✕ Budget exceeded — run terminated with partial results │
│   100.5K tokens consumed · $1.01 spent                  │
└─────────────────────────────────────────────────────────┘
```

- Coral `#F47C6D` background, white text
- Not dismissible — stays until run is cleared
- Partial results displayed in Pane 2

### Progressive Disclosure Level 3 (Expert Mode)

In expert mode, add a "Token Breakdown" section at the bottom of Pane 1:

```
Token Breakdown
─────────────────────────────────────
Node          Calls    Tokens     Cost
plan          8        7,000      $0.045
compact       1        1,500      $0.007
semantic      0        0          $0.000
─────────────────────────────────────
Total         9        8,500      $0.052
```

- Simple table, monospace font
- Updates in real time
- Only visible in expert mode (Level 3 progressive disclosure, BLK-045)

### SSE Integration

Handle `token_usage` event from BLK-050:
```typescript
// lib/sse.ts
export interface SSETokenUsageEvent {
  type: 'token_usage';
  node: 'plan' | 'compact' | 'semantic_check';
  cycle: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
  running_total_tokens: number;
  running_total_cost: number;
}
```

Handle `budget_warning` and `budget_exceeded` events from BLK-051:
```typescript
export interface SSEBudgetWarningEvent {
  type: 'budget_warning';
  level: 'run' | 'definition' | 'global';
  consumed_tokens: number;
  budget_tokens: number;
  consumed_cost_usd: number;
  budget_cost_usd: number;
  percentage: number;
  message: string;
}

export interface SSEBudgetExceededEvent {
  type: 'budget_exceeded';
  level: 'run' | 'definition' | 'global';
  consumed_tokens: number;
  budget_tokens: number;
  consumed_cost_usd: number;
  budget_cost_usd: number;
  message: string;
}
```

## Acceptance Criteria

- [ ] Token count + cost display in Pane 1 header (next to control buttons)
- [ ] Updates in real time via SSE `token_usage` events
- [ ] Color-coded: neutral <60%, Tech Yellow 60-80%, Coral >80%
- [ ] Budget warning banner on `budget_warning` SSE event (Tech Yellow)
- [ ] Budget exceeded banner on `budget_exceeded` SSE event (Coral, not dismissible)
- [ ] Token breakdown table in expert mode (Level 3 progressive disclosure)
- [ ] Token breakdown shows per-node: calls, tokens, cost
- [ ] SSE client handles `token_usage`, `budget_warning`, `budget_exceeded` events
- [ ] Token counts formatted with K/M suffixes (8.5K, 1.2M)
- [ ] Cost formatted to 2 decimal places ($0.05)
- [ ] Both dark and light mode
- [ ] ADEP brand colors

## Constraints

- Token display is compact — don't let it dominate the header [SF]
- Expert mode table only loads when toggled (no performance impact on default view)
- Budget banners don't block interaction — user can still pause/stop/rollback

## Dependencies

- BLK-028 (Pane 1 — where the display lives)
- BLK-050 (Token tracking — provides SSE events and data)
- BLK-045 (Progressive disclosure — expert mode for breakdown table)

## Notes

- This is the in-flight companion to the admin panel (BLK-052)
- Together they provide complete cost observability [TM]
