"""The engine loop (ADE-39): a pydantic-ai Agent wiring ADE-34-38 together.

A framework-run tool loop, not a hand-authored LangGraph state machine. The agent plans its own
approach from a thin system prompt (progressive disclosure: skill knowledge is loaded via
load_skill at runtime, never baked into the prompt or scripted via a skill's probe_order).

Every bbox in this module's tools and prompt is pixel-space (x1, y1, x2, y2) — ade's own
convention (src/tools/base.py::BBox), carried through from ADE-38's survey_layout/survey_region/
crop_and_read.
This differs from ade2's reference design, which used bare normalized [ymin, xmin, ymax, xmax]
floats; ADE-38 already converts to pixel space before returning, so the agent must ask for and
receive pixel coordinates throughout, never normalized ones.

to_dexpi_xml/to_spice_netlist are clean stubs: ade has no real DEXPI 1.3/Proteus or SPICE
serializer yet (ADE-14, ADE-16 respectively). They return a structured "not available" result,
never an exception and never a fabricated XML/netlist string.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model

from src.config import settings
from src.documents.store import get_document_store
from src.engine import skills as engine_skills
from src.engine import tools as engine_tools
from src.engine import validation as engine_validation
from src.engine.budget import BudgetTracker

logger = logging.getLogger(__name__)


# --- Extraction state (passed as deps to the agent) -----------------------------------------------


@dataclass
class ExtractionState:
    """Mutable state for a single extraction run, accessed by tools via ctx.deps.

    todo tracks the agent's own plan (update_plan), validations accumulates every
    validate_extraction result, and budget lets the agent reason about remaining turns/cost/time.
    """

    document_id: str = ""
    skill_id: str = ""
    todo: list[dict[str, str]] = field(default_factory=list)
    validations: list[dict[str, Any]] = field(default_factory=list)
    budget: BudgetTracker = field(default_factory=BudgetTracker)


# --- Thin system prompt (progressive disclosure) ----------------------------------------------
# The agent plans its own approach. Skill knowledge is injected via load_skill at runtime, never
# baked into this prompt - and never a skill's probe_order, which stays knowledge, not a script
# (ADE-12's rule, carried through ADE-34's Skill.to_prompt_block).

SYSTEM_PROMPT = """\
You are an autonomous engineering document agent.

You extract structured data from engineering documents - drawings, schematics, schedules,
datasheets, forms - using vision tools to survey and read pages.

## Tools

**Perception**
- list_document_pages(document_id) - page count and per-page dimensions
- survey_layout_tool(document_id, page_num) - semantic zones with pixel-space bounding boxes
  (x1, y1, x2, y2)
- survey_region_tool(document_id, bbox_pixel, page_num) - re-survey a sub-region at native
  resolution to find dense symbols (valves, instruments) too small in the top-level survey. Use
  after survey_layout_tool identifies piping runs, or when validate_extraction warns about thin
  counts. bbox_pixel is in the same pixel space survey_layout_tool returned.
- crop_and_read_tool(document_id, bbox_pixel, question_or_task, page_num) - native-resolution
  pixel-space crop + VLM query
- ocr_page_tool(document_id, page_num) - raw text extraction

**Planning**
- update_plan(tasks) - create or update your task list. Each task: {description, status:
  "pending"|"in_progress"|"completed"}. Call this at the start to plan, and update it as you work.

**Budget**
- budget_status() - check your remaining turns, cost, and time. FREE (costs no turns). Call it
  after survey_layout_tool to plan how many crops you can afford, and again when running low. The
  recommendations tell you when to batch crops and when to stop and serialize.

**Verification**
- validate_extraction(data) - check your data against the schema, skill invariants, and
  completeness/thinness heuristics. Runs locally, costs nothing, and tells you what is missing.

**Serialization**
- to_dexpi_xml(data) - serialize P&ID graph data to DEXPI XML, when available
- to_spice_netlist(data) - serialize circuit data to a SPICE netlist, when available

**Skill discovery** (when no skill is pre-selected)
- list_skills() - available domain skills with visual cues
- load_skill(skill_id) - full skill knowledge: hints, invariants, output schema

## How to work

1. Plan. What document is this? What needs extracting? Call update_plan with your task list.
2. Survey. Call survey_layout_tool to get a page overview with pixel-space zones.
3. Check budget. Call budget_status to see how many crops you can afford.
4. Re-survey dense regions. For each dense zone, call survey_region_tool for a high-resolution
   symbol inventory.
5. Read efficiently. For each element found, call crop_and_read_tool. When turns are limited, crop
   WIDER regions covering multiple symbols in one call rather than cropping each individually.
6. Adapt. If a crop returns incomplete data, re-crop or survey_region_tool the area. Check budget
   periodically.
7. Validate early. Call validate_extraction BEFORE serializing. Fix what it reports if you have
   budget left; serialize what you have if budget is nearly exhausted.
8. Serialize. Call to_dexpi_xml or to_spice_netlist and include the result in your output.
9. Validate final. Call validate_extraction one more time.
10. Return. Provide the final structured output as JSON matching the schema. Return ONLY valid
    JSON.

If a skill was provided, use its knowledge (visual cues, invariants, schema) to inform your plan -
but adapt based on what you actually see in the document. Skills describe what to look for, not a
script to follow.
"""


def _build_model() -> Model:
    """Build the real model for the active provider (OpenAI or Azure OpenAI) [ADE-41].

    Mirrors the client wiring in src/providers/vlm_azure.py so the agent and its perception
    tools always talk to the same provider. Never logs a key or an endpoint.
    """
    from pydantic_ai.models.openai import OpenAIChatModel

    if settings.active_llm_provider == "openai":
        from pydantic_ai.providers.openai import OpenAIProvider

        logger.info("Building engine agent model: provider=openai, model=%s", settings.chat_model)
        return OpenAIChatModel(
            settings.chat_model, provider=OpenAIProvider(api_key=settings.openai_api_key)
        )

    from pydantic_ai.providers.azure import AzureProvider

    logger.info("Building engine agent model: provider=azure, deployment=%s", settings.chat_model)
    provider = AzureProvider(
        azure_endpoint=settings.azure_chat_endpoint,
        api_key=settings.azure_api_key,
        api_version="2024-02-15-preview",
    )
    return OpenAIChatModel(settings.chat_model, provider=provider)


def build_agent(model: Model | None = None) -> Agent:
    """Build the engine agent. Pass model= to inject a TestModel/FunctionModel for hermetic tests.

    When model is None, builds the real model for the active provider from settings (lazy: never
    happens at import time, so this module is importable with no credentials set at all).
    """
    agent: Agent = Agent(
        model if model is not None else _build_model(),
        system_prompt=SYSTEM_PROMPT,
        output_type=str,
        deps_type=ExtractionState,
        retries=2,
    )

    # --- Perception tools ---

    @agent.tool
    def list_document_pages(ctx: RunContext[ExtractionState], document_id: str) -> dict[str, Any]:
        """List all pages in a document with metadata (page count, per-page dimensions)."""
        ctx.deps.budget.record_tool("list_document_pages")
        try:
            return get_document_store().get_document(document_id)
        except (FileNotFoundError, ValueError) as exc:
            return {"error": str(exc)}

    @agent.tool
    def survey_layout_tool(
        ctx: RunContext[ExtractionState], document_id: str, page_num: int = 1
    ) -> dict[str, Any]:
        """Survey a page for semantic zones. Returns pixel-space bboxes (x1, y1, x2, y2)."""
        ctx.deps.budget.record_tool("survey_layout_tool")
        return engine_tools.survey_layout(document_id, page_num)

    @agent.tool
    def survey_region_tool(
        ctx: RunContext[ExtractionState],
        document_id: str,
        bbox_pixel: tuple[int, int, int, int],
        page_num: int = 1,
    ) -> dict[str, Any]:
        """Re-survey a pixel-space sub-region at native resolution for dense symbols."""
        ctx.deps.budget.record_tool("survey_region_tool")
        return engine_tools.survey_region(document_id, bbox_pixel, page_num)

    @agent.tool
    def crop_and_read_tool(
        ctx: RunContext[ExtractionState],
        document_id: str,
        bbox_pixel: tuple[int, int, int, int],
        question_or_task: str,
        page_num: int = 1,
    ) -> dict[str, Any]:
        """Crop a pixel-space sub-region at native resolution and query the VLM about it."""
        ctx.deps.budget.record_tool("crop_and_read_tool")
        return engine_tools.crop_and_read(document_id, bbox_pixel, question_or_task, page_num)

    @agent.tool
    def ocr_page_tool(
        ctx: RunContext[ExtractionState], document_id: str, page_num: int = 1
    ) -> dict[str, Any]:
        """Run OCR to extract raw text from a document page."""
        ctx.deps.budget.record_tool("ocr_page_tool")
        return engine_tools.ocr_page(document_id, page_num)

    # --- Budget tool (free) ---

    @agent.tool
    def budget_status(ctx: RunContext[ExtractionState]) -> dict[str, Any]:
        """Check remaining budget (turns, cost, time) and get strategic recommendations. FREE."""
        return ctx.deps.budget.status()

    # --- Planning tool (free) ---

    @agent.tool
    def update_plan(
        ctx: RunContext[ExtractionState], tasks: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Create or update the task list for this extraction."""
        ctx.deps.budget.record_tool("update_plan")
        ctx.deps.todo = tasks
        pending = sum(1 for t in tasks if t.get("status") == "pending")
        in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        return {
            "plan": tasks,
            "summary": f"{completed} completed, {in_progress} in progress, {pending} pending",
        }

    # --- Verification tool (free) ---

    @agent.tool
    def validate_extraction(
        ctx: RunContext[ExtractionState], data: dict[str, Any]
    ) -> dict[str, Any]:
        """Check extracted data against the schema, invariants, and completeness heuristics."""
        ctx.deps.budget.record_tool("validate_extraction")
        errors: list[str] = []
        warnings: list[str] = []
        result: dict[str, Any] = {}

        skill = engine_skills.load_skill(ctx.deps.skill_id) if ctx.deps.skill_id else None

        if skill and skill.schema:
            import json

            schema_result = engine_validation.validate_output(
                json.dumps(data, default=str), skill.schema
            )
            errors.extend(schema_result["errors"])
            result["schema_checked"] = True

        if skill and skill.invariants:
            inv = engine_validation.validate_invariants(data, skill.invariants)
            errors.extend(f"{v['name']}: {v['message']}" for v in inv["violated"])
            result["invariants_passed"] = inv["checked"]
            result["invariants_unchecked"] = inv["could_not_check"]
            if inv["could_not_check"]:
                warnings.append(
                    f"{len(inv['could_not_check'])} invariant(s) could not be checked: "
                    f"{', '.join(inv['could_not_check'])}. Confirm these yourself."
                )

        pid_collections = ("nodes", "valves", "instruments", "edges", "off_page_connectors")
        for key in pid_collections:
            if key in data and not data.get(key):
                errors.append(
                    f"'{key}' is empty - survey and crop the drawing again to find {key}. "
                    "A P&ID with zero of these is almost certainly incomplete."
                )
        counts = {k: len(v) for k, v in data.items() if isinstance(v, list)}
        result["counts"] = counts

        eq_count = counts.get("nodes", 0)
        valve_count = counts.get("valves", 0)
        edge_count = counts.get("edges", 0)
        if eq_count > 0 and valve_count > 0 and valve_count < eq_count:
            warnings.append(
                f"Only {valve_count} valve(s) for {eq_count} equipment item(s) - P&IDs typically "
                "have several valves per equipment. Crop along the pipe lines."
            )
        if eq_count > 0 and edge_count > 0 and edge_count < eq_count * 2:
            warnings.append(
                f"Only {edge_count} edge(s) for {eq_count} equipment item(s) - each equipment "
                "item usually connects to multiple pipes."
            )

        xml_str = data.get("dexpi_xml")
        if xml_str:
            try:
                ET.fromstring(xml_str)
                result["dexpi"] = {"valid": True}
            except ET.ParseError as exc:
                errors.append(f"dexpi_xml is not well-formed XML: {exc}")
                result["dexpi"] = {"valid": False}
        elif skill and skill.modality == "graph_digitization":
            warnings.append("No dexpi_xml yet - call to_dexpi_xml and include its output.")

        result["valid"] = not errors
        result["errors"] = errors
        result["warnings"] = warnings
        if errors:
            result["guidance"] = (
                "Extraction is NOT complete. Fix the errors above, usually by cropping the "
                "regions you have not read yet, then call validate_extraction again."
            )

        ctx.deps.validations.append(result)
        logger.info(
            "validate_extraction: valid=%s errors=%d warnings=%d",
            result["valid"],
            len(errors),
            len(warnings),
        )
        return result

    # --- Serialization tools (clean stubs pending ADE-14 / ADE-16) ---

    @agent.tool
    def to_dexpi_xml(ctx: RunContext[ExtractionState], data: dict[str, Any]) -> dict[str, Any]:
        """Serialize P&ID graph data to DEXPI XML. Not available yet (ADE-14)."""
        ctx.deps.budget.record_tool("to_dexpi_xml")
        return {"error": "DEXPI serialization is not available yet (ADE-14)", "dexpi_xml": None}

    @agent.tool
    def to_spice_netlist(ctx: RunContext[ExtractionState], data: dict[str, Any]) -> dict[str, Any]:
        """Serialize circuit data to a SPICE netlist. Not available yet (ADE-16)."""
        ctx.deps.budget.record_tool("to_spice_netlist")
        return {"error": "SPICE serialization is not available yet (ADE-16)", "spice_netlist": None}

    # --- Skill discovery tools (tool_plain: no state, no budget cost) ---

    @agent.tool_plain
    def list_skills() -> list[dict]:
        """Discover available domain skills (id, name, description, visual cues)."""
        return engine_skills.list_skills()

    @agent.tool_plain
    def load_skill(skill_id: str) -> dict[str, Any]:
        """Load a skill's full knowledge (hints, invariants, schema) by id."""
        skill = engine_skills.load_skill(skill_id)
        if skill is None:
            return {"error": f"Skill '{skill_id}' not found"}
        return skill.to_dict()

    return agent
