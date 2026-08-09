# Vision: Agentic Document Extraction Platform (ADEP)

> A composable platform where **agent definitions** are assembled from
> interchangeable bricks — agent runtime, tools, skills, templates — and users
> instantiate them via a chat interface to solve real extraction tasks.
> Document extraction is the first domain; the platform is the product.

---

## 0. The Platform Concept

ADEP is not a single-purpose extraction engine. It is a **platform** where
four types of Lego bricks snap together to define an agent for a particular
class of task:

| Brick           | What it is                                          | Example                              |
|-----------------|-----------------------------------------------------|--------------------------------------|
| **Agent**       | The runtime loop (ReAct) + LLM + state model        | LangGraph ReAct loop with GPT-5.4    |
| **Tools**       | Atomic, stateless capabilities the agent may call   | `ocr`, `crop`, `detect_layout`, ...  |
| **Skills**      | Domain playbooks: prompt, tool prefs, probe order,  | `InvoiceSkill`, `UtilityBillSkill`   |
|                 | invariants, failure actions                         |                                      |
| **Templates**   | Outcome contracts: Pydantic schemas declaring what  | `InvoiceTemplate`, `BankStatement`   |
|                 | a valid result looks like                           |                                      |

### 0.1 Agent Definition → Instance

An **Agent Definition** is a named, versioned composition of these bricks:

```
AgentDefinition {
  name:         "Invoice Extractor"
  agent:        ReAct (LangGraph, GPT-5.4)
  tools:        [detect_layout, crop, ocr, vlm, ground, verify, ...]
  skill:        InvoiceSkill
  template:     InvoiceTemplate
}
```

A **Run Instance** is a live invocation of a definition against a concrete
input (a document, a chat session, a batch). The definition is the blueprint;
the instance is the execution.

### 0.2 User-Facing Surfaces — 3-Pane Workbench

The platform is a **local-first workbench** — a single app running on your
laptop, not a cloud SaaS. The primary UI is a 3-pane layout designed for
interactive document extraction with pixel-grounded verification:

```
+-----------------------------------------------------------------------------------+
|  [Sidebar]  | Pane 1: Agent Console | Pane 2: Extracted Data | Pane 3: Document |
|  Collapsible| (Reasoning Trace      | (Field Cards / JSON    | (PDF/Image + BBox |
|  Definitions|  Tool Calls, Results) |  Tree View, Toggleable)|  Overlay Highlight) |
+-------------+-----------------------+------------------------+-------------------+
```

- **Pane 1 — Agent Console** (consumption): streams the agent's ReAct loop
  in real time — thoughts, tool calls (with inline thumbnails for crop
  results), observations, and a field-completion progress bar. This is the
  Devin/Windsurf-style reasoning trace, not a plain text stream.
  Independent vertical scrollbar; sticky header with Compact button and
  progress bar.
- **Pane 2 — Extracted Data** (outcome view): toggleable between a **Field
  Card Grid** (each field shows value, confidence badge, status, and
  grounding link) and an **editable JSON/Form view** for human-in-the-loop
  corrections. Clicking a field card fires `setActiveBBox(bbox, page)` to
  highlight the source in Pane 3. Independent vertical scrollbar; sticky
  header with view toggle.
- **Pane 3 — Document Viewer** (grounding): renders the input PDF or image
  with an SVG overlay layer for bounding boxes. Clicking a bbox scrolls
  Pane 2 to the corresponding field. Bidirectional click-to-highlight
  linking between Pane 2 and Pane 3. **Page navigation toolbar** (`<` `>`
  buttons + "Page X of N" indicator) for multi-page documents — clicking
  a field in Pane 2 auto-navigates to the correct page. Independent
  vertical and horizontal scrollbars; sticky toolbar with page nav and
  zoom controls.
- **Sidebar** (navigation): collapsible list of agent definitions, skill
  editor, template editor, and definition builder — the configuration
  layer accessible but not dominant.
- **Skill Editor** (sidebar → modal/page): structured form for creating,
  editing, and cloning skills — prompts, tool preferences, probe order,
  invariants, failure actions, optional semantic checks toggle.
- **Template Editor** (sidebar → modal/page): schema builder UI for
  defining fields, types, descriptions, constraints, and confidence
  thresholds.
- **Agent Definition Builder** (sidebar → wizard): compose an agent
  definition by selecting skill + template + tools + agent runtime.
  Uses **card-based selectors** (not dropdowns) — each skill and template
  shows a rich preview card with description, tool list, field count, and
  key fields so users can compare options at a glance, similar to
  Instagram filter thumbnails or VS Code extension picker.

The 3-pane layout is the v1 consumption surface. The editors are the v1
configuration surface. Both live in the same app — no separate admin panel.

### 0.3 Why a Platform, Not a Pipeline

A pipeline hardcodes the flow for one document type. A platform lets users
**define new extraction agents without writing engine code**. The litmus test:
a user can onboard a new document type through the UI alone — creating a
template, authoring a skill, composing an agent definition, and running it —
without touching Python.

---

## 1. The Problem We Are Not Solving

We are **not** building another document-to-markdown converter.

Markdown is a lossy intermediate. It flattens layout, destroys spatial
relationships, mangles tables, and silently drops everything OCR cannot read —
charts, signatures, stamps, handwriting, infographics, logos. Treating markdown
as the goal forces every downstream task to re-derive structure that was already
present in the pixels.

The real job is **information extraction**: given a document and a declaration of
what we want out of it, produce a structured object whose every field is

1. **correct**,
2. **grounded** to the pixels it came from (a bounding box), and
3. **verifiable** (confidence + provenance trace).

Markdown and OCR text are *signals the agent may use*, never the deliverable.

---

## 2. Core Principles

### 2.1 Outcome-Based, Not Process-Based

The user declares **what** they want (a schema), never **how** to get it. The
agent owns the plan: which regions matter, which tools to run, in what order,
when to retry, when to escalate from OCR to VLM, when to stop.

```
Input:  document image  +  outcome schema (Pydantic)
Output: schema instance  +  grounding  +  confidence  +  trace
```

### 2.2 The Agent Is the Orchestrator

A **ReAct loop** sits at the center:

```
Reason  ->  Act (call one atomic tool)  ->  Observe  ->  Reflect  ->  repeat
```

- **Reason**: given the current state of the partial extraction, what is the
  next most useful action? Which field is still empty? Which value is
  low-confidence? Which region have we not looked at?
- **Act**: invoke exactly one atomic tool with explicit parameters.
- **Observe**: tool returns structured data (text, bbox, confidence, image).
- **Reflect**: is the outcome schema satisfied? Are values grounded and
  consistent? Do confidence thresholds pass? Should we crop deeper, deskew,
  re-ask the VLM with a sharper question, or switch modality? Reflection is
  **pragmatic-first**: the Outcome Validator runs code checks where they're
  cheap and reliable (presence, type/format, math invariants, grounding,
  thresholds) and emits a structured `GapReport`. For semantic or contextual
  checks that code can't handle, the LLM may be consulted with structured
  prompts — but the default is code, not vibes. See §4.1.
- **Terminate**: return the filled schema with provenance, or — on give-up — a
  partial result with explicit gaps (which fields failed and why). See §2.6.

The agent is **not** a fixed pipeline. It adapts per document, per field, per
failure mode — exactly the failure modes L2 exposed (garbled exponents,
misaligned columns, handwriting, thermal-printed receipts).

### 2.3 Atomic, Image-Centric Tools

Every tool does **one** thing and declares its inputs explicitly. Tools are
stateless, composable, and swappable. The agent chains them: `detect_layout` →
`crop` → `rotate` → `ocr` (or `vlm`) → `ground`.

| Category        | Tool                          | Inputs                                  | Output                                    |
|-----------------|-------------------------------|-----------------------------------------|-------------------------------------------|
| Perception      | `detect_layout`               | image                                   | regions[] {type, bbox, confidence}        |
|                 | `detect_text`                 | image, lang?                            | boxes[] {text, bbox, score}               |
|                 | `detect_tables`               | image                                   | tables[] {bbox, cells?}                   |
|                 | `detect_figures`              | image                                   | figures[] {bbox, type}                    |
|                 | `detect_signatures`           | image                                   | sigs[] {bbox, present}                    |
| Geometry        | `crop`                        | image, bbox                             | image                                     |
|                 | `deskew`                      | image                                   | image, angle_applied (auto-estimated)     |
|                 | `auto_orient`                 | image                                   | image, rotation (auto-estimated)          |
|                 | `rotate`                      | image, angle                            | image (agent-supplied; deliberate only)   |
|                 | `resize`                      | image, scale                            | image                                     |
|                 | `denoise` / `threshold`       | image                                   | image                                     |
| Reading         | `ocr`                         | image, lang?, engine?                   | text + boxes + scores                     |
|                 | `vlm`                         | image, question, model?                 | answer (text or structured)               |
|                 | `read_table`                  | image                                   | rows[][] (structured cells)               |
|                 | `read_chart`                  | image, question?                        | series[] / value                          |
| Grounding       | `locate`                      | image, query                            | bbox                                      |
|                 | `ground`                      | image, value                            | bbox (trace a value to its pixels)        |
| Verification    | `verify`                      | field, value, evidence                  | {ok, reason, confidence}                  |
|                 | `cross_check`                 | field_a, field_b, rule                  | {ok, reason}                              |

**Why atomic?** So the agent can recover. If `ocr` garbles a table cell, the
agent can `crop` that cell, `deskew` it, and re-run `ocr` — or abandon OCR and
ask `vlm` directly. Monolithic tools cannot be rescued mid-flight.

**The geometry trap, avoided.** An LLM cannot perceive a 12° skew to pass
`angle=12`. So geometry tools split by *who computes the parameter*:
`deskew`/`auto_orient` estimate the angle themselves (Hough/minAreaRect, or the
layout/OCR model) and the agent passes nothing. `rotate(image, angle)` is the
only geometry tool that takes an agent-supplied angle, reserved for deliberate
cases where the agent has a reason ("this stamp region is upside down → 180").
The common path is auto-estimating; agent-supplied geometry is the exception.

### 2.4 VLM-First Where OCR Fails

OCR is one perception signal among several. For charts, signatures, stamps,
handwriting, infographics, and low-quality scans, the VLM is the **primary**
reader and OCR is the fallback — the inverse of the L2-era assumption. The agent
picks the modality per region, per field.

### 2.5 Grounding Is Non-Negotiable

Every extracted value carries a bounding box back to the source pixels. No
grounding, no value. This is what makes extraction **auditable** and is the
single biggest lesson from L8/L9 (chunk IDs, source location references).
Grounding is also what enables `verify` and `cross_check` to operate on
evidence rather than on the agent's assertion.

### 2.6 Give-Up Threshold and Partial Results

Agentic loops are prone to excessive tool-call recursion when confused or when
the source document is simply illegible. Two hard caps, enforced by the graph:

- **Per-field cycle cap** — max ReAct attempts dedicated to one field.
- **Per-document cycle cap** — max total ReAct attempts across the run.

On exhaustion, the run **terminates with a partial result and explicit gaps**
(which fields failed, why, and the last evidence seen) — never an infinite
loop and never a fabricated fill. A failed extraction is a structured object,
not an exception. This is agentic hygiene, not a feature, and it is what makes
the system safe to put behind an API.

### 2.7 Provider Failure and Error Propagation

Tools call external providers (OCR engines, VLM APIs, image libraries). These
fail — network timeouts, rate limits, corrupt images, unexpected formats.
The error propagation model is simple and explicit:

1. **Tool errors are structured, not exceptions.** A tool returns
   `ToolResult(ok=False, error=<structured message>)`. The agent sees the
   error in the `observe` step, not a stack trace.
2. **Retry with backoff at the tool level** [EH]. The tool function itself
   retries transient failures (429, timeout) with exponential backoff via
   tenacity. The agent never sees transient failures — only persistent ones.
3. **Per-tool failure cap.** If the same tool fails N times on the same input
   (same region, same args), the tool returns a terminal `ToolResult(ok=False,
   error="persistent_failure")`. The agent's `reflect` node sees this and the
   Skill's failure-actions table guides the next move: switch modality (ocr →
   vlm), re-crop with different parameters, or mark the field as failed.
4. **Provider-level circuit breaker.** If a provider (e.g. Azure VLM) fails
   repeatedly across multiple calls in a single run, the Run Engine trips a
   circuit breaker — subsequent calls to that provider return immediately with
   a `provider_unavailable` error. The agent can fall back to an alternative
   provider if one is configured, or terminate with gaps. The circuit resets
   on the next run.
5. **No silent failures.** Every tool error is logged with context (tool name,
   args, provider, error type) and appears in the trace. The final
   `ExtractedResult` includes a `provider_errors` list for debugging.

The principle: **the agent should never be surprised by the same error twice
in the same run.** If a tool failed on this region, the trace carries that
failure so the `plan` node doesn't route the agent back into the same dead end.

### 2.8 State Carries Handles, Not Pixels

The single most important `State` rule, baked in from v1: **`State` stores
image *handles* (paths/IDs), never base64 blobs.** Only the specific tool
invocation receives the cropped pixels it needs. The LLM context carries the
*region index* (id, page, type, bbox, text-snippet, confidence) and the
`GapReport` — never the images. Get this right in the Invoice slice and it
scales to hundreds of pages; get it wrong and v2 is a rewrite. See §12.

---

## 3. The Four Bricks: Templates, Skills, Tools, and Agent Runtime

Four layers, cleanly separated. This is the heart of "composable platform" —
each brick is independently creatable, editable, and swappable.

### 3.1 Template — the outcome contract

A **Template** is a declarative extraction spec: a Pydantic schema with field
descriptions, types, constraints, and confidence thresholds. It is
**document-agnostic**. It says *what* a valid result looks like, nothing about
*how* to obtain it.

```python
class InvoiceTemplate(BaseModel):
    invoice_number: str   = Field(description="Vendor invoice ID")
    invoice_date:  str    = Field(description="Issue date, ISO YYYY-MM-DD")
    vendor:        str    = Field(description="Issuing company name")
    line_items:    list[LineItem]
    subtotal:      float
    tax:           float
    total:         float
    # threshold: every field must be grounded + confidence >= 0.8
```

### 3.2 Skill — the know-how for a document archetype

A **Skill** is a reusable playbook for a document *type* (invoice, pay stub,
W-2, utility bill, ID, bank statement, loan package...). It bundles:

- a **system prompt** framing the agent for that archetype,
- **tool preferences** (e.g. "prefer `vlm` for the usage-history chart; prefer
  `ocr` for the tabular charges"),
- **probe order** (which regions to look at first),
- **verification rules** (e.g. "subtotal + tax == total ± 0.01"),
- **failure actions** — an explicit table mapping deterministic `GapReport`
  failures to candidate actions (e.g. "math invariant fails → re-crop the
  totals band and re-run `vlm`"; "`tax` confidence < 0.8 → re-crop totals
  band, `deskew`, re-ask `vlm`"). The `plan` node consumes this table
  alongside the `GapReport`; the mapping is document-type-specific and lives
  in the Skill, never in the engine.
- **known failure modes** and recovery hints (e.g. "thermal receipts: deskew
  before ocr").

A Skill is **not** a fixed pipeline — it is advice the agent may follow or
override based on what it observes. Skills compose with any Template.

### 3.3 Agent Runtime — the ReAct loop

The **Agent Runtime** is the execution engine: a ReAct loop (LangGraph) that
reasons, acts, observes, reflects, and terminates. It is **task-agnostic** —
it knows nothing about invoices or documents specifically. It receives an
Agent Definition (skill + template + tool set) and a document, and it runs.

The runtime is the same regardless of document type. Swapping the LLM (e.g.
GPT-5.4 → a future model) is a config change, not a code change.

### 3.4 Agent Definition — the composition

An **Agent Definition** binds the four bricks into a named, reusable unit:

```
AgentDefinition {
  name:       "Invoice Extractor"
  version:    "1.0.0"
  agent:      ReAct (LangGraph, GPT-5.4 via Azure)
  tools:      [detect_layout, crop, ocr, vlm, ground, verify, ...]
  skill:      InvoiceSkill
  template:   InvoiceTemplate
}
```

Agent Definitions are the **platform's product**. They are what users browse,
select, and instantiate. They are also what users create through the Agent
Definition Builder UI.

### 3.5 Run Instance — Definition + Input

```
run(definition, input) -> ExtractedResult
```

A run instantiates the agent definition against a concrete input (a document,
a chat session, a batch). The output is the filled schema plus grounding,
confidence, and a full trace of tool calls for debugging and evaluation.
In v1, the input is a single document image and the interface is chat.

---

## 4. Platform Architecture

```
  ┌──────────────────────────────────────────────────────┐
  │                     Frontend                          │
  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │
  │  │   Chat    │  │  Skill   │  │  Template        │    │
  │  │ Interface │  │  Editor  │  │  Editor          │    │
  │  └─────┬─────┘  └────┬─────┘  └───────┬──────────┘    │
  │        │              │                │                │
  │        └──────────────┴────────────────┘                │
  │                        │                               │
  │              ┌─────────v──────────┐                    │
  │              │  Agent Definition  │                    │
  │              │     Builder        │                    │
  │              └─────────┬──────────┘                    │
  └────────────────────────┼──────────────────────────────┘
                           │  REST / SSE
  ┌────────────────────────┼──────────────────────────────┐
  │                   Backend (src/)                       │
  │                        │                               │
  │  ┌─────────────────────v──────────────────────────┐   │
  │  │              API Layer (FastAPI)                │   │
  │  │  /definitions  /skills  /templates  /runs      │   │
  │  │  SSE: /runs/{id}/stream                        │   │
  │  └─────────────────────┬──────────────────────────┘   │
  │                        │                               │
  │  ┌─────────────────────v──────────────────────────┐   │
  │  │            Agent Definition Store               │   │
  │  │  (.adep/ folder: JSON files on disk)            │   │
  │  └─────────────────────┬──────────────────────────┘   │
  │                        │                               │
  │  ┌─────────────────────v──────────────────────────┐   │
  │  │              Run Engine                         │   │
  │  │   run(definition, input) -> ExtractedResult     │   │
  │  └─────────────────────┬──────────────────────────┘   │
  │                        │                               │
  │  ┌─────────────────────v──────────────────────────┐   │
  │  │            ReAct Agent (LangGraph)              │   │
  │  │    reason / act / observe / reflect / end       │   │
  │  └──+──────────────────────────────────+──────────┘   │
  │     │                                  │               │
  │  ┌──v──────────┐              ┌────────v──────────┐    │
  │  │ Tool Registry│              │ Outcome Validator  │    │
  │  │ (pluggable)  │              │ (pragmatic)        │    │
  │  └──+──────────┘              └───────────────────┘    │
  │     │                                                    │
  │  ┌──v──────────────────────────────────────────────┐   │
  │  │  Providers (swappable)                           │   │
  │  │   ocr:   paddle / tesseract / cloud              │   │
  │  │   vlm:   azure (gpt-5.4) / openai / local        │   │
  │  │   layout: paddle / detectron2 / cloud            │   │
  │  │   image: PIL + OpenCV                            │   │
  │  └──────────────────────────────────────────────────┘   │
  └────────────────────────────────────────────────────────┘
```

- **Frontend**: Chat interface for consumption; Skill/Template editors for
  authoring; Agent Definition Builder for composition. All three communicate
  with the backend via REST + SSE (for streaming agent reasoning).
- **API Layer (FastAPI)**: REST endpoints for CRUD on definitions, skills,
  templates; SSE for streaming run progress to the Agent Console.
- **Agent Definition Store**: persists definitions, skills, and templates.
  v1 uses file-based storage (JSON/YAML on disk); database migration in
  Phase 5 (BLK-036).
- **Run Engine**: instantiates an Agent Definition into a live ReAct run.
- **Tool Registry**: tools register with explicit schemas; the agent sees only
  tool names + arg schemas + descriptions (LangChain `@tool` style).
- **Providers are swappable**: same `ocr` tool, different backends. Same `vlm`
  tool, different models. No vendor lock-in (per [FP]).
- **Outcome Validator** closes the loop: pragmatic gap-report generator
  (see §4.1). Code checks first, LLM where it adds value.

### 4.1 Outcome Validator — pragmatic-first

The validator is the linchpin of the loop. The principle: **use code checks
where they're cheap and reliable, use the LLM where it adds real value, and
don't build more than you need.** The validator runs checks in order:

1. **Required-field presence** — schema-driven; code.
2. **Type/format checks** — ISO date regex, numeric, enum membership; code.
3. **Math invariants** — declared in the Skill (e.g.
   `subtotal + tax == total ± 0.01`); pure arithmetic; code.
4. **Grounding presence** — every value has a bbox; code.
5. **Confidence ≥ threshold** — per-field, from the Template; code.
6. **Semantic checks** (optional, per-Skill) — e.g. "is this vendor name
   plausible given the document context?" These are LLM-assisted, structured
   prompts with the candidate value + evidence snippet. The LLM returns a
   structured verdict, not free text. Skills decide whether to enable these;
   the default is off. Don't build semantic checks until a real document type
   proves they're needed [SF].

The validator returns a structured `GapReport` (missing / failed / ungrounded
/ low-confidence / semantic-fail fields) that the `reflect` node maps to the
next action. Code first, LLM second, vibes never.

---

## 5. What Makes This Different

| Approach               | This platform                                 |
|------------------------|-----------------------------------------------|
| Doc-to-markdown (L2)   | Outcome-based extraction; md is a signal only |
| Fixed OCR pipeline     | Adaptive ReAct agent that recovers from fails |
| Monolithic ADE API (L8)| Open, composable, swappable, self-hostable    |
| One-shot VLM prompting | Atomic tools + grounding + verification loop  |
| Hand-written regex     | Schema-driven; LLM reasons, tools perceive    |
| Closed-box SaaS extract| User-defined agents via UI; own your skills    |
| Single-purpose engine  | Platform: compose bricks → define → instantiate|

---

## 6. Non-Goals (for now)

- Not a general-purpose document chatbot — the chat interface is for
  consumption of defined extraction agents, not free-form Q&A.
- Not a full document parsing/layout engine from scratch — we wrap existing
  OCR/layout/VLM providers behind atomic tool interfaces.
- Not multi-document orchestration in v1 (L9's loan-pipeline cross-doc
  validation is a v2 concern; v1 nails single-document extraction).
- Not a marketplace or multi-tenant SaaS in v1 — single-user, self-hosted.
  Multi-tenancy is a v3 consideration if the platform proves out.

---

## 7. Success Criteria

A v1 win looks like:

### 7.1 Engine (extraction core)

1. Define an `InvoiceTemplate` (Pydantic) + `InvoiceSkill`.
2. Point the run at `invoice.png`.
3. The agent, unaided, calls `detect_layout`, crops the relevant bands, runs
   `ocr` (and `vlm` where needed), grounds every value, cross-checks
   `subtotal + tax == total ± 0.01` via the deterministic validator, and
   returns a validated `InvoiceTemplate` instance with bboxes and a tool-call
   trace.
4. On an illegible field, the run terminates with a **partial result and
   explicit gaps** — not a hang, not a fabricated fill (§2.6).
5. `State` carries image handles, not base64 (§2.7) — verified by inspecting
   the LLM context during the run.
6. Swap the VLM provider with one config change; the run still works.
7. Add a new document type by writing a new Template + Skill — **no engine
   code changes**.

### 7.2 Platform (composition + UI)

8. A user can compose an Agent Definition via the Builder wizard by
   selecting a skill, template, and tool set — no Python code.
9. A user can create and edit Skills through the Skill Editor UI —
   adjusting prompts, tool preferences, probe order, invariants, failure
   actions, and semantic check toggles.
10. A user can create and edit Templates through the Template Editor UI —
    defining fields, types, descriptions, and confidence thresholds.
11. A user can instantiate a defined agent via the 3-pane workbench,
    upload a document, and watch the agent reason + extract in real time
    across all three panes.
12. **Pane 1 (Agent Console)** streams the agent's reasoning trace
    (thoughts, tool calls with inline thumbnails, observations) as it
    runs — not just a final result. A field-completion progress bar shows
    extraction status.
13. **Pane 2 (Extracted Data)** shows field cards with value, confidence
    badge, and grounding link. Clicking a field highlights the source
    bbox in Pane 3. Toggleable to editable JSON/form view for
    human-in-the-loop corrections.
14. **Pane 3 (Document Viewer)** renders the document with SVG bbox
    overlays. Clicking a bbox scrolls Pane 2 to the corresponding field.
    Bidirectional click-to-highlight linking is functional.
15. The app runs locally on a laptop — no cloud services required beyond
    the LLM API endpoint.

If a new document type can be onboarded through the UI alone — creating a
template, authoring a skill, composing a definition, and running it — the
platform is right.

---

## 8. Guiding Constraints (from project rules)

- Simplicity first [SF]; readability priority [RP]; DRY [AC].
- Type hints everywhere (Python 3.10+ syntax) [TH].
- Atomic, self-contained changes [AC].
- Secrets via env vars only [AKM]; no PII in logs [DP].
- Retry + backoff on all external calls [EH]; token-aware [TM].
- Pydantic for schemas and settings [CM]; prompts in files/constants [PE].
- pytest with mocked providers [TS][MLC]; deterministic tests [NFT].
- Logging via `logging` module with structured context [LS]; trace per run [TR].

---

## 9. Decisions (locked)

- **LLM: GPT-5.4 via Azure OpenAI.** The primary LLM for all agent runs is
  GPT-5.4, accessed through Azure OpenAI Service. Config is env-driven
  (`AZURE_API_KEY`, `AZURE_CHAT_ENDPOINT`, `AZURE_CHAT_DEPLOYMENT`). The VLM
  tool also uses GPT-5.4's vision capabilities through the same Azure endpoint.
  Swapping to another model is a config change, not a code change.
- **Agent framework: LangGraph.** The ReAct loop is a state-machine graph with
  explicit nodes (`plan`, `act`, `observe`, `reflect`, `terminate`) and edges.
  LangGraph gives us checkpointing for resumable runs, a typed `State` object
  carrying the partial extraction + tool-call trace, and clean conditional
  edges for the reflect → re-plan branch. This is a deliberate upgrade from the
  L2/L6 `AgentExecutor` pattern: we need the Outcome Validator to drive
  conditional transitions, which LangGraph models natively.
- **v1 vertical slice: Invoice.** `InvoiceTemplate` + `InvoiceSkill` against
  `invoice.png` (L2's sample). Fields: `invoice_number`, `invoice_date`,
  `vendor`, `line_items[]`, `subtotal`, `tax`, `total`, with the
  `subtotal + tax == total ± 0.01` cross-check as the verification rule. This
  is the smallest slice that exercises perception (detect_layout), geometry
  (crop), reading (ocr + vlm), grounding, and verification end-to-end.
- **v1 providers (all four):**
  - **PaddleOCR** — `detect_layout`, `detect_text`, `ocr` (primary OCR; gives
    bboxes + scores, self-hostable).
  - **Tesseract** — secondary `ocr` backend for fallback/comparison (trivial
    wrap, already used in L2).
  - **Azure GPT-5.4 VLM** — `vlm`, `read_chart`, `read_table` via GPT-5.4
    vision capabilities through Azure OpenAI.
  - **PIL + OpenCV** — `crop`, `rotate`, `deskew`, `resize`, `denoise`,
    `threshold` (no external deps beyond what's already imported).
  - Provider selection is config-driven; the `ocr`/`vlm` tool interfaces are
    identical regardless of backend, so swapping is a one-line change.
- **ToolRegistry loading: hardcoded v1, dynamic later.** v1 uses config-driven
  imports (`if config.ocr_provider == "paddle": from providers.ocr_paddle
  import ocr as _ocr`) — a one-line swap with zero plugin infrastructure. The
  swappability win comes from the **interface contract**, not the loading
  mechanism. A `ProviderSpec` protocol is extracted when the second provider
  actually lands (v1.5); dynamic discovery via entry points is deferred to v2
  and only if 3+ providers make the if/elif chain genuinely painful. Don't
  build a plugin loader before you have a second plugin [SF].
- **Backend API: FastAPI + SSE.** REST for CRUD on definitions/skills/
  templates; SSE for streaming run progress to the Agent Console. Chosen for
  async-native streaming, Pydantic integration, and OpenAPI docs. SSE over
  WebSocket: simpler for unidirectional server→client streaming, no connection
  management overhead.
- **Frontend: Next.js + TailwindCSS + shadcn/ui.** 3-pane workbench layout
  with Agent Console (Pane 1), Extracted Data (Pane 2), and Document Viewer
  (Pane 3). Next.js App Router for routing, `react-pdf` or custom canvas for
  document rendering, SVG overlay for bounding boxes. Chosen for ecosystem
  maturity, component availability, and team familiarity.
- **Streaming: SSE (Server-Sent Events).** FastAPI streams LangGraph node
  updates (thoughts, tool calls, observations, gap reports) to the Next.js
  frontend via SSE. Simpler than WebSocket for unidirectional server→client
  streaming, no connection management complexity. The frontend uses
  `EventSource` to consume the stream.
- **Local persistence: `.adep/` folder.** Runs, traces, definitions, skills,
  and templates are stored as JSON files in a local `.adep/` directory on
  disk. No database, no Redis, no cloud storage. Simple, inspectable,
  version-controllable. Database migration promoted to Phase 5 (BLK-036).
- **Agent Definition storage: file-based v1, database in Phase 5.**
  Definitions, skills, and templates are stored as JSON/YAML files on disk.
  Simple, version-controllable, and sufficient for single-user v1. Database
  migration promoted to Phase 5 (BLK-036) to support the ADAS meta-agents
  which generate many candidate definitions during evolution loops [SF].
- **Frontend color scheme: ADEP brand palette.** The UI follows the ADEP
  brand color scheme with both dark mode and light mode support. Primary
  palette: ADEP Blue `#00205C`, Mobility Blue `#0071CE`, S. Green `#4DB848`,
  Tech Yellow `#F2E500`, Neutral Dark `#101820`, Electric Blue `#00B5E2`,
  Purple `#A27CC9`, Periwinkle `#C5B4E3`, Neutral Light `#E1E1E1`. Secondary
  palette: Light Blue `#8FD3E8`, Skobeloff `#007A78`, Coral `#F47C6D`,
  Dark Blue `#374785`, Grey `#A7A9AC`. Implemented as CSS custom properties
  in TailwindCSS config with `dark:` variants.

---

## 10. Roadmap

### Phase 1: Engine — **COMPLETE** (15 items)

1. Lock the tool interface contract (arg schemas, return schemas, grounding
   format) — a `ToolSpec` per tool and a shared `Grounding` type. Include the
   geometry-tool split (§2.3): auto-estimating `deskew`/`auto_orient` vs
   agent-supplied `rotate`.
2. Scaffold the package layout (see §11) and the LangGraph `State` + node
   skeletons. **`State` stores image handles, not pixels (§2.7)** — get this
   right before any tool is wired.
3. Implement the Tool Registry + the four v1 providers behind atomic tool
   interfaces.
4. Implement the ReAct graph + the **deterministic-first Outcome Validator**
   (§4.1) emitting a `GapReport`. Wire the per-field/per-document give-up caps
   (§2.6) into the graph's conditional edges.
5. Ship `InvoiceSkill` + `InvoiceTemplate` as the vertical slice that proves
   the architecture.
6. Add an evaluation harness: grounded accuracy + confidence calibration on a
   small held-out set per document type.

### Phase 2: Platform API — **COMPLETE** (10 items)

7. Implement the Agent Definition model — a serializable composition of skill +
   template + tool set + agent config.
8. Implement the file-based Definition Store (CRUD for definitions, skills,
   templates as JSON/YAML on disk).
9. Implement the FastAPI layer: REST endpoints for definitions/skills/templates,
   SSE for streaming run progress to the Agent Console.
10. Wire `run(definition, input)` through the API — workbench sends a document,
    backend streams reasoning trace + final result via SSE.
11. Local persistence: store runs, traces, and definitions as JSON files in
    a `.adep/` folder on disk.

### Phase 3: Frontend — **COMPLETE** (22 items)

12. Build the Next.js 3-pane workbench shell: sidebar + Pane 1 (Agent
    Console) + Pane 2 (Extracted Data) + Pane 3 (Document Viewer).
13. Build Pane 1 — Agent Console: streaming reasoning trace with
    collapsible cards for thoughts, tool calls (with inline thumbnails),
    observations, and a field-completion progress bar. Consumes SSE stream.
14. Build Pane 2 — Extracted Data: toggleable Field Card Grid (value,
    confidence badge, grounding link) and editable JSON/Form view.
    Clicking a field fires `setActiveBBox(bbox, page)`.
15. Build Pane 3 — Document Viewer: PDF/image rendering with SVG bbox
    overlay. Clicking a bbox scrolls Pane 2 to the corresponding field.
    Bidirectional click-to-highlight linking with Pane 2.
16. Build the Skill Editor: structured form for creating/editing skills
    (prompt, tool prefs, probe order, invariants, failure actions, semantic
    check toggle).
17. Build the Template Editor: schema builder UI for creating/editing
    templates (fields, types, descriptions, constraints, thresholds).
18. Build the Agent Definition Builder: wizard for composing a definition
    by selecting skill + template + tools + agent runtime.

### Phase 4: Polish, Scale & Evolve — **COMPLETE** (82 items, 1243 tests)

19. Async run execution with SSE streaming, cooperative pause/resume/stop
    (BLK-129).
20. Structured logging + OpenTelemetry tracing (BLK-130).
21. LLM guardrails: prompt injection defense, hallucination detection,
    output sanitization, tool allowlists, circular reasoning detection,
    retry storm prevention, PII redaction, data exfiltration prevention,
    audit logging (BLK-079 to BLK-086).
22. Prebuilt agent catalogue covering all 11 GICS sectors (BLK-087).
23. Task type abstraction: graph extraction (P&ID → DEXPI),
    `OutputContract` hierarchy, `RunResult` hierarchy (BLK-101 to BLK-103).
24. Token & cost management: per-run/definition/global budgets, admin panel
    (BLK-050, BLK-051).
25. HITL approval gates, trajectory integrity, progressive workbench
    layout (BLK-049, BLK-078).
26. Rate limiting middleware (BLK-123).
27. Run analytics dashboard with real backend data (BLK-119, BLK-165,
    BLK-166).
28. Registry search bars, SkillEditor advanced pane fixes, upload-first
    flow (BLK-163, BLK-164, BLK-131).
29. Codebase audit: 13 issue items, all fixed (BLK-139 to BLK-151).

**Deferred to Phase 5 or later:**
- Multi-document orchestration (v2, §12.6)
- Multi-tenant support (v3, if warranted)

### Phase 5: ADAS / Agentic Builder — **IN PROGRESS** (9 items prioritized)

The Automated Design of Agentic Systems (ADAS) phase. Meta-agents that
generate templates, skills, and agent definitions from natural language,
plus optimization loops (GEPA, MCTS, DocETL). See §16 for the full vision.

**Dependency chain (critical path: BLK-070 → 068 → 071 → 072 → 073):**

```
BLK-036 (DB Store, L)      ──────── independent
BLK-074 (OneFlow, M)       ──────── independent (deps: BLK-008 ✓)
BLK-067 (Template Comp, M) ────────┐
BLK-070 (Surrogate Ver, L) ────────┤
                                  │
BLK-068 (Skill Comp, L) ←─────────┤ (deps: BLK-029 ✓, BLK-070)
                                  │
BLK-069 (Agent Comp, L) ←────────┘ (deps: BLK-031 ✓, BLK-067, BLK-068)
BLK-071 (GEPA, L) ←──────────────── (deps: BLK-068, BLK-070)
BLK-072 (MCTS, L) ←───────────────── (deps: BLK-071)
BLK-073 (DocETL, L) ←─────────────── (deps: BLK-072)
```

**5-wave plan:**

| Wave | Backend                              | Frontend                     |
|------|--------------------------------------|------------------------------|
| 1    | BLK-070 (Surrogate Verifier, L)      | BLK-067 UI (Template Comp, M) |
|      | BLK-067 API (Template Composer, M)   |                              |
| 2    | BLK-068 API (Skill Composer, L)      | BLK-068 UI (Skill Composer, M) |
|      | BLK-036 (DB Store, L)                |                              |
| 3    | BLK-071 (GEPA, L)                    | BLK-069 UI (Agent Composer, L) |
|      | BLK-069 API (Agent Composer, L)      |                              |
| 4    | BLK-072 (MCTS, L)                    | —                            |
|      | BLK-074 (OneFlow, M)                 |                              |
| 5    | BLK-073 (DocETL, L)                  | —                            |

**After Phase 5:** User testing and depth — dogfooding the platform on
real documents, refining skills based on production traces, and fleshing
out the prebuilt catalogue with real-world edge cases.

---

## 11. Proposed Package Layout (v1)

```
adep/
  src/                          # Backend Python package
    tools/
      __init__.py               # Tool Registry
      base.py                   # ToolSpec, Grounding, ToolResult types
      perception.py             # detect_layout, detect_text, detect_tables, ...
      geometry.py               # crop, rotate, deskew, resize, denoise, threshold
      reading.py                # ocr, vlm, read_table, read_chart
      grounding.py              # locate, ground
      verification.py           # verify, cross_check
    providers/
      ocr_paddle.py
      ocr_tesseract.py
      vlm_azure.py              # GPT-5.4 via Azure OpenAI
      image_cv.py               # PIL + OpenCV geometry ops
    agent/
      state.py                  # LangGraph State (partial extraction + trace)
      graph.py                  # nodes + edges: plan/act/observe/reflect/compact/terminate
      validator.py              # Outcome Validator (schema + grounding + thresholds)
    skills/
      base.py                   # Skill dataclass: prompt, tool_prefs, probe_order, rules
      invoice.py                # InvoiceSkill
    templates/
      base.py                   # Template base class
      invoice.py                # InvoiceTemplate (Pydantic)
    definitions/
      base.py                   # AgentDefinition model (composition of bricks)
      store.py                  # File-based CRUD for definitions/skills/templates
    api/
      main.py                   # FastAPI app
      routes/                   # REST + SSE endpoints
        definitions.py
        skills.py
        templates.py
        runs.py
    run.py                      # run(definition, input) -> ExtractedResult
    config.py                   # Pydantic Settings: provider selection, thresholds
    tests/                      # pytest suite
  frontend/                     # Next.js + TailwindCSS + shadcn/ui
    app/                      # Next.js App Router
      page.tsx                # 3-pane workbench layout
      definitions/[id]/       # Definition builder wizard
      skills/[id]/            # Skill editor
      templates/[id]/         # Template editor
    components/
      sidebar/                # Collapsible nav: definitions, skills, templates
      agent-console/          # Pane 1: streaming reasoning trace
        thought-card.tsx      # Collapsible thought display
        tool-call-card.tsx    # Tool call + inline thumbnail
        observation-card.tsx  # Structured tool result
        progress-bar.tsx      # Field completion progress
      extracted-data/        # Pane 2: outcome view
        field-card-grid.tsx   # Field cards with confidence badges
        json-form-view.tsx    # Editable JSON/form toggle
      document-viewer/       # Pane 3: document + bbox overlay
        pdf-canvas.tsx        # react-pdf or custom canvas
        bbox-overlay.tsx      # SVG bounding box overlay
      shared/
        active-highlight.tsx  # Context: setActiveBBox for Pane 2 ↔ Pane 3
    lib/
      api.ts                  # REST client (definitions, skills, templates, runs)
      sse.ts                  # SSE client (EventSource wrapper for run streaming)
      types.ts                # TypeScript types matching backend Pydantic models
  notebooks/                    # Reference labs (L2, L4, L6, L8, L9)
  comms/                        # Inter-team messaging protocol
  vision.md                     # This file
  README.md
  requirements.txt
  .env.example
```

The litmus test from §7 holds: onboarding a new document type means adding one
file under `templates/` and one under `skills/` — no edits to `tools/`,
`providers/`, or `agent/`. With the platform UI, this can be done entirely
through the frontend editors.

---

## 12. Scaling Beyond v1

v1 nails single-document extraction. The patterns that scale to dozens or
hundreds of pages — and to multi-document packages — are established in v1 and
fully realized in v2. The architecture does not need a rewrite for scale; it
needs the `State` contract (§2.7) to be right from the start.

### 12.1 Hierarchical State

```
DocumentState
  └─ PageState[]          # one detect_layout pass per page
       └─ RegionState[]   # {id, type, bbox, text?, confidence}
```

`DocumentState` holds an **index** of pages/regions, not pixels. The LLM sees
the region index (lightweight tuples) + the `GapReport`. To look at a region it
calls `crop(page, bbox)`, which materializes *only that region's* pixels for
the tool. 100 pages never enter context.

### 12.2 Field-Driven Working Set

The `plan` node takes the validator's `GapReport`, maps each unsatisfied field
to candidate regions (via the index + skill hints), and produces a small
**working set** for the next `act` cycle. The agent reasons over the working
set, not the whole document. This is what keeps context bounded regardless of
document length.

### 12.3 Trace Compaction via Checkpointing

LangGraph persists the full trace to disk per checkpoint. The `plan` node
receives a **rolling window** of context: (a) the current `GapReport`, (b) the
region index, and (c) the last K `act/observe` pairs. **Resolved fields are
pruned** from the active trace — their final values live in the partial
extraction, not in the trace. The default is code-based pruning (simple,
fast, no hallucination risk). If the trace grows beyond what a rolling window
can handle in v2, an LLM summarizer may be introduced as an opt-in strategy —
but only when the problem is real, not preemptively [SF]. The full trace
remains recoverable from the checkpoint for eval/debug.

**Retry-loop prevention.** The rolling window alone is not enough — without
context, the agent could retry the same failed tool on the same region and
forget it already tried. Two safeguards:

1. **Failed attempts are sticky.** When a tool returns `ok=False` on a
   region, that failure is kept in a per-region `attempted` set in `State`,
   outside the rolling window. The `plan` node checks this set before routing
   the agent to act on a region — if the same tool was already tried with the
   same args, the plan node must choose a different tool, different args, or a
   different region.
2. **GapReport carries last-error.** Each `FieldGap` includes the last error
   message and tool that failed for that field, so the agent has context on
   what was already tried even if the trace entry has rolled out of the window.

These are lightweight (a set of tuples + a string per gap), not a complex
data structure. They prevent the "amnesiac retry" problem without adding
LLM summarization or heavy state [SF].

### 12.4 Context Compaction (`/compaction`)

The rolling window (§12.3) is passive — it prunes resolved fields and
truncates to K entries. For long-running extractions (30+ cycles, complex
documents), this is not enough. The agent needs **active compaction** —
the ability to summarize its trace into a compact narrative, just like
Claude Code, Windsurf, or Devin do when their context window fills up.

**Two trigger modes:**

1. **Auto-compaction (threshold-based).** After the `reflect` node, if the
   trace length exceeds `ADE_COMPACTION_THRESHOLD` (default: 15 entries),
   the graph routes to a `compact` node instead of back to `plan`. The
   compact node uses the LLM to summarize the trace into a structured
   `compaction_summary` string, then routes to `plan` with the summary
   replacing the trace in the LLM prompt. The full trace remains in the
   LangGraph checkpoint for debugging and evaluation.

2. **Manual compaction (`/compaction` action).** The frontend Agent Console
   (Pane 1) has a "Compact" button. Clicking it sends a `compact` event
   via SSE to the backend. On the next `reflect → plan` transition, the
   graph routes to `compact` regardless of trace length. This lets the
   user force compaction when they see the agent struggling or looping.

**What the compact node preserves:**

The LLM is prompted to produce a structured summary that retains:
- **GapReport** — current gaps (already in State, not summarized)
- **Extraction state** — current field values (already in State)
- **Attempted set** — per-region failed tool+args (already in State,
  sticky, never compacted)
- **Narrative summary** — what tools were tried, what worked, what failed,
  and why. This is the new `compaction_summary` field in State.

After compaction, the `plan` node's LLM prompt includes:
```
## Compacted Trace Summary
{compaction_summary}

## Current Gaps
{gap_report}

## Already Attempted (do not retry)
{attempted}
```

Instead of the raw trace entries. This reduces context from K trace
entries (each with full tool args, results, observations) to a single
paragraph + the always-present GapReport and attempted set.

**Graph flow with compaction:**
```
plan → act → observe → reflect → (plan | compact | terminate)
                                    compact → plan
```

The `should_continue` conditional edge now has three outcomes:
- `terminate` — complete or caps exhausted
- `compact` — trace exceeds threshold OR manual `/compaction` requested
- `plan` — continue normally

**Design constraints:**
- Compaction is opt-in via `ADE_COMPACTION_ENABLED=true` (default: true)
- Threshold is config-driven: `ADE_COMPACTION_THRESHOLD=15`
- The `compaction_summary` is a single string field, not a complex data
  structure [SF]
- The full trace is never lost — it persists in the LangGraph checkpoint
- The `attempted` set is never compacted — retry-loop prevention is
  non-negotiable [§12.3]
- Manual compaction resets the trace window but does not reset extraction
  state, gaps, or attempted set

### 12.5 Hierarchical `locate` (v2)

When the region index grows too large to scan cheaply, `locate` queries an
**embedded region store** (text + type metadata) to retrieve candidate regions
per field. This is the vector path — but only when warranted. Premature
vector-DB integration is a classic over-engineering trap [SF]; v1's structured
region index is sufficient and the embedding layer slots in behind the same
`locate` interface.

### 12.6 Multi-Document Orchestration (v2, L9 territory)

Per-document extraction produces per-doc `ExtractedResult`s. A **separate
cross-doc validator graph** operates over those results (the "same applicant"
check from L9), never over pixels. Cross-doc validation is a different layer
sitting above the per-doc loop, not a modification of it. v1's per-doc
`ExtractedResult` contract is what makes this layer composable later.

### 12.7 What v1 Establishes for v2

| Pattern                  | Established in v1 (Invoice slice)        | Realized in v2                  |
|--------------------------|------------------------------------------|---------------------------------|
| Image handles, not blobs | `State` carries paths/IDs only           | Scales to 100s of pages         |
| Region index in context  | One page's regions in `State`            | `DocumentState` over all pages  |
| Gap-report-driven scope  | Validator drives next `act`             | `plan` builds working set       |
| Checkpointed trace       | LangGraph persistence per node           | Compacted summary in context    |
| Partial result on give-up| Per-field/per-doc caps                   | Same, at document-package scale |

---

## 13. Agentic UX Heuristics

ADEP is an agentic application — the agent operates autonomously, makes
probabilistic decisions, and executes multi-step workflows. Traditional
usability heuristics (Nielsen, ISO 9241-110) must be adapted for this
context. The following principles guide ADEP's UX design.

### 13.1 Progressive Disclosure (3-Tier Transparency)

The UI must not overwhelm users with raw logs by default, nor hide all
logic behind a conversational facade. Three tiers of detail:

- **Level 1 (Surface):** Status badges, progress bar, confidence colors.
  Glanceable in 3 seconds. Default view.
- **Level 2 (Expansion):** Click a cycle → show tool call + result.
  Click a field → show provenance (tool, region, confidence).
- **Level 3 (Deep Dive):** Expert mode toggle → raw JSON, full trace,
  attempted set, compaction summary. For debugging and auditing.

### 13.2 User Control and Emergency Exits

The agent must never act without the possibility of human intervention.

- **Pause/Resume:** Halt after current cycle, continue when ready.
- **Stop:** Emergency halt — partial results preserved.
- **Rollback:** Rewind to a past cycle (LangGraph checkpoint restoration).
  The `attempted` set is preserved across rollback — retry-loop prevention
  is non-negotiable.

### 13.3 Trust Calibration

Trust is volatile in autonomous systems. Over-trust → catastrophic
delegation. Under-trust → useless micromanagement.

- **First-run onboarding:** "What ADEP can and cannot do" modal.
- **Confidence as color + number:** Green ≥0.8, Yellow 0.5-0.79, Red <0.5.
  Always visible, not hidden in tooltips.
- **No anthropomorphism:** Agent is a "tool" (FileSearch icon), not a
  "companion" (no human avatar or name). Status uses machine metaphors
  ("Processing", "Analyzing" — not "Thinking", "Reading").
- **Uncertainty surfacing:** "Agent having difficulty" banner after
  retries. "Approaching iteration cap" at 80%.

### 13.4 Gate Pattern (HITL)

Risk-tiered approval for agent actions. The agent prepares an action but
pauses for human review before execution. Only high-risk and critical
actions trigger blocking gates — low/medium proceed autonomously to
avoid confirmation fatigue.

| Tier | ADEP Action | Gating |
|------|------------|--------|
| Low | OCR/VLM on region | No gate — auto-execute |
| Medium | Confidence 0.5-0.79 | Non-blocking flag for review |
| High | Confidence <0.5, semantic fail | Blocking — user must approve/reject |
| Critical | Partial termination | Modal — "Accept partial result?" |

Deny by default on timeout for high-risk (safety-first).

### 13.5 Trajectory Integrity

Multi-step agents suffer from trajectory instability — a minor error
cascades through subsequent stages. The UI must visualize trajectory
health and support recovery:

- **Health dots per cycle:** Green (gap reduced), Yellow (no improvement),
  Red (tool failed).
- **Cascade detection:** 3+ consecutive non-improving cycles → warning.
  5+ → critical, auto-pause.
- **Recovery options:** Rollback to last green cycle, compact and retry,
  or stop and review.

### 13.6 Prompt Injection Defense (UX Layer)

The UI must visually differentiate between user-provided prompts and
data retrieved from external sources. Anomalous agent actions (unexpected
tool calls, strange argument patterns) should be surfaced with
high-salience warnings. The LLM is never the authority — the deterministic
validator is. This is both a security and a UX principle.

---

## 14. Industry Skill Matrix (GICS Mapping)

ADEP's primitives (Agent, Tools, Skills, Templates) are universally
adaptable across industries. The GICS 11-sector framework provides a MECE
taxonomy for planning the skill library.

### 14.1 Sector → Skill → Key Invariants

| Sector | Skill | Key Documents | Deterministic Invariants |
|--------|-------|---------------|--------------------------|
| Financials | TradeFinanceScrutinySkill | MT700, BoL, invoices | Date arithmetic, amount tolerance, doc coverage |
| Industrials | BillOfQuantitiesSkill | BOQ, engineering specs | qty × rate = total, VAT consistency |
| IT | ComplianceAuditSkill | SOC 2, OSPAR, MAS TRM | Boolean control checks, encryption standards |
| Real Estate | CommercialLeaseSkill | Lease agreements | CAM fees, rent escalation clauses |
| Energy | CommodityTradeSkill | Assay reports, BoL | Volumetric tolerance bands, API gravity |
| Materials | MetallurgicalAssaySkill | MSDS, assay certs | Composition matrix, OCR→VLM fallback |
| Health Care | MedicalClaimSkill | CMS-1500, UB-04 | ICD-10 cross-checks, demographic logic |
| Consumer Disc. | StoreAuditSkill | Audit reports, photos | Visual evidence cross-reference |
| Consumer Staples | ThermalReceiptSkill | Thermal receipts, POS | subtotal + tax = total, geometry-first |
| Communication | AdBuySkill | Insertion orders | Local tiers sum to national total |
| Utilities | UtilityBillSkill | Utility bills | Chart extraction (read_chart), consumption |

### 14.2 VLM Strengths vs Weaknesses (Design Principle)

- **VLMs excel at:** Reading unstructured prose, extracting structured
  entities, cross-document semantic matching, handwriting recognition,
  chart/infographic interpretation.
- **VLMs fail at:** Date arithmetic, exhaustive completeness checks,
  mathematical invariants, noticing what is absent.

**Design rule:** VLMs handle perception; deterministic code handles
math, dates, and coverage. The LLM is never the authority — the
Outcome Validator is. This also neutralizes prompt injection (the LLM
cannot issue a "clean verdict" because it doesn't issue verdicts).

### 14.3 Evaluation Metrics

ADEP's grounding requirement aligns with emerging evaluation frameworks:

- **ANLS** (Average Normalized Levenshtein Similarity): partial credit
  for near-matches. Standard for DocVQA. Blind spot: ignores grounding.
- **SMuDGE**: factors in spatial localization (bbox IoU) and output type.
  ADEP's mandatory grounding satisfies SMuDGE by design.
- **Multi-page benchmarks:** MP-DocVQA, DUDE — validate hierarchical
  state and field-driven working sets (BLK-041).

---

## 15. Token & Cost Management

ADEP makes LLM calls on every ReAct cycle. Without token monitoring and
budget enforcement, a single runaway extraction could burn through an
entire API quota silently. Token management is a first-class concern.

### 15.1 Token Tracking

Every LLM call (plan node, compact node, semantic checks) records:
- Input tokens, output tokens, total tokens
- Calculated cost (USD) based on model pricing
- Node name, cycle number, timestamp

This data accumulates in `AgentState.token_usage` and persists to
`.adep/runs/{run_id}/token_usage.json`. Aggregate stats roll up to
`.adep/stats/aggregate.json` for dashboard consumption.

SSE `token_usage` events stream in real time so the workbench can
display running consumption.

### 15.2 Budget Enforcement

Three budget levels, each with token and cost caps:

| Level | Scope | Warning (80%) | Limit (100%) |
|-------|-------|---------------|--------------|
| Run | Single extraction | SSE warning, Pane 1 banner | Agent terminates PARTIAL |
| Definition | Per definition, per day | Admin dashboard alert | New runs blocked (429) |
| Global | All runs, per day | Admin dashboard alert | All new runs blocked (429) |

Budgets complement give-up caps (§2.6): cycle caps prevent loops,
budget caps prevent cost overruns. Both produce graceful partial
results.

### 15.3 Admin Panel

A `/admin` route provides:
- Stat cards, 7-day consumption chart, budget status bars
- Recent runs table and top expensive runs
- Budget settings form

### 15.4 Design Principles

- Token tracking must not add latency
- Cost is an estimate, not a billing system
- v1: single-tenant, global budgets
- Daily reset is date-based (midnight UTC)

---

## 16. Automated Design of Agentic Systems (ADAS) — Phase 5 (Active)

The long-term evolution of ADEP is an **agentic agent builder**: a
meta-agent that converts natural language requirements into production-
ready extraction agents by generating templates, skills, and orchestrating
logic. **This is now active work** — Phase 5 launched with 9 items
prioritized and a 5-wave delivery plan (see §10).

### 16.1 The Three Composers

- **Template Composer (BLK-067):** generates Pydantic schemas from NL
- **Skill Composer (BLK-068):** generates skills from NL and samples
- **Agent Composer (BLK-069):** binds primitives into a ReAct graph

### 16.2 Co-Evolution with Surrogate Verifier

Skills cannot be generated reliably in one pass. The Skill Composer
couples a generator with an information-isolated Surrogate Verifier
(BLK-070) that evaluates traces and proposes patches without ground truth.

### 16.3 Reflective Prompt Evolution (GEPA)

GEPA (BLK-071) optimizes prompts by reflecting on execution trajectories
and applying Pareto-optimal genetic mutations. It reportedly outperforms
GRPO with far fewer rollouts.

### 16.4 MCTS and DocETL Optimization

- **MCTS workflow optimization (BLK-072):** searches graph topologies using
  Monte Carlo Tree Search.
- **DocETL query rewriting (BLK-073):** decomposes failing tasks into
  smaller sub-tasks and validates rewrites against baselines.

### 16.5 OneFlow, Provider Registry, and Cost Estimation

- **OneFlow mode (BLK-074):** single-agent role-play for homogeneous
  multi-agent workflows, maximizing KV cache reuse.
- **Provider registry (BLK-075):** cost/accuracy metadata for OCR/VLM
  providers, enabling dynamic selection and fallback.
- **Dynamic cost estimator (BLK-076):** predicts extraction cost from
  pages, output size, and provider rates.

---

## 17. Progressive Workbench Layout

The 3-pane workbench does not show all panes at once. Panes appear
progressively as the user advances through the extraction workflow,
reducing cognitive load and matching the natural task flow.

### 17.1 Three Phases

| Phase | Trigger | Panes Visible | Layout |
|-------|---------|---------------|--------|
| Chat | New session | Pane 1 only | Full width |
| Document | Upload document | Pane 1 + Pane 3 | 50/50 split |
| Extraction | Start run | Pane 1 + Pane 3 + Pane 2 | Equal thirds |

### 17.2 Pane 2 In-Progress State

When extraction starts, Pane 2 shows an "in progress" indicator — not
empty cards or mock data. As `field_update` SSE events arrive, field
cards replace the indicator one by one. When the run completes, the
full field grid is displayed.

### 17.3 Design Rationale

- **Chat phase:** User focuses on selecting a definition and uploading
  a document. No distraction from empty panes.
- **Document phase:** User can inspect the uploaded document before
  committing to an extraction run. Pane 3 (Document Viewer) validates
  the upload visually.
- **Extraction phase:** All three panes are visible. Pane 1 shows the
  reasoning trace, Pane 3 shows the document with bbox overlays, and
  Pane 2 shows extraction results as they arrive.

### 17.4 Transitions

- "New Session" resets to chat phase
- Selecting a past session from the sidebar loads the correct phase
  based on run status
- Transitions use 200-300ms CSS animations (fade/slide)

Reference: BLK-078.

---

## 18. LLM Guardrails

ADEP treats the LLM as an untrusted perception engine. Every input is
sanitized, every output is validated, and every action is sandboxed.
The guardrail system is defense-in-depth: no single guardrail is the
last line of defense.

### 18.1 Existing Defenses

- **Prompt injection defense (BLK-043):** LLM-as-perception pattern,
  instruction pattern detection in input and output.
- **Give-up caps (§2.6):** Per-field and per-document cycle limits.
- **Token tracking (BLK-050):** Every LLM call's token usage recorded.
- **Budget enforcement (BLK-051):** Per-run, per-definition, and global
  cost caps with graceful termination.
- **Trajectory integrity (BLK-049):** Error cascade detection and
  rollback.

### 18.2 Output Guardrails

- **Schema validation (BLK-079):** Every LLM response validated against
  a Pydantic model. Invalid responses retried, then failed.
- **Hallucination detection (BLK-081):** Every extracted value cross-
  checked against the OCR text layer at the grounding bbox. Mismatches
  flagged and confidence capped.
- **Output sanitization (BLK-079):** Instruction patterns, oversized
  responses, and unknown fields stripped from LLM output.

### 18.3 Tool Guardrails

- **Tool allowlist (BLK-080):** Only registered tools can be called.
- **Argument validation (BLK-080):** Tool args validated against
  ToolSpec schemas. Path traversal and out-of-bounds rejected.
- **Rate limiting (BLK-080):** Per-tool call limits prevent spamming.
- **No dynamic tools (BLK-080):** Tool registry is immutable during a run.

### 18.4 Loop & Resource Guardrails

- **Circular reasoning detection (BLK-082):** Same tool+args for 3
  cycles, thought similarity > 0.95, or oscillation → terminate.
- **Retry storm prevention (BLK-085):** Exponential backoff with jitter,
  circuit breaker pattern, per-run retry budget, provider fallback.

### 18.5 Data Guardrails

- **PII redaction (BLK-083):** PII redacted before entering LLM prompts.
  Extraction results preserve real values; logs and traces are redacted.
- **Data exfiltration prevention (BLK-086):** No outbound network from
  tools, encoded data detection in output, tool argument size limits,
  input sanitization (control chars, unicode, HTML).
- **Content classification (BLK-083):** Documents tagged with
  sensitivity level; restricted documents use on-prem models only.

### 18.6 Audit & Observability

- **LLM call audit log (BLK-084):** Every LLM call logged with full
  context (prompt, response, tokens, latency, guardrail decisions).
  Tamper-evident chained logs. Exportable for compliance.
- **Guardrail decision log (BLK-084):** Separate log for all guardrail
  actions (rejections, sanitizations, retries, terminations).

### 18.7 Design Principles

1. **Never trust LLM output** — validate everything
2. **Defense in depth** — multiple guardrails, no single point of failure
3. **Fail safe** — guardrails terminate gracefully with partial results
4. **Log everything** — every decision is auditable
5. **Configurable** — thresholds, patterns, and policies are settings

---

## 19. Prebuilt Agent Catalogue

ADEP ships with a full catalogue of prebuilt agent definitions covering
all 11 GICS sectors. Users can immediately select an agent for their
document type without building one from scratch.

### 19.1 Catalogue Overview

| Sector | Skill | Template | Agent Definition |
|--------|-------|----------|-----------------|
| Financials | TradeFinanceScrutinySkill | trade_finance_mt700 | def-trade-finance-scrutiny |
| Industrials | BillOfQuantitiesSkill | bill_of_quantities | def-boq-estimator |
| IT | ComplianceAuditSkill | compliance_audit_soc2 | def-compliance-audit |
| Real Estate | CommercialLeaseSkill | commercial_lease | def-commercial-lease |
| Energy | CommodityTradeSkill | commodity_trade_assay | def-commodity-trade |
| Materials | MetallurgicalAssaySkill | metallurgical_assay | def-metallurgical-assay |
| Health Care | MedicalClaimSkill | medical_claim_cms1500 | def-medical-claim |
| Consumer Discretionary | StoreAuditSkill | store_audit_checklist | def-store-audit |
| Consumer Staples | ThermalReceiptSkill | thermal_receipt | def-thermal-receipt |
| Communication Services | AdBuySkill | ad_insertion_order | def-ad-buy |
| Utilities | UtilityBillSkill | utility_bill | def-utility-bill |

### 19.2 Design Principles

- Each skill specifies a **probe order** (geometry-first for degraded
  documents, perception-first for clean digital documents)
- Each template defines **per-field confidence thresholds** (not a
  single global threshold)
- All **mathematical invariants** are in deterministic code via
  `cross_check` — never LLM
- Each agent definition is shipped as a JSON file in
  `.adep/definitions/` and appears immediately in the UI
- The catalogue is extensible — users can build custom agents using
  the 7-step wizard (BLK-031) on top of prebuilt skills and templates

### 19.3 UI Integration

The sidebar library nav says "Choose Agent" (not "Definitions"). The
agent selection page shows prebuilt agents as cards with skill name,
template field count, and max iterations. Users can:
1. Select a prebuilt agent and start extracting immediately
2. Build a custom agent using the 7-step wizard
3. Duplicate a prebuilt agent and customize it

Reference: BLK-087.

---

## 20. Task Type Abstraction — Beyond Field Extraction

### 20.1 The Problem

The current architecture is hardcoded to **flat field extraction**:
- `Template` = Pydantic schema with flat fields
- `ExtractedResult` = flat dict of `FieldValue` with grounding
- `Outcome Validator` = field-level checks (presence, type, math, grounding)
- `Tools` = all designed for reading text/values from documents

This works for invoices, receipts, and forms. It does NOT work for:
- **P&ID → DEXPI/Smart P&ID**: a P&ID diagram is a graph (equipment,
  valves, instruments, pipes), not a set of fields. The output is a
  topology graph serialized to an industry XML/JSON format.
- **Classification**: tagging a document with categories, not
  extracting fields.
- **Transformation**: converting a document to a different
  representation (redacted, translated, summarized).

The platform claims to be composable and general-purpose, but the
output model is single-purpose. This section generalizes it.

### 20.2 The Abstraction: Task Types

The **Agent Runtime (ReAct loop)** is already task-agnostic — it
reasons, acts, observes, reflects. What needs to change is the
**output contract**, **result model**, **validator**, and **tool set**.

We introduce a `TaskType` enum that dispatches to task-specific
implementations:

```
TaskType:
  extraction          (v1, current)    — document → flat fields
  graph_extraction    (new)            — diagram → graph → target format
  classification      (future)         — document → labels
  transformation      (future)         — document → different representation
```

### 20.3 Output Contract (generalizes Template)

The current `Template` becomes a specialization of a generic
`OutputContract`:

```python
class OutputContract(BaseModel):
    """Base class for all output contracts."""
    task_type: str
    name: str
    description: str

class FieldExtractionContract(OutputContract):
    """Current Template — flat Pydantic fields."""
    task_type: str = "extraction"
    # Pydantic fields defined by subclass

class GraphExtractionContract(OutputContract):
    """Graph extraction — nodes, edges, attributes, topology rules."""
    task_type: str = "graph_extraction"
    node_types: list[NodeTypeSpec]       # type, subtypes, required_attrs
    edge_types: list[EdgeTypeSpec]       # type, allowed_source, allowed_target
    required_attributes: dict[str, list[str]]
    topology_rules: list[TopologyRule]   # e.g., "every valve connected"
    output_formats: list[str]            # e.g., ["dexpi_xml", "graphml"]
```

Backward compatibility: existing `Template` subclasses continue to
work — `Template` becomes an alias for `FieldExtractionContract`.

### 20.4 Result Model (generalizes ExtractedResult)

```python
class RunResult:
    """Base class for all run results."""
    is_complete: bool
    status: str
    trace: list[TraceEntry]
    gap_report: GapReport
    token_usage_summary: dict

class FieldExtractionResult(RunResult):
    """Current ExtractedResult — flat fields."""
    values: Any                          # filled Pydantic model
    field_values: dict[str, FieldValue]

class GraphExtractionResult(RunResult):
    """Graph extraction result."""
    graph: dict                          # nodes[], edges[], attributes
    node_grounding: dict[str, BBox]      # node_id → bbox in source
    edge_grounding: dict[str, list[BBox]]# edge_id → bboxes along path
    serialized_output: dict[str, str]    # format_name → serialized string
```

### 20.5 Validator (generalizes Outcome Validator)

The validator dispatches based on `task_type`:

**Extraction (current):**
1. Required-field presence
2. Type/format checks
3. Math invariants
4. Grounding presence
5. Confidence ≥ threshold
6. Semantic checks (optional)

**Graph Extraction (new):**
1. Node coverage — all required node types detected
2. Edge connectivity — no orphan nodes (unless explicitly capped)
3. Attribute completeness — required attributes filled per node type
4. Topology rules — e.g., "every valve connected to at least one pipe"
5. Tag format — e.g., ISA-5.1 for instrument tags
6. Control loop completeness — sensor → controller → final element
7. Grounding — every node/edge traceable to source pixels
8. Serialization validity — output parses in target format

### 20.6 New Tools for Graph Extraction

| Category        | Tool                    | Inputs                          | Output                                    |
|-----------------|-------------------------|---------------------------------|-------------------------------------------|
| Symbol Detection| `detect_symbols`        | image, symbol_library?          | symbols[] {bbox, class, confidence}       |
|                 | `classify_symbol`       | image, bbox                     | {class, confidence}                       |
| Connection      | `detect_connections`    | image, symbols[]                | connections[] {from, to, path, type}      |
|                 | `trace_line`            | image, start_point, direction?  | path {bboxes, end_point, connected_to}    |
| Tag Reading     | `read_tag`              | image, bbox                     | {tag, parsed_components, confidence}      |
| Graph           | `build_graph`           | symbols[], connections[]        | graph {nodes, edges}                      |
|                 | `validate_topology`     | graph, rules                    | {violations[], ok}                        |
| Serialization   | `serialize_graph`       | graph, format                   | {format, content}                         |

These tools are **additive** — they don't change existing tools. The
agent can use both extraction tools (ocr, vlm, crop) and graph tools
(detect_symbols, trace_line) in the same run if needed.

### 20.7 P&ID → DEXPI / Smart P&ID

The first graph extraction use case: converting engineering P&ID
diagrams to industry-standard digital formats.

**DEXPI** (Digital Exchange of Process Information) is an XML-based
standard for exchanging process plant data. **Smart P&ID** is
Intergraph's intelligent P&ID format. Both require a topology graph
of equipment, valves, instruments, and connections.

**GraphExtractionContract:**

```python
class PnIDContract(GraphExtractionContract):
    name = "P&ID to DEXPI/Smart P&ID"
    node_types = [
        NodeTypeSpec("equipment", ["vessel", "pump", "heat_exchanger",
                                   "tank", "compressor"]),
        NodeTypeSpec("valve", ["manual", "control", "check", "relief"]),
        NodeTypeSpec("instrument", ["sensor", "controller", "indicator"]),
        NodeTypeSpec("pipe", []),
        NodeTypeSpec("fitting", ["reducer", "elbow", "tee"]),
    ]
    edge_types = [
        EdgeTypeSpec("connected_to", "any", "any"),
        EdgeTypeSpec("branches_from", "pipe", "pipe"),
        EdgeTypeSpec("measures", "instrument", "equipment|pipe"),
        EdgeTypeSpec("controls", "instrument", "valve"),
    ]
    topology_rules = [
        "every valve connected to at least one pipe",
        "every instrument tag follows ISA-5.1 (XX-NNN)",
        "control loops complete: sensor → controller → final_element",
        "no orphan pipes (both ends connected or explicitly capped)",
    ]
    output_formats = ["dexpi_xml", "smart_pid_json", "graphml"]
```

**PnIDSkill:**

```python
PnIDSkill:
    system_prompt = """
        You are a process engineer analyzing P&ID (Piping and
        Instrumentation Diagram) drawings. Identify all equipment,
        valves, instruments, and pipe connections. Build a complete
        process topology graph and serialize it to the target format.
        """
    probe_order = [
        ("title_block", "Read drawing title, revision, scale"),
        ("legend", "Identify symbol library / legend"),
        ("main_diagram", "Detect all symbols in the main drawing area"),
        ("tags", "Read instrument tags for each detected symbol"),
        ("connections", "Trace pipe lines between symbols"),
        ("topology", "Build and validate the process graph"),
        ("serialize", "Convert to target output format"),
    ]
    invariants = [
        Invariant("every_valve_connected", ...),
        Invariant("isa_51_tag_format", ...),
        Invariant("control_loop_completeness", ...),
        Invariant("no_orphan_pipes", ...),
    ]
    failure_actions = {
        GapType.SYMBOL_UNCLASSIFIED: "crop region, vlm with symbol library",
        GapType.TAG_UNREADABLE: "crop tag area, deskew, ocr",
        GapType.CONNECTION_AMBIGUOUS: "trace_line from both endpoints",
        GapType.TOPOLOGY_VIOLATION: "re-examine region, check for missed symbol",
    }
```

**Agent Definition:**

```
AgentDefinition {
    name:       "P&ID to DEXPI Converter"
    task_type:  "graph_extraction"
    tools:      [detect_layout, detect_symbols, classify_symbol,
                 ocr, vlm, read_tag, trace_line, detect_connections,
                 build_graph, validate_topology, serialize_graph,
                 crop, deskew]
    skill:      PnIDSkill
    contract:   PnIDContract
}
```

### 20.8 Impact on Existing Architecture

The abstraction is **backward compatible**:

| Component          | Current                   | After Abstraction              |
|--------------------|---------------------------|--------------------------------|
| Template           | Pydantic BaseModel        | Alias for FieldExtractionContract |
| ExtractedResult    | Flat dict + grounding     | Alias for FieldExtractionResult   |
| Outcome Validator  | Field-level checks        | Dispatches by task_type           |
| Skill              | Field extraction playbook | Same structure, new invariant types |
| Tools              | Perception/reading        | + Symbol/connection/graph tools   |
| Agent Runtime      | ReAct loop                | Unchanged — already task-agnostic |
| Run Engine         | run(definition, input)    | Same signature, dispatches by task_type |

**What doesn't change:** The ReAct loop, the state model (image
handles not pixels), the give-up caps, the guardrails, the SSE
streaming, the 3-pane workbench, the comms protocol.

**What changes:** Template base class, ExtractedResult, validator
dispatch, tool registry (additive), and the frontend Pane 2 (needs
to render graph output, not just field cards).

### 20.9 Frontend Impact

Pane 2 (Extracted Data) currently renders field cards. For graph
extraction tasks, it needs to render:

1. **Graph visualization** — interactive node-link diagram showing
   the extracted topology (equipment, valves, instruments, pipes)
2. **Node detail panel** — click a node → show attributes, tag,
   grounding bbox in Pane 3
3. **Output format selector** — toggle between DEXPI XML, Smart P&ID
   JSON, GraphML views
4. **Topology validation panel** — show rule violations as actionable
   warnings

The Agent Definition Builder wizard needs a new step: **Task Type
Selection** (Extraction vs Graph Extraction vs Classification). This
determines which contracts and tools are available.

### 20.10 Implementation Phases

**Phase A — Abstraction (no new functionality):**
- Generalize Template → OutputContract hierarchy
- Generalize ExtractedResult → RunResult hierarchy
- Add task_type dispatch to validator
- Keep all existing behavior identical
- All 1243 tests still pass

**Phase B — Graph Extraction Tools:**
- Implement `detect_symbols`, `classify_symbol`
- Implement `detect_connections`, `trace_line`
- Implement `read_tag`
- Implement `build_graph`, `validate_topology`, `serialize_graph`
- Add DEXPI XML serializer
- Add Smart P&ID JSON serializer
- Add GraphML serializer

**Phase C — P&ID Skill + Contract:**
- Implement `PnIDContract` (GraphExtractionContract)
- Implement `PnIDSkill` with probe order, invariants, failure actions
- Create prebuilt agent definition: `def-pnid-to-dexpi`
- Download sample P&ID diagrams for testing

**Phase D — Frontend:**
- Add task type selector to Agent Definition Builder
- Add graph visualization to Pane 2
- Add output format selector
- Add topology validation panel
