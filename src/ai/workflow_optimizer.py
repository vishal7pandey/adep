"""MCTS Workflow Optimizer — AFlow-style graph topology search [BLK-072, SCRUM-79].

Uses Monte Carlo Tree Search (MCTS) to search the space of possible agent
workflow topologies. Inspired by AFlow (ICLR 2025), each tree node represents
a complete workflow definition, and the LLM acts as the expansion operator.

The search space includes:
- Node additions/removals (review, revise, ensemble, pre_validate)
- Edge rewiring (reflect → review → plan, plan → ensemble → observe)
- Parameter tuning (compaction window, max cycles, confidence thresholds)
- Operator insertions (review before terminate, revise after reflect)

Algorithm:
1. Selection — traverse the tree using UCB1 until reaching an expandable node
2. Expansion — LLM proposes a modified workflow (add/remove/modify nodes/edges)
3. Evaluation — execute the workflow on sample tasks, measure performance
4. Backpropagation — update visit counts and average scores up the tree

Depends on:
- BLK-008 (Agent Runtime / graph.py)
- BLK-071 (GEPA / prompt_evolver.py) for skill optimization integration

Uses Azure OpenAI (GPT-5.4) for workflow expansion.
"""

from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from src.providers.llm import invoke_llm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Workflow topology definition
# ---------------------------------------------------------------------------

@dataclass
class WorkflowNode:
    """A node in the agent workflow graph.

    Attributes:
        name: Node identifier (plan, act, observe, reflect, compact, terminate, review, revise, ensemble, pre_validate).
        node_type: Category — core, optional, custom.
        enabled: Whether the node is active in the workflow.
        params: Node-specific parameters (e.g., compaction_window for compact, threshold for review).
    """
    name: str
    node_type: str = "core"
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowEdge:
    """A directed edge in the workflow graph.

    Attributes:
        source: Source node name.
        target: Target node name.
        condition: Optional condition description (for conditional edges).
    """
    source: str
    target: str
    condition: str = ""


@dataclass
class WorkflowTopology:
    """A complete agent workflow topology.

    Attributes:
        nodes: Dict of node name → WorkflowNode.
        edges: List of WorkflowEdge.
        entry_point: Name of the entry node.
        parameters: Global workflow parameters (max_cycles, compaction_window, confidence_threshold).
        description: Human-readable description of the workflow.
    """
    nodes: dict[str, WorkflowNode] = field(default_factory=dict)
    edges: list[WorkflowEdge] = field(default_factory=list)
    entry_point: str = "plan"
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {
                name: {"node_type": n.node_type, "enabled": n.enabled, "params": n.params}
                for name, n in self.nodes.items()
            },
            "edges": [{"source": e.source, "target": e.target, "condition": e.condition} for e in self.edges],
            "entry_point": self.entry_point,
            "parameters": self.parameters,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkflowTopology:
        nodes = {}
        for name, nd in d.get("nodes", {}).items():
            nodes[name] = WorkflowNode(
                name=name,
                node_type=nd.get("node_type", "core"),
                enabled=nd.get("enabled", True),
                params=nd.get("params", {}),
            )
        edges = [
            WorkflowEdge(source=e["source"], target=e["target"], condition=e.get("condition", ""))
            for e in d.get("edges", [])
        ]
        return cls(
            nodes=nodes,
            edges=edges,
            entry_point=d.get("entry_point", "plan"),
            parameters=d.get("parameters", {}),
            description=d.get("description", ""),
        )

    @classmethod
    def default_react(cls) -> WorkflowTopology:
        """The default ReAct topology: plan → act → observe → reflect → (plan | compact | terminate)."""
        core_nodes = ["plan", "act", "observe", "reflect", "compact", "terminate"]
        nodes = {n: WorkflowNode(name=n, node_type="core") for n in core_nodes}
        edges = [
            WorkflowEdge("plan", "act", "not_complete"),
            WorkflowEdge("plan", "terminate", "complete"),
            WorkflowEdge("act", "observe"),
            WorkflowEdge("observe", "reflect"),
            WorkflowEdge("reflect", "plan", "gaps_remain"),
            WorkflowEdge("reflect", "compact", "compact_requested"),
            WorkflowEdge("reflect", "terminate", "caps_exhausted"),
            WorkflowEdge("compact", "plan"),
            WorkflowEdge("terminate", "END"),
        ]
        return cls(
            nodes=nodes,
            edges=edges,
            entry_point="plan",
            parameters={
                "max_cycles_per_field": 5,
                "max_cycles_per_document": 20,
                "compaction_window": 10,
                "confidence_threshold": 0.85,
            },
            description="Default ReAct: plan → act → observe → reflect → (plan | compact | terminate)",
        )


# ---------------------------------------------------------------------------
# Available operators for expansion
# ---------------------------------------------------------------------------

OPERATORS: dict[str, dict[str, Any]] = {
    "review": {
        "description": "Pre-terminate quality review — checks extraction completeness before terminating",
        "node_type": "optional",
        "default_params": {"threshold": 0.85, "check_grounding": True},
    },
    "revise": {
        "description": "Re-extract low-confidence fields — re-probes fields below threshold after reflect",
        "node_type": "optional",
        "default_params": {"max_revisions": 2, "confidence_cutoff": 0.7},
    },
    "ensemble": {
        "description": "Multi-tool ensemble — calls multiple tools and votes on the best result",
        "node_type": "optional",
        "default_params": {"tools": ["ocr", "vlm"], "voting": "majority"},
    },
    "pre_validate": {
        "description": "Pre-validation step — checks invariants before reflect, short-circuits on failure",
        "node_type": "optional",
        "default_params": {"strict": False},
    },
    "rerank": {
        "description": "Re-rank regions — re-sorts regions by expected information value after each cycle",
        "node_type": "optional",
        "default_params": {"strategy": "gap_aware"},
    },
}


# ---------------------------------------------------------------------------
# MCTS tree node
# ---------------------------------------------------------------------------

@dataclass
class MCTSNode:
    """A node in the MCTS search tree.

    Each node represents a complete workflow topology. The tree structure
    allows backpropagation of evaluation results.

    Attributes:
        workflow: The workflow topology at this node.
        parent: Parent MCTSNode (None for root).
        children: List of child MCTSNodes.
        visits: Number of times this node has been visited.
        total_score: Cumulative score from all evaluations.
        expanded: Whether this node has been expanded.
        expansion_action: Description of the action that created this node from its parent.
    """
    workflow: WorkflowTopology
    parent: MCTSNode | None = None
    children: list[MCTSNode] = field(default_factory=list)
    visits: int = 0
    total_score: float = 0.0
    expanded: bool = False
    expansion_action: str = ""

    @property
    def avg_score(self) -> float:
        return self.total_score / max(self.visits, 1)

    @property
    def ucb1(self) -> float:
        """UCB1 value for selection: avg_score + C * sqrt(ln(parent_visits) / visits)."""
        if self.visits == 0:
            return float("inf")
        parent_visits = self.parent.visits if self.parent else self.visits
        exploration = math.sqrt(math.log(max(parent_visits, 1)) / self.visits)
        return self.avg_score + 1.41 * exploration


# ---------------------------------------------------------------------------
# MCTS result
# ---------------------------------------------------------------------------

@dataclass
class MCTSResult:
    """Result of the MCTS workflow optimization.

    Attributes:
        best_workflow: The best workflow topology found.
        best_score: Score of the best workflow.
        tree_size: Total number of nodes in the search tree.
        iterations: Number of MCTS iterations completed.
        history: Per-iteration snapshots.
        token_usage: Total token usage across all LLM calls.
        convergence_reason: Why the search terminated.
    """
    best_workflow: WorkflowTopology | None = None
    best_score: float = 0.0
    tree_size: int = 0
    iterations: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    token_usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
    convergence_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "best_workflow": self.best_workflow.to_dict() if self.best_workflow else None,
            "best_score": self.best_score,
            "tree_size": self.tree_size,
            "iterations": self.iterations,
            "history": self.history,
            "token_usage": self.token_usage,
            "convergence_reason": self.convergence_reason,
        }


# ---------------------------------------------------------------------------
# Selection — UCB1 traversal
# ---------------------------------------------------------------------------

def _select(root: MCTSNode) -> MCTSNode:
    """Traverse the tree from root to a selectable node using UCB1.

    If a node has unexpanded children potential, return it for expansion.
    Otherwise, descend to the child with the highest UCB1 value.
    """
    node = root
    while node.children:
        if not node.expanded:
            return node
        node = max(node.children, key=lambda c: c.ucb1)
    return node


# ---------------------------------------------------------------------------
# Expansion — LLM proposes a modified workflow
# ---------------------------------------------------------------------------

_EXPANSION_PROMPT = """You are an expert agent workflow optimizer for a document extraction platform.

You will receive:
1. The current workflow topology (nodes, edges, parameters)
2. Available operators that can be added
3. Performance feedback from the last evaluation
4. Accumulated experience from previous iterations

Your task: Propose ONE targeted modification to improve the workflow. Choose from:
- **Add a node**: Insert an operator (review, revise, ensemble, pre_validate, rerank) into the workflow
- **Remove a node**: Disable an optional node that isn't helping
- **Rewire an edge**: Change the routing between nodes
- **Tune a parameter**: Adjust max_cycles, compaction_window, confidence_threshold, etc.
- **Modify node params**: Change operator-specific parameters

Rules:
- Make ONLY ONE change per expansion
- Keep the topology valid (entry_point must reach terminate, no orphan nodes)
- Explain your reasoning

Return JSON:
{
  "action": "add_node|remove_node|rewire_edge|tune_parameter|modify_node_params",
  "description": "Human-readable description of the change",
  "details": {
    "node_name": "...",
    "edge_source": "...",
    "edge_target": "...",
    "edge_condition": "...",
    "parameter_name": "...",
    "parameter_value": ...,
    "node_params": {...}
  },
  "rationale": "Why this change should improve performance"
}

Return ONLY the JSON."""

_AVAILABLE_OPERATORS_PROMPT = """Available operators:
- review: Pre-terminate quality review (threshold, check_grounding)
- revise: Re-extract low-confidence fields (max_revisions, confidence_cutoff)
- ensemble: Multi-tool ensemble with voting (tools, voting_strategy)
- pre_validate: Pre-validation step checking invariants (strict)
- rerank: Re-rank regions by expected value (strategy)"""


def _expand(
    node: MCTSNode,
    feedback: str,
    accumulated_experience: str,
) -> tuple[MCTSNode, dict[str, int]]:
    """Expand a tree node by generating a child workflow via LLM [BLK-072].

    Returns:
        Tuple of (new_child_node, token_usage).
    """
    workflow_json = json.dumps(node.workflow.to_dict(), indent=2)

    user_prompt = (
        f"## Current Workflow\n{workflow_json}\n\n"
        f"{_AVAILABLE_OPERATORS_PROMPT}\n\n"
        f"## Performance Feedback\n{feedback}\n\n"
        f"## Accumulated Experience\n{accumulated_experience or 'None'}\n\n"
        f"Propose ONE modification to improve this workflow."
    )

    response = invoke_llm(_EXPANSION_PROMPT, user_prompt, max_tokens=2000)

    token_usage = {
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "total_tokens": response.total_tokens,
    }

    if not response.content:
        # No LLM — heuristic expansion (add review node if not present)
        new_workflow = _heuristic_expand(node.workflow)
        child = MCTSNode(
            workflow=new_workflow,
            parent=node,
            expansion_action="heuristic: add review node",
        )
        node.children.append(child)
        node.expanded = True
        return child, token_usage

    content = response.content.strip()
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found")
        action = json.loads(content[start:end])
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Expansion LLM returned invalid JSON: %s — using heuristic", e)
        new_workflow = _heuristic_expand(node.workflow)
        child = MCTSNode(
            workflow=new_workflow,
            parent=node,
            expansion_action="heuristic: add review node (LLM fallback)",
        )
        node.children.append(child)
        node.expanded = True
        return child, token_usage

    # Apply the proposed action to the workflow
    new_workflow = _apply_action(node.workflow, action)
    child = MCTSNode(
        workflow=new_workflow,
        parent=node,
        expansion_action=action.get("description", "unknown"),
    )
    node.children.append(child)
    node.expanded = True

    return child, token_usage


def _heuristic_expand(workflow: WorkflowTopology) -> WorkflowTopology:
    """Heuristic expansion when LLM is unavailable — adds a review node if not present."""
    new_wf = WorkflowTopology(
        nodes=dict(workflow.nodes),
        edges=list(workflow.edges),
        entry_point=workflow.entry_point,
        parameters=dict(workflow.parameters),
        description=workflow.description,
    )

    if "review" not in new_wf.nodes:
        new_wf.nodes["review"] = WorkflowNode(
            name="review",
            node_type="optional",
            params={"threshold": 0.85, "check_grounding": True},
        )
        # Insert review before terminate: reflect → review → (plan | terminate)
        new_wf.edges = [
            e for e in new_wf.edges if not (e.source == "reflect" and e.target == "terminate")
        ]
        new_wf.edges.append(WorkflowEdge("reflect", "review", "pre_terminate_check"))
        new_wf.edges.append(WorkflowEdge("review", "plan", "quality_below_threshold"))
        new_wf.edges.append(WorkflowEdge("review", "terminate", "quality_ok"))
        new_wf.description = workflow.description + " + review node (heuristic)"

    return new_wf


def _apply_action(workflow: WorkflowTopology, action: dict[str, Any]) -> WorkflowTopology:
    """Apply a proposed action to a workflow topology, returning a new topology."""
    new_wf = WorkflowTopology(
        nodes={name: WorkflowNode(name=n.name, node_type=n.node_type, enabled=n.enabled, params=dict(n.params))
               for name, n in workflow.nodes.items()},
        edges=[WorkflowEdge(e.source, e.target, e.condition) for e in workflow.edges],
        entry_point=workflow.entry_point,
        parameters=dict(workflow.parameters),
        description=workflow.description,
    )

    action_type = action.get("action", "")
    details = action.get("details", {})
    desc = action.get("description", "")

    if action_type == "add_node":
        node_name = details.get("node_name", "review")
        if node_name not in new_wf.nodes and node_name in OPERATORS:
            op = OPERATORS[node_name]
            new_wf.nodes[node_name] = WorkflowNode(
                name=node_name,
                node_type=op["node_type"],
                params=op["default_params"].copy(),
            )
            # Insert after reflect, before terminate
            new_wf.edges = [e for e in new_wf.edges if not (e.source == "reflect" and e.target == "terminate")]
            new_wf.edges.append(WorkflowEdge("reflect", node_name, "pre_terminate_check"))
            new_wf.edges.append(WorkflowEdge(node_name, "plan", "needs_revision"))
            new_wf.edges.append(WorkflowEdge(node_name, "terminate", "quality_ok"))

    elif action_type == "remove_node":
        node_name = details.get("node_name", "")
        if node_name in new_wf.nodes and new_wf.nodes[node_name].node_type != "core":
            del new_wf.nodes[node_name]
            new_wf.edges = [e for e in new_wf.edges if e.source != node_name and e.target != node_name]
            # Re-connect: if reflect lost its terminate edge, add it back
            has_terminate = any(e.target == "terminate" for e in new_wf.edges if e.source == "reflect")
            if not has_terminate:
                new_wf.edges.append(WorkflowEdge("reflect", "terminate", "caps_exhausted"))

    elif action_type == "rewire_edge":
        source = details.get("edge_source", "")
        target = details.get("edge_target", "")
        condition = details.get("edge_condition", "")
        if source in new_wf.nodes and target in new_wf.nodes:
            new_wf.edges.append(WorkflowEdge(source, target, condition))

    elif action_type == "tune_parameter":
        param_name = details.get("parameter_name", "")
        param_value = details.get("parameter_value")
        if param_name and param_value is not None:
            new_wf.parameters[param_name] = param_value

    elif action_type == "modify_node_params":
        node_name = details.get("node_name", "")
        node_params = details.get("node_params", {})
        if node_name in new_wf.nodes:
            new_wf.nodes[node_name].params.update(node_params)

    new_wf.description = workflow.description + f" | {desc}" if desc else workflow.description
    return new_wf


# ---------------------------------------------------------------------------
# Evaluation — score a workflow on sample data
# ---------------------------------------------------------------------------

def _evaluate_workflow(
    workflow: WorkflowTopology,
    evaluate_fn: Callable[[WorkflowTopology], dict[str, float]],
) -> tuple[float, str]:
    """Evaluate a workflow topology using the provided evaluation function.

    Args:
        workflow: The workflow to evaluate.
        evaluate_fn: A callable that takes a WorkflowTopology and returns a dict of scores.

    Returns:
        Tuple of (aggregate_score, feedback_string).
    """
    scores = evaluate_fn(workflow)

    # Aggregate score (weighted sum)
    coverage = scores.get("field_coverage", 0.0)
    confidence = scores.get("avg_confidence", 0.0)
    efficiency = scores.get("token_efficiency", 0.0)
    gap_severity = scores.get("gap_severity", 0.0)
    speed = scores.get("speed_score", 0.0)

    aggregate = coverage * 0.35 + confidence * 0.25 + efficiency * 0.15 + speed * 0.15 - gap_severity * 0.1

    feedback_parts = [
        f"Field coverage: {coverage:.1%}",
        f"Average confidence: {confidence:.3f}",
        f"Token efficiency: {efficiency:.6f}",
        f"Gap severity: {gap_severity:.3f}",
        f"Speed score: {speed:.3f}",
        f"Aggregate: {aggregate:.4f}",
    ]

    # Add topology info
    enabled_nodes = [n for n, wfn in workflow.nodes.items() if wfn.enabled]
    feedback_parts.append(f"Enabled nodes: {', '.join(enabled_nodes)}")
    feedback_parts.append(f"Parameters: {json.dumps(workflow.parameters)}")

    return aggregate, "\n".join(feedback_parts)


# ---------------------------------------------------------------------------
# Backpropagation
# ---------------------------------------------------------------------------

def _backpropagate(node: MCTSNode, score: float) -> None:
    """Backpropagate the evaluation score up the tree."""
    while node is not None:
        node.visits += 1
        node.total_score += score
        node = node.parent


# ---------------------------------------------------------------------------
# Accumulated experience
# ---------------------------------------------------------------------------

def _accumulate_experience(node: MCTSNode) -> str:
    """Collect experience from the path from root to this node."""
    experiences: list[str] = []
    current = node
    while current is not None and current.parent is not None:
        if current.expansion_action:
            avg = current.avg_score if current.visits > 0 else 0.0
            experiences.append(f"- {current.expansion_action} (avg_score={avg:.4f}, visits={current.visits})")
        current = current.parent
    return "\n".join(reversed(experiences)) if experiences else "No prior experience."


# ---------------------------------------------------------------------------
# Main MCTS optimization loop
# ---------------------------------------------------------------------------

def optimize_workflow(
    seed_workflow: WorkflowTopology | None = None,
    evaluate_fn: Callable[[WorkflowTopology], dict[str, float]] | None = None,
    *,
    max_iterations: int = 20,
    convergence_threshold: float = 0.005,
    rng_seed: int | None = None,
) -> MCTSResult:
    """Run the MCTS workflow optimization loop [BLK-072].

    Args:
        seed_workflow: The initial workflow topology to optimize. Defaults to the standard ReAct topology.
        evaluate_fn: A callable that takes a WorkflowTopology and returns a dict of scores
                     (field_coverage, avg_confidence, token_efficiency, gap_severity, speed_score).
                     If None, a default heuristic evaluator is used.
        max_iterations: Maximum number of MCTS iterations.
        convergence_threshold: If best score improvement is below this for 3 consecutive iterations, stop.
        rng_seed: Optional random seed for reproducibility.

    Returns:
        MCTSResult with the best workflow found, tree statistics, and history.
    """
    rng = random.Random(rng_seed)
    result = MCTSResult()

    if seed_workflow is None:
        seed_workflow = WorkflowTopology.default_react()

    if evaluate_fn is None:
        evaluate_fn = _default_evaluator

    # Initialize root
    root = MCTSNode(workflow=seed_workflow)

    # Evaluate root
    root_score, root_feedback = _evaluate_workflow(seed_workflow, evaluate_fn)
    _backpropagate(root, root_score)

    result.history.append({
        "iteration": 0,
        "event": "seed_evaluated",
        "score": root_score,
        "feedback": root_feedback,
    })

    best_score = root_score
    best_workflow = seed_workflow
    best_score_history: list[float] = [root_score]

    for iteration in range(1, max_iterations + 1):
        logger.info("MCTS iteration %d/%d — tree_size=%d", iteration, max_iterations, _count_nodes(root))

        # Step 1: Selection
        selected = _select(root)

        # Step 2: Expansion
        experience = _accumulate_experience(selected)
        last_feedback = result.history[-1].get("feedback", "No prior feedback.")

        child, tu = _expand(selected, last_feedback, experience)
        result.token_usage["input_tokens"] += tu.get("input_tokens", 0)
        result.token_usage["output_tokens"] += tu.get("output_tokens", 0)
        result.token_usage["total_tokens"] += tu.get("total_tokens", 0)

        # Step 3: Evaluation
        child_score, child_feedback = _evaluate_workflow(child.workflow, evaluate_fn)

        # Step 4: Backpropagation
        _backpropagate(child, child_score)

        # Track best
        if child_score > best_score:
            best_score = child_score
            best_workflow = child.workflow
            logger.info("MCTS: New best score=%.4f (action: %s)", best_score, child.expansion_action)

        best_score_history.append(best_score)

        result.history.append({
            "iteration": iteration,
            "event": "expanded",
            "action": child.expansion_action,
            "score": child_score,
            "best_score": best_score,
            "feedback": child_feedback,
            "tree_size": _count_nodes(root),
        })

        # Step 5: Convergence check
        if len(best_score_history) >= 4:
            recent = best_score_history[-3:]
            if max(recent) - min(recent) < convergence_threshold:
                result.convergence_reason = f"Converged at iteration {iteration} (score plateau)"
                result.iterations = iteration
                break
    else:
        result.convergence_reason = f"Reached max iterations ({max_iterations})"
        result.iterations = max_iterations

    # Finalize
    result.best_workflow = best_workflow
    result.best_score = best_score
    result.tree_size = _count_nodes(root)

    return result


# ---------------------------------------------------------------------------
# Default heuristic evaluator (for testing / no-execution mode)
# ---------------------------------------------------------------------------

def _default_evaluator(workflow: WorkflowTopology) -> dict[str, float]:
    """Default heuristic evaluator that scores topologies based on structural properties.

    This is a proxy for actual execution. In production, replace with a real
    evaluation function that executes the workflow on sample documents.
    """
    base_coverage = 0.75
    base_confidence = 0.82
    base_efficiency = 0.001
    base_gap_severity = 0.15
    base_speed = 0.70

    # Bonus for optional nodes
    optional_bonuses = {
        "review": {"coverage": 0.05, "confidence": 0.03, "gap_severity": -0.03},
        "revise": {"coverage": 0.08, "confidence": 0.05, "gap_severity": -0.05, "speed": -0.10},
        "ensemble": {"coverage": 0.06, "confidence": 0.04, "speed": -0.05},
        "pre_validate": {"gap_severity": -0.04, "speed": 0.05},
        "rerank": {"coverage": 0.03, "speed": 0.03},
    }

    for node_name, node in workflow.nodes.items():
        if node.enabled and node_name in optional_bonuses:
            for metric, bonus in optional_bonuses[node_name].items():
                if metric == "coverage":
                    base_coverage += bonus
                elif metric == "confidence":
                    base_confidence += bonus
                elif metric == "gap_severity":
                    base_gap_severity += bonus
                elif metric == "speed":
                    base_speed += bonus

    # Parameter effects
    max_cycles = workflow.parameters.get("max_cycles_per_field", 5)
    if max_cycles > 5:
        base_coverage += 0.02
        base_speed -= 0.05
    elif max_cycles < 5:
        base_speed += 0.05
        base_coverage -= 0.02

    compaction = workflow.parameters.get("compaction_window", 10)
    if compaction > 10:
        base_efficiency *= 1.2
    elif compaction < 10:
        base_efficiency *= 0.8

    # Penalize overly complex topologies
    enabled_count = sum(1 for n in workflow.nodes.values() if n.enabled)
    if enabled_count > 8:
        base_speed -= 0.10
        base_efficiency *= 0.9

    return {
        "field_coverage": min(base_coverage, 1.0),
        "avg_confidence": min(base_confidence, 1.0),
        "token_efficiency": base_efficiency,
        "gap_severity": max(base_gap_severity, 0.0),
        "speed_score": min(max(base_speed, 0.0), 1.0),
    }


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _count_nodes(node: MCTSNode) -> int:
    """Count total nodes in the MCTS tree."""
    count = 1
    for child in node.children:
        count += _count_nodes(child)
    return count
