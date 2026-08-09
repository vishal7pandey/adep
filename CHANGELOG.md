# Changelog

All notable changes to ADEP are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- BLK-050: Token tracking & cost calculation
- BLK-051: Budget limits & enforcement (per-run, per-definition, global)
- BLK-059: Document import & pre-processing pipeline (PDF, PNG, JPG, TIFF, BMP)
- BLK-060: Trace export (JSON, CSV)
- BLK-061: Search & filter for definitions, skills, templates, runs
- BLK-063: CI/CD pipeline, Docker, pre-commit hooks
- BLK-064: Webhook notifications
- BLK-065: i18n backend (Accept-Language, locales endpoint)
- BLK-066: Advanced analytics endpoints
- Wave 5: API docs (OpenAPI, landing page, HTTPError model), dev scripts (seed, Makefile), health checks, request logging middleware
- SSE events: `field_update`, `status_change`, `token_usage`, `budget_warning`, `budget_exceeded`
- Agent control: pause, resume, stop, rollback [BLK-046]
- HITL gate approval [BLK-047]
- Context compaction [BLK-039]

### Changed
- `field_update` SSE event: `field` is now a string (field name), not nested object
- `POST /runs` returns 429 when budget exceeded

### Security
- HMAC signature support for webhooks [BLK-064]
