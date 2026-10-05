"""Regression tests for multi-page document collapse bug [SCRUM-35, BLK-220].

Verifies that:
1. build_initial_state with page_paths creates correct multi-page DocumentHandle.
2. build_initial_state without page_paths falls back to single-page (backward compat).
3. DocumentState page count matches DocumentHandle page count.
4. Plan node includes page info in LLM prompt for multi-page documents.
5. Plan node includes single-page info for single-page documents.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agent.state import (
    AgentState,
    DocumentHandle,
    DocumentState,
    PageStatus,
    RunStatus,
)
from src.run import build_initial_state
from src.skills.base import Skill
from src.templates.base import Template


class FakeTemplate(Template):
    """Minimal template for testing."""

    pass


@pytest.fixture
def fake_skill():
    """Minimal skill for testing."""
    return Skill(
        name="test_skill",
        system_prompt="You are a test agent.",
        probe_order=[("text", "OCR first")],
        failure_actions=[],
        confidence_overrides={},
    )


@pytest.fixture
def fake_image(tmp_path):
    """Create a fake image file for testing."""
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG fake")
    return img


class TestBuildInitialStateMultiPage:
    """Verify build_initial_state handles page_paths correctly [BLK-220]."""

    def test_single_page_no_page_paths(self, fake_skill, fake_image):
        """Without page_paths, defaults to single-page handle (backward compat)."""
        state = build_initial_state(
            str(fake_image),
            FakeTemplate,
            fake_skill,
        )
        handle = state["document"]
        assert handle.pages == 1
        assert len(handle.page_paths) == 1
        assert str(fake_image.resolve()) in handle.page_paths[0]
        assert state["document_state"].total_pages == 1

    def test_multi_page_with_page_paths(self, fake_skill, fake_image):
        """With page_paths, creates multi-page handle and DocumentState."""
        page_paths = [
            str(fake_image),
            str(fake_image),  # same file, just for testing
            str(fake_image),
        ]
        state = build_initial_state(
            str(fake_image),
            FakeTemplate,
            fake_skill,
            page_paths=page_paths,
        )
        handle = state["document"]
        assert handle.pages == 3
        assert len(handle.page_paths) == 3
        assert handle.page_paths == page_paths
        assert state["document_state"].total_pages == 3
        assert len(state["document_state"].pages) == 3
        assert all(p.status == PageStatus.PENDING for p in state["document_state"].pages)

    def test_empty_page_paths_falls_back_to_single(self, fake_skill, fake_image):
        """Empty page_paths list falls back to single-page."""
        state = build_initial_state(
            str(fake_image),
            FakeTemplate,
            fake_skill,
            page_paths=[],
        )
        handle = state["document"]
        assert handle.pages == 1
        assert len(handle.page_paths) == 1

    def test_none_page_paths_falls_back_to_single(self, fake_skill, fake_image):
        """None page_paths falls back to single-page."""
        state = build_initial_state(
            str(fake_image),
            FakeTemplate,
            fake_skill,
            page_paths=None,
        )
        handle = state["document"]
        assert handle.pages == 1

    def test_two_page_document(self, fake_skill, fake_image):
        """Two-page document gets correct handle and state."""
        page_paths = [str(fake_image), str(fake_image)]
        state = build_initial_state(
            str(fake_image),
            FakeTemplate,
            fake_skill,
            page_paths=page_paths,
        )
        handle = state["document"]
        assert handle.pages == 2
        assert state["document_state"].total_pages == 2
        assert state["document_state"].current_page == 0

    def test_document_state_pages_match_page_paths_count(self, fake_skill, fake_image):
        """DocumentState pages list length matches page_paths length."""
        page_paths = [str(fake_image)] * 5
        state = build_initial_state(
            str(fake_image),
            FakeTemplate,
            fake_skill,
            page_paths=page_paths,
        )
        assert len(state["document_state"].pages) == 5
        for i, page in enumerate(state["document_state"].pages):
            assert page.page_number == i

    def test_page_paths_preserved_in_handle(self, fake_skill, fake_image):
        """Page paths are preserved exactly as provided in DocumentHandle."""
        page_paths = [
            "/data/doc/page_001.png",
            "/data/doc/page_002.png",
            "/data/doc/page_003.png",
        ]
        state = build_initial_state(
            str(fake_image),
            FakeTemplate,
            fake_skill,
            page_paths=page_paths,
        )
        assert state["document"].page_paths == page_paths


class TestPlanNodeMultiPageAwareness:
    """Verify plan_node includes page info in LLM prompt [BLK-220]."""

    def _make_state(self, pages: int, page_paths: list[str] | None = None) -> AgentState:
        """Build a minimal AgentState for plan_node testing."""
        if page_paths is None:
            page_paths = ["/test/img.png"] * pages
        handle = DocumentHandle(
            path="/test/doc.pdf",
            pages=pages,
            page_paths=page_paths,
        )
        doc_state = DocumentState.from_page_count(pages)
        return AgentState(
            document=handle,
            template_schema=type,
            skill_name="test",
            regions={},
            extraction={},
            trace=[],
            step=0,
            field_attempts={},
            total_cycles=0,
            status=RunStatus.PLANNING,
            attempted={},
            provider_errors=[],
            compaction_summary="",
            _planned_action=None,
            _tool_result=None,
            _compact_requested=False,
            document_state=doc_state,
            consecutive_non_improving=0,
            token_usage=[],
            total_tokens=0,
            total_cost_usd=0.0,
            task_type="extraction",
        )

    def test_multi_page_prompt_includes_page_count(self):
        """Plan node prompt for multi-page doc includes page count."""
        from src.agent.graph import plan_node

        state = self._make_state(3, ["/p1.png", "/p2.png", "/p3.png"])
        captured_prompt = {}

        def mock_invoke(system_prompt, user_prompt):
            captured_prompt["user"] = user_prompt
            return '{"thought": "test", "tool": "", "args": {}, "field": ""}'

        mock_llm = MagicMock()
        mock_llm.invoke = mock_invoke

        mock_skill = MagicMock()
        mock_skill.system_prompt = "You are a test agent."
        mock_skill.probe_order = []

        mock_registry = MagicMock()
        mock_registry.specs.return_value = []

        plan_node(
            state,
            llm_client=mock_llm,
            skill=mock_skill,
            registry=mock_registry,
        )

        assert "3 pages" in captured_prompt["user"]
        assert "/p1.png" in captured_prompt["user"]
        assert "/p2.png" in captured_prompt["user"]
        assert "/p3.png" in captured_prompt["user"]
        assert "Page 0" in captured_prompt["user"]
        assert "Page 1" in captured_prompt["user"]
        assert "Page 2" in captured_prompt["user"]

    def test_single_page_prompt_includes_single_page_info(self):
        """Plan node prompt for single-page doc mentions single page."""
        from src.agent.graph import plan_node

        state = self._make_state(1, ["/single.png"])
        captured_prompt = {}

        def mock_invoke(system_prompt, user_prompt):
            captured_prompt["user"] = user_prompt
            return '{"thought": "test", "tool": "", "args": {}, "field": ""}'

        mock_llm = MagicMock()
        mock_llm.invoke = mock_invoke

        mock_skill = MagicMock()
        mock_skill.system_prompt = "You are a test agent."
        mock_skill.probe_order = []

        mock_registry = MagicMock()
        mock_registry.specs.return_value = []

        plan_node(
            state,
            llm_client=mock_llm,
            skill=mock_skill,
            registry=mock_registry,
        )

        assert "Single-page document" in captured_prompt["user"]
        assert "/single.png" in captured_prompt["user"]

    def test_multi_page_prompt_includes_navigation_hint(self):
        """Plan node prompt for multi-page doc includes navigation hint."""
        from src.agent.graph import plan_node

        state = self._make_state(5, ["/p0.png", "/p1.png", "/p2.png", "/p3.png", "/p4.png"])
        captured_prompt = {}

        def mock_invoke(system_prompt, user_prompt):
            captured_prompt["user"] = user_prompt
            return '{"thought": "test", "tool": "", "args": {}, "field": ""}'

        mock_llm = MagicMock()
        mock_llm.invoke = mock_invoke

        mock_skill = MagicMock()
        mock_skill.system_prompt = "You are a test agent."
        mock_skill.probe_order = []

        mock_registry = MagicMock()
        mock_registry.specs.return_value = []

        plan_node(
            state,
            llm_client=mock_llm,
            skill=mock_skill,
            registry=mock_registry,
        )

        assert "Navigate to different pages" in captured_prompt["user"]
        assert "5 pages" in captured_prompt["user"]
