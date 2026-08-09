---
id: BLK-074
type: feature
title: "OneFlow single-agent optimization mode — replace homogeneous multi-agent with single-agent role-play"
priority: high
status: backlog
phase: 5
owner: unassigned
created: 2026-08-08T00:35:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-008]
tags: [ai, adas, oneflow, single-agent, kv-cache, cost-optimization, research]
---

## Description

Implement a single-agent mode that can mathematically simulate a
homogeneous multi-agent workflow. Instead of dispatching to multiple
agent instances with the same LLM, a single agent sequentially role-
plays each role within one context window, maximizing KV cache reuse
and reducing TTFT latency and cost.

## Motivation

From `agentic agent builder.md`: OneFlow proves that homogeneous multi-
agent teams can be replaced by a single cache-optimized agent. This is
especially relevant for ADE where a single ReAct graph already
coordinates tools.

## Design

**Core idea:**
- A single LLM instance acts as planner, reviewer, verifier
- It switches roles via explicit system prompt prefixes:
  - `[PLANNER]` decide next tool
  - `[REVIEWER]` evaluate extraction
  - `[VERIFIER]` check invariants
- All reasoning stays in one context window
- KV cache is reused across turns

**When to use:**
- Skill has no heterogeneous model requirements (all same LLM)
- Cost/latency is a concern
- Multi-agent mode (if ever implemented) proves homogeneous

**Mode selector:**
- `single` (OneFlow) — default
- `multi` — if heterogeneous models added later

**Implementation:**
- New `OneFlowGraph` in `agent/graph.py`
- Plan/Review/Verify as turns within one `llm_client.invoke` session
- Role prefix in every assistant message
- Tool calls still routed through ToolRegistry

**API:**
- `POST /api/v1/definitions/{id}/run` with `mode=oneflow`

**Metrics:**
- Compare cost and latency against current multi-step graph
- Track KV cache hit rate (if provider exposes it)

## Acceptance Criteria

- [ ] `OneFlowGraph` implementation
- [ ] Single LLM session with role prefixes
- [ ] All roles (planner, reviewer, verifier) function correctly
- [ ] Same extraction accuracy as multi-step graph
- [ ] Lower token cost and TTFT latency
- [ ] `mode=oneflow` parameter in run API
- [ ] Test: same document, lower cost, same or better accuracy

## Constraints

- Only for skills that don't require heterogeneous models
- Does not replace LangGraph — adds an alternative mode
- Requires careful prompt engineering to prevent role confusion

## Dependencies

- BLK-008 (ReAct graph)

## Notes

- `agentic agent builder.md`: OneFlow single-agent baseline
- Counter-balance to MCTS/multi-agent generation
