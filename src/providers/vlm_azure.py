"""Azure GPT-5.4 VLM provider — vlm, read_chart, read_table [§9, BLK-006].

Uses Azure OpenAI Service with GPT-5.4 vision capabilities. Config from
env vars: AZURE_API_KEY, AZURE_CHAT_ENDPOINT, AZURE_CHAT_DEPLOYMENT.

Retry + exponential backoff on rate limits (429) [EH].
"""

from __future__ import annotations

import base64
import logging
import os
import tempfile
from typing import Any

from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from src.config import settings
from src.tools.base import Grounding, ToolResult

logger = logging.getLogger(__name__)

_client: Any = None


def _get_client() -> Any:
    """Lazy-load the OpenAI or Azure OpenAI client (singleton per process) [ADE-41]."""
    global _client
    if _client is not None:
        return _client
    try:
        if settings.active_llm_provider == "openai":
            from openai import OpenAI

            _client = OpenAI(api_key=settings.openai_api_key)
        else:
            from openai import AzureOpenAI

            _client = AzureOpenAI(
                api_key=settings.azure_api_key,
                azure_endpoint=settings.azure_chat_endpoint,
                api_version="2024-02-15-preview",
            )
        return _client
    except ImportError:
        raise RuntimeError("openai package not installed. Install with: uv add openai")


def token_limit_kwargs(limit: int) -> dict[str, int]:
    """The output-token limit under the name the active provider accepts.

    Current OpenAI models reject `max_tokens` and require `max_completion_tokens`; the Azure
    API version this project pins still takes `max_tokens`.
    """
    key = "max_completion_tokens" if settings.active_llm_provider == "openai" else "max_tokens"
    return {key: limit}


class ImagePathNotAllowed(ValueError):
    """The image path resolves outside the directories images are read from."""


def _encode_image(image_path: str) -> str:
    """Encode an image file as a base64 data URI.

    Only files under the working directory (``.adep/documents``, ``sample-data``) or the
    system temp directory (survey images and crops) are read.

    Raises:
        ImagePathNotAllowed: If the resolved path is outside both directories.
    """
    working_root = os.path.realpath(os.getcwd())
    temp_root = os.path.realpath(tempfile.gettempdir())
    real_path = os.path.realpath(image_path)
    if not (
        real_path.startswith(working_root + os.sep) or real_path.startswith(temp_root + os.sep)
    ):
        raise ImagePathNotAllowed("Image path is outside the allowed directories")
    with open(real_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    ext = image_path.rsplit(".", 1)[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type(ImagePathNotAllowed),
    retry_error_callback=lambda retry_state: None,
)
def _call_vlm(image_path: str, question: str, model: str | None = None) -> str:
    """Call Azure GPT-5.4 vision with an image and question.

    Retries on transient failures (429, timeout) with exponential backoff [EH].
    """
    client = _get_client()
    deployment = model or settings.chat_model
    image_data = _encode_image(image_path)

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ],
            }
        ],
        **token_limit_kwargs(1000),
    )
    return response.choices[0].message.content


def vlm(image_path: str, question: str, model: str | None = None, **kwargs: Any) -> ToolResult:
    """Ask the VLM a question about an image.

    Args:
        image_path: Path to the image file.
        question: Natural language question about the image content.
        model: Optional model override (defaults to AZURE_CHAT_DEPLOYMENT).

    Returns:
        ToolResult with data=answer string.
    """
    try:
        answer = _call_vlm(image_path, question, model)
        if answer is None:
            return ToolResult(
                ok=False,
                error="VLM call failed after retries (rate limit or timeout)",
                tool="vlm",
            )
        return ToolResult(ok=True, data=answer, tool="vlm")
    except RuntimeError as e:
        return ToolResult(ok=False, error=str(e), tool="vlm")
    except Exception as e:
        return ToolResult(ok=False, error=f"VLM call failed: {e}", tool="vlm")


def read_table(
    image_path: str, question: str = "Extract this table as structured data.", **kwargs: Any
) -> ToolResult:
    """Read a table from an image using the VLM.

    Args:
        image_path: Path to the image file containing a table.
        question: Optional specific question about the table.

    Returns:
        ToolResult with data=structured table text.
    """
    return vlm(image_path, question, **kwargs)


_CHART_SYSTEM_PROMPT = (
    "You are a chart data extraction assistant. Extract the underlying "
    "numerical data from the chart image. Return ONLY a JSON object with "
    "this structure: "
    '{"series": [{"label": "...", "values": [num, ...]}], '
    '"x_axis": ["label1", "label2", ...], '
    '"y_axis": {"label": "...", "min": num, "max": num}, '
    '"chart_type": "bar|line|pie|stacked_area"}. '
    "Do not include descriptions or explanations — only the JSON."
)


def read_chart(
    image_path: str,
    chart_type: str | None = None,
    question: str | None = None,
    **kwargs: Any,
) -> ToolResult:
    """Read a chart from an image and extract structured data series [BLK-040].

    Routes the chart image directly to the VLM (GPT-5.4 vision), bypassing
    OCR entirely. The VLM natively interprets chart geometry to reconstruct
    the underlying data.

    Args:
        image_path: Path to the image file containing a chart.
        chart_type: Optional hint ("bar", "line", "pie", "stacked_area").
        question: Optional specific question about the chart data.

    Returns:
        ToolResult with data=structured dict:
            {"series": [...], "x_axis": [...], "y_axis": {...}, "chart_type": "..."}
            Grounding bbox is set from the image dimensions.
    """
    import json as _json

    prompt = _CHART_SYSTEM_PROMPT
    if chart_type:
        prompt += f"\n\nThe chart type appears to be: {chart_type}."
    if question:
        prompt += f"\n\nAdditional question: {question}"

    try:
        answer = _call_vlm(image_path, prompt, kwargs.get("model"))
        if answer is None:
            return ToolResult(
                ok=False,
                error="VLM call failed after retries (rate limit or timeout)",
                tool="read_chart",
            )

        # Parse the JSON response
        try:
            start = answer.find("{")
            end = answer.rfind("}") + 1
            if start == -1 or end == 0:
                return ToolResult(
                    ok=False,
                    error=f"VLM did not return valid JSON: {answer[:200]}",
                    tool="read_chart",
                )
            data = _json.loads(answer[start:end])
        except (_json.JSONDecodeError, ValueError) as e:
            return ToolResult(
                ok=False,
                error=f"Failed to parse chart data JSON: {e}",
                tool="read_chart",
            )

        # Validate structure
        if "series" not in data:
            return ToolResult(
                ok=False,
                error="VLM response missing 'series' key",
                tool="read_chart",
            )

        # Add grounding from image dimensions
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                w, h = img.size
            grounding = Grounding(bbox=(0, 0, w, h), source_tool="read_chart", confidence=0.85)
        except Exception:
            grounding = Grounding(bbox=(0, 0, 0, 0), source_tool="read_chart", confidence=0.85)

        return ToolResult(ok=True, data=data, tool="read_chart", grounding=grounding)

    except RuntimeError as e:
        return ToolResult(ok=False, error=str(e), tool="read_chart")
    except Exception as e:
        return ToolResult(ok=False, error=f"read_chart failed: {e}", tool="read_chart")
