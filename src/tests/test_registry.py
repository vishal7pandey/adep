"""Tests for the ToolRegistry [TS, NFT]."""

from __future__ import annotations

import pytest

from src.tools.base import ToolResult, ToolSpec, ToolRegistry


def _dummy_tool(**kwargs: object) -> ToolResult:
    """A no-op tool for testing."""
    return ToolResult(ok=True, data="dummy", tool="dummy")


class TestToolRegistry:
    """Verify registry registration, lookup, and invocation."""

    def test_register_and_get(self):
        registry = ToolRegistry()
        spec = ToolSpec(name="dummy", description="A dummy tool")
        registry.register(spec, _dummy_tool)
        retrieved_spec, retrieved_func = registry.get("dummy")
        assert retrieved_spec.name == "dummy"
        assert retrieved_func is _dummy_tool

    def test_call_invokes_function(self):
        registry = ToolRegistry()
        spec = ToolSpec(name="dummy", description="A dummy tool")
        registry.register(spec, _dummy_tool)
        result = registry.call("dummy")
        assert result.ok is True
        assert result.tool == "dummy"

    def test_duplicate_registration_raises(self):
        registry = ToolRegistry()
        spec = ToolSpec(name="dummy", description="A dummy tool")
        registry.register(spec, _dummy_tool)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(spec, _dummy_tool)

    def test_get_unknown_tool_raises(self):
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")

    def test_specs_returns_all(self):
        registry = ToolRegistry()
        registry.register(ToolSpec(name="a", description="tool a"), _dummy_tool)
        registry.register(ToolSpec(name="b", description="tool b"), _dummy_tool)
        specs = registry.specs()
        assert len(specs) == 2
        assert {s.name for s in specs} == {"a", "b"}

    def test_names_returns_all(self):
        registry = ToolRegistry()
        registry.register(ToolSpec(name="a", description="tool a"), _dummy_tool)
        registry.register(ToolSpec(name="b", description="tool b"), _dummy_tool)
        assert set(registry.names()) == {"a", "b"}
