"""SSE event emitter — streams run progress to frontend [BLK-023, BLK-024].

Produces Server-Sent Events matching the frontend's ``lib/sse.ts`` types.
Events: thought, tool_call, tool_result, progress, field_update, complete.

The emitter wraps a queue that the SSE endpoint consumes. The ReAct graph
nodes push events into the queue as they execute.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any

from src.agent.state import TraceEntry
from src.tools.base import ToolResult

logger = logging.getLogger(__name__)


class SSEEventEmitter:
    """Queue-based event emitter for SSE streaming.

    The graph nodes call ``emit_*`` methods to push events. The SSE
    endpoint consumes them via ``async_iter()``.

    Supports multiple concurrent subscribers via a fanout list — each
    subscriber gets its own queue so events are not stolen by one
    consumer [SCRUM-484].

    Attributes:
        _subscribers: List of per-subscriber async queues.
        _closed: Whether the emitter is closed (complete event sent).
    """

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[dict[str, Any] | None]] = []
        self._closed = False
        self._event_buffer: list[dict[str, Any]] = []

    def subscribe(self) -> asyncio.Queue[dict[str, Any] | None]:
        """Create a new subscriber queue for fanout support [SCRUM-484].

        Replays all buffered events to the new subscriber so late
        subscribers don't miss earlier events.

        Returns:
            A queue that will receive all future events.
        """
        q: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        # Replay buffered events to this new subscriber
        for event in self._event_buffer:
            q.put_nowait(event)
        # If emitter is already closed, signal end of stream
        if self._closed:
            q.put_nowait(None)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any] | None]) -> None:
        """Remove a subscriber queue [SCRUM-484]."""
        if q in self._subscribers:
            self._subscribers.remove(q)

    def _timestamp(self) -> str:
        """ISO 8601 UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def emit_thought(self, cycle: int, text: str) -> None:
        """Emit a thought event (agent reasoning)."""
        self._emit({
            "type": "thought",
            "cycle": cycle,
            "text": text,
            "timestamp": self._timestamp(),
        })

    def emit_tool_call(self, cycle: int, tool: str, args: dict[str, Any]) -> None:
        """Emit a tool_call event."""
        self._emit({
            "type": "tool_call",
            "cycle": cycle,
            "tool": tool,
            "args": args,
            "timestamp": self._timestamp(),
        })

    def emit_tool_result(
        self,
        cycle: int,
        tool: str,
        result: ToolResult,
        crop_thumbnail: str | None = None,
    ) -> None:
        """Emit a tool_result event."""
        result_data: dict[str, Any] = {"ok": result.ok}
        if result.error:
            result_data["error"] = result.error
        if result.data is not None:
            # Truncate large data for streaming
            data_str = str(result.data)
            if len(data_str) > 500:
                result_data["data"] = data_str[:500] + "..."
            else:
                result_data["data"] = result.data
        if result.grounding:
            result_data["bbox"] = {
                "x": result.grounding.bbox[0],
                "y": result.grounding.bbox[1],
                "width": result.grounding.bbox[2] - result.grounding.bbox[0],
                "height": result.grounding.bbox[3] - result.grounding.bbox[1],
            }
            result_data["confidence"] = result.grounding.confidence

        self._emit({
            "type": "tool_result",
            "cycle": cycle,
            "tool": tool,
            "result": result_data,
            "crop_thumbnail": crop_thumbnail,
            "timestamp": self._timestamp(),
        })

    def emit_progress(
        self,
        completed_fields: int,
        total_fields: int,
        failing_fields: int,
    ) -> None:
        """Emit a progress event."""
        self._emit({
            "type": "progress",
            "completed_fields": completed_fields,
            "total_fields": total_fields,
            "failing_fields": failing_fields,
        })

    def emit_field_update(
        self,
        field_id: str,
        name: str,
        value: Any,
        confidence: float,
        bbox: dict[str, int] | None = None,
        page: int = 0,
        status: str = "extracted",
        extracted_fields_count: int = 0,
        total_fields: int = 0,
        risk_tier: str = "low",
    ) -> None:
        """Emit a field_update event [Wave 4/5].

        The frontend expects ``{ type: 'field_update', field: ExtractedField }``
        where ``field`` is a nested object [SCRUM-484].
        """
        self._emit({
            "type": "field_update",
            "field": {
                "id": field_id,
                "name": name,
                "value": value,
                "confidence": confidence,
                "bbox": bbox,
                "page": page,
                "status": status,
            },
            "extracted_fields_count": extracted_fields_count,
            "total_fields": total_fields,
            "risk_tier": risk_tier,
        })

    def emit_status_change(
        self,
        status: str,
        cycle: int = 0,
        previous_status: str | None = None,
    ) -> None:
        """Emit a status_change event [Wave 4/5].

        Fired on every run status transition (idle → running → paused → etc).
        """
        self._emit({
            "type": "status_change",
            "status": status,
            "cycle": cycle,
            "previous_status": previous_status,
        })

    def emit_compaction(self, entries_compacted: int, summary_length: int) -> None:
        """Emit a compaction event — trace was summarized [§12.4, BLK-039].

        Args:
            entries_compacted: Number of trace entries that were compacted.
            summary_length: Character length of the resulting compaction_summary.
        """
        self._emit({
            "type": "compaction",
            "entries_compacted": entries_compacted,
            "summary_length": summary_length,
        })

    def emit_paused(self, cycle: int) -> None:
        """Emit a paused event — agent halted after current cycle [BLK-046]."""
        self._emit({"type": "paused", "cycle": cycle})

    def emit_resumed(self, cycle: int) -> None:
        """Emit a resumed event — agent continuing from paused state [BLK-046]."""
        self._emit({"type": "resumed", "cycle": cycle})

    def emit_stopped(self, cycle: int, partial_result: dict[str, Any] | None = None) -> None:
        """Emit a stopped event — emergency halt with partial results [BLK-046]."""
        self._emit({
            "type": "stopped",
            "cycle": cycle,
            "partial_result": partial_result,
        })

    def emit_rolled_back(self, from_cycle: int, to_cycle: int) -> None:
        """Emit a rolled_back event — state restored to earlier cycle [BLK-046]."""
        self._emit({
            "type": "rolled_back",
            "from_cycle": from_cycle,
            "to_cycle": to_cycle,
        })

    def emit_trajectory_warning(self, cycle: int, consecutive_non_improving: int) -> None:
        """Emit a trajectory_warning event — agent may be stuck [BLK-049].

        Fired after 3 consecutive non-improving cycles.
        """
        self._emit({
            "type": "trajectory_warning",
            "cycle": cycle,
            "consecutive_non_improving": consecutive_non_improving,
        })

    def emit_trajectory_critical(self, cycle: int, consecutive_non_improving: int) -> None:
        """Emit a trajectory_critical event — agent likely in a loop [BLK-049].

        Fired after 5 consecutive non-improving cycles. Agent auto-pauses.
        """
        self._emit({
            "type": "trajectory_critical",
            "cycle": cycle,
            "consecutive_non_improving": consecutive_non_improving,
        })

    def emit_gate_triggered(
        self,
        field: str,
        risk_tier: str,
        confidence: float,
        reason: str,
        cycle: int = 0,
        required_action: str = "approve or reject this field",
    ) -> None:
        """Emit a gate_triggered event — HITL gate requires user action [BLK-047].

        Fired when a high-risk or critical action needs user approval.
        """
        self._emit({
            "type": "gate_triggered",
            "field": field,
            "risk_tier": risk_tier,
            "confidence": confidence,
            "reason": reason,
            "cycle": cycle,
            "required_action": required_action,
        })

    def emit_token_usage(
        self,
        node: str,
        cycle: int,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cost_usd: float,
        running_total_tokens: int,
        running_total_cost: float,
    ) -> None:
        """Emit a token_usage event after each LLM call [BLK-050, §15].

        Args:
            node: Which graph node made the call ("plan", "compact", etc.).
            cycle: ReAct cycle number.
            input_tokens: Input token count for this call.
            output_tokens: Output token count for this call.
            total_tokens: Total tokens for this call.
            cost_usd: Cost for this call in USD.
            running_total_tokens: Cumulative tokens across the run.
            running_total_cost: Cumulative cost across the run.
        """
        self._emit({
            "type": "token_usage",
            "node": node,
            "cycle": cycle,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(cost_usd, 6),
            "running_total_tokens": running_total_tokens,
            "running_total_cost": round(running_total_cost, 6),
        })

    def emit_budget_warning(
        self,
        level: str,
        consumed_tokens: int,
        budget_tokens: int,
        consumed_cost_usd: float,
        budget_cost_usd: float,
    ) -> None:
        """Emit a budget_warning event at 80% threshold [BLK-051, §15].

        Args:
            level: Budget level ("run", "definition_daily", "global_daily").
            consumed_tokens: Tokens consumed so far.
            budget_tokens: Token limit for this level.
            consumed_cost_usd: Cost consumed so far.
            budget_cost_usd: Cost limit for this level.
        """
        percentage = int((consumed_tokens / budget_tokens * 100)) if budget_tokens > 0 else 0
        self._emit({
            "type": "budget_warning",
            "level": level,
            "consumed_tokens": consumed_tokens,
            "budget_tokens": budget_tokens,
            "consumed_cost_usd": round(consumed_cost_usd, 6),
            "budget_cost_usd": budget_cost_usd,
            "percentage": percentage,
            "message": f"Approaching {level} budget limit — {percentage}% consumed",
        })

    def emit_budget_exceeded(
        self,
        level: str,
        consumed_tokens: int,
        budget_tokens: int,
        consumed_cost_usd: float,
        budget_cost_usd: float,
    ) -> None:
        """Emit a budget_exceeded event at 100% threshold [BLK-051, §15].

        Args:
            level: Budget level ("run", "definition_daily", "global_daily").
            consumed_tokens: Tokens consumed so far.
            budget_tokens: Token limit for this level.
            consumed_cost_usd: Cost consumed so far.
            budget_cost_usd: Cost limit for this level.
        """
        self._emit({
            "type": "budget_exceeded",
            "level": level,
            "consumed_tokens": consumed_tokens,
            "budget_tokens": budget_tokens,
            "consumed_cost_usd": round(consumed_cost_usd, 6),
            "budget_cost_usd": budget_cost_usd,
            "message": f"{level} budget exceeded — terminating with partial results",
        })

    def emit_complete(self, status: str, summary: str | None = None,
                      run_id: str | None = None,
                      execution_mode: str | None = None) -> None:
        """Emit the complete event and close the stream [BLK-129].

        Includes run_id for multi-tab client disambiguation (frontend addition).
        Includes execution_mode when the run did not use the ReAct agent
        (e.g. "fallback") so the frontend can surface this to the user [BLK-287].
        """
        payload: dict[str, Any] = {
            "type": "complete",
            "status": status,
            "summary": summary,
        }
        if run_id:
            payload["run_id"] = run_id
        if execution_mode:
            payload["execution_mode"] = execution_mode
        self._emit(payload)
        self.close()

    def close(self) -> None:
        """Close the emitter — sends None to all subscribers to signal end of stream."""
        self._closed = True
        for q in self._subscribers:
            q.put_nowait(None)
        self._subscribers.clear()

    def _emit(self, event: dict[str, Any]) -> None:
        """Push an event to all subscriber queues and buffer it [SCRUM-484]."""
        if not self._closed:
            self._event_buffer.append(event)
            for q in self._subscribers:
                q.put_nowait(event)

    async def async_iter(self):
        """Async generator yielding SSE-formatted strings.

        Subscribes to the emitter's fanout list so multiple consumers
        can each receive all events [SCRUM-484].

        Yields:
            ``data: {json}\n\n`` strings for each event.
        """
        q = self.subscribe()
        try:
            while True:
                event = await q.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            self.unsubscribe(q)

    @staticmethod
    def encode_crop_thumbnail(image_path: str) -> str | None:
        """Encode a cropped image as a base64 data URL for SSE streaming."""
        try:
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
        except Exception:
            return None
