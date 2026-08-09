"""P&ID extraction contract — graph schema for Piping & Instrumentation Diagrams [BLK-111].

Defines the node types, edge types, topology rules, and output formats
for converting P&ID drawings to DEXPI XML and Smart P&ID JSON.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from src.templates.base import GraphExtractionContract


# ---------------------------------------------------------------------------
# Node/Edge type specs (as dicts for the GraphExtractionContract schema)
# ---------------------------------------------------------------------------

_NODE_TYPES = [
    {
        "name": "equipment",
        "subtypes": ["vessel", "pump", "heat_exchanger", "tank", "compressor"],
    },
    {
        "name": "valve",
        "subtypes": ["manual", "control", "check", "relief"],
    },
    {
        "name": "instrument",
        "subtypes": ["sensor", "controller", "indicator"],
    },
    {
        "name": "pipe",
        "subtypes": [],
    },
    {
        "name": "fitting",
        "subtypes": ["reducer", "elbow", "tee"],
    },
]

_EDGE_TYPES = [
    {
        "name": "connected_to",
        "source_type": "any",
        "target_type": "any",
    },
    {
        "name": "branches_from",
        "source_type": "pipe",
        "target_type": "pipe",
    },
    {
        "name": "measures",
        "source_type": "instrument",
        "target_type": "equipment|pipe",
    },
    {
        "name": "controls",
        "source_type": "instrument",
        "target_type": "valve",
    },
]

_TOPOLOGY_RULES = [
    {"name": "every_valve_connected_to_pipe", "description": "Every valve connected to at least one pipe"},
    {"name": "isa_51_tag_format", "description": "Every instrument tag follows ISA-5.1 (XX-NNN)"},
    {"name": "control_loop_completeness", "description": "Control loops complete: sensor → controller → final_element"},
    {"name": "no_orphan_pipes", "description": "No orphan pipes (both ends connected or explicitly capped)"},
]

_OUTPUT_FORMATS = ["dexpi_xml", "smart_pid_json", "graphml"]


class PnIDContract(GraphExtractionContract):
    """Graph extraction contract for P&ID → DEXPI/Smart P&ID [BLK-111].

    Defines the valid node types (equipment, valve, instrument, pipe, fitting),
    edge types (connected_to, branches_from, measures, controls), topology
    rules, and supported output serialization formats.
    """

    name: str = Field(default="P&ID to DEXPI/Smart P&ID")
    description: str = Field(
        default="Extract process graph from P&ID drawings and serialize to DEXPI XML or Smart P&ID JSON."
    )
    node_types: list[dict[str, Any]] = Field(default_factory=lambda: list(_NODE_TYPES))
    edge_types: list[dict[str, Any]] = Field(default_factory=lambda: list(_EDGE_TYPES))
    topology_rules: list[dict[str, Any]] = Field(default_factory=lambda: list(_TOPOLOGY_RULES))
    output_formats: list[str] = Field(default_factory=lambda: list(_OUTPUT_FORMATS))
