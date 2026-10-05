"""REST endpoints for Skills [BLK-020]."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.definitions.store import get_store

router = APIRouter(tags=["skills"])


class ProbeStep(BaseModel):
    """A single probe step in a skill's probe order."""

    region_type: str = Field(description="Region type to probe")
    rationale: str = Field(description="Why this region is probed")


class InvariantSpec(BaseModel):
    """Declarative invariant specification (metadata only, not executable)."""

    name: str = Field(description="Invariant name")
    fields: list[str] = Field(
        default_factory=list, description="Field paths this invariant depends on"
    )
    description: str = Field(default="", description="What this invariant checks")


class CreateSkillRequest(BaseModel):
    """Request body for creating a skill [BLK-121]."""

    id: str = Field(description="Unique skill identifier")
    name: str
    description: str = ""
    system_prompt: str = ""
    tool_preferences: dict[str, str] = Field(default_factory=dict)
    probe_order: list[ProbeStep] = Field(default_factory=list)
    invariants: list[InvariantSpec] = Field(default_factory=list)
    failure_actions: dict[str, str] = Field(default_factory=dict)
    known_failures: str = ""
    confidence_overrides: dict[str, float] = Field(default_factory=dict)
    semantic_checks_enabled: bool = False
    semantic_prompt: str | None = None
    tools: list[str] = Field(default_factory=list)


class UpdateSkillRequest(BaseModel):
    """Request body for updating a skill [BLK-121].

    All fields optional — only provided fields are updated.
    Fields not in the request are preserved.
    """

    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    tool_preferences: dict[str, str] | None = None
    probe_order: list[ProbeStep] | None = None
    invariants: list[InvariantSpec] | None = None
    failure_actions: dict[str, str] | None = None
    known_failures: str | None = None
    confidence_overrides: dict[str, float] | None = None
    semantic_checks_enabled: bool | None = None
    semantic_prompt: str | None = None
    tools: list[str] | None = None


@router.get("/skills")
async def list_skills(
    q: str | None = None,
    tool: str | None = None,
    semantic: bool | None = None,
) -> list[dict[str, Any]]:
    """List all skills with optional search and filters [BLK-061].

    Args:
        q: Search query — case-insensitive substring match on name and description.
        tool: Filter by tool name (checks tools list).
        semantic: Filter by semantic_checks_enabled flag.
    """
    items = get_store().list_skills()

    if q:
        q_lower = q.lower()
        items = [
            s
            for s in items
            if q_lower in s.get("name", "").lower() or q_lower in s.get("description", "").lower()
        ]

    if tool:
        items = [s for s in items if tool in s.get("tools", [])]

    if semantic is not None:
        items = [s for s in items if s.get("semantic_checks_enabled") == semantic]

    return items


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str) -> dict[str, Any]:
    """Get a single skill by ID."""
    try:
        return get_store().get_skill(skill_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")


@router.post("/skills", status_code=status.HTTP_201_CREATED)
async def create_skill(req: CreateSkillRequest) -> dict[str, Any]:
    """Create a new skill."""
    data = req.model_dump()
    try:
        return get_store().create_skill(req.id, data)
    except FileExistsError:
        raise HTTPException(status_code=409, detail=f"Skill '{req.id}' already exists")


@router.put("/skills/{skill_id}")
async def update_skill(skill_id: str, req: UpdateSkillRequest) -> dict[str, Any]:
    """Update an existing skill."""
    store = get_store()
    try:
        existing = store.get_skill(skill_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    update_data = req.model_dump(exclude_none=True)
    existing.update(update_data)
    return store.update_skill(skill_id, existing)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(skill_id: str) -> Response:
    """Delete a skill."""
    try:
        get_store().delete_skill(skill_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")


class VerifySkillRequest(BaseModel):
    """Request body for Surrogate Verifier [BLK-070]."""

    trace: list[dict[str, Any]] = Field(default_factory=list, description="Execution trace entries")
    gap_report: dict[str, Any] = Field(default_factory=dict, description="Gap report from the run")
    extraction: dict[str, Any] = Field(default_factory=dict, description="Extracted field values")


@router.post("/skills/{skill_id}/verify")
async def verify_skill(skill_id: str, req: VerifySkillRequest) -> dict[str, Any]:
    """Run the Surrogate Verifier on a skill [BLK-070].

    Analyzes the skill's execution trace without ground truth and returns
    diagnoses, proposed tests, and skill patches.

    The skill is loaded from the store. The trace, gap_report, and extraction
    are provided by the caller (from a sample run).
    """
    from src.ai.surrogate_verifier import verify_skill as _verify

    store = get_store()
    try:
        skill = store.get_skill(skill_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    result = _verify(
        skill=skill,
        trace=req.trace,
        gap_report=req.gap_report,
        extraction=req.extraction,
    )

    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    return result


class ComposeSkillRequest(BaseModel):
    """Request body for AI Skill Composer [BLK-068]."""

    description: str = Field(
        description="Natural language description of the document type and what to extract"
    )
    sample_fields: list[str] = Field(
        default_factory=list, description="Field names from the template schema"
    )
    sample_document_summary: str | None = Field(
        default=None, description="Optional summary of a sample document"
    )


class CoEvolveSkillRequest(BaseModel):
    """Request body for co-evolution loop [BLK-068, BLK-070]."""

    description: str = Field(description="Natural language description of the document type")
    trace: list[dict[str, Any]] = Field(
        default_factory=list, description="Execution trace from a sample run"
    )
    gap_report: dict[str, Any] = Field(default_factory=dict, description="Gap report from the run")
    extraction: dict[str, Any] = Field(default_factory=dict, description="Extracted field values")
    sample_fields: list[str] = Field(
        default_factory=list, description="Field names from the template schema"
    )
    max_iterations: int = Field(default=3, ge=1, le=10, description="Max co-evolution iterations")


@router.post("/skills/compose")
async def compose_skill(req: ComposeSkillRequest) -> dict[str, Any]:
    """Generate a skill playbook from natural language [BLK-068].

    Uses the AI Skill Composer to produce a candidate skill definition.
    The generated skill is returned for review — not auto-saved.
    """
    from src.ai.skill_composer import generate_skill

    result = generate_skill(
        description=req.description,
        sample_fields=req.sample_fields or None,
        sample_document_summary=req.sample_document_summary,
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/skills/co-evolve")
async def co_evolve_skill(req: CoEvolveSkillRequest) -> dict[str, Any]:
    """Co-evolve a skill with the Surrogate Verifier [BLK-068, BLK-070].

    Runs the generate → verify → patch loop. Returns the final skill
    and iteration history.
    """
    from src.ai.skill_composer import co_evolve_skill as _co_evolve

    result = _co_evolve(
        description=req.description,
        trace=req.trace,
        gap_report=req.gap_report,
        extraction=req.extraction,
        sample_fields=req.sample_fields or None,
        max_iterations=req.max_iterations,
    )

    return result.to_dict()


class OptimizeSkillRequest(BaseModel):
    """Request body for GEPA prompt evolution [BLK-071]."""

    seed_skill: dict[str, Any] = Field(description="The initial skill dict to optimize")
    traces: list[list[dict[str, Any]]] = Field(
        description="List of execution traces (one per sample)"
    )
    gap_reports: list[dict[str, Any]] = Field(description="List of gap reports (one per sample)")
    extractions: list[dict[str, Any]] = Field(
        description="List of extraction dicts (one per sample)"
    )
    max_iterations: int = Field(default=10, ge=1, le=50, description="Max GEPA iterations")
    population_size: int = Field(default=6, ge=2, le=20, description="Max population size")
    merge_probability: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Probability of merge vs mutation"
    )
    convergence_threshold: float = Field(
        default=0.01, ge=0.0, le=1.0, description="Fitness plateau threshold"
    )
    token_usages: list[dict[str, int]] | None = Field(
        default=None, description="Per-sample token usage"
    )
    rng_seed: int | None = Field(default=None, description="Random seed for reproducibility")


@router.post("/skills/optimize")
async def optimize_skill(req: OptimizeSkillRequest) -> dict[str, Any]:
    """Optimize a skill using GEPA reflective prompt evolution [BLK-071].

    Runs the Genetic-Pareto optimization loop: evaluate → reflect → mutate →
    select via Pareto front. Returns the best candidate, full population,
    and iteration history.
    """
    from src.ai.prompt_evolver import optimize_skill as _optimize

    result = _optimize(
        seed_skill=req.seed_skill,
        traces=req.traces,
        gap_reports=req.gap_reports,
        extractions=req.extractions,
        max_iterations=req.max_iterations,
        population_size=req.population_size,
        merge_probability=req.merge_probability,
        convergence_threshold=req.convergence_threshold,
        token_usages=req.token_usages,
        rng_seed=req.rng_seed,
    )

    return result.to_dict()


class OptimizeWorkflowRequest(BaseModel):
    """Request body for MCTS workflow optimization [BLK-072]."""

    seed_workflow: dict[str, Any] | None = Field(
        default=None, description="Seed workflow topology (defaults to standard ReAct)"
    )
    max_iterations: int = Field(default=20, ge=1, le=100, description="Max MCTS iterations")
    convergence_threshold: float = Field(
        default=0.005, ge=0.0, le=1.0, description="Score plateau threshold"
    )
    rng_seed: int | None = Field(default=None, description="Random seed for reproducibility")


@router.post("/workflows/optimize")
async def optimize_workflow(req: OptimizeWorkflowRequest) -> dict[str, Any]:
    """Optimize an agent workflow topology using MCTS [BLK-072].

    Runs AFlow-style Monte Carlo Tree Search over workflow topologies:
    select → expand (LLM) → evaluate → backpropagate.
    Returns the best workflow found and search history.
    """
    from src.ai.workflow_optimizer import WorkflowTopology, optimize_workflow

    seed = WorkflowTopology.from_dict(req.seed_workflow) if req.seed_workflow else None

    result = optimize_workflow(
        seed_workflow=seed,
        max_iterations=req.max_iterations,
        convergence_threshold=req.convergence_threshold,
        rng_seed=req.rng_seed,
    )

    return result.to_dict()


class RewriteSkillRequest(BaseModel):
    """Request body for agentic query rewriting [BLK-073]."""

    definition_id: str = Field(description="Agent definition ID to analyze for rewriting")
    use_llm: bool = Field(default=True, description="Use LLM for decomposition (vs heuristic)")
    min_sample: int = Field(default=5, ge=1, description="Minimum runs to trigger analysis")
    failure_threshold: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Failure rate threshold"
    )


@router.post("/rewrite")
async def rewrite_failing_skill(req: RewriteSkillRequest) -> dict[str, Any]:
    """Rewrite a failing skill into sub-skills using agentic query rewriting [BLK-073].

    Analyzes run history for a definition. If the failure rate exceeds the
    threshold, decomposes the skill into focused sub-skills with validation
    criteria. Returns the rewrite result for review — not auto-saved.

    Uses DocETL-style pipeline decomposition: the LLM analyzes failure patterns
    (gap types, failing fields, cycle consumption) and proposes a decomposition
    that isolates complex fields and groups fields by visual proximity.
    """
    from src.ai.query_rewriter import rewrite_failing_skill as _rewrite

    store = get_store()

    # Get the definition
    try:
        defn = store.get_definition(req.definition_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Definition '{req.definition_id}' not found")

    # Get the skill
    skill_id = defn.get("skill_id") or defn.get("skill_ref", "")
    try:
        skill = store.get_skill(skill_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    # Get runs for this definition
    all_runs = store.list_runs()
    defn_runs = [r for r in all_runs if r.get("definition_id") == req.definition_id]

    if not defn_runs:
        raise HTTPException(
            status_code=400,
            detail=f"No runs found for definition '{req.definition_id}'. Need run history to analyze failures.",
        )

    # Get template fields if available
    template_id = defn.get("template_id") or defn.get("template_ref", "")
    template_fields = None
    try:
        template = store.get_template(template_id)
        template_fields = [f.get("name", "") for f in template.get("fields", [])]
    except FileNotFoundError:
        pass

    result = _rewrite(
        definition_id=req.definition_id,
        runs=defn_runs,
        skill=skill,
        template_fields=template_fields,
        use_llm=req.use_llm,
        min_sample=req.min_sample,
        failure_threshold=req.failure_threshold,
    )

    if result is None:
        return {
            "rewritten": False,
            "message": "No rewriting needed — failure rate below threshold or insufficient runs.",
            "definition_id": req.definition_id,
        }

    return {
        "rewritten": True,
        "definition_id": req.definition_id,
        "failure_pattern": {
            "failure_rate": result.failure_pattern.failure_rate,
            "total_runs": result.failure_pattern.total_runs,
            "failed_runs": result.failure_pattern.failed_runs,
            "gap_type_counts": result.failure_pattern.gap_type_counts,
            "failing_fields": result.failure_pattern.failing_fields,
            "avg_cycles_per_run": result.failure_pattern.avg_cycles_per_run,
        },
        "sub_skills": [
            {
                "name": ss.name,
                "description": ss.description,
                "system_prompt": ss.system_prompt,
                "field_subset": ss.field_subset,
                "probe_order": ss.probe_order,
                "validation_criteria": ss.validation_criteria,
            }
            for ss in result.sub_skills
        ],
        "rewritten_skill": result.rewritten_skill,
        "rationale": result.rationale,
        "estimated_improvement": result.estimated_improvement,
    }


class OneFlowCostEstimateRequest(BaseModel):
    """Request body for OneFlow cost estimation [BLK-074]."""

    num_cycles: int = Field(default=10, ge=1, le=100, description="Expected number of ReAct cycles")
    input_tokens_per_call: int = Field(
        default=3000, ge=1, description="Avg input tokens per LLM call"
    )
    output_tokens_per_call: int = Field(
        default=500, ge=1, description="Avg output tokens per LLM call"
    )


@router.post("/oneflow/estimate")
async def estimate_oneflow_cost(req: OneFlowCostEstimateRequest) -> dict[str, Any]:
    """Estimate cost savings of OneFlow vs standard ReAct mode [BLK-074].

    OneFlow halves the number of LLM calls per cycle by combining
    plan+act and observe+reflect into single nodes, and maximizes
    KV cache reuse by keeping all roles in one context window.
    """
    from src.agent.oneflow import estimate_cost_savings
    from src.config import settings

    return estimate_cost_savings(
        num_cycles=req.num_cycles,
        input_tokens_per_call=req.input_tokens_per_call,
        output_tokens_per_call=req.output_tokens_per_call,
        input_price_per_1k=settings.llm_pricing_input_per_1k,
        output_price_per_1k=settings.llm_pricing_output_per_1k,
    )
