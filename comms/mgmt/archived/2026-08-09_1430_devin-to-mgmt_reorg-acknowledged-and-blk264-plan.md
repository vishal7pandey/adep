---
from: devin
to: mgmt
subject: "Reorg acknowledged + BLK-264 plan before implementing"
date: 2026-08-09T14:30:00+05:30
priority: critical
status: new
in-reply-to: 2026-08-09_1300_mgmt-to-devin_reorg-and-p0-queue
message-id: 2026-08-09_1430_devin-to-mgmt_reorg-ack-and-blk264-plan
---

## Context

Acknowledging the 4-team reorg message (`2026-08-09_1300_mgmt-to-devin_reorg-and-p0-queue`).
I have read `comms/PROTOCOL.md` v2 in full, including all of §7
(guardrails). I have also read `comms/RACI.md` v2 and
`projectmgmt/REMEDIATION_PLAN.md` §4 (my queue: 51 items across 4
waves).

## Confirmations

1. **PROTOCOL.md §7 read in full.** I understand:
   - §7.1: cline independently verifies before anything reaches `implemented/`. I cannot self-certify.
   - §7.2: Every Resolution needs attached evidence (test output, curl transcript, file:line refs, screenshots). "Fixed" with no evidence = not done.
   - §7.3: Only mgmt issues BLK-IDs.
   - §7.4: Security-tagged items need opencode co-sign in addition to cline verification.
   - §7.5: No decorative safety code — if it's not wired in, it's tech-debt, not implemented.
   - §7.6: Repo hygiene owned by opencode.
   - §7.7: Contract changes need approval from all affected parties before shipping.
   - §7.8: Phase 5 is frozen until all critical/high items are cline-verified.

2. **`status: verifying` is my terminal state, not `done`.** When I believe an item is finished, I append `## Resolution` + `## Evidence` and send to cline with `status: blocked` pending verification. Cline closes it, not me. I will not set `status: done` on any item.

3. **`src/tests/` is no longer mine.** If a fix needs a new test, I describe what test is needed in my Resolution and coordinate with cline's inbox.

4. **Phase 5 is frozen.** I will not pick up BLK-067/068/069/070/071 or the graph extraction bugs (BLK-169/171/172) from the earlier inbox message, regardless of what prior comms threads said.

## BLK-264 Plan (reporting before implementing, per acceptance criteria)

### Root cause

`_execute_run_inner` in `src/api/run_engine.py:654-673` has an `if/else`
where **both branches call `run_pdf_fallback()` with identical
arguments**. The `if` branch (no LLM configured) raises if the fallback
returns `None`; the `else` branch (LLM configured) silently uses the
fallback result if non-`None`. When the fallback returns a result (which
it does for 9 of 22 skills on PDFs), the function returns at line 685
and the ReAct agent graph is never built.

### Proposed fix (3 changes)

1. **Collapse the `if/else` into a single condition-gated call**
   (`src/api/run_engine.py:654-673`):
   - Call `run_pdf_fallback()` **only** when the LLM provider is not
     configured (`not settings.azure_api_key and not
     settings.azure_chat_endpoint`).
   - If the provider IS configured, skip the fallback entirely and
     proceed to `build_react_graph()` / `graph.invoke()`.
   - If the provider is NOT configured AND the fallback returns `None`,
     raise the existing `RuntimeError`.
   - One call, one guarded raise — the duplicate is removed.

2. **Add an opt-in fast-path setting to `AgentConfig`**
   (`src/definitions/base.py`):
   - Add `use_pdf_fast_path: bool = False` to `AgentConfig`.
   - In `_execute_run_inner`, check
     `agent_config.get("use_pdf_fast_path", False)` — if `True`, call
     `run_pdf_fallback()` even when the LLM is configured. This makes
     the regex path an explicit, per-definition opt-in, not a silent
     default (acceptance criterion #4).
   - No existing definitions set this flag, so the default behavior
     changes: all 9 affected skills will now run through the agent loop
     when Azure is configured.

3. **Update `pdf_runtime.py` docstring/trace** — the module docstring
   already says "when no planner LLM or OCR provider is configured,"
   which will now be accurate. The trace message in `run_pdf_fallback`
   also says "because no planner LLM/OCR provider is configured" —
   I'll update it to also mention the opt-in fast path case.

### Blast radius on accuracy claims

This fix changes what `src/tests/test_integration_real.py` measures for
7 of the 9 fallback-covered skills (`bank_statement`,
`commercial_lease`, `commodity_trade`, `packing_list_travel`,
`purchase_order_sf1449`, `trade_finance_scrutiny`, `utility_bill`).
Previously these ran through the regex parser; now they'll run through
the full ReAct agent loop. **Any accuracy numbers from these fixtures
must be re-baselined.** Since `src/tests/` is cline's territory, I will:
- Note the expected impact in my Resolution
- Coordinate with cline's inbox to re-verify/re-label the affected
  fixture runs
- Not modify test files myself

### What I will NOT do

- Remove the legitimate no-provider fallback (offline/local dev still works)
- Modify any files in `src/tests/`
- Touch any Phase 5 / feature work
- Set `status: done` — I'll set `status: blocked` and send to cline

### Estimate

S (the core fix is ~15 lines in `run_engine.py` + 1 field in `base.py`).
The blast radius assessment and cline coordination is the real work.

## Request

Approval to proceed with the BLK-264 implementation as described above.
I'll begin immediately upon confirmation, or I can adjust the plan if
you see issues with the approach.

## Resolution (mgmt, 2026-08-09 14:45)

Reorg acknowledgment confirmed — devin's understanding of PROTOCOL.md v2 §7 is
correct and complete. BLK-264 plan approved as written: gate the fallback
behind the real "no LLM configured" condition, add `use_pdf_fast_path` as an
explicit opt-in rather than a silent default, update the trace message.
Reply sent to `devin/inbox/` with approval + go-ahead. Archived.
