# Agentic Document Extraction Platform (ADEP)

> A composable platform where agent definitions are assembled from
> interchangeable bricks — agent runtime, tools, skills, templates — and users
> instantiate them via a chat interface to solve real extraction tasks.
> Document extraction is the first domain; the platform is the product.

See [vision.md](vision.md) for the full architectural vision.

## Quick Start

```bash
# Install dependencies (requires uv)
uv sync

# Set up environment variables
cp .env.example .env  # then edit .env with your AZURE_API_KEY

# Run the v1 invoice extraction slice
uv run python -c "
from src.templates.invoice import InvoiceTemplate
from src.skills.invoice import InvoiceSkill
from src.run import run
result = run(InvoiceTemplate, InvoiceSkill, 'notebooks/invoice.png')
print(result.is_complete, result.gap_report.missing_fields())
"
```

## Project Structure

```
adep/                        # Project root
  vision.md                 # Architectural vision
  pyproject.toml
  uv.lock
  src/                      # Backend Python package
    tools/                  # Atomic image-centric tools + contracts
    providers/              # Swappable backends (OCR, VLM, image ops)
    agent/                  # ReAct loop (LangGraph), state, validator
    skills/                 # Reusable playbooks per document archetype
    templates/              # Declarative outcome contracts (Pydantic)
    tests/                  # pytest suite
    config.py               # Pydantic Settings
    run.py                  # run(template, skill, document) -> ExtractedResult
  frontend/                 # Next.js + TailwindCSS + shadcn/ui (Phase 3)
  notebooks/                # Reference labs (L2, L4, L6, L8, L9)
  comms/                    # Inter-team messaging protocol
  backlog/                  # Pending work items (features, bugs, ideas, tech-debt)
  implemented/              # Completed work items
  projectmgmt/              # PM process docs, status board, item template
```

## Architecture

Four bricks, cleanly separated and composable:

- **Agent Runtime** — the ReAct loop (LangGraph + GPT-5.4). Task-agnostic
  execution engine.
- **Tools** — atomic, stateless capabilities the agent may call (OCR, VLM,
  crop, detect_layout, ground, verify, ...).
- **Skill** — the know-how for a document archetype. Says *how* to approach
  extraction for a document type.
- **Template** — the outcome contract (Pydantic schema). Says *what* a valid
  result looks like.

An **Agent Definition** composes these bricks into a named, reusable unit. A
**Run Instance** executes a definition against a concrete input.

Onboarding a new document type = one Template + one Skill, composable via UI
or code. No engine code changes.

## Testing

### Unit Tests (default)

```bash
uv run pytest src/tests/ -m "not integration"
```

All unit tests use mocked providers and run in CI. 1100+ tests.

### Integration Tests (real providers)

Integration tests exercise the full extraction pipeline against real OCR and
VLM providers. They cost real money and **never run in CI by default**.

```bash
# Run integration tests explicitly
uv run pytest -m integration

# Run only benchmarks
uv run pytest -m integration -k benchmark
```

**Prerequisites:**
- Set `AZURE_OPENAI_API_KEY` or `OPENAI_API_KEY` in your environment
- Place `.expected.json` fixtures in `sample-data/` (see BLK-104 for label format)

**Skip behavior:** Integration tests skip cleanly with a clear message when
credentials or fixtures are missing — they never fail the suite.

### Accuracy Reports

Integration runs produce machine-readable accuracy reports in `.adep/reports/`:
- `accuracy_{timestamp}.json` — per-field accuracy, confidence calibration, failures
- `benchmarks_{timestamp}.json` — latency benchmarks with pass/fail vs targets

### Confidence Calibration

The harness measures Expected Calibration Error (ECE) and flags any confidence
bucket where `|reported - actual| > 0.15` as a calibration failure.
