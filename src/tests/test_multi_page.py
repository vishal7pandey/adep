"""Tests for Multi-page Hierarchical State [BLK-041, §12.1, TS].

Tests cover:
- PageState creation, region management, status transitions
- DocumentState creation, navigation, region flattening
- DocumentState summary for plan node context
- Backward compatibility: single-page documents
- Field-driven page queries
- AgentState includes document_state key
"""

from __future__ import annotations

import pytest

from src.agent.state import (
    AgentState,
    DocumentHandle,
    DocumentState,
    PageState,
    PageStatus,
    RunStatus,
)
from src.tools.base import Region, RegionType


def _make_region(rid: str, page: int = 0) -> Region:
    """Build a minimal Region for testing."""
    return Region(
        id=rid,
        type=RegionType.TEXT,
        bbox=(0, 0, 100, 100),
        page=page,
    )


class TestPageState:
    """Verify PageState behavior."""

    def test_default_creation(self):
        page = PageState(page_number=0)
        assert page.page_number == 0
        assert page.regions == {}
        assert page.status == PageStatus.PENDING
        assert page.fields_extracted == set()
        assert page.text_summary == ""

    def test_add_region(self):
        page = PageState(page_number=1)
        region = _make_region("p1_r0", page=1)
        page.add_region(region)
        assert "p1_r0" in page.regions
        assert page.regions["p1_r0"] == region

    def test_mark_scanned(self):
        page = PageState(page_number=0)
        page.mark_scanned()
        assert page.status == PageStatus.SCANNED

    def test_mark_extracted(self):
        page = PageState(page_number=0)
        page.mark_extracted("invoice_number")
        assert "invoice_number" in page.fields_extracted
        assert page.status == PageStatus.EXTRACTED

    def test_multiple_fields_extracted(self):
        page = PageState(page_number=2)
        page.mark_extracted("total")
        page.mark_extracted("vendor")
        assert len(page.fields_extracted) == 2


class TestDocumentState:
    """Verify DocumentState behavior."""

    def test_from_page_count(self):
        doc = DocumentState.from_page_count(5)
        assert doc.total_pages == 5
        assert len(doc.pages) == 5
        assert all(p.status == PageStatus.PENDING for p in doc.pages)
        assert doc.current_page == 0

    def test_from_page_count_single(self):
        doc = DocumentState.from_page_count(1)
        assert doc.total_pages == 1
        assert len(doc.pages) == 1

    def test_get_page_valid(self):
        doc = DocumentState.from_page_count(3)
        page = doc.get_page(1)
        assert page is not None
        assert page.page_number == 1

    def test_get_page_invalid(self):
        doc = DocumentState.from_page_count(3)
        assert doc.get_page(5) is None
        assert doc.get_page(-1) is None

    def test_current_page_state(self):
        doc = DocumentState.from_page_count(3)
        assert doc.current_page_state is not None
        assert doc.current_page_state.page_number == 0

    def test_navigate_to_valid(self):
        doc = DocumentState.from_page_count(5)
        assert doc.navigate_to(3) is True
        assert doc.current_page == 3
        assert doc.current_page_state.page_number == 3

    def test_navigate_to_invalid(self):
        doc = DocumentState.from_page_count(3)
        assert doc.navigate_to(10) is False
        assert doc.current_page == 0  # unchanged

    def test_navigate_to_negative(self):
        doc = DocumentState.from_page_count(3)
        assert doc.navigate_to(-1) is False

    def test_all_regions_flat(self):
        doc = DocumentState.from_page_count(2)
        doc.pages[0].add_region(_make_region("p0_r0", page=0))
        doc.pages[0].add_region(_make_region("p0_r1", page=0))
        doc.pages[1].add_region(_make_region("p1_r0", page=1))
        flat = doc.all_regions()
        assert len(flat) == 3
        assert "p0_r0" in flat
        assert "p0_r1" in flat
        assert "p1_r0" in flat

    def test_all_regions_empty(self):
        doc = DocumentState.from_page_count(3)
        assert doc.all_regions() == {}

    def test_pages_with_field(self):
        doc = DocumentState.from_page_count(3)
        doc.pages[0].mark_extracted("vendor")
        doc.pages[2].mark_extracted("vendor")
        result = doc.pages_with_field("vendor")
        assert result == [0, 2]

    def test_pages_with_field_not_found(self):
        doc = DocumentState.from_page_count(3)
        assert doc.pages_with_field("nonexistent") == []

    def test_summary_includes_all_pages(self):
        doc = DocumentState.from_page_count(3)
        doc.pages[0].add_region(_make_region("p0_r0", page=0))
        doc.pages[0].mark_scanned()
        doc.pages[1].mark_extracted("total")
        summary = doc.summary()
        assert "3 pages" in summary
        assert "Page 0" in summary
        assert "Page 1" in summary
        assert "Page 2" in summary
        assert "scanned" in summary
        assert "extracted" in summary

    def test_summary_shows_current_page(self):
        doc = DocumentState.from_page_count(5)
        doc.navigate_to(2)
        summary = doc.summary()
        assert "current: page 2" in summary


class TestDocumentStateBackwardCompat:
    """Verify single-page documents work as before."""

    def test_single_page_document(self):
        """Single-page document should have 1 PageState with all regions."""
        doc = DocumentState.from_page_count(1)
        doc.pages[0].add_region(_make_region("r0", page=0))
        doc.pages[0].add_region(_make_region("r1", page=0))
        flat = doc.all_regions()
        assert len(flat) == 2
        assert doc.current_page == 0

    def test_empty_document(self):
        """Zero-page document is valid but empty."""
        doc = DocumentState.from_page_count(0)
        assert doc.total_pages == 0
        assert doc.pages == []
        assert doc.all_regions() == {}
        assert doc.get_page(0) is None


class TestAgentStateHasDocumentState:
    """Verify AgentState TypedDict includes document_state."""

    def test_document_state_in_state_dict(self):
        """A state dict should accept document_state key."""
        doc = DocumentState.from_page_count(3)
        state: AgentState = {
            "document": DocumentHandle(path="test.pdf", pages=3),
            "template_schema": type,
            "skill_name": "invoice",
            "regions": {},
            "extraction": {},
            "trace": [],
            "step": 0,
            "field_attempts": {},
            "total_cycles": 0,
            "status": RunStatus.PLANNING,
            "attempted": {},
            "provider_errors": [],
            "compaction_summary": "",
            "_planned_action": None,
            "_tool_result": None,
            "_compact_requested": False,
            "document_state": doc,
        }
        assert state["document_state"].total_pages == 3
        assert state["document_state"].current_page == 0


class TestMultiPageNavigation:
    """Simulate a 5-page extraction with page-aware navigation."""

    def test_5_page_navigation_flow(self):
        """Agent navigates through 5 pages, extracting fields from each."""
        doc = DocumentState.from_page_count(5)

        # Page 0: detect layout
        doc.pages[0].add_region(_make_region("p0_r0", page=0))
        doc.pages[0].add_region(_make_region("p0_r1", page=0))
        doc.pages[0].mark_scanned()

        # Page 1: extract invoice_number
        doc.navigate_to(1)
        doc.pages[1].add_region(_make_region("p1_r0", page=1))
        doc.pages[1].mark_scanned()
        doc.pages[1].mark_extracted("invoice_number")

        # Page 3: extract total
        doc.navigate_to(3)
        doc.pages[3].add_region(_make_region("p3_r0", page=3))
        doc.pages[3].mark_scanned()
        doc.pages[3].mark_extracted("total")

        # Verify state
        assert doc.current_page == 3
        assert doc.pages[0].status == PageStatus.SCANNED
        assert doc.pages[1].status == PageStatus.EXTRACTED
        assert doc.pages[3].status == PageStatus.EXTRACTED
        assert doc.pages[2].status == PageStatus.PENDING  # not visited
        assert doc.pages[4].status == PageStatus.PENDING  # not visited

        # Verify field queries
        assert doc.pages_with_field("invoice_number") == [1]
        assert doc.pages_with_field("total") == [3]

        # Verify region count
        assert len(doc.all_regions()) == 4

    def test_20_page_document_navigation(self):
        """Simulate a 20-page document — agent navigates to correct pages."""
        doc = DocumentState.from_page_count(20)

        # Agent needs field on page 15
        assert doc.navigate_to(15) is True
        doc.pages[15].mark_scanned()
        doc.pages[15].mark_extracted("lease_clause_3")

        # Agent needs field on page 3
        assert doc.navigate_to(3) is True
        doc.pages[3].mark_scanned()
        doc.pages[3].mark_extracted("lease_start_date")

        # Verify
        assert doc.current_page == 3
        assert doc.pages_with_field("lease_clause_3") == [15]
        assert doc.pages_with_field("lease_start_date") == [3]
        assert doc.pages[0].status == PageStatus.PENDING
        assert doc.pages[15].status == PageStatus.EXTRACTED
