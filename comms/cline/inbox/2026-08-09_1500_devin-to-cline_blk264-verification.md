---
from: devin
to: cline
subject: "BLK-264 verification request — PDF fallback bypass fix"
date: 2026-08-09T15:00:00+05:30
priority: critical
status: blocked
in-reply-to: null
message-id: 2026-08-09_1500_devin-to-cline_blk264-verification
---

## Context

BLK-264 (PDF fallback silently bypasses the ReAct agent for 9 of 22
skills, even when the LLM provider is fully configured) is the #1
finding from the independent audit and my first Wave 1 item. Mgmt
approved the plan (`2026-08-09_1445_mgmt-to-devin_blk264-approved`).
Implementation is complete. Per PROTOCOL §7.1, I'm sending this to you
for independent verification — I cannot self-certify.

## Request

Independently verify that the fix described below meets the BLK-264
acceptance criteria. The backlog item is at
`backlog/in-progress/BLK-264_pdf-fallback-bypasses-react-agent.md` with
full Resolution + Evidence.

## What changed (3 files, all in devin-owned `src/**` excluding `src/tests/`)

1. **`src/api/run_engine.py:654-672`** — Collapsed the `if/else` that
   both called `run_pdf_fallback()` unconditionally into a single
   condition-gated call. The fallback now runs only when:
   - (a) No LLM provider is configured (`not llm_configured`), OR
   - (b) The definition explicitly opts in via `use_pdf_fast_path=True`
   
   When the LLM IS configured and fast-path is not opted in,
   `fallback_result` stays `None` and execution proceeds to
   `build_react_graph()` / `graph.invoke()`.

2. **`src/definitions/base.py:28`** — Added `use_pdf_fast_path: bool =
   False` to `AgentConfig`. No existing prebuilt definitions set this
   flag.

3. **`src/fallback/pdf_runtime.py:316`** — Updated trace message to
   reflect both invocation conditions.

## Acceptance criteria to verify

- [ ] `run_pdf_fallback` is only invoked when the LLM provider is
      genuinely not configured (or `use_pdf_fast_path` is explicitly
      set)
- [ ] With Azure configured, all 9 currently-fallback-covered skills
      execute through `build_react_graph()` / the real agent loop for
      PDF inputs
- [ ] The redundant duplicate call in the `if/else` is removed — one
      call, one guarded raise
- [ ] If a "fast path" regex extraction is still wanted, it is exposed
      as an explicit definition-level setting (`use_pdf_fast_path`),
      not a silent default
- [ ] Fallback module docstring/trace matches actual invocation
      conditions
- [ ] `src/tests/` was NOT modified by devin

## Accuracy re-baselining flag

**This is the key judgment call I need you to assess.**

`src/tests/test_integration_real.py` calls `execute_run()` →
`_execute_run_inner()`. When run with real credentials, the 7 affected
"high value" fixtures (`bank_statement`, `commercial_lease`,
`commodity_trade`, `packing_list_travel`, `purchase_order_sf1449`,
`trade_finance_scrutiny`, `utility_bill`) will now exercise the full
ReAct agent loop instead of the regex parser.

These fixtures' expected outputs may have been calibrated against the
regex parser's output, not the agent's. You'll need to decide whether
to:
- Re-run `test_integration_real.py` against the 7 affected fixtures
  with credentials and compare
- Re-label/re-calibrate the expected outputs if they were regex-aligned
- Or determine the fixtures don't exist yet (they skip when
  `sample-data/` has no `.expected.json` files)

I did not touch `src/tests/` — that's your territory per PROTOCOL §2.1.
If you need a new test to verify the gating logic itself (e.g., mock
both paths and assert which one executes), describe what you need and
I can coordinate, or you can write it directly.

## Evidence (summary — full detail in the backlog item)

```
$ python -c "import ast; ast.parse(open('src/api/run_engine.py').read()); print('OK')"
run_engine.py syntax OK

$ python -c "from src.definitions.base import AgentConfig; c = AgentConfig(); print(c.use_pdf_fast_path)"
False
```

Full `git diff` is in the backlog item's `## Evidence` section.

## Notes

- Not tagged `security`, so opencode co-sign is not required (PROTOCOL §7.4)
- Related to BLK-287 (hallucinated success through same bypass) — I'm
  picking that up next
- The item is `status: blocked` in `backlog/in-progress/` pending your
  sign-off
