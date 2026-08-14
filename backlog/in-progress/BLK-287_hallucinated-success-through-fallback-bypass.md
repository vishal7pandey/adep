---
id: BLK-287
type: bug
title: "Silent fallback bypass creates hallucinated success and false agentic confidence"
priority: critical
status: verifying
phase: 1
owner: devin
created: 2026-08-09T11:00:00+05:30
started: 2026-08-09T15:10:00+05:30
completed: null
estimate: M
depends-on: []
tags: [fallback, hallucination, anti-agentic, provider-bypass, trust, correctness]
---

## Description

The system has multiple runtime paths where a deterministic regex/PyMuPDF fallback can return a result while the ReAct agent never runs. When the fallback produces a plausible-looking output, the platform reports a completed run without any evidence that the actual reasoning loop, tool use, validation, or grounding happened.

This is not a harmless optimization; it is an anti-agentic design anti-pattern: a cheap fallback is silently substituted for the agent, and the result is then treated as if it were produced by the real reasoning pipeline.

## Problem Statement

The runtime logic in `src/api/run_engine.py` calls `run_pdf_fallback()` from both the provider-configured and provider-missing branches, and in the fallback success case it serializes and returns the result directly. The code then emits a completion status and persists the result as if the agent executed.

This creates a severe hallucination risk:

- a regex extraction can look valid without proving the model grounded the fields
- analytics may count this result as a successful agent run
- users may trust the platform because the run is returned with a success badge, even though no planning, tool calls, or validation occurred
- benchmark and leaderboard results are contaminated by non-agentic outputs masquerading as agentic ones

This violates the project’s core claim that the system is an agentic document-extraction pipeline grounded in evidence, not a silent parser fallback disguised as AI.

## Acceptance Criteria

- [ ] A fallback result is only allowed when the provider is genuinely unavailable and the fallback path is explicitly permitted by policy
- [ ] When a provider is configured, the real agent loop must execute for the relevant document types
- [ ] A fallback-produced result is clearly annotated as fallback-generated and not treated as a full agent run in analytics or UI badges
- [ ] The execution logs preserve a clear marker showing whether the run used fallback or the full ReAct graph
- [ ] Benchmarks and leaderboard metrics exclude fallback-only runs from agentic success claims unless explicitly labeled as parser-mode results

## Constraints

- No hidden fallback substitution behind a successful-looking status
- Keep offline/local dev fallback available but visible and explicit
- Do not permit metrics or success-rate claims to collapse fallback and agentic execution together

## Dependencies

- `src/api/run_engine.py`
- `src/fallback/pdf_runtime.py`
- `backend analytics and run-status serialization
- BLK-178, BLK-184, BLK-187, BLK-188

## Notes

- This is one of the clearest anti-agentic failure modes in the current codebase
- It directly raises hallucination risk because the system emits completion even when the evidence path never ran
- It undermines benchmark integrity, product trust, and any claim about grounded extraction

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T15:10 (devin)**: Implementation complete. Criteria 1-2 already fixed by BLK-264 (condition-gated fallback). Criteria 3-4 addressed by adding `execution_mode` field to all serialized run results + logger.info markers. Criterion 5 (benchmark exclusion) flagged for cline — the eval/benchmark harness in `src/eval/` has no existing mechanism to distinguish run types; cline owns test/eval code and should decide whether to filter on `execution_mode` in benchmark reports. Handed to cline for verification.

## Resolution

BLK-287 shares the same root cause as BLK-264 — the unconditional `run_pdf_fallback()` bypass. Criteria 1 and 2 are already addressed by the BLK-264 fix (fallback only runs when provider is unconfigured or `use_pdf_fast_path` is explicitly opted in). The remaining criteria (3, 4, 5) are addressed here:

### Criterion 3: Fallback results annotated as fallback-generated

Added `execution_mode` field to all serialized run results in `src/api/run_engine.py`:
- `serialize_extraction_result()` (line 445): returns `"execution_mode": "agent"` by default
- `_serialize_graph_result()` (line 492): returns `"execution_mode": "agent"`
- Fallback return path (line 678): overrides to `serialized["execution_mode"] = "fallback"`
- Error return path (line 732): includes `"execution_mode": "agent"`

This means any consumer of the serialized run result (frontend, analytics, API clients) can now distinguish fallback-produced results from agent-produced results by checking the `execution_mode` field. The frontend team (antigravity) can use this to display a "fallback mode" badge instead of a success badge.

### Criterion 4: Execution logs preserve clear marker

Added two `logger.info` calls:
- Line 676: `logger.info("Run %s using PDF fallback (execution_mode=fallback)", run_id, ...)` — logged when the fallback path produces a result
- Line 803: `logger.info("Run %s completed via ReAct agent (execution_mode=agent)", run_id, ...)` — logged when the agent loop completes

Both include `execution_mode` in the `extra` dict for structured logging consumers.

### Criterion 5: Benchmarks exclude fallback-only runs

The eval/benchmark harness in `src/eval/` (`benchmarks.py`, `accuracy.py`, `harness.py`) has no existing mechanism to distinguish run types — it calls `execute_run()` and treats all results uniformly. Since `src/eval/` is test/verification code (cline's territory per PROTOCOL §2.1), I did not modify it. The `execution_mode` field is now present in every serialized run result, so cline can filter benchmark/accuracy reports by `execution_mode == "agent"` to exclude fallback-only runs from agentic success claims. I've flagged this in the verification message to cline.

## Evidence

### Syntax validation

```
$ python -c "import ast; ast.parse(open('src/api/run_engine.py').read()); print('run_engine.py syntax OK')"
run_engine.py syntax OK
```

### Diff (git diff -- src/api/run_engine.py)

```diff
--- a/src/api/run_engine.py
+++ b/src/api/run_engine.py
@@ serialize_extraction_result return dict
+        "execution_mode": "agent",

@@ _serialize_graph_result return dict
+        "execution_mode": "agent",

@@ fallback return path
+    if fallback_result is not None:
+        logger.info("Run %s using PDF fallback (execution_mode=fallback)", run_id, extra={"run_id": run_id, "execution_mode": "fallback"})
         serialized = serialize_extraction_result(...)
+        serialized["execution_mode"] = "fallback"

@@ error return path
+            "execution_mode": "agent",

@@ agent return path
+    logger.info("Run %s completed via ReAct agent (execution_mode=agent)", run_id, extra={"run_id": run_id, "execution_mode": "agent"})
```

### Files changed (1, all in devin-owned `src/**` excluding `src/tests/`)

- `src/api/run_engine.py` — 5 insertion points: `execution_mode` field in 4 return dicts + 2 logger.info calls

### Files NOT changed (cline's territory)

- `src/eval/benchmarks.py`, `src/eval/accuracy.py`, `src/eval/harness.py` — cline should decide whether to filter on `execution_mode` in benchmark/accuracy reports
- `src/tests/` — not modified
