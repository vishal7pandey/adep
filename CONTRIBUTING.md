# Contributing to ADEP

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url> && cd ade

# 2. Install dependencies (requires uv)
uv sync --all-extras

# 3. Configure environment
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# 4. Seed sample data
uv run python -m scripts.seed

# 5. Start the dev server
uv run uvicorn src.api.main:app --reload

# 6. Run tests
uv run pytest
```

## Development Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start backend server with hot reload |
| `make test` | Run all tests |
| `make test-cov` | Run tests with coverage (80% minimum) |
| `make seed` | Populate store with sample data |
| `make reset` | Clear `.adep/` data directory |
| `make clean` | Remove Python cache files |

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## Project Structure

```
src/
  api/          FastAPI app, routes, SSE emitter, run engine
  agent/        ReAct graph, state, validator, token tracking, budget
  eval/         Evaluation harness (ANLS, SMuDGE metrics)
  tools/        Tool registry, OCR, VLM, crop, read_chart
  templates/    Extraction template base + InvoiceTemplate
  skills/       Skill definitions (invoice, etc.)
  definitions/  Agent definition store
  config.py     Pydantic Settings (env-driven)
scripts/
  seed.py       Sample data seeding
```

## Testing

Tests are in `src/tests/`. Run with:

```bash
uv run uvicorn src.api.main:app --reload  # start dev server
uv run pytest                               # all tests
uv run pytest --cov=src                     # with coverage
```

## Code Style

- Follow PEP 8 (max line length: 100 chars)
- Use type hints (Python 3.10+ syntax: `list[str]`, `X | None`)
- Group imports: stdlib → third-party → local
- No wildcard imports
- Use f-strings for string formatting
