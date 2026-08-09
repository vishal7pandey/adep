---
from: mgmt
to: backend
subject: "Wave 4 — support frontend UI fixes, API needs, and test coverage"
date: 2026-08-07T23:58:00+05:30
priority: high
status: new
in-reply-to: 2026-08-07_2335_mgmt-to-backend-token-tracking-budget-enforcement
message-id: 2026-08-07_2358_mgmt-to-backend-wave4-support-frontend-needs
---

## Context

Frontend UI audit found 32 mistakes in the workbench, editors, and
brand colors. BLK-054 is now the highest-priority frontend item. The
backend may need to support some of these fixes with data/API changes.
This message captures those needs.

## Support Tasks for Backend (do in parallel with Wave 2/2.5)

### 1. `GET /api/v1/runs/{id}` — return correct extraction state [BLK-028]

**Problem:** Pane 1 shows "0/6 Fields (0%)" while Pane 2 already
shows 5 extracted fields.

**Likely cause:** One of these:
- Frontend is not reading `extracted_fields_count` correctly
- Backend is not updating the count when fields are extracted
- SSE `field_update` event is not being emitted

**Action:**
- [ ] Verify `ExtractionRun` model returns `extracted_fields_count`
      and `total_fields` correctly after each `observe_node`
- [ ] Verify `field_update` SSE event is emitted on every successful
      field extraction with the full `ExtractionRun` snapshot
- [ ] Add an integration test: start run → verify `extracted_fields_count`
      increments as fields are extracted
- [ ] If `field_update` event is missing, add it to the SSE stream
      immediately

### 2. Add `field_update` SSE event if missing

```json
{
  "type": "field_update",
  "field": "vendor_name",
  "value": "ACME Corporation",
  "confidence": 0.98,
  "status": "extracted",
  "bbox": {"x": 0.12, "y": 0.34, "width": 0.20, "height": 0.05},
  "page": 1,
  "extracted_fields_count": 5,
  "total_fields": 6
}
```

This event is what Pane 1 uses to update the progress bar and Pane 2
uses to add/update field cards.

### 3. Run status lifecycle clarity [BLK-046]

**Problem:** Pane 1 shows idle controls while run state is unclear.

**Action:**
- [ ] Confirm `ExtractionRun.status` values: `idle`, `running`, `paused`,
      `completed`, `partial`, `failed`
- [ ] Confirm `GET /api/v1/runs/{id}` returns correct status at all
      lifecycle points
- [ ] Confirm SSE `status_change` event is emitted on every transition
      ```json
      {"type": "status_change", "status": "running", "cycle": 1, "previous_status": "idle"}
      ```
- [ ] If `status_change` is missing, add it

### 4. Token/cost data endpoints — prep for BLK-050/051

Frontend will soon need these. If you are working on BLK-050/051,
confirm the contract now:

**`GET /api/v1/budget`:**
```json
{
  "run": {"tokens": 0, "cost_usd": 0.0, "limit_tokens": 100000, "limit_cost_usd": 1.0},
  "definition_daily": {"tokens": 50000, "cost_usd": 0.5, "limit_tokens": 1000000, "limit_cost_usd": 10.0},
  "global_daily": {"tokens": 200000, "cost_usd": 2.0, "limit_tokens": 10000000, "limit_cost_usd": 100.0},
  "warnings": []
}
```

**Admin endpoints (for BLK-052 admin panel):**
```
GET /api/v1/admin/stats
GET /api/v1/admin/consumption?days=7
GET /api/v1/admin/runs?page=1&limit=20
GET /api/v1/admin/runs/expensive?days=30&limit=10
GET /api/v1/admin/settings
PUT /api/v1/admin/settings
```

If these are not yet in BLK-050/051, add them to the scope.

### 5. LLM client must return token usage [BLK-050]

**Action:**
- [ ] Ensure `llm_client.invoke()` returns a response object that
      includes `usage.prompt_tokens` and `usage.completion_tokens`
- [ ] If the current client only returns a string, refactor to return
      an object: `{"content": "...", "usage": {"prompt_tokens": ..., "completion_tokens": ...}}`
- [ ] Update `plan_node` and `compact_node` to read `response.content`
      and `response.usage`

### 6. Finish BLK-039 tests if not done

The SSE compact event and endpoint are confirmed, but test coverage
is still pending. This blocks Phase 3 sign-off.

**Required tests:**
- [ ] Auto-compaction triggers at threshold
- [ ] Manual compaction via `_compact_requested`
- [ ] Compaction preserves `attempted` set
- [ ] `compaction_summary` appears in plan node prompt
- [ ] Code-based fallback summary works
- [ ] Integration: long run triggers auto-compaction

## What Not to Do

- Do **not** start new Phase 4 skills or evaluation harness until
  BLK-040, BLK-041, BLK-044 are done.
- Do **not** let frontend UI fixes block your Wave 2/2.5 work — most
  support items above are quick confirmations or small additions.

## Full Backend Priority (re-iterated)

1. **Urgent support:** confirm/fix `field_update` + `status_change`
   (for frontend progress bar and controls)
2. **Finish BLK-039 tests**
3. **Continue Wave 2:** BLK-040, BLK-041, BLK-044
4. **Wave 2.5:** BLK-050, BLK-051
5. **Wave 3:** BLK-042, BLK-049, BLK-047, BLK-015

## Action Required

1. Acknowledge the frontend support needs
2. Verify `field_update` and `status_change` SSE events
3. Confirm `GET /api/v1/runs/{id}` returns correct field/extraction counts
4. If `field_update` or `status_change` is missing, implement immediately
5. Continue Wave 2/2.5 work


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
