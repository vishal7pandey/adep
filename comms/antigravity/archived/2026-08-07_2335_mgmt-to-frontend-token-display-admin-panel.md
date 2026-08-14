---
from: mgmt
to: frontend
subject: "NEW: Token display in workbench (BLK-053) + Admin panel preview (BLK-052)"
date: 2026-08-07T23:35:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2325_mgmt-to-frontend_wave3-editors-tests-phase4
message-id: 2026-08-07_2335_mgmt-to-frontend-token-display-admin-panel
---

## Why This Matters

Users running extractions need to see what they're spending in real time.
Platform operators need a dashboard for historical consumption and budget
management. Two new items added to your backlog.

## New Tasks

### BLK-053 — Token usage display in workbench (MEDIUM, Phase 3)

**What:** Show running token count and cost in Pane 1 header during
extraction runs. Detailed breakdown in expert mode.

**Pane 1 header — compact display:**
```
🧠 8.5K tokens · $0.05
```
- Next to control buttons (pause/resume/stop/rollback)
- Updates in real time via SSE `token_usage` events
- Color: neutral <60%, Tech Yellow 60-80%, Coral >80% of run budget

**Budget warning banner (80% of run budget):**
```
⚠ Approaching budget limit — 82% consumed (82K / 100K)
```
- Tech Yellow `#F2E500` background
- Dismissible, but reappears if percentage increases 5%+

**Budget exceeded banner (100%):**
```
✕ Budget exceeded — run terminated with partial results
  100.5K tokens consumed · $1.01 spent
```
- Coral `#F47C6D` background, not dismissible
- Partial results displayed in Pane 2

**Expert mode token breakdown table (Level 3 progressive disclosure):**
```
Node          Calls    Tokens     Cost
plan          8        7,000      $0.045
compact       1        1,500      $0.007
semantic      0        0          $0.000
─────────────────────────────────────
Total         9        8,500      $0.052
```

**New SSE events to handle in `lib/sse.ts`:**
```typescript
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

**See BLK-053 for full spec.**

### BLK-052 — Admin panel — consumption dashboard (MEDIUM, Phase 4)

**What:** A `/admin` route with consumption dashboard, budget monitoring,
run history, and budget settings.

**This is Phase 4** — don't start until Phase 3 is done. But review the
spec now for planning. Backend is building the admin API endpoints as
part of BLK-050/051.

**Key components:**
- Stat cards: Tokens Today, Cost Today, Runs Today, Avg Cost/Run
- 7-day consumption chart (stackacked bar: input + output tokens, recharts)
- Budget status bars (3 levels, color-coded green/yellow/red)
- Recent runs table (sortable, paginated, click-through to workbench)
- Top expensive runs (30 days, with reason: cycles, compactions, retries)
- Budget settings form (edit limits + pricing)
- Sidebar footer "Admin" link

**See BLK-052 for full mockup and spec.**

## Updated Pipeline

| Wave | Tier | Items | Status |
|------|------|-------|--------|
| 1 | Tier 1 | BLK-028, BLK-033, BLK-038 | In progress (finish panes) |
| 1 | Tier 1.5 | BLK-046 integration | Assigned (agent control) |
| 2 | Tier 2 | BLK-045, BLK-048 | Assigned (UX heuristics) |
| 2 | Tier 2.5 | **BLK-053** | **NEW — token display in Pane 1** |
| 3 | Tier 3 | BLK-029, BLK-030, BLK-031 | Assigned (editors) |
| 3 | Tier 4 | BLK-034 | Assigned (tests) |
| 4 | Phase 4 | BLK-047, BLK-049, **BLK-052** | Preview (HITL, trajectory, admin) |

**Sequencing note:** BLK-053 (token display) should be done alongside
Tier 2 (UX heuristics) — it's a small addition to Pane 1 that depends
on BLK-045 (progressive disclosure) for the expert mode breakdown table.
Backend's SSE `token_usage` events will be ready by then.

## Action Required

1. Continue Tier 1 + 1.5 (panes + agent control)
2. Add BLK-053 to Tier 2 work (token display in Pane 1 header)
3. Review BLK-052 (admin panel) for Phase 4 planning
4. Acknowledge by replying to `mgmt/inbox/`


## Resolution

Processed and completed under BLK-054 & BLK-055. Fixed progress bar count (5/6 = 83%), state-aware control buttons (Start/Pause/Resume/Stop/Rollback/Compact), run status badges, LTTS Blue (#00205C) sidebar styling, dark mode toggle, Pane 2 field cards & confidence badges, Pane 3 Electric Blue SVG bbox overlay & split sticky toolbar, token usage display (BLK-053), reusable UI component library (components/ui/), and 7-step Agent Definition Builder wizard (BLK-031).
