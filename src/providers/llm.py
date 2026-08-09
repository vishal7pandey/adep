"""Text-only LLM client for Azure OpenAI chat completions [BLK-067, BLK-070].

Wraps Azure OpenAI for text-only chat calls (no vision). Reuses the same
Azure client as the VLM provider but with text messages instead of image
content. Returns LLMResponse with token usage [BLK-050].
"""

from __future__ import annotations

import logging
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from src.agent.token_tracking import LLMResponse, estimate_tokens
from src.config import settings

logger = logging.getLogger(__name__)


def _get_azure_client() -> Any:
    """Lazy-load the Azure OpenAI client (shared singleton)."""
    from src.providers.vlm_azure import _get_client
    return _get_client()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry_error_callback=lambda retry_state: None,
)
def _call_llm(system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> Any:
    """Call Azure OpenAI with text-only messages.

    Returns the raw chat completion response, or None if all retries failed.
    """
    client = _get_azure_client()
    deployment = settings.azure_chat_deployment

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
    )
    return response


def invoke_llm(system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> LLMResponse:
    """Invoke LLM with system + user prompts, return LLMResponse with token usage.

    Args:
        system_prompt: System message instructing the LLM.
        user_prompt: User message with the actual request.
        max_tokens: Max output tokens.

    Returns:
        LLMResponse with content and token counts. On failure, returns
        LLMResponse with empty content and zero tokens.
    """
    try:
        response = _call_llm(system_prompt, user_prompt, max_tokens=max_tokens)
        if response is None:
            logger.warning("LLM call failed after retries")
            return LLMResponse(content="", input_tokens=0, output_tokens=0)

        content = response.choices[0].message.content or ""
        input_tokens = response.usage.prompt_tokens if response.usage else estimate_tokens(system_prompt + user_prompt)
        output_tokens = response.usage.completion_tokens if response.usage else estimate_tokens(content)

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return LLMResponse(content="", input_tokens=0, output_tokens=0)
