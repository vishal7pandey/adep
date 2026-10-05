# ADE-31 — Head-to-head P&ID evaluation: old LangGraph engine vs new engine

Status: approved · Risk: medium · Jira: ADE-31
Created: 2026-10-05 · Slug: pid-head-to-head

## Problem

The owner decided (ADE-13) to migrate ADEP from the old LangGraph engine to the new, much simpler agent engine, and to delete the old engine (ADE-33) only after the new one shows parity on real work. Today nothing measures that. The new engine has been run once on one drawing (ADE-41); the old engine has never been run on a P&ID in this repo. Without a repeatable, same-input comparison with variance, "parity" would be a feeling, and ADE-33 would be a guess.

## Users and context

The maintainer and agents deciding whether to switch the API to the new engine (ADE-32) and retire the old one (ADE-33). The inputs are the DEXPI e.V. reference drawings (`ADE_DEXPI_REF_DIR`, read-only), whose Proteus XML gives ground truth; ADE-15 (`src/eval/pid_scoring.py`, `pid_ground_truth.py`) already scores an extraction against it. The old engine's P&ID path is the `graph_extraction` task (`PnIDContract`, `PnIDSkill`, tools `detect_symbols`... `build_graph`), whose result is a typed graph; the new engine returns the five flat lists of the `pid-dexpi-digitizer` skill.

## Goals and non-goals

**Goals**
- Run both engines on the same drawings, the same model and each engine's own native perception tools, N times each, and report accuracy (ADE-15 metrics), latency, tokens and failure rate with their spread.
- Make the comparison repeatable with one command and safe to run: hard spend caps, no secrets in output.

**Non-goals**
- Improving either engine's accuracy; DEXPI export (ADE-14); non-P&ID documents (ground truth untrustworthy, ADE-10); switching or deleting an engine (ADE-32/33).
- A price table. Cost is reported in tokens; dollars only when the caller passes per-million-token prices.

## Requirements

- R1. The system runs every selected engine on every selected drawing N times, alternating engines within each repetition so provider drift or rate limits do not favour one side, and records for each run the wall-clock seconds, the ADE-15 score, and the tokens used.
- R2. The system summarises each engine on each drawing, and each engine overall, as count, failures, and mean, sample standard deviation, minimum and maximum for mean count recall, label precision, seconds and tokens, computed over successful runs only.
- R3. A run that raises, times out or returns unparseable output is recorded as a failure with its error type only (never the message, which can echo secrets) and does not stop the comparison.
- R4. The old engine's typed graph (`nodes` with `type`, `edges`) is mapped onto the scorer's five categories by a pure, documented function; the new engine's output is scored as is.
- R5. Token use is measured outside both engines, at the OpenAI client calls that either engine makes (sync and async, agent and perception tools alike), and a hard cap on calls and on tokens stops spending before the next call.
- R6. The system writes one JSON results file under the git-ignored `.adep/eval/` and prints a side-by-side markdown table; neither contains an API key.
- R7. When the spend cap is reached the remaining runs are recorded as skipped for budget and the report says the comparison is incomplete.
- R8. Each engine runs with its own native perception, and the report states which: the new engine's VLM-based tools (its OCR tool falls back to the VLM when Tesseract is missing), the old engine's PaddleOCR layout and OCR (`--old-ocr paddle`, the default). `--old-ocr none` runs the old engine with no layout/OCR tool; it is allowed but recorded as such.

## Acceptance criteria

- AC1. With stub engines A and B, 2 drawings and N=3, each engine's `run` is called exactly 3 times per drawing, A and B alternate within each repetition, and the records carry seconds (from an injected clock), score and tokens. (R1)
- AC2. For records with known recalls (e.g. 0.5, 0.7, 0.9), the summary gives mean 0.7, sample standard deviation 0.2, min 0.5, max 0.9; with one success the standard deviation is `None`; with zero successes all statistics are `None` and failures are counted; failed runs are excluded from the means. (R2)
- AC3. A stub engine that raises `RuntimeError("sk-secret-123")` on its second run yields a failure record whose error is `RuntimeError`, the comparison finishes the remaining runs, and the string `sk-secret-123` appears in neither the records, the results file nor the table. An engine returning output with no parseable lists is a failure with error type `UnparseableOutput`. (R3)
- AC4. A graph with nodes of type `vessel`, `pump`, `valve`, `control_valve`, `instrument`, `sensor`, `off_page_connector`, `pipe`, `fitting` and 4 edges maps to: nodes = vessel + pump, valves = both valve types, instruments = instrument + sensor, off_page_connectors = 1, edges = 4, and tags are carried over; `pipe` and `fitting` nodes are not counted; an empty or malformed graph (`None`, missing keys, non-dict nodes) maps to five empty lists without raising. (R4)
- AC5. With a fake completions function returning known usage, the meter counts calls and prompt/completion tokens for both sync and async `create`, a second call after the call cap raises `SpendCapReached` without calling the underlying function, the same for the token cap, and the original methods are restored on exit even when the body raises. (R5)
- AC6. The results file is valid JSON containing meta (engines, model name, N, drawings, caps, perception note), all records and the summary, is written under `.adep/eval/` by default (a path confirmed git-ignored), and does not contain the value of `OPENAI_API_KEY` when one is set in the environment; the table has one row per engine per drawing plus overall rows, each with n and failures, and the meta records each engine's perception setup. (R6, R8)
- AC7. With a token cap that is exhausted midway, later runs are recorded as `skipped_budget`, the summary excludes them, and the table and the results meta say the comparison is incomplete. (R7)
- AC8. Manual: the real comparison, N>=5 per engine per drawing on the three DEXPI references, runs under a stated cap, and its table, spread and the cost in tokens are posted on ADE-31 and in Confluence, with a verdict on parity for ADE-32/33 and the honest limits (see Risks). (R1-R8)

## Edge cases and failure modes

- A drawing whose ground truth has zero of a category: ADE-15 already treats it as not applicable; it is excluded from that category's recall.
- An engine hanging: each run has a wall-clock timeout (default 600 s); on expiry it is a failure of type `Timeout`.
- Missing references directory or unknown drawing name: a clear error before any model call.
- Missing API key: a clear error before any model call.
- A run that returns valid JSON with all lists empty is a success with recall 0, not a failure: accuracy is the question, not the format.

## Non-functional requirements

- Security: the key is read from the process environment only; never printed, logged or written (see `.factory/policies/security.md`). Error text from the provider is never stored.
- Cost: default caps keep a full run to a few dollars at most on the small model; caps are required arguments with defaults, not optional.
- Hermetic tests: the unit tests never touch the network or need a key.

## Assumptions

- Each engine is judged with its own native perception (R8). A first smoke run showed the old engine cannot work without its layout tool: with no OCR provider registered its P&ID skill keeps calling `detect_layout`, is rejected five times and auto-pauses with nothing extracted (recall 0.0). So VLM-only parity was dropped as the default: it measures the missing tool, not the engine. Running the old engine natively needs PaddleOCR, which has no wheels for the repo's Python 3.14, so the real comparison runs in a separate Python 3.12 environment (paddlepaddle 2.6.2, numpy<2 with two numpy alias shims); this is recorded with the results.
- One model for both engines and all runs, chosen on the command line; default the small model for the variance study (cheap), with an optional smaller confirmation pass on the larger one.
- N=5 and the three references (C01V04, C02V03, C03V04) are the default; the owner may raise N.
- Tokens are counted at the OpenAI client; this also gives an independent check for the agent-usage anomaly in ADE-42.

## Risks and dependencies

- Risk is medium: money is spent, but it is capped and reversible. Does not change either engine or any API behaviour.
- Fairness: the two engines use different perception stacks by design (that is the question), and the old engine runs in a patched 3.12 environment, so the verdict is "on this input, with this setup", not a general ranking.
- Three drawings are a small sample and the DEXPI references are synthetic-looking training drawings; they say little about messy scans.
- ADE-42 (the new engine's own token accounting) is not required: the meter measures independently.

## Open questions

None. Assumptions above are recorded for the owner to overrule.
