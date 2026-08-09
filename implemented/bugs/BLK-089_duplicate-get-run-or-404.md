---
id: BLK-089
type: bug
title: "Backend: duplicate _get_run_or_404 function definition in runs.py"
priority: medium
status: backlog
phase: 3
owner: backend
created: 2026-08-08T02:30:00+05:30
estimate: S
depends-on: []
tags: [backend, bug, duplicate, runs, stabilization]
---

## Bug

`src/api/routes/runs.py` defines `_get_run_or_404` **twice**:

- Line 26: `def _get_run_or_404(run_id: str) -> dict[str, Any]:`
- Line 327: `def _get_run_or_404(run_id: str) -> dict[str, Any]:`

The second definition (line 327) silently shadows the first. Both
have identical implementations, so it works by accident, but this is
a code smell that will cause confusion.

## Fix

Remove the second definition (lines 327-332). Keep only the first
(line 26-31).
