"""Graph building and topology validation — deterministic code [BLK-110].

No LLM involved. Maps symbols to nodes, connections to edges,
and validates topology rules from the contract.
"""

from __future__ import annotations

import logging
from typing import Any

from src.tools.base import ToolResult

logger = logging.getLogger(__name__)


def build_graph(
    symbols: list[dict[str, Any]] | None = None,
    connections: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> ToolResult:
    """Build a graph structure from detected symbols and connections [BLK-110].

    Pure deterministic code — maps symbols to nodes, connections to edges.

    Args:
        symbols: List of detected symbols with id, bbox, class.
        connections: List of detected connections with from_id, to_id, type.

    Returns:
        ToolResult with data = {nodes, edges}.
    """
    symbols = symbols or []
    connections = connections or []

    nodes = []
    for sym in symbols:
        nodes.append({
            "id": sym["id"],
            "type": sym.get("class", "unknown"),
            "bbox": sym.get("bbox"),
            "confidence": sym.get("confidence", 0.0),
            "tag": sym.get("tag"),
            "tag_components": sym.get("tag_components"),
        })

    edges = []
    for conn in connections:
        edges.append({
            "id": conn.get("id", f"edge_{len(edges)}"),
            "source": conn["from_id"],
            "target": conn["to_id"],
            "type": conn.get("type", "pipe"),
            "path_bbox": conn.get("path_bbox", []),
            "confidence": conn.get("confidence", 0.0),
        })

    return ToolResult(
        ok=True,
        data={"nodes": nodes, "edges": edges},
        tool="build_graph",
    )


def validate_topology(
    graph: dict[str, Any] | None = None,
    rules: list[str] | None = None,
    **kwargs: Any,
) -> ToolResult:
    """Validate graph topology against a set of rules [BLK-110].

    Pure deterministic code. Checks:
    - Every valve connected to at least one pipe
    - Every instrument tag follows ISA-5.1 (if tag present)
    - Control loops complete (sensor → controller → final element)
    - No orphan nodes (nodes with no edges)

    Args:
        graph: Graph dict with nodes and edges.
        rules: Optional list of rule names to check. If None, checks all.

    Returns:
        ToolResult with data = {violations, ok}.
    """
    graph = graph or {"nodes": [], "edges": []}
    rules = rules or ["valve_connected", "isa_tag_format", "control_loop", "no_orphans"]
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    violations: list[dict[str, str]] = []

    # Build adjacency
    node_ids = {n["id"] for n in nodes}
    connected_ids: set[str] = set()
    for e in edges:
        connected_ids.add(e["source"])
        connected_ids.add(e["target"])

    # Check: no orphan nodes
    if "no_orphans" in rules:
        for node in nodes:
            if node["id"] not in connected_ids:
                violations.append({
                    "rule": "no_orphans",
                    "node": node["id"],
                    "message": f"Node {node['id']} ({node.get('type', 'unknown')}) has no connections",
                })

    # Check: every valve connected to at least one pipe
    if "valve_connected" in rules:
        pipe_edges = [e for e in edges if e.get("type") == "pipe"]
        pipe_connected = {e["source"] for e in pipe_edges} | {e["target"] for e in pipe_edges}
        for node in nodes:
            node_type = node.get("type", "").lower()
            if "valve" in node_type and node["id"] not in pipe_connected:
                violations.append({
                    "rule": "valve_connected",
                    "node": node["id"],
                    "message": f"Valve {node['id']} is not connected to any pipe",
                })

    # Check: ISA-5.1 tag format
    if "isa_tag_format" in rules:
        from src.tools.graph.tag_reading import parse_isa_tag
        for node in nodes:
            tag = node.get("tag")
            if tag:
                parsed = parse_isa_tag(tag)
                if parsed.get("parse_error"):
                    violations.append({
                        "rule": "isa_tag_format",
                        "node": node["id"],
                        "message": f"Tag '{tag}' does not follow ISA-5.1 format",
                    })

    # Check: control loop completeness
    if "control_loop" in rules:
        _check_control_loops(nodes, edges, violations)

    return ToolResult(
        ok=True,
        data={"violations": violations, "ok": len(violations) == 0},
        tool="validate_topology",
    )


def _check_control_loops(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    violations: list[dict[str, str]],
) -> None:
    """Check that control loops are complete.

    A control loop requires: sensor (transmitter) → controller → final element (valve).
    We check if any instrument tagged as a transmitter (modifier "T") has a path
    to a controller (modifier "C") and then to a valve.
    """
    # Build adjacency list
    adj: dict[str, list[str]] = {}
    for e in edges:
        adj.setdefault(e["source"], []).append(e["target"])
        adj.setdefault(e["target"], []).append(e["source"])

    # Classify nodes by ISA role
    transmitters: list[dict[str, Any]] = []
    controllers: list[dict[str, Any]] = []
    final_elements: list[dict[str, Any]] = []

    for node in nodes:
        components = node.get("tag_components")
        if not components or components.get("parse_error"):
            continue
        modifier = components.get("modifier", "")
        if not modifier:
            continue
        if "T" in modifier:
            transmitters.append(node)
        if "C" in modifier:
            controllers.append(node)
        node_type = node.get("type", "").lower()
        if "valve" in node_type or "V" == modifier:
            final_elements.append(node)

    # For each transmitter, check if there's a path to a controller
    # and then to a final element (BFS, 2 hops max)
    for tx in transmitters:
        tx_id = tx["id"]
        reachable = _bfs(adj, tx_id, max_depth=3)
        has_controller = any(c["id"] in reachable for c in controllers)
        has_final = any(f["id"] in reachable for f in final_elements)
        if not has_controller:
            violations.append({
                "rule": "control_loop",
                "node": tx_id,
                "message": f"Transmitter {tx_id} has no reachable controller in the graph",
            })
        if not has_final:
            violations.append({
                "rule": "control_loop",
                "node": tx_id,
                "message": f"Transmitter {tx_id} has no reachable final element (valve) in the graph",
            })


def _bfs(adj: dict[str, list[str]], start: str, max_depth: int = 3) -> set[str]:
    """Breadth-first search with depth limit."""
    visited: set[str] = set()
    queue = [(start, 0)]
    while queue:
        node, depth = queue.pop(0)
        if depth > max_depth:
            break
        if node in visited:
            continue
        visited.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                queue.append((neighbor, depth + 1))
    return visited
