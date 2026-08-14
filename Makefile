# ADEP — Agentic Document Extraction Platform
# Makefile for common dev tasks [Wave 5.3]

.PHONY: dev test test-cov seed reset clean install help

# Default target
help:
	@echo "ADEP — Agentic Document Extraction Platform"
	@echo ""
	@echo "Targets:"
	@echo "  make install    Install Python dependencies"
	@echo "  make dev        Start backend server (uvicorn)"
	@echo "  make test       Run all tests"
	@echo "  make test-cov   Run tests with coverage report"
	@echo "  make seed       Populate store with sample data"
	@echo "  make reset      Clear .adep/ data directory"
	@echo "  make clean      Remove __pycache__ and .pyc files"

install:
	uv sync --all-extras

dev:
	uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest src/tests/ -v

test-cov:
	uv run pytest src/tests/ --cov=src --cov-report=term-missing --cov-fail-under=80

seed:
	uv run python -m scripts.seed

reset:
	rm -rf .adep/
	@echo "Cleared .adep/ data directory"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned cache files"
