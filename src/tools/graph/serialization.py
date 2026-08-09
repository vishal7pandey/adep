"""Graph serialization — multi-format output [BLK-110].

Formats: json, graphml, dexpi_xml, smart_pid_json.
All serializers are deterministic code — no LLM.
"""

from __future__ import annotations

from typing import Any

from src.tools.base import ToolResult


def serialize_graph(
    graph: dict[str, Any] | None = None,
    format: str = "json",
    **kwargs: Any,
) -> ToolResult:
    """Serialize a graph to a target format [BLK-110].

    Args:
        graph: Graph dict with nodes and edges.
        format: Target format — "json", "graphml", "dexpi_xml", or "smart_pid_json".

    Returns:
        ToolResult with data = {format, content}.
    """
    graph = graph or {"nodes": [], "edges": []}

    if format == "json":
        return _serialize_json(graph)
    elif format == "graphml":
        return _serialize_graphml(graph)
    elif format == "dexpi_xml":
        return _serialize_dexpi(graph)
    elif format == "smart_pid_json":
        return _serialize_smart_pid(graph)
    else:
        return ToolResult(
            ok=False,
            error=f"Unknown serialization format: {format}. "
            f"Supported: json, graphml, dexpi_xml, smart_pid_json",
            tool="serialize_graph",
        )


def _serialize_json(graph: dict[str, Any]) -> ToolResult:
    """Serialize to plain JSON."""
    import json
    content = json.dumps(graph, indent=2, default=str)
    return ToolResult(
        ok=True,
        data={"format": "json", "content": content},
        tool="serialize_graph",
    )


def _serialize_graphml(graph: dict[str, Any]) -> ToolResult:
    """Serialize to GraphML (XML-based graph exchange format)."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
        '  <key id="edge_type" for="edge" attr.name="type" attr.type="string"/>',
        '  <graph id="G" edgedefault="undirected">',
    ]

    for node in nodes:
        node_id = node["id"]
        node_type = node.get("type", "unknown")
        lines.append(f'    <node id="{_xml_escape(node_id)}">')
        lines.append(f'      <data key="type">{_xml_escape(node_type)}</data>')
        tag = node.get("tag")
        if tag:
            lines.append(f'      <data key="tag">{_xml_escape(tag)}</data>')
        lines.append('    </node>')

    for i, edge in enumerate(edges):
        edge_id = edge.get("id", f"e{i}")
        source = edge["source"]
        target = edge["target"]
        edge_type = edge.get("type", "pipe")
        lines.append(f'    <edge id="{_xml_escape(edge_id)}" '
                      f'source="{_xml_escape(source)}" '
                      f'target="{_xml_escape(target)}">')
        lines.append(f'      <data key="edge_type">{_xml_escape(edge_type)}</data>')
        lines.append('    </edge>')

    lines.append('  </graph>')
    lines.append('</graphml>')

    return ToolResult(
        ok=True,
        data={"format": "graphml", "content": "\n".join(lines)},
        tool="serialize_graph",
    )


def _serialize_dexpi(graph: dict[str, Any]) -> ToolResult:
    """Serialize to DEXPI XML (ISO 15926-based process plant format)."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<DEXPI xmlns="http://dexpi.org/schema/2018/01">',
        '  <Plant>',
        '    <Equipment>',
    ]

    for node in nodes:
        node_id = node["id"]
        node_type = node.get("type", "unknown")
        tag = node.get("tag", "")
        lines.append(f'      <Item ID="{_xml_escape(node_id)}" '
                      f'Class="{_xml_escape(node_type)}">')
        if tag:
            lines.append(f'        <Tag>{_xml_escape(tag)}</Tag>')
        bbox = node.get("bbox")
        if bbox:
            lines.append(f'        <Position x="{bbox[0]}" y="{bbox[1]}" '
                          f'w="{bbox[2] - bbox[0]}" h="{bbox[3] - bbox[1]}"/>')
        lines.append('      </Item>')

    lines.append('    </Equipment>')
    lines.append('    <Piping>')

    for i, edge in enumerate(edges):
        edge_id = edge.get("id", f"p{i}")
        source = edge["source"]
        target = edge["target"]
        edge_type = edge.get("type", "pipe")
        lines.append(f'      <PipeLine ID="{_xml_escape(edge_id)}" '
                      f'From="{_xml_escape(source)}" '
                      f'To="{_xml_escape(target)}" '
                      f'Type="{_xml_escape(edge_type)}"/>')

    lines.append('    </Piping>')
    lines.append('  </Plant>')
    lines.append('</DEXPI>')

    return ToolResult(
        ok=True,
        data={"format": "dexpi_xml", "content": "\n".join(lines)},
        tool="serialize_graph",
    )


def _serialize_smart_pid(graph: dict[str, Any]) -> ToolResult:
    """Serialize to Smart P&ID JSON representation."""
    import json
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    smart_pid = {
        "version": "1.0",
        "format": "smart_pid_json",
        "components": [
            {
                "id": n["id"],
                "type": n.get("type", "unknown"),
                "tag": n.get("tag", ""),
                "geometry": {
                    "x": n["bbox"][0] if n.get("bbox") else 0,
                    "y": n["bbox"][1] if n.get("bbox") else 0,
                    "width": (n["bbox"][2] - n["bbox"][0]) if n.get("bbox") else 0,
                    "height": (n["bbox"][3] - n["bbox"][1]) if n.get("bbox") else 0,
                },
            }
            for n in nodes
        ],
        "connections": [
            {
                "id": e.get("id", f"c{i}"),
                "from": e["source"],
                "to": e["target"],
                "type": e.get("type", "pipe"),
            }
            for i, e in enumerate(edges)
        ],
    }

    return ToolResult(
        ok=True,
        data={"format": "smart_pid_json", "content": json.dumps(smart_pid, indent=2)},
        tool="serialize_graph",
    )


def _xml_escape(text: str) -> str:
    """Escape special XML characters."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
