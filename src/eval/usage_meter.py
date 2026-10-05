"""Measure and cap OpenAI chat-completion spend from outside the engines (ADE-31).

`UsageMeter` wraps `Completions.create` and `AsyncCompletions.create` on the `openai` SDK at class
level, so every client instance is measured (the old engine's shared client and the new engine's
pydantic-ai client alike) without either engine knowing. It reads only `response.usage` and never
sees or stores a key, a prompt or an error message.
"""

from __future__ import annotations

from typing import Any

from openai.resources.chat.completions import AsyncCompletions, Completions


class SpendCapReached(RuntimeError):
    """Raised before a model call that would exceed the call or token cap."""


def _count(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


class UsageMeter:
    """Context manager: counts calls and tokens, refuses calls past a hard cap."""

    def __init__(self, max_calls: int | None = None, max_tokens: int | None = None) -> None:
        self.max_calls = max_calls
        self.max_tokens = max_tokens
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self._originals: tuple[Any, Any] | None = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def exhausted(self) -> bool:
        return (self.max_calls is not None and self.calls >= self.max_calls) or (
            self.max_tokens is not None and self.total_tokens >= self.max_tokens
        )

    def snapshot(self) -> tuple[int, int, int]:
        """(calls, prompt_tokens, completion_tokens) so far, for per-run deltas."""
        return self.calls, self.prompt_tokens, self.completion_tokens

    def _check(self) -> None:
        if self.exhausted:
            raise SpendCapReached("spend cap reached")

    def _record(self, response: Any) -> None:
        self.calls += 1
        usage = getattr(response, "usage", None)
        self.prompt_tokens += _count(getattr(usage, "prompt_tokens", 0))
        self.completion_tokens += _count(getattr(usage, "completion_tokens", 0))

    def __enter__(self) -> UsageMeter:
        if self._originals is not None:
            raise RuntimeError("UsageMeter is already active")
        sync_create, async_create = Completions.create, AsyncCompletions.create
        self._originals = (sync_create, async_create)
        meter = self

        def metered_sync(*args: Any, **kwargs: Any) -> Any:
            meter._check()
            response = sync_create(*args, **kwargs)
            meter._record(response)
            return response

        async def metered_async(*args: Any, **kwargs: Any) -> Any:
            meter._check()
            response = await async_create(*args, **kwargs)
            meter._record(response)
            return response

        Completions.create = metered_sync  # type: ignore[method-assign,assignment]
        AsyncCompletions.create = metered_async  # type: ignore[method-assign,assignment]
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._originals is not None:
            Completions.create, AsyncCompletions.create = self._originals  # type: ignore[method-assign,assignment]
            self._originals = None
