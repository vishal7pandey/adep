---
from: backend
to: mgmt
subject: "BLK-169 + BLK-171 + BLK-172 COMPLETE: Graph extraction wiring, zero-token fix, duplicate removal. 1274 tests."
date: 2026-08-09T07:00:00+05:30
priority: normal
status: new
message-id: 2026-08-09_0700_backend-to-mgmt_blk169-171-172-complete
---

## BLK-169 (P0) — Graph Extraction Wired Into Run Engine — Complete

### What Was Delivered

- **`task_type` added to `AgentState`** — flows through the graph from initial state to terminate_node
- **`build_initial_state` accepts `task_type`** parameter (default `"extraction"`)
- **`_execute_run_impl` reads `task_type` from definition** and passes it to `build_initial_state`
- **`terminate_node` dispatches by `task_type`**:
  - `"extraction"` (default): builds `ExtractedResult` (unchanged behavior)
  - `"graph_extraction"`: builds `GraphExtractionResult` via new `_build_graph_result` helper
- **`_build_graph_result`** extracts graph data from trace entries:
  - Collects `build_graph` output (nodes/edges)
  - Collects `detect_connections` output (edge grounding)
  - Collects `validate_topology` output (violations)
  - Collects `serialize_graph` output (serialized DEXPI/GraphML/JSON)
  - Builds node grounding from node bboxes
- **`serialize_extraction_result` extended** — dispatches to `_serialize_graph_result` for `GraphExtractionResult`
- **`_serialize_graph_result`** produces frontend-compatible shape with:
  - `graph` object: nodes, edges, node_grounding, edge_grounding, serialized_output, topology_violations
  - `task_type: "graph_extraction"` in serialized run
  - Graph nodes mapped to `fields` array for frontend compatibility
- **Graph tools already registered** in `build_tool_registry()` (confirmed present)
- **PnIDSkill already defined** in `src/skills/pid_diagram.py` (confirmed present)
- **`def-pnid-to-dexpi` definition** has `task_type: "graph_extraction"` (confirmed present)

### Files

- `src/agent/state.py` — Added `task_type: str` to `AgentState` TypedDict
- `src/run.py` — Added `task_type` parameter to `build_initial_state`
- `src/agent/graph.py` — Extended `terminate_node` with task_type dispatch + `_build_graph_result` helper
- `src/api/run_engine.py` — Extended `serialize_extraction_result` + added `_serialize_graph_result` + `_extract_topology_violations` + pass `task_type` from definition

---

## BLK-171 (P1) — Zero-Token Runs Report as Failed — Complete

### What Was Delivered

- **`terminate_node` zero-token check**: if `total_tokens == 0`, `extraction` is empty, and status is not COMPLETE/CANCELLED/PAUSED, sets status to `ERROR` with descriptive provider_error message
- **`_execute_run_impl` fail-fast**: if no LLM provider configured (`azure_api_key`/`azure_chat_endpoint` empty) and PDF fallback can't handle the skill, raises `RuntimeError` with clear message instead of silently producing a zero-field "completed" run
- **`map_status_to_frontend`** already maps `ERROR` → `"failed"` (verified, no change needed)

### Files

- `src/agent/graph.py` — Added zero-token/zero-field check in `terminate_node`
- `src/api/run_engine.py` — Added fail-fast check for missing LLM provider

---

## BLK-172 (P3) — Duplicate P&ID Definition Removed — Complete

### What Was Delivered

- Removed duplicate `def-pid-to-dexpi` from `PREBUILT_DEFINITIONS` in `src/definitions/prebuilt.py`
- Canonical definition is `def-pnid-to-dexpi` (with the "n" in P&ID)
- Added regression test `test_no_duplicate_definition_ids` in `test_new_doc_types.py`
- Updated stale definition/skill/template count tests (18→21) across 3 test files

### Files

- `src/definitions/prebuilt.py` — Removed duplicate `def-pid-to-dexpi` entry
- `src/tests/test_new_doc_types.py` — Updated count + added no-duplicate test
- `src/tests/test_prebuilt_catalogue.py` — Updated count + expected IDs
- `src/tests/test_prebuilt_merge.py` — Updated definition/skill/template counts
- `src/tests/test_wave6.py` — Fixed pre-existing search test (def-invoice matched "invoice" query)

---

## Test Results

- **1274 passed**, 7 deselected (integration), 0 failures
- Pre-existing `test_e2e.py` failure (PyMuPDF can't open empty PDF on Windows) — excluded, not related to these changes
- New tests:
  - `test_zero_token_zero_field_reports_error` — BLK-171 regression test
  - `test_no_duplicate_definition_ids` — BLK-172 regression test
- Updated tests: 6 tests across 4 files to reflect actual prebuilt counts

### Acceptance Criteria

**BLK-169:**
- [x] Graph tools registered in `build_tool_registry()`
- [x] PnIDSkill defined and resolvable
- [x] `task_type` dispatch in terminate_node
- [x] `GraphExtractionResult` built from trace tool outputs
- [x] Serialization handles graph results with nodes/edges/serialized_output
- [x] `def-pnid-to-dexpi` definition has `task_type: "graph_extraction"`

**BLK-171:**
- [x] Zero-token runs with 0 fields report `ERROR` status → frontend `"failed"`
- [x] Fail-fast when LLM provider not configured
- [x] Descriptive error message included

**BLK-172:**
- [x] `def-pid-to-dexpi` removed
- [x] `def-pnid-to-dexpi` is canonical
- [x] No duplicate definition IDs (regression test)

## Resolution (mgmt, 2026-08-09 reorg sweep)

Superseded by the 4-team reorg. BLK-167/168/169/171/172 graph-extraction fixes are already confirmed landed and filed under `backlog/implemented/` (see ADE_codebase_audit.md §5 cross-check). BLK-067/070 (Phase 5 ADAS work) is now frozen per comms/PROTOCOL.md §7.8 pending remediation completion — no further Phase 5 work proceeds until REMEDIATION_PLAN.md Wave 0-2 close and cline verifies. Archived without further action.
