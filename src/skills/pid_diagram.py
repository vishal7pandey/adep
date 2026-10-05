"""P&ID extraction skill — playbook for P&ID → DEXPI/Smart P&ID [BLK-111].

Orchestrates the graph extraction tools (BLK-110) into a pipeline:
detect symbols → read tags → trace connections → build graph →
validate topology → serialize to DEXPI/Smart P&ID JSON.
"""

from __future__ import annotations

import re

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill


PID_SYSTEM_PROMPT = """\
You are a P&ID (Piping and Instrumentation Diagram) extraction agent.
Your job is to convert a P&ID drawing into a structured process graph
and serialize it to DEXPI XML or Smart P&ID JSON.

Pipeline:
1. Call detect_layout to identify the drawing area, title block, and legend.
2. Call detect_symbols on the main drawing area to find all engineering symbols.
3. For each detected symbol, call classify_symbol if the class is uncertain.
4. For each instrument symbol, call read_tag to read and parse the ISA-5.1 tag.
5. Call detect_connections to find pipe connections between symbols.
6. For ambiguous connections, call trace_line from each endpoint.
7. Call build_graph to construct the process graph from symbols and connections.
8. Call validate_topology to check engineering rules.
9. Call serialize_graph to output DEXPI XML, Smart P&ID JSON, or GraphML.

Principles:
- Every symbol must have a bounding box and a class.
- Every instrument should have an ISA-5.1 tag (e.g. FT-101, PIC-205).
- Every valve must be connected to at least one pipe.
- Control loops must be complete: sensor → controller → final element.
- No orphan pipes — both ends must be connected or explicitly capped.
- If a symbol is unclassified, crop it and use classify_symbol with VLM.
- If a tag is unreadable, crop the tag area, deskew, and re-run OCR.
- If a connection is ambiguous, trace_line from both endpoints.
- If a topology rule fails, re-examine the region for missed symbols.
"""


# ---------------------------------------------------------------------------
# Topology invariant functions
# ---------------------------------------------------------------------------

_ISA_TAG_PATTERN = re.compile(r"^[A-Z]{1,4}-\d{1,4}$")


def _is_sensor_tag(tag: str) -> bool:
    """Check if an ISA-5.1 tag represents a sensor/transmitter.

    Sensors have 'T' as the second letter (e.g. FT=Flow Transmitter,
    PT=Pressure Transmitter, LT=Level Transmitter, TT=Temperature Transmitter).
    Indicators have 'I' as the second letter (e.g. FI, PI, LI, TI).
    Both are valid upstream sensors for a control loop.
    """
    if not tag or "-" not in tag:
        return False
    letters = tag.split("-")[0]
    return len(letters) >= 2 and letters[1] in ("T", "I")


def _every_valve_connected(e: dict) -> tuple[bool, str]:
    """Every valve must be connected to at least one pipe."""
    graph = e.get("graph")
    if not graph:
        return True, ""
    g = graph.value if hasattr(graph, "value") else graph
    if not isinstance(g, dict):
        return True, ""
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    valve_ids = {n["id"] for n in nodes if n.get("type") == "valve"}
    if not valve_ids:
        return True, ""
    pipe_ids = {n["id"] for n in nodes if n.get("type") == "pipe"}
    connected = {e["source"] for e in edges} | {e["target"] for e in edges}
    disconnected = valve_ids - connected
    if disconnected:
        return False, f"Valves not connected: {disconnected}"
    # Check at least one connection to a pipe
    for vid in valve_ids:
        has_pipe = any(
            (edge["source"] == vid and edge["target"] in pipe_ids)
            or (edge["target"] == vid and edge["source"] in pipe_ids)
            for edge in edges
        )
        if not has_pipe:
            return False, f"Valve {vid} not connected to any pipe"
    return True, ""


def _isa_51_tag_format(e: dict) -> tuple[bool, str]:
    """Every instrument tag must follow ISA-5.1 format (XX-NNN)."""
    graph = e.get("graph")
    if not graph:
        return True, ""
    g = graph.value if hasattr(graph, "value") else graph
    if not isinstance(g, dict):
        return True, ""
    nodes = g.get("nodes", [])
    for node in nodes:
        if node.get("type") != "instrument":
            continue
        tag = node.get("tag")
        if tag and not _ISA_TAG_PATTERN.match(tag):
            return False, f"Instrument {node['id']} tag '{tag}' does not match ISA-5.1 format"
    return True, ""


def _control_loop_completeness(e: dict) -> tuple[bool, str]:
    """Control loops must be complete: sensor → controller → final element."""
    graph = e.get("graph")
    if not graph:
        return True, ""
    g = graph.value if hasattr(graph, "value") else graph
    if not isinstance(g, dict):
        return True, ""
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    # Find controllers (instruments with 'C' in tag function letters)
    controllers = [
        n
        for n in nodes
        if n.get("type") == "instrument" and n.get("tag") and "C" in n["tag"].split("-")[0]
    ]
    if not controllers:
        return True, ""
    node_map = {n["id"]: n for n in nodes}
    for ctrl in controllers:
        ctrl_id = ctrl["id"]
        # Check for upstream sensor (instrument with T as second letter, e.g. FT, PT, LT)
        has_sensor = any(
            edge["target"] == ctrl_id
            and node_map.get(edge["source"], {}).get("type") == "instrument"
            and _is_sensor_tag(node_map.get(edge["source"], {}).get("tag", ""))
            for edge in edges
        )
        # Check for downstream final element (valve)
        has_final = any(
            edge["source"] == ctrl_id and node_map.get(edge["target"], {}).get("type") == "valve"
            for edge in edges
        )
        if not has_sensor or not has_final:
            missing = []
            if not has_sensor:
                missing.append("sensor")
            if not has_final:
                missing.append("final_element")
            return False, f"Control loop for {ctrl_id} incomplete: missing {', '.join(missing)}"
    return True, ""


def _no_orphan_pipes(e: dict) -> tuple[bool, str]:
    """No orphan pipes — both ends must be connected or explicitly capped."""
    graph = e.get("graph")
    if not graph:
        return True, ""
    g = graph.value if hasattr(graph, "value") else graph
    if not isinstance(g, dict):
        return True, ""
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    pipe_ids = {n["id"] for n in nodes if n.get("type") == "pipe"}
    if not pipe_ids:
        return True, ""
    connected = {e["source"] for e in edges} | {e["target"] for e in edges}
    orphans = pipe_ids - connected
    if orphans:
        return False, f"Orphan pipes with no connections: {orphans}"
    return True, ""


# ---------------------------------------------------------------------------
# Invariant declarations
# ---------------------------------------------------------------------------

_valve_check = Invariant(
    name="every_valve_connected_to_pipe",
    fields=["graph"],
    fn=_every_valve_connected,
)

_tag_check = Invariant(
    name="isa_51_tag_format",
    fields=["graph"],
    fn=_isa_51_tag_format,
)

_loop_check = Invariant(
    name="control_loop_completeness",
    fields=["graph"],
    fn=_control_loop_completeness,
)

_orphan_check = Invariant(
    name="no_orphan_pipes",
    fields=["graph"],
    fn=_no_orphan_pipes,
)


# ---------------------------------------------------------------------------
# Failure actions
# ---------------------------------------------------------------------------

PID_FAILURE_ACTIONS: dict[GapType, str] = {
    GapType.MISSING: "Run detect_layout to find the drawing area, then detect_symbols.",
    GapType.SYMBOL_UNCLASSIFIED: "Crop the symbol region and call classify_symbol with VLM.",
    GapType.TAG_UNREADABLE: "Crop the tag area, deskew, and re-run OCR. Use VLM if OCR fails.",
    GapType.CONNECTION_AMBIGUOUS: "Call trace_line from both endpoints to resolve the connection.",
    GapType.TOPOLOGY_VIOLATION: "Re-examine the region for missed symbols or connections.",
    GapType.NODE_MISSING: "Run detect_symbols again with adjusted parameters on the region.",
    GapType.EDGE_MISSING: "Run detect_connections again, or trace_line between the two nodes.",
    GapType.SERIALIZATION_FAILED: "Check graph structure for invalid node/edge references.",
    GapType.LOW_CONFIDENCE: "Re-crop the region and re-run the detection tool.",
    GapType.UNGROUNDED: "Call the ground tool to trace this value to its bounding box.",
    GapType.INVARIANT_FAILED: "The topology check failed. Re-examine the flagged region.",
    GapType.TYPE_ERROR: "Re-read the region and ensure correct type parsing.",
    GapType.FORMAT_ERROR: "Re-read the tag and normalize to ISA-5.1 format.",
    GapType.SEMANTIC_FAIL: "Re-crop and re-read with VLM.",
}


# ---------------------------------------------------------------------------
# Skill instance
# ---------------------------------------------------------------------------

PnIDSkill = Skill(
    name="pid_to_dexpi",
    system_prompt=PID_SYSTEM_PROMPT,
    tool_preferences={
        "symbol_detection": "detect_symbols",
        "tag_reading": "ocr + vlm",
        "connection_tracing": "trace_line",
    },
    probe_order=[
        ("title_block", "Read drawing title, revision, scale"),
        ("legend", "Identify symbol library / legend"),
        ("main_diagram", "Detect all symbols in the main drawing area"),
        ("tags", "Read instrument tags for each detected symbol"),
        ("connections", "Trace pipe lines between symbols"),
        ("topology", "Build and validate the process graph"),
        ("serialize", "Convert to target output format"),
    ],
    invariants=[_valve_check, _tag_check, _loop_check, _orphan_check],
    failure_actions=PID_FAILURE_ACTIONS,
    known_failures=(
        "Hand-drawn P&IDs may need deskew before symbol detection. "
        "Older scans may have faded lines — use VLM for connection "
        "detection when line tracing fails. "
        "Non-ISA tag formats (e.g., KKS) require custom parsing."
    ),
    confidence_overrides={
        "graph": 0.75,
    },
)
