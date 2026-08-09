---
from: backend
to: mgmt
subject: "BLK-088 to BLK-100: All 10 stabilization fixes complete. 745 tests passing."
date: 2026-08-08T03:00:00+05:30
priority: high
status: closed
message-id: 2026-08-08_0300_backend-to-mgmt_stabilization-complete
in-reply-to: 2026-08-08_0240_mgmt-to-backend-stabilization-review
---

## Stabilization Review â€” All 10 Items Fixed âœ…

**745 tests passing in 13.72s.** 30 new tests in `test_stabilization.py`.

### Critical Fixes (items 1-4)

#### BLK-088 â€” Run engine skill/template registry incomplete âœ…

**File:** `src/api/run_engine.py`

Added all 12 skills and 12 templates to `_SKILL_REGISTRY` and `_TEMPLATE_REGISTRY`. Previously only `invoice` was registered â€” any run using `trade_finance`, `bill_of_quantities`, `utility_bill`, or the 8 new BLK-087 skills would fail with `ValueError`.

**Test:** `TestSkillTemplateRegistry` â€” 6 tests verifying all 12 skills/templates registered, resolve functions work, unknown IDs raise.

#### BLK-091 â€” API field name mismatch: skill_ref vs skill_id âœ…

**Files:** `src/definitions/base.py`, `src/api/routes/definitions.py`, `src/api/run_engine.py`, `src/definitions/prebuilt.py`

- Renamed `skill_ref`â†’`skill_id` and `template_ref`â†’`template_id` in `AgentDefinition` model
- Added `populate_by_name=True` with backward-compatible aliases (`skill_ref`/`template_ref` still accepted as aliases)
- Updated `CreateDefinitionRequest`, `UpdateDefinitionRequest` to use `skill_id`/`template_id`
- Updated `run_engine.py` to resolve via `skill_id` with fallback to `skill_ref` for old data
- Updated all 11 prebuilt definitions to use `skill_id`/`template_id`
- Updated all existing tests to use new field names

**Test:** `TestSkillIdFieldNames` â€” 3 tests verifying field name, alias acceptance, and dump format.

#### BLK-093 â€” Start run field mismatch: document_path vs document_url âœ…

**File:** `src/api/routes/runs.py`

Added `document_url` as alias for `document_path` in `StartRunRequest` with `populate_by_name=True`. Frontend can now send either field name.

**Test:** `TestDocumentUrlAlias` â€” 2 tests verifying both field names work.

#### BLK-092 â€” Store not seeded with prebuilt content âœ…

**File:** `src/definitions/prebuilt.py`

Added `seed_store()` function that creates all 12 skills, 12 templates, and 11 definitions in `.adep/` on first boot. Safe to call on every boot â€” only seeds what's missing. Does not overwrite existing content.

**Test:** `TestSeedStore` â€” 5 tests verifying creation, no-overwrite, and file existence.

### Medium Fixes (items 5-8)

#### BLK-095 â€” RunStatus.PAUSED not defined âœ…

**Files:** `src/agent/state.py`, `src/agent/graph.py`, `src/api/run_engine.py`

- Added `PAUSED = "paused"` constant to `RunStatus`
- Updated `reflect_node` to use `RunStatus.PAUSED` instead of string literal `"paused"`
- Updated `should_continue` and `should_act` to route PAUSED â†’ terminate (prevents infinite loop)
- Updated `map_status_to_frontend` to map PAUSED â†’ `"paused"` (was mapping to `"failed"`)

**Test:** `TestRunStatusPaused` â€” 6 tests verifying constant, all 3 status mappings, and both conditional edges.

#### BLK-096 â€” build_initial_state missing 5 keys âœ…

**File:** `src/run.py`

Added `document_state`, `consecutive_non_improving`, `token_usage`, `total_tokens`, `total_cost_usd` to the return dict of `build_initial_state`. Also added `DocumentState` import.

**Test:** `TestBuildInitialStateKeys` â€” 2 tests verifying all 21 keys present and default values correct.

#### BLK-094 â€” Max cycles override broken âœ…

**File:** `src/api/run_engine.py`

The old code set `state["total_cycles"] = 0` which was already 0 â€” a no-op. Now reads `max_cycles_per_document` from the definition's `agent_config` and uses it for the graph's `recursion_limit`. Falls back to `settings.max_cycles_per_document` if no override.

**Test:** `TestMaxCyclesOverride` â€” 1 test verifying the override value (15) produces `recursion_limit=25` (15+10).

#### BLK-099 â€” field_attempts incremented on success âœ…

**File:** `src/agent/graph.py`

Removed lines 876-877 from `_process_tool_result` that incremented `field_attempts` on successful extraction. Give-up caps were triggering prematurely because attempts were double-counted (once in `observe_node` for failures, once in `_process_tool_result` for successes).

**Test:** `TestFieldAttemptsOnSuccess` â€” 1 test verifying `field_attempts` unchanged after successful extraction.

### Low Priority (items 9-10)

#### BLK-089 â€” Duplicate _get_run_or_404 in runs.py âœ…

**File:** `src/api/routes/runs.py`

Removed the second definition at line 327. The first definition at line 26 is the canonical one.

**Test:** `TestNoDuplicateGetRunOr404` â€” 1 test verifying only 1 definition exists in source.

#### BLK-100 â€” _INJECTION_PATTERS typo âœ…

**File:** `src/agent/graph.py`

Renamed `_INJECTION_PATTERS` â†’ `_INJECTION_PATTERNS` and updated the reference in `_contains_instruction_patterns`.

**Test:** `TestInjectionPatternsTypo` â€” 3 tests verifying constant name, detection works, and list is populated.

### Note on BLK-090

BLK-090 (SSE stream replays, not live) was flagged as HIGH but the fix requires either background task execution or a fundamentally different run architecture. The current v1 design executes runs synchronously and replays trace events via SSE. This is a known v1 limitation documented in the `stream_run` endpoint. Recommend deferring to v2 with async run execution.


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
