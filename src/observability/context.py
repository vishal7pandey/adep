"""Context propagation via contextvars [BLK-130].

Provides request_id, run_id, definition_id, and cycle context variables
that are automatically attached to structured log records and OTel span
attributes without threading them through every function signature.
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Any, Iterator


# Context variables — propagated automatically across async boundaries
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None,
)
run_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "run_id", default=None,
)
definition_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "definition_id", default=None,
)
cycle_var: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "cycle", default=None,
)


def get_context() -> dict[str, Any]:
    """Return all current context values as a dict."""
    ctx: dict[str, Any] = {}
    val = request_id_var.get()
    if val is not None:
        ctx["request_id"] = val
    val = run_id_var.get()
    if val is not None:
        ctx["run_id"] = val
    val = definition_id_var.get()
    if val is not None:
        ctx["definition_id"] = val
    val = cycle_var.get()
    if val is not None:
        ctx["cycle"] = val
    return ctx


@contextmanager
def set_context(**kwargs: Any) -> Iterator[None]:
    """Set context variables within a scope, restoring on exit.

    Usage::

        with set_context(run_id="run-42", definition_id="def-invoice"):
            # logs and spans inside this block carry run_id and definition_id
            ...
    """
    tokens: list[tuple[contextvars.ContextVar[Any], contextvars.Token[Any]]] = []
    var_map = {
        "request_id": request_id_var,
        "run_id": run_id_var,
        "definition_id": definition_id_var,
        "cycle": cycle_var,
    }
    for key, value in kwargs.items():
        var = var_map.get(key)
        if var is not None:
            token = var.set(value)
            tokens.append((var, token))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)
