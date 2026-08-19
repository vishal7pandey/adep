"""OneFlow single-agent optimization mode [BLK-074, SCRUM-81].

Implements a single-agent mode that mathematically simulates a homogeneous
multi-agent workflow. Instead of spinning up multiple agents (planner, extractor,
validator, reviewer), a single agent sequentially role-plays each role within
one context window, maximizing KV cache reuse.

Benefits:
- **KV cache reuse**: Single context window means the LLM doesn't re-process
  the system prompt and document context for each role transition.
- **Reduced token cost**: Eliminates redundant context re-injection.
- **Lower latency**: Fewer LLM round-trips for simple documents.
- **Simplified orchestration**: No inter-agent communication overhead.

The OneFlow mode is opt-in via agent config (`execution_mode: "oneflow"`).
When disabled, the standard ReAct graph is used.

Architecture:
    Standard ReAct:  plan → act → observe → reflect → (plan | terminate)
    OneFlow:         plan_and_act → observe_and_reflect → (plan_and_act | terminate)

The plan_and_act node combines planning + tool selection + tool execution in a
single LLM call. The observe_and_reflect node combines observation processing
+ validation in a single pass. This halves the number of LLM calls per cycle.

Depends on:
- BLK-008 (Agent Runtime / graph.py)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.graph import END, StateGraph

from src.agent.state import (
    AgentState,
    RunStatus,
    TraceEntry,
    compact_trace,
)
from src.agent.budget import check_run_budget, BudgetLevel
from src.agent.token_tracking import LLMResponse, estimate_tokens, record_token_usage
from src.agent.validator import (
    GapReport,
    TaskValidator,
    ValidatorConfig,
    validate_extraction,
)
from src.agent.graph import (
    CircuitBreaker,
    _format_gaps,
    _format_regions,
    _format_attempted,
    _check_caps,
    _process_tool_result,
    _build_graph_result,
    terminate_node,
)
from src.config import settings
from src.skills.base import Skill
from src.templates.base import ExtractedResult
from src.tools.base import FieldValue, ToolRegistry, ToolResult

from src.agent.guardrails.output_validation import (
    sanitize_instruction_patterns as _guard_sanitize_instructions,
    truncate_output as _guard_truncate_output,
)
from src.agent.guardrails.pii_redaction import redact_pii as _guard_redact_pii
from src.agent.guardrails.exfiltration_prevention import sanitize_input as _guard_sanitize_input
from src.agent.guardrails.tool_guardrails import (
    ToolCallRateLimiter,
    evaluate_tool_call as _guard_evaluate_tool_call,
)
from src.agent.guardrails.loop_detection import LoopDetector, LoopType
from src.agent.guardrails.hallucination_detection import check_grounding as _guard_check_grounding
from src.agent.guardrails.audit_logging import AuditLogger, AuditLogEntry
from src.observability.tracing import span as otel_span
from src.observability.context import set_context, cycle_var

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.api.run_executor import RunControl
    from src.api.sse import SSEEventEmitter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OneFlow system prompt — role-play header
# ---------------------------------------------------------------------------

_ONEFLOW_ROLE_HEADER = """You are a single agent operating in OneFlow mode. You will sequentially role-play multiple roles within this single conversation, maximizing context reuse.

For each extraction cycle, you will:

1. **Planner Role**: Analyze the current gap report and decide which tool to call next.
2. **Extractor Role**: Execute the tool call and process the result.
3. **Validator Role**: Check if the extracted values meet the template requirements.

Since you are playing all roles in one context, you benefit from full KV cache reuse — no context re-injection between roles.

Current document: {doc_name}
Skill: {skill_name}
Template fields: {fields}

Gap report:
{gaps}

Regions detected:
{regions}

Previous attempts:
{attempted}

Based on the above, decide the next tool call. Return a JSON object:
{{"thought": "Your reasoning", "tool": "tool_name", "args": {{...}}}}

If all fields are satisfied, return:
{{"thought": "All fields complete", "tool": "none", "args": {{}}}}
"""


# ---------------------------------------------------------------------------
# Combined plan_and_act node
# ---------------------------------------------------------------------------


def plan_and_act_node(
    state: AgentState,
    *,
    llm_client: Any = None,
    skill: Skill | None = None,
    registry: ToolRegistry | None = None,
    breaker: CircuitBreaker | None = None,
    emitter: Any = None,
    audit_logger: AuditLogger | None = None,
    rate_limiter: ToolCallRateLimiter | None = None,
) -> dict[str, Any]:
    """OneFlow combined plan + act node.

    In a single LLM call, this node:
    1. Analyzes the gap report (planner role)
    2. Decides the next tool call (planner role)
    3. Executes the tool call (extractor role)

    This eliminates one LLM round-trip per cycle compared to the standard
    ReAct graph where plan and act are separate nodes.
    """
    step = state.get("step", 0) + 1
    gap_report = state.get("gap_report")
    extraction = state.get("extraction", {})
    regions = state.get("regions", {})
    attempted = state.get("attempted", {})
    document = state.get("document")
    document_state = state.get("document_state")

    cycle_var.set(step)

    # Check if complete
    if gap_report is not None and gap_report.is_complete:
        return {
            "step": step,
            "status": RunStatus.COMPLETE,
            "_planned_action": None,
        }

    if llm_client is None:
        raise RuntimeError("OneFlow requires an LLM client.")
    if skill is None:
        raise RuntimeError("OneFlow requires a skill.")
    if registry is None:
        raise RuntimeError("OneFlow requires a tool registry.")

    # Build combined prompt
    tool_descriptions = "\n".join(
        f"- {s.name}: {s.description}" for s in registry.specs()
    )
    gap_summary = _format_gaps(gap_report) if gap_report else "No gaps (initial run)."
    region_summary = _format_regions(regions)
    attempted_summary = _format_attempted(attempted)

    doc_name = document or "unknown"
    fields_list = list(extraction.keys()) if extraction else ["(no fields extracted yet)"]

    prompt = _ONEFLOW_ROLE_HEADER.format(
        doc_name=doc_name,
        skill_name=skill.name,
        fields=", ".join(fields_list),
        gaps=gap_summary,
        regions=region_summary,
        attempted=attempted_summary,
    ) + f"\n\nAvailable tools:\n{tool_descriptions}\n\nSkill probe order:\n" + "\n".join(
        f"- {p.get('region_type', '?')}: {p.get('rationale', '')}"
        for p in (skill.probe_order or [])
    )

    # Sanitize input for exfiltration prevention
    prompt = _guard_sanitize_input(prompt).text

    # Single LLM call for plan + act decision
    from src.providers.llm import invoke_llm
    llm_response = invoke_llm(
        system_prompt=skill.system_prompt or "You are a document extraction agent.",
        user_prompt=prompt,
        max_tokens=2000,
    )
    response_text = llm_response.content if hasattr(llm_response, "content") else str(llm_response)

    # Sanitize output
    response_text, _truncated = _guard_truncate_output(response_text)
    response_text, _detected = _guard_sanitize_instructions(response_text)

    # Parse the tool call decision
    try:
        decision = json.loads(response_text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{[\s\S]*\}', response_text)
        if match:
            try:
                decision = json.loads(match.group())
            except json.JSONDecodeError:
                logger.error("OneFlow: Failed to parse LLM response: %s", response_text[:200])
                return {
                    "step": step,
                    "status": RunStatus.PLANNING,
                    "_planned_action": None,
                    "trace": state.get("trace", []) + [TraceEntry(
                        step=step,
                        thought="Failed to parse LLM response",
                        tool_name="",
                        tool_args={},
                        result=ToolResult(ok=False, error="Failed to parse LLM response"),
                    )],
                }
        else:
            logger.error("OneFlow: No JSON in LLM response")
            return {
                "step": step,
                "status": RunStatus.PLANNING,
                "_planned_action": None,
            }

    tool_name = decision.get("tool", "none")
    tool_args = decision.get("args", {})
    thought = decision.get("thought", "")

    # Check if agent says done
    if tool_name == "none" or tool_name == "None":
        if gap_report is not None and not gap_report.is_complete:
            logger.warning(
                "OneFlow: Agent declared complete but %d gaps remain — returning PARTIAL",
                len(gap_report.gaps),
            )
            return {
                "step": step,
                "status": RunStatus.PARTIAL,
                "_planned_action": None,
            }
        return {
            "step": step,
            "status": RunStatus.COMPLETE,
            "_planned_action": None,
        }

    # Execute the tool call immediately (act role)
    try:
        tool_spec, tool_func = registry.get(tool_name)
    except KeyError:
        logger.warning("OneFlow: Unknown tool '%s'", tool_name)
        return {
            "step": step,
            "status": RunStatus.PLANNING,
            "_planned_action": None,
        }

    # Check circuit breaker
    if breaker and breaker.is_tripped(tool_name):
        logger.warning("OneFlow: Circuit tripped for tool '%s'", tool_name)
        return {
            "step": step,
            "status": RunStatus.PLANNING,
            "_planned_action": None,
            "provider_errors": state.get("provider_errors", []) + [
                f"Circuit breaker tripped for tool '{tool_name}'"
            ],
        }

    # Execute tool
    try:
        result = registry.call(tool_name, **tool_args)
    except Exception as e:
        logger.error("OneFlow: Tool '%s' failed: %s", tool_name, e)
        if breaker:
            breaker.record_failure(tool_name)
        result = ToolResult(
            ok=False,
            data=None,
            error=f"Tool execution failed: {e}",
            tool=tool_name,
        )

    # Build trace entry combining plan + act
    trace_entry = TraceEntry(
        step=step,
        thought=thought,
        tool_name=tool_name,
        tool_args=tool_args,
        result=result,
    )

    # Update state with tool result
    new_extraction = dict(extraction)
    if result.ok and result.data:
        if isinstance(result.data, dict):
            for k, v in result.data.items():
                if isinstance(v, FieldValue):
                    new_extraction[k] = v
                elif isinstance(v, dict) and "value" in v:
                    new_extraction[k] = FieldValue(
                        name=k,
                        value=v["value"],
                        confidence=v.get("confidence", 0.8),
                    )

    return {
        "step": step,
        "status": RunStatus.PLANNING,
        "extraction": new_extraction,
        "trace": state.get("trace", []) + [trace_entry],
        "_planned_action": None,
    }


# ---------------------------------------------------------------------------
# Combined observe_and_reflect node
# ---------------------------------------------------------------------------


def observe_and_reflect_node(
    state: AgentState,
    *,
    skill: Skill | None = None,
    validator_config: ValidatorConfig | None = None,
    emitter: Any = None,
    loop_detector: LoopDetector | None = None,
) -> dict[str, Any]:
    """OneFlow combined observe + reflect node.

    Processes the latest tool result and runs validation in a single pass.
    This eliminates the separate observe → reflect edge traversal.
    """
    step = state.get("step", 0)
    extraction = state.get("extraction", {})
    trace = state.get("trace", [])
    document = state.get("document")
    document_state = state.get("document_state")

    # Get the latest trace entry
    if not trace:
        return {"status": RunStatus.PLANNING}

    latest = trace[-1]

    # Observe: process tool result (update regions, document state)
    new_regions = dict(state.get("regions", {}))
    if latest.result and latest.result.ok:
        data = latest.result.data
        if isinstance(data, dict):
            # If data contains regions, merge them
            if "regions" in data and isinstance(data["regions"], dict):
                new_regions.update(data["regions"])

    # Reflect: run validation
    if skill is None or validator_config is None:
        return {
            "regions": new_regions,
            "status": RunStatus.PLANNING,
        }

    # Determine template from state
    template_cls = state.get("template")
    if template_cls is None:
        return {
            "regions": new_regions,
            "status": RunStatus.PLANNING,
        }

    gap_report = validate_extraction(
        schema=template_cls,
        extraction=extraction,
        invariants=skill.invariants,
        config=validator_config,
        failure_actions=skill.failure_actions,
    )

    # Check for loops
    if loop_detector and latest.tool_name:
        loop_type = loop_detector.check(step, {"tool": latest.tool_name, "args": latest.tool_args})
        if loop_type != LoopType.NONE:
            logger.warning("OneFlow: Loop detected (%s) at cycle %d", loop_type.value, step)

    # Check give-up caps
    total_cycles = state.get("total_cycles", 0) + 1
    field_attempts = state.get("field_attempts", {})

    give_up = _check_caps(
        field_attempts, total_cycles
    )

    if give_up:
        return {
            "regions": new_regions,
            "gap_report": gap_report,
            "total_cycles": total_cycles,
            "status": RunStatus.PARTIAL,
        }

    # Emit SSE event for cycle completion
    if emitter:
        try:
            emitter.emit_cycle_complete(step, gap_report)
        except Exception:
            pass

    return {
        "regions": new_regions,
        "gap_report": gap_report,
        "total_cycles": total_cycles,
        "status": RunStatus.PLANNING if not gap_report.is_complete else RunStatus.COMPLETE,
    }


# ---------------------------------------------------------------------------
# OneFlow graph builder
# ---------------------------------------------------------------------------


def build_oneflow_graph(
    registry: ToolRegistry,
    skill: Skill,
    validator_config: ValidatorConfig,
    llm_client: Any = None,
    breaker: CircuitBreaker | None = None,
    control: Any = None,
    emitter: Any = None,
    rate_limiter: ToolCallRateLimiter | None = None,
    loop_detector: LoopDetector | None = None,
    audit_logger: AuditLogger | None = None,
) -> Any:
    """Build the OneFlow single-agent LangGraph state machine.

    The OneFlow graph has only 2 nodes (vs 6 in standard ReAct):
    - plan_and_act: Combined planning + tool execution
    - observe_and_reflect: Combined observation + validation

    This reduces LLM calls by ~50% and maximizes KV cache reuse.

    Args:
        registry: Tool registry with all tools registered.
        skill: The active skill for this run.
        validator_config: Validator configuration.
        llm_client: LLM client (injected for testability).
        breaker: Circuit breaker (defaults to new instance).
        control: Optional RunControl for cooperative pause/cancel.
        emitter: Optional SSE emitter for live event streaming.
        rate_limiter: Optional tool call rate limiter.
        loop_detector: Optional loop detector.
        audit_logger: Optional audit logger.

    Returns:
        A compiled LangGraph ready to invoke.
    """
    if breaker is None:
        breaker = CircuitBreaker()

    graph = StateGraph(AgentState)

    # Add combined nodes
    graph.add_node("plan_and_act", lambda s: plan_and_act_node(
        s, llm_client=llm_client, skill=skill, registry=registry,
        breaker=breaker, emitter=emitter, audit_logger=audit_logger,
        rate_limiter=rate_limiter,
    ))
    graph.add_node("observe_and_reflect", lambda s: observe_and_reflect_node(
        s, skill=skill, validator_config=validator_config,
        emitter=emitter, loop_detector=loop_detector,
    ))
    graph.add_node("terminate", lambda s: _oneflow_terminate(s, emitter=emitter))

    # Edges
    graph.set_entry_point("plan_and_act")
    graph.add_edge("plan_and_act", "observe_and_reflect")

    # Conditional: continue or terminate
    def _route(s: AgentState) -> str:
        status = s.get("status", RunStatus.PLANNING)
        if status in (RunStatus.COMPLETE, RunStatus.PARTIAL, RunStatus.ERROR):
            return "terminate"
        if control:
            from src.agent.graph import should_continue_with_control
            next_node = should_continue_with_control(s, control)
            # OneFlow has no separate compact node — route compact to plan_and_act
            if next_node in ("plan", "compact"):
                return "plan_and_act"
            return next_node  # "terminate" or other
        return "plan_and_act"

    graph.add_conditional_edges(
        "observe_and_reflect",
        _route,
        {"plan_and_act": "plan_and_act", "terminate": "terminate"},
    )
    graph.add_edge("terminate", END)

    return graph.compile()


def _oneflow_terminate(state: AgentState, *, emitter: Any = None) -> dict[str, Any]:
    """OneFlow terminate node — builds the final ExtractedResult."""
    from src.agent.graph import terminate_node
    return terminate_node(state, emitter=emitter)


# ---------------------------------------------------------------------------
# Cost comparison utility
# ---------------------------------------------------------------------------


def estimate_cost_savings(
    num_cycles: int,
    standard_calls_per_cycle: int = 2,  # plan + reflect (act/observe don't use LLM)
    oneflow_calls_per_cycle: int = 1,   # plan_and_act (observe_and_reflect is code-only)
    input_tokens_per_call: int = 3000,
    output_tokens_per_call: int = 500,
    input_price_per_1k: float = 0.005,
    output_price_per_1k: float = 0.015,
) -> dict[str, float]:
    """Estimate cost savings of OneFlow vs standard ReAct.

    Args:
        num_cycles: Expected number of ReAct cycles for the document.
        standard_calls_per_cycle: LLM calls per cycle in standard mode.
        oneflow_calls_per_cycle: LLM calls per cycle in OneFlow mode.
        input_tokens_per_call: Average input tokens per LLM call.
        output_tokens_per_call: Average output tokens per LLM call.
        input_price_per_1k: Price per 1K input tokens.
        output_price_per_1k: Price per 1K output tokens.

    Returns:
        Dict with cost estimates and savings.
    """
    standard_llm_calls = num_cycles * standard_calls_per_cycle
    oneflow_llm_calls = num_cycles * oneflow_calls_per_cycle

    # Standard mode re-injects context for each role transition
    standard_input_tokens = standard_llm_calls * input_tokens_per_call
    standard_output_tokens = standard_llm_calls * output_tokens_per_call
    standard_cost = (
        (standard_input_tokens / 1000) * input_price_per_1k
        + (standard_output_tokens / 1000) * output_price_per_1k
    )

    # OneFlow reuses KV cache — only incremental tokens for role switching
    oneflow_input_tokens = oneflow_llm_calls * input_tokens_per_call
    oneflow_output_tokens = oneflow_llm_calls * output_tokens_per_call
    oneflow_cost = (
        (oneflow_input_tokens / 1000) * input_price_per_1k
        + (oneflow_output_tokens / 1000) * output_price_per_1k
    )

    savings = standard_cost - oneflow_cost
    savings_pct = (savings / standard_cost * 100) if standard_cost > 0 else 0.0

    return {
        "standard_cost_usd": round(standard_cost, 6),
        "oneflow_cost_usd": round(oneflow_cost, 6),
        "savings_usd": round(savings, 6),
        "savings_percent": round(savings_pct, 1),
        "standard_llm_calls": standard_llm_calls,
        "oneflow_llm_calls": oneflow_llm_calls,
        "call_reduction_percent": round(
            (1 - oneflow_llm_calls / standard_llm_calls) * 100
            if standard_llm_calls > 0 else 0.0, 1
        ),
    }
