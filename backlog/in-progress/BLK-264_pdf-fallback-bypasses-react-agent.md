---
id: BLK-264
type: bug
title: "PDF fallback silently bypasses the ReAct agent for 9 of 22 skills, even when the LLM provider is fully configured"
priority: critical
status: verifying
phase: 1
owner: devin
created: 2026-08-09T10:00:00+05:30
started: 2026-08-09T14:30:00+05:30
completed: null
estimate: S
depends-on: []
tags: [agent, run-engine, fallback, correctness, eval-integrity, high-severity]
---

## Description

`_execute_run_inner` in `src/api/run_engine.py` calls `run_pdf_fallback()` (`src/fallback/pdf_runtime.py`) unconditionally for any PDF document whose skill has a registered regex parser — regardless of whether an LLM provider is configured. When the fallback returns a result, the function returns immediately; `build_react_graph()` / `graph.invoke()` is never called.

```python
if not settings.azure_api_key and not settings.azure_chat_endpoint:
    fallback_result = run_pdf_fallback(document_path, template_cls=template_cls,
                                        skill=skill, validator_config=validator_config)
    if fallback_result is None:
        raise RuntimeError("No LLM provider configured. ...")
else:
    fallback_result = run_pdf_fallback(document_path, template_cls=template_cls,
                                        skill=skill, validator_config=validator_config)
if fallback_result is not None:
    serialized = serialize_extraction_result(...)
    ...
    return serialized   # agent graph never runs
```

Both branches of the `if/else` call `run_pdf_fallback` with identical arguments — the only difference is whether a `RuntimeError` is raised when it returns `None`. The guard that looks like it's restricting the fallback to "no LLM configured" is cosmetic; it runs either way.

`run_pdf_fallback` itself decides whether to activate based only on file extension (`.pdf`) and skill name — not on provider availability:

```python
def run_pdf_fallback(document_path, *, template_cls, skill, validator_config):
    if Path(document_path).suffix.lower() != ".pdf":
        return None
    parser = _PARSERS.get(skill.name)
    if parser is None:
        return None
    ...
```

`_PARSERS` currently covers: `bank_statement`, `utility_bill`, `commercial_lease`, `trade_finance_scrutiny`, `commodity_trade`, `purchase_order`, `packing_list`, `purchase_order_sf1449`, `packing_list_travel`.

## Problem Statement

Upload a PDF bank statement, utility bill, commercial lease, trade-finance doc, commodity-trade doc, purchase order, or packing list — with Azure fully configured — and the system never builds the LangGraph, never calls the LLM planner, never calls a tool, never runs the circuit breaker, never runs trajectory-cascade detection, never runs the outcome validator's iterative gap-filling. A hand-written regex/PyMuPDF parser runs once and its output is returned as the run result. The "plan → act → observe → reflect" ReAct loop the platform is built around does not execute for these document types.

This directly undermines the project's accuracy claims: `src/tests/fixtures/high_value/` contains fixtures for `bank_statement`, `commercial_lease`, `commodity_trade`, `packing_list_travel`, `purchase_order_sf1449`, `trade_finance`, `utility_bill` — 7 of the 9 fallback-covered skills — and `src/tests/test_integration_real.py` runs them through `execute_run()`, the exact function containing this bypass. Any "integration real" / accuracy result for these 7 document types currently measures the regex parser, not the agent. If the agent's planning, tool selection, or gap-filling logic has bugs, this test suite structurally cannot catch them for the majority of the "high value" category.

It also contradicts the fallback module's own docstring, which frames it as an emergency path used "when no planner LLM or OCR provider is configured" — the code doesn't check that condition before using it.

## Acceptance Criteria

- [ ] `run_pdf_fallback` is only invoked when the LLM provider is genuinely not configured (i.e. collapse the `if/else` into a single condition-gated call)
- [ ] With Azure configured, all 9 currently-fallback-covered skills execute through `build_react_graph()` / the real agent loop for PDF inputs
- [ ] The redundant duplicate call in the `if/else` (§ same block) is removed as part of this fix — one call, one guarded raise
- [ ] If a "fast path" regex extraction is still wanted as an opt-in for these skills, it is exposed as an explicit definition-level setting, not a silent default
- [ ] `src/tests/test_integration_real.py` and any "high value" fixture runs are re-verified/re-labeled once they're measuring the agent instead of the fallback parser
- [ ] Fallback module docstring is updated to match actual invocation conditions (or code is changed to match the docstring)

## Constraints

- Do not remove the legitimate no-provider-configured fallback behavior — offline/local dev runs should still work
- Changing this will change eval numbers for 7 "high value" fixtures; flag this clearly in the PR description so accuracy claims get re-baselined, not silently changed

## Dependencies

- `src/api/run_engine.py` (`_execute_run_inner`)
- `src/fallback/pdf_runtime.py`
- `src/tests/test_integration_real.py`, `src/tests/fixtures/high_value/`
- Related to BLK-173 (missing provider-config validation) — that ticket covers the config-boundary check; this ticket covers the fact that the fallback runs even when config IS valid

## Notes

- Found via full-repo audit (`ADE_codebase_audit.md`, §1 and §4); confirmed still present in code as of 2026-08-09
- This is the highest-impact single bug found in the audit: it silently changes what the system does in production for ~40% of document skills and is exactly what the accuracy claims are built on

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T10:00 (mgmt)**: Logged after re-confirming the bypass is still live in `src/api/run_engine.py` lines ~654-674.

- **2026-08-09T14:30 (devin)**: Plan approved by mgmt (comms `2026-08-09_1445_mgmt-to-devin_blk264-approved`). Implementation complete, handed to cline for verification.

## Resolution

Collapsed the unconditional `if/else` in `_execute_run_inner` (`src/api/run_engine.py:654-672`) that called `run_pdf_fallback()` in both branches — regardless of whether an LLM provider was configured — into a single condition-gated call:

1. **`src/api/run_engine.py:654-672`**: `run_pdf_fallback()` is now called only when `(a)` no LLM provider is configured (`not llm_configured`), or `(b)` the definition explicitly opts in via `use_pdf_fast_path=True` in `agent_config`. When the LLM IS configured and fast-path is not opted in, `fallback_result` stays `None` and execution proceeds to `build_react_graph()` / `graph.invoke()` — the ReAct agent loop. The duplicate `else` branch call is removed entirely.

2. **`src/definitions/base.py:28`**: Added `use_pdf_fast_path: bool = False` to `AgentConfig`. This makes the regex fallback path an explicit per-definition opt-in rather than a silent default. No existing prebuilt definitions set this flag, so the default behavior changes: all 9 previously-fallback-covered skills (`bank_statement`, `utility_bill`, `commercial_lease`, `trade_finance_scrutiny`, `commodity_trade`, `purchase_order`, `packing_list`, `purchase_order_sf1449`, `packing_list_travel`) now run through the agent loop when Azure is configured.

3. **`src/fallback/pdf_runtime.py:316`**: Updated the trace message from "because no planner LLM/OCR provider is configured" to "(no LLM provider configured or fast-path opt-in enabled)" to accurately reflect both invocation conditions.

### Blast radius — accuracy re-baselining needed

`src/tests/test_integration_real.py` calls `execute_run()` → `_execute_run_inner()`. When run with real credentials, the 7 affected "high value" fixtures (`bank_statement`, `commercial_lease`, `commodity_trade`, `packing_list_travel`, `purchase_order_sf1449`, `trade_finance_scrutiny`, `utility_bill`) will now exercise the full ReAct agent loop instead of the regex parser. Any accuracy numbers previously derived from these fixtures measured the fallback parser, not the agent. **These fixtures' expected outputs may have been calibrated against the regex parser's output and need re-verification against agent output.**

No `src/tests/` files were modified (cline's territory per PROTOCOL §2.1).

## Evidence

### Syntax validation

```
$ python -c "import ast; ast.parse(open('src/api/run_engine.py').read()); print('run_engine.py syntax OK'); ast.parse(open('src/fallback/pdf_runtime.py').read()); print('pdf_runtime.py syntax OK')"
run_engine.py syntax OK
pdf_runtime.py syntax OK
```

### AgentConfig field verification

```
$ python -c "from src.definitions.base import AgentConfig; c = AgentConfig(); print(f'use_pdf_fast_path={c.use_pdf_fast_path}'); c2 = AgentConfig(use_pdf_fast_path=True); print(f'opt-in={c2.use_pdf_fast_path}'); print('AgentConfig OK')"
use_pdf_fast_path=False
opt-in=True
AgentConfig OK
```

### Diff (git diff -- src/api/run_engine.py src/definitions/base.py src/fallback/pdf_runtime.py)

```diff
--- a/src/api/run_engine.py
+++ b/src/api/run_engine.py
@@ -651,18 +651,19 @@
-    # BLK-171: Fail fast if LLM provider is not configured (unless PDF fallback can handle it)
-    if not settings.azure_api_key and not settings.azure_chat_endpoint:
+    # BLK-264: PDF fallback only runs when (a) no LLM provider is configured, or
+    # (b) the definition explicitly opts in via use_pdf_fast_path. Previously
+    # both branches of an if/else called run_pdf_fallback unconditionally,
+    # silently bypassing the ReAct agent for 9 of 22 skills even with Azure configured.
+    use_fast_path = agent_config.get("use_pdf_fast_path", False)
+    llm_configured = bool(settings.azure_api_key and settings.azure_chat_endpoint)
+    fallback_result = None
+    if not llm_configured or use_fast_path:
         fallback_result = run_pdf_fallback(...)
-        if fallback_result is None:
+        if fallback_result is None and not llm_configured:
             raise RuntimeError(...)
-    else:
-        fallback_result = run_pdf_fallback(...)

--- a/src/definitions/base.py
+++ b/src/definitions/base.py
+    use_pdf_fast_path: bool = False

--- a/src/fallback/pdf_runtime.py
+++ b/src/fallback/pdf_runtime.py
-                thought="Use deterministic PDF text fallback because no planner LLM/OCR provider is configured."
+                thought="Use deterministic PDF text fallback (no LLM provider configured or fast-path opt-in enabled)."
```

### Files changed (3, all in devin-owned `src/**` excluding `src/tests/`)

- `src/api/run_engine.py:654-672` — collapsed if/else into condition-gated call
- `src/definitions/base.py:28` — added `use_pdf_fast_path` field
- `src/fallback/pdf_runtime.py:316` — updated trace message

### Files NOT changed (cline's territory)

- `src/tests/test_integration_real.py` — calls `execute_run()` but was not modified; accuracy re-baselining is cline's call
