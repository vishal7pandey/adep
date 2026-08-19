"""Regression tests for tool configuration contract drift [SCRUM-32, BLK-217].

Verifies that:
1. AgentDefinition.tool_names are actually used to filter the ToolRegistry.
2. Prebuilt definition tool_names only reference tools that exist in the registry.
3. Stale tool names (crop_image, cross_check, locate, detect_figures) are gone.
4. build_tool_registry with empty/None tool_names returns all tools (backward compat).
5. build_tool_registry with unknown tool_names logs warnings but doesn't crash.
6. build_tool_registry with all-unknown tool_names raises RuntimeError.
"""

from __future__ import annotations

import pytest

from src.run import build_tool_registry


class TestToolNamesFiltering:
    """Verify build_tool_registry respects tool_names parameter [BLK-217]."""

    def test_no_filter_returns_all_tools(self):
        """build_tool_registry() with no args returns all tools."""
        registry = build_tool_registry()
        all_names = set(registry.names())
        assert len(all_names) > 0

    def test_empty_list_returns_all_tools(self):
        """build_tool_registry(tool_names=[]) returns all tools (backward compat)."""
        registry = build_tool_registry(tool_names=[])
        all_names = set(registry.names())
        assert len(all_names) > 0

    def test_none_returns_all_tools(self):
        """build_tool_registry(tool_names=None) returns all tools."""
        registry = build_tool_registry(tool_names=None)
        all_names = set(registry.names())
        assert len(all_names) > 0

    def test_subset_filter(self):
        """build_tool_registry with a subset returns only those tools."""
        full = build_tool_registry()
        full_names = full.names()
        # Pick first 2 tools that exist
        subset = full_names[:2]
        registry = build_tool_registry(tool_names=subset)
        assert set(registry.names()) == set(subset)

    def test_unknown_names_logged_not_fatal(self):
        """Unknown tool names are logged as warnings but valid ones still work."""
        full = build_tool_registry()
        real_name = full.names()[0]
        registry = build_tool_registry(tool_names=[real_name, "nonexistent_tool"])
        assert real_name in registry.names()
        assert "nonexistent_tool" not in registry.names()

    def test_all_unknown_raises(self):
        """All-unknown tool names raises RuntimeError."""
        with pytest.raises(RuntimeError, match="empty after filtering"):
            build_tool_registry(tool_names=["totally_fake_1", "totally_fake_2"])


class TestPrebuiltDefinitionToolNames:
    """Verify prebuilt definitions only reference real tool names [BLK-217]."""

    @pytest.fixture(scope="class")
    def registry_names(self):
        """All tool names available in the registry."""
        registry = build_tool_registry()
        return set(registry.names())

    @pytest.fixture(scope="class")
    def prebuilt_defs(self):
        """All prebuilt definitions."""
        from src.definitions.prebuilt import PREBUILT_DEFINITIONS
        return PREBUILT_DEFINITIONS

    def test_all_prebuilt_tool_names_exist_in_registry(self, registry_names, prebuilt_defs):
        """Every tool_name in every prebuilt definition must exist in the registry."""
        stale = []
        for defn in prebuilt_defs:
            for name in defn.get("tool_names", []):
                if name not in registry_names:
                    stale.append((defn["id"], name))
        assert not stale, (
            f"Prebuilt definitions reference tools not in registry: {stale}"
        )

    def test_no_stale_crop_image(self, prebuilt_defs):
        """No prebuilt definition references the stale 'crop_image' name."""
        for defn in prebuilt_defs:
            assert "crop_image" not in defn.get("tool_names", []), (
                f"{defn['id']} still uses stale 'crop_image'"
            )

    def test_no_stale_cross_check(self, prebuilt_defs):
        """No prebuilt definition references the stale 'cross_check' name."""
        for defn in prebuilt_defs:
            assert "cross_check" not in defn.get("tool_names", []), (
                f"{defn['id']} still uses stale 'cross_check'"
            )

    def test_no_stale_locate(self, prebuilt_defs):
        """No prebuilt definition references the stale 'locate' name."""
        for defn in prebuilt_defs:
            assert "locate" not in defn.get("tool_names", []), (
                f"{defn['id']} still uses stale 'locate'"
            )

    def test_no_stale_detect_figures(self, prebuilt_defs):
        """No prebuilt definition references the stale 'detect_figures' name."""
        for defn in prebuilt_defs:
            assert "detect_figures" not in defn.get("tool_names", []), (
                f"{defn['id']} still uses stale 'detect_figures'"
            )

    def test_all_prebuilt_have_tool_names(self, prebuilt_defs):
        """Every prebuilt definition has a non-empty tool_names list."""
        for defn in prebuilt_defs:
            names = defn.get("tool_names", [])
            assert len(names) > 0, f"{defn['id']} has empty tool_names"


class TestSkillToolMetadata:
    """Verify _skill_tools metadata matches prebuilt definition tool_names [BLK-217]."""

    def test_skill_tools_no_stale_names(self):
        """_skill_tools mapping should not contain stale tool names."""
        from src.definitions.prebuilt import _skill_tools
        stale_names = {"crop_image", "cross_check", "locate", "detect_figures"}
        for skill_id, tools in _skill_tools.items():
            for tool in tools:
                assert tool not in stale_names, (
                    f"_skill_tools[{skill_id!r}] still references stale {tool!r}"
                )
