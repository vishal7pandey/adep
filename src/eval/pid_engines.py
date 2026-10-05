"""Adapters that run the two engines on one P&ID image for the head-to-head (ADE-31).

Only `graph_to_extraction` and `parse_json_object` are pure and unit-tested; the adapters call real
models and are exercised by the capped manual run. Each engine uses its own native
perception: the new engine's VLM tools, the old engine's OCR/layout provider (`ocr_provider`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.eval.pid_compare import Drawing, Engine, UnparseableOutput
from src.eval.pid_ground_truth import discover_references, load_ground_truth, svg_to_png
from src.eval.pid_scoring import CATEGORIES

INSTRUMENT_TYPES = ("instrument", "sensor", "controller", "indicator", "transmitter")
IGNORED_NODE_TYPES = ("pipe", "fitting")
OLD_MAX_CYCLES = 50  # the prebuilt P&ID definition's max_cycles_per_document
DEFAULT_DRAWING_COUNT = 3
PNG_DIR = Path(".adep") / "eval" / "png"

NEW_ENGINE_PROMPT = (
    "Digitize this P&ID into the skill's JSON schema. Use the skill 'pid-dexpi-digitizer' "
    "(load it with load_skill_tool). Document id: {doc_id}. Return only the JSON."
)


# --- pure helpers -----------------------------------------------------------------------------


def graph_to_extraction(graph: Any) -> dict[str, list[dict[str, Any]]]:
    """Map the old engine's typed graph onto the scorer's five categories.

    A node whose type contains "valve" is a valve; instrument-like types are instruments; types
    containing "off_page"/"offpage" are off-page connectors; "pipe" and "fitting" nodes are not
    counted (the DEXPI ground truth counts piping as segments, which are the graph's edges);
    anything else is equipment. Malformed input maps to five empty lists.
    """
    out: dict[str, list[dict[str, Any]]] = {c: [] for c in CATEGORIES}
    if not isinstance(graph, dict):
        return out
    nodes, edges = graph.get("nodes"), graph.get("edges")
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        kind = str(node.get("type") or "").lower()
        item = {"tag": node.get("tag"), "type": node.get("type")}
        if kind in IGNORED_NODE_TYPES:
            continue
        if "valve" in kind:
            out["valves"].append(item)
        elif kind in INSTRUMENT_TYPES:
            out["instruments"].append(item)
        elif "off_page" in kind or "offpage" in kind:
            out["off_page_connectors"].append(item)
        else:
            out["nodes"].append(item)
    out["edges"] = (
        [dict(e) for e in edges if isinstance(e, dict)] if isinstance(edges, list) else []
    )
    return out


def parse_json_object(text: Any) -> dict[str, Any]:
    """Parse a model answer into a JSON object; tolerates a code fence or chatter around it."""
    if isinstance(text, dict):
        return text
    raw = str(text or "").strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    for candidate in (raw, raw[raw.find("{") : raw.rfind("}") + 1]):
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    raise UnparseableOutput("answer is not a JSON object")


# --- drawings ---------------------------------------------------------------------------------


def prepare_drawings(names: list[str]) -> list[Drawing]:
    """Load ground truth and render the SVG to a PNG for the named DEXPI references."""
    refs, message = discover_references()
    if not refs:
        raise FileNotFoundError(message)
    by_name = {r.name: r for r in refs}
    chosen = names or [r.name for r in refs[:DEFAULT_DRAWING_COUNT]]
    unknown = [n for n in chosen if n not in by_name]
    if unknown:
        raise ValueError(f"unknown reference(s) {unknown}; available: {sorted(by_name)}")
    drawings = []
    for name in chosen:
        ref = by_name[name]
        png = svg_to_png(ref.svg, PNG_DIR / f"{name}.png", zoom=2.0)
        drawings.append(Drawing(name, Path(png), load_ground_truth(ref.xml, ref.svg)))
    return drawings


# --- engines ----------------------------------------------------------------------------------


class NewEngineAdapter:
    """The new pydantic-ai engine with the pid-dexpi-digitizer skill (as in the ADE-41 real run)."""

    name = "new"

    def __init__(self) -> None:
        self._doc_ids: dict[Path, str] = {}

    def run(self, image_path: Path, drawing: str) -> dict[str, Any]:
        from pydantic_ai.usage import UsageLimits

        from src.documents.store import get_document_store
        from src.engine import agent as engine_agent

        if image_path not in self._doc_ids:
            self._doc_ids[image_path] = get_document_store().import_document(image_path).doc_id
        doc_id = self._doc_ids[image_path]
        result = engine_agent.build_agent().run_sync(
            NEW_ENGINE_PROMPT.format(doc_id=doc_id),
            deps=engine_agent.ExtractionState(document_id=doc_id, skill_id="pid-dexpi-digitizer"),
            usage_limits=UsageLimits(request_limit=30),
        )
        return parse_json_object(result.output)


class OldEngineAdapter:
    """The old LangGraph engine on its `graph_extraction` P&ID path (mirrors the API run path)."""

    name = "old"

    def __init__(self, ocr_provider: str = "paddle") -> None:
        self.ocr_provider = ocr_provider

    def run(self, image_path: Path, drawing: str) -> dict[str, Any]:
        from src.agent.graph import CircuitBreaker, _build_graph_result, build_react_graph
        from src.api.run_engine import _build_planner_client
        from src.config import settings
        from src.definitions.prebuilt import PREBUILT_DEFINITIONS
        from src.run import build_initial_state, build_tool_registry, build_validator_config
        from src.skills.pid_diagram import PnIDSkill
        from src.templates.pid_diagram import PnIDContract

        tool_names = next(d for d in PREBUILT_DEFINITIONS if d["id"] == "def-pnid-to-dexpi")[
            "tool_names"
        ]
        previous_ocr = settings.ocr_provider
        settings.ocr_provider = self.ocr_provider
        try:
            state = build_initial_state(
                str(image_path), PnIDContract, PnIDSkill, task_type="graph_extraction"
            )
            graph = build_react_graph(
                registry=build_tool_registry(tool_names=tool_names),
                skill=PnIDSkill,
                validator_config=build_validator_config(PnIDSkill),
                llm_client=_build_planner_client(),
                breaker=CircuitBreaker(threshold=3),
            )
            final = graph.invoke(state, config={"recursion_limit": OLD_MAX_CYCLES + 10})
        finally:
            settings.ocr_provider = previous_ocr

        result = final.get("result")
        graph_data = getattr(result, "graph", None)
        if graph_data is None:
            graph_data = _build_graph_result(
                state=final,
                is_complete=False,
                gap_report=None,
                trace=final.get("trace", []),
                total_cycles=final.get("total_cycles", 0),
                status=final.get("status", "partial"),
                provider_errors=final.get("provider_errors", []),
            ).graph
        return graph_to_extraction(graph_data)


def build_engines(names: list[str], old_ocr: str = "paddle") -> list[Engine]:
    adapters: dict[str, Engine] = {"new": NewEngineAdapter(), "old": OldEngineAdapter(old_ocr)}
    return [adapters[n] for n in names]
