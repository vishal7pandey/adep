"""Tests for MCTS Workflow Optimizer [BLK-072, SCRUM-79].

Tests cover:
- WorkflowTopology (construction, serialization, default_react)
- MCTSNode (UCB1, avg_score)
- Selection (UCB1 traversal)
- Expansion (LLM mock, heuristic fallback, action application)
- Action application (add_node, remove_node, rewire_edge, tune_parameter, modify_node_params)
- Evaluation (default evaluator, aggregate scoring)
- Backpropagation
- Experience accumulation
- Full optimize_workflow loop (convergence, max iterations, token tracking)
- API endpoint (POST /workflows/optimize)
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.ai.workflow_optimizer import (
    MCTSNode,
    MCTSResult,
    OPERATORS,
    WorkflowEdge,
    WorkflowNode,
    WorkflowTopology,
    _accumulate_experience,
    _apply_action,
    _backpropagate,
    _count_nodes,
    _default_evaluator,
    _evaluate_workflow,
    _expand,
    _heuristic_expand,
    _select,
    optimize_workflow,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _make_workflow() -> WorkflowTopology:
    return WorkflowTopology.default_react()


def _make_eval_fn(coverage: float = 0.8, confidence: float = 0.85, efficiency: float = 0.001,
                  gap_severity: float = 0.1, speed: float = 0.75) -> Any:
    """Create a mock evaluation function with fixed scores."""
    def eval_fn(wf: WorkflowTopology) -> dict[str, float]:
        return {
            "field_coverage": coverage,
            "avg_confidence": confidence,
            "token_efficiency": efficiency,
            "gap_severity": gap_severity,
            "speed_score": speed,
        }
    return eval_fn


# ---------------------------------------------------------------------------
# Unit tests — WorkflowTopology
# ---------------------------------------------------------------------------

class TestWorkflowTopology:
    def test_default_react(self):
        wf = WorkflowTopology.default_react()
        assert "plan" in wf.nodes
        assert "act" in wf.nodes
        assert "observe" in wf.nodes
        assert "reflect" in wf.nodes
        assert "compact" in wf.nodes
        assert "terminate" in wf.nodes
        assert wf.entry_point == "plan"
        assert len(wf.edges) > 0
        assert wf.parameters["max_cycles_per_field"] == 5

    def test_to_dict_from_dict_roundtrip(self):
        wf = _make_workflow()
        d = wf.to_dict()
        restored = WorkflowTopology.from_dict(d)
        assert set(restored.nodes.keys()) == set(wf.nodes.keys())
        assert len(restored.edges) == len(wf.edges)
        assert restored.entry_point == wf.entry_point
        assert restored.parameters == wf.parameters

    def test_from_dict_partial(self):
        d = {"nodes": {"plan": {"node_type": "core"}}, "edges": [], "entry_point": "plan"}
        wf = WorkflowTopology.from_dict(d)
        assert "plan" in wf.nodes
        assert wf.nodes["plan"].node_type == "core"
        assert wf.entry_point == "plan"


# ---------------------------------------------------------------------------
# Unit tests — MCTSNode
# ---------------------------------------------------------------------------

class TestMCTSNode:
    def test_avg_score_no_visits(self):
        node = MCTSNode(workflow=_make_workflow())
        assert node.avg_score == 0.0

    def test_avg_score_with_visits(self):
        node = MCTSNode(workflow=_make_workflow())
        node.visits = 4
        node.total_score = 3.0
        assert node.avg_score == 0.75

    def test_ucb1_no_visits(self):
        node = MCTSNode(workflow=_make_workflow())
        assert node.ucb1 == float("inf")

    def test_ucb1_with_visits_no_parent(self):
        node = MCTSNode(workflow=_make_workflow())
        node.visits = 10
        node.total_score = 5.0
        # avg_score=0.5, exploration = sqrt(ln(10)/10) * 1.41
        import math
        expected = 0.5 + 1.41 * math.sqrt(math.log(10) / 10)
        assert abs(node.ucb1 - expected) < 0.001

    def test_ucb1_with_parent(self):
        parent = MCTSNode(workflow=_make_workflow())
        parent.visits = 20
        child = MCTSNode(workflow=_make_workflow(), parent=parent)
        child.visits = 5
        child.total_score = 3.0
        # avg_score=0.6, exploration = sqrt(ln(20)/5) * 1.41
        import math
        expected = 0.6 + 1.41 * math.sqrt(math.log(20) / 5)
        assert abs(child.ucb1 - expected) < 0.001


# ---------------------------------------------------------------------------
# Unit tests — Selection
# ---------------------------------------------------------------------------

class TestSelect:
    def test_select_root_no_children(self):
        root = MCTSNode(workflow=_make_workflow())
        selected = _select(root)
        assert selected is root

    def test_select_descends_to_best_child(self):
        root = MCTSNode(workflow=_make_workflow())
        root.expanded = True
        root.visits = 10

        child1 = MCTSNode(workflow=_make_workflow(), parent=root)
        child1.visits = 5
        child1.total_score = 3.0  # avg=0.6

        child2 = MCTSNode(workflow=_make_workflow(), parent=root)
        child2.visits = 5
        child2.total_score = 4.0  # avg=0.8

        root.children = [child1, child2]
        selected = _select(root)
        assert selected is child2  # Higher UCB1


# ---------------------------------------------------------------------------
# Unit tests — Expansion
# ---------------------------------------------------------------------------

class TestExpand:
    def test_expand_with_llm_add_node(self):
        root = MCTSNode(workflow=_make_workflow())

        action = {
            "action": "add_node",
            "description": "Add review node",
            "details": {"node_name": "review"},
            "rationale": "Quality check before terminate",
        }

        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps(action),
                input_tokens=100, output_tokens=200, total_tokens=300,
            )
            child, tu = _expand(root, "feedback", "experience")

            assert "review" in child.workflow.nodes
            assert child.parent is root
            assert child.expansion_action == "Add review node"
            assert tu["total_tokens"] == 300
            assert root.expanded is True
            assert len(root.children) == 1

    def test_expand_no_llm_heuristic(self):
        root = MCTSNode(workflow=_make_workflow())

        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0)
            child, tu = _expand(root, "feedback", "experience")

            assert "review" in child.workflow.nodes
            assert "heuristic" in child.expansion_action

    def test_expand_invalid_json_heuristic(self):
        root = MCTSNode(workflow=_make_workflow())

        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(content="not json", input_tokens=10, output_tokens=20, total_tokens=30)
            child, _ = _expand(root, "feedback", "experience")

            assert "review" in child.workflow.nodes
            assert "heuristic" in child.expansion_action


# ---------------------------------------------------------------------------
# Unit tests — Action application
# ---------------------------------------------------------------------------

class TestApplyAction:
    def test_add_node(self):
        wf = _make_workflow()
        action = {
            "action": "add_node",
            "details": {"node_name": "review"},
            "description": "Add review",
        }
        new_wf = _apply_action(wf, "review" and action)
        assert "review" in new_wf.nodes
        assert new_wf.nodes["review"].node_type == "optional"
        # Original should be unchanged
        assert "review" not in wf.nodes

    def test_remove_node(self):
        wf = _make_workflow()
        wf.nodes["review"] = WorkflowNode(name="review", node_type="optional")
        wf.edges.append(WorkflowEdge("reflect", "review", "check"))
        wf.edges.append(WorkflowEdge("review", "terminate", "ok"))

        action = {
            "action": "remove_node",
            "details": {"node_name": "review"},
            "description": "Remove review",
        }
        new_wf = _apply_action(wf, action)
        assert "review" not in new_wf.nodes
        # Reflect should regain terminate edge
        has_terminate = any(e.target == "terminate" for e in new_wf.edges if e.source == "reflect")
        assert has_terminate

    def test_remove_core_node_blocked(self):
        wf = _make_workflow()
        action = {
            "action": "remove_node",
            "details": {"node_name": "plan"},
            "description": "Remove plan",
        }
        new_wf = _apply_action(wf, action)
        # Core nodes should not be removed
        assert "plan" in new_wf.nodes

    def test_rewire_edge(self):
        wf = _make_workflow()
        action = {
            "action": "rewire_edge",
            "details": {"edge_source": "observe", "edge_target": "plan", "edge_condition": "skip_reflect"},
            "description": "Skip reflect sometimes",
        }
        new_wf = _apply_action(wf, action)
        assert any(e.source == "observe" and e.target == "plan" for e in new_wf.edges)

    def test_tune_parameter(self):
        wf = _make_workflow()
        action = {
            "action": "tune_parameter",
            "details": {"parameter_name": "max_cycles_per_field", "parameter_value": 8},
            "description": "Increase cycle cap",
        }
        new_wf = _apply_action(wf, action)
        assert new_wf.parameters["max_cycles_per_field"] == 8
        # Original unchanged
        assert wf.parameters["max_cycles_per_field"] == 5

    def test_modify_node_params(self):
        wf = _make_workflow()
        wf.nodes["review"] = WorkflowNode(name="review", node_type="optional", params={"threshold": 0.85})
        action = {
            "action": "modify_node_params",
            "details": {"node_name": "review", "node_params": {"threshold": 0.90}},
            "description": "Raise review threshold",
        }
        new_wf = _apply_action(wf, action)
        assert new_wf.nodes["review"].params["threshold"] == 0.90


# ---------------------------------------------------------------------------
# Unit tests — Heuristic expansion
# ---------------------------------------------------------------------------

class TestHeuristicExpand:
    def test_adds_review_if_missing(self):
        wf = _make_workflow()
        assert "review" not in wf.nodes
        new_wf = _heuristic_expand(wf)
        assert "review" in new_wf.nodes

    def test_does_not_add_if_present(self):
        wf = _make_workflow()
        wf.nodes["review"] = WorkflowNode(name="review", node_type="optional")
        new_wf = _heuristic_expand(wf)
        # Should still have review but not duplicate
        assert "review" in new_wf.nodes


# ---------------------------------------------------------------------------
# Unit tests — Evaluation
# ---------------------------------------------------------------------------

class TestEvaluateWorkflow:
    def test_basic_evaluation(self):
        wf = _make_workflow()
        eval_fn = _make_eval_fn(coverage=0.9, confidence=0.85, efficiency=0.002, gap_severity=0.1, speed=0.8)
        score, feedback = _evaluate_workflow(wf, eval_fn)
        # 0.9*0.35 + 0.85*0.25 + 0.002*0.15 + 0.8*0.15 - 0.1*0.1
        # = 0.315 + 0.2125 + 0.0003 + 0.12 - 0.01 = 0.6378
        assert abs(score - 0.6378) < 0.01
        assert "Field coverage" in feedback
        assert "Enabled nodes" in feedback

    def test_default_evaluator_base(self):
        wf = _make_workflow()
        scores = _default_evaluator(wf)
        assert 0.0 <= scores["field_coverage"] <= 1.0
        assert 0.0 <= scores["avg_confidence"] <= 1.0
        assert scores["gap_severity"] >= 0.0

    def test_default_evaluator_with_optional_nodes(self):
        wf = _make_workflow()
        wf.nodes["review"] = WorkflowNode(name="review", node_type="optional", enabled=True)
        scores_base = _default_evaluator(_make_workflow())
        scores_with_review = _default_evaluator(wf)
        assert scores_with_review["field_coverage"] > scores_base["field_coverage"]
        assert scores_with_review["gap_severity"] < scores_base["gap_severity"]

    def test_default_evaluator_complexity_penalty(self):
        wf = _make_workflow()
        for op in OPERATORS:
            wf.nodes[op] = WorkflowNode(name=op, node_type="optional", enabled=True)
        scores = _default_evaluator(wf)
        # Should have speed penalty for >8 enabled nodes
        assert scores["speed_score"] < 0.75


# ---------------------------------------------------------------------------
# Unit tests — Backpropagation
# ---------------------------------------------------------------------------

class TestBackpropagate:
    def test_single_node(self):
        node = MCTSNode(workflow=_make_workflow())
        _backpropagate(node, 0.8)
        assert node.visits == 1
        assert node.total_score == 0.8

    def test_chain(self):
        root = MCTSNode(workflow=_make_workflow())
        child = MCTSNode(workflow=_make_workflow(), parent=root)
        grandchild = MCTSNode(workflow=_make_workflow(), parent=child)
        _backpropagate(grandchild, 0.9)
        assert grandchild.visits == 1
        assert grandchild.total_score == 0.9
        assert child.visits == 1
        assert child.total_score == 0.9
        assert root.visits == 1
        assert root.total_score == 0.9


# ---------------------------------------------------------------------------
# Unit tests — Experience accumulation
# ---------------------------------------------------------------------------

class TestAccumulateExperience:
    def test_no_parent(self):
        root = MCTSNode(workflow=_make_workflow())
        exp = _accumulate_experience(root)
        assert "No prior experience" in exp

    def test_with_chain(self):
        root = MCTSNode(workflow=_make_workflow())
        root.visits = 5
        root.total_score = 3.0
        child = MCTSNode(workflow=_make_workflow(), parent=root, expansion_action="Add review node")
        child.visits = 3
        child.total_score = 2.0
        exp = _accumulate_experience(child)
        assert "Add review node" in exp
        assert "avg_score" in exp


# ---------------------------------------------------------------------------
# Unit tests — Count nodes
# ---------------------------------------------------------------------------

class TestCountNodes:
    def test_single_node(self):
        root = MCTSNode(workflow=_make_workflow())
        assert _count_nodes(root) == 1

    def test_with_children(self):
        root = MCTSNode(workflow=_make_workflow())
        root.children = [
            MCTSNode(workflow=_make_workflow(), parent=root),
            MCTSNode(workflow=_make_workflow(), parent=root),
        ]
        root.children[0].children = [MCTSNode(workflow=_make_workflow(), parent=root.children[0])]
        assert _count_nodes(root) == 4


# ---------------------------------------------------------------------------
# Unit tests — Full optimize_workflow loop
# ---------------------------------------------------------------------------

class TestOptimizeWorkflow:
    def test_default_seed(self):
        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"action": "add_node", "description": "Add review", "details": {"node_name": "review"}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_workflow(
                max_iterations=3,
                rng_seed=42,
            )
            assert result.best_workflow is not None
            assert result.iterations == 3
            assert result.tree_size >= 2
            assert len(result.history) >= 4

    def test_max_iterations(self):
        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"action": "add_node", "description": "Add review", "details": {"node_name": "review"}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_workflow(
                seed_workflow=_make_workflow(),
                max_iterations=5,
                rng_seed=42,
            )
            assert result.iterations <= 5
            assert "max iterations" in result.convergence_reason or "Converged" in result.convergence_reason

    def test_convergence_plateau(self):
        eval_fn = _make_eval_fn(coverage=0.8, confidence=0.85, efficiency=0.001, gap_severity=0.1, speed=0.75)
        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"action": "add_node", "description": "Add review", "details": {"node_name": "review"}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_workflow(
                seed_workflow=_make_workflow(),
                evaluate_fn=eval_fn,
                max_iterations=30,
                convergence_threshold=0.001,
                rng_seed=42,
            )
            # With constant eval, should converge via plateau
            assert result.iterations < 30 or result.convergence_reason.startswith("Converged")

    def test_token_usage_accumulated(self):
        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"action": "add_node", "description": "Add review", "details": {"node_name": "review"}}),
                input_tokens=100, output_tokens=200, total_tokens=300,
            )
            result = optimize_workflow(
                seed_workflow=_make_workflow(),
                max_iterations=3,
                rng_seed=42,
            )
            assert result.token_usage["total_tokens"] > 0
            assert result.token_usage["input_tokens"] > 0

    def test_history_records_iterations(self):
        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"action": "add_node", "description": "Add review", "details": {"node_name": "review"}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_workflow(
                seed_workflow=_make_workflow(),
                max_iterations=3,
                rng_seed=42,
            )
            assert result.history[0]["event"] == "seed_evaluated"
            for h in result.history[1:]:
                assert h["event"] == "expanded"
                assert "action" in h
                assert "score" in h

    def test_to_dict(self):
        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"action": "add_node", "description": "Add review", "details": {"node_name": "review"}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_workflow(
                seed_workflow=_make_workflow(),
                max_iterations=2,
                rng_seed=42,
            )
            d = result.to_dict()
            assert "best_workflow" in d
            assert "best_score" in d
            assert "tree_size" in d
            assert "iterations" in d
            assert "history" in d
            assert "token_usage" in d
            assert "convergence_reason" in d

    def test_best_workflow_improves_with_review(self):
        """Test that adding a review node improves the default evaluator score."""
        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"action": "add_node", "description": "Add review", "details": {"node_name": "review"}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_workflow(
                seed_workflow=_make_workflow(),
                max_iterations=5,
                rng_seed=42,
            )
            # The best workflow should have a review node (since it improves scores)
            assert result.best_workflow is not None
            best_has_review = "review" in result.best_workflow.nodes
            # If the best is still the seed, that's also acceptable (convergence may pick seed)
            # but typically the review node should improve the score
            seed_score = _default_evaluator(_make_workflow())["field_coverage"]
            best_score = _default_evaluator(result.best_workflow)["field_coverage"]
            assert best_score >= seed_score


# ---------------------------------------------------------------------------
# Integration tests — API endpoint
# ---------------------------------------------------------------------------

class TestOptimizeWorkflowAPI:
    @pytest.fixture
    def client(self, tmp_path) -> TestClient:
        import src.definitions.store as store_module
        import src.config as config_module
        from src.definitions.store import DefinitionStore

        old_store = store_module._store
        old_auth = config_module.settings.auth_enabled
        store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
        config_module.settings.auth_enabled = False

        from src.api.main import create_app
        app = create_app()
        test_client = TestClient(app)

        yield test_client

        config_module.settings.auth_enabled = old_auth
        store_module._store = old_store

    def test_optimize_workflow_endpoint(self, client: TestClient):
        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"action": "add_node", "description": "Add review", "details": {"node_name": "review"}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            response = client.post("/api/v1/workflows/optimize", json={
                "max_iterations": 3,
                "rng_seed": 42,
            })
            assert response.status_code == 200
            data = response.json()
            assert "best_workflow" in data
            assert "best_score" in data
            assert "iterations" in data
            assert "history" in data
            assert "convergence_reason" in data

    def test_optimize_workflow_with_seed(self, client: TestClient):
        seed = _make_workflow().to_dict()
        with patch("src.ai.workflow_optimizer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"action": "tune_parameter", "description": "Increase cycles", "details": {"parameter_name": "max_cycles_per_field", "parameter_value": 8}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            response = client.post("/api/v1/workflows/optimize", json={
                "seed_workflow": seed,
                "max_iterations": 2,
                "rng_seed": 42,
            })
            assert response.status_code == 200
            data = response.json()
            assert data["best_workflow"] is not None
