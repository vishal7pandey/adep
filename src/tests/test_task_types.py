"""Tests for Task Type Abstraction — BLK-109.

Tests the OutputContract hierarchy, RunResult hierarchy, TaskValidator
dispatch, and new GapType values.
"""

from __future__ import annotations

import pytest

from src.agent.validator import (
    GapReport,
    GapType,
    TaskValidator,
    ValidatorConfig,
)
from src.templates.base import (
    ExtractedResult,
    FieldExtractionContract,
    FieldExtractionResult,
    GraphExtractionContract,
    GraphExtractionResult,
    OutputContract,
    RunResult,
    Template,
)


class TestOutputContractHierarchy:
    """Verify OutputContract hierarchy and aliases [BLK-109]."""

    def test_template_is_field_extraction_contract_alias(self):
        assert Template is FieldExtractionContract

    def test_extracted_result_is_field_extraction_result_alias(self):
        assert ExtractedResult is FieldExtractionResult

    def test_field_extraction_contract_task_type(self):
        assert FieldExtractionContract().task_type == "extraction"

    def test_graph_extraction_contract_task_type(self):
        assert GraphExtractionContract().task_type == "graph_extraction"

    def test_output_contract_is_base(self):
        assert issubclass(FieldExtractionContract, OutputContract)
        assert issubclass(GraphExtractionContract, OutputContract)

    def test_existing_templates_subclass_field_extraction_contract(self):
        from src.templates.invoice import InvoiceTemplate
        assert issubclass(InvoiceTemplate, FieldExtractionContract)
        assert InvoiceTemplate.model_fields["task_type"].default == "extraction"


class TestRunResultHierarchy:
    """Verify RunResult hierarchy [BLK-109]."""

    def test_field_extraction_result_is_run_result(self):
        assert issubclass(FieldExtractionResult, RunResult)

    def test_graph_extraction_result_is_run_result(self):
        assert issubclass(GraphExtractionResult, RunResult)

    def test_field_extraction_result_defaults(self):
        result = FieldExtractionResult(is_complete=True)
        assert result.values is None
        assert result.field_values == {}
        assert result.status == "complete"

    def test_graph_extraction_result_defaults(self):
        result = GraphExtractionResult(is_complete=True)
        assert result.graph == {"nodes": [], "edges": []}
        assert result.node_grounding == {}
        assert result.edge_grounding == {}
        assert result.serialized_output == {}


class TestNewGapTypes:
    """Verify new GapType enum values [BLK-109]."""

    @pytest.mark.parametrize("gap_type", [
        GapType.SYMBOL_UNCLASSIFIED,
        GapType.TAG_UNREADABLE,
        GapType.CONNECTION_AMBIGUOUS,
        GapType.TOPOLOGY_VIOLATION,
        GapType.NODE_MISSING,
        GapType.EDGE_MISSING,
        GapType.ATTRIBUTE_MISSING,
        GapType.SERIALIZATION_FAILED,
    ])
    def test_gap_type_exists(self, gap_type: GapType):
        assert gap_type.value  # non-empty string value

    def test_gap_type_is_str_enum(self):
        assert isinstance(GapType.NODE_MISSING.value, str)

    def test_existing_gap_types_preserved(self):
        assert GapType.MISSING.value == "missing"
        assert GapType.INVARIANT_FAILED.value == "invariant_failed"


class TestAgentDefinitionTaskType:
    """Verify AgentDefinition has task_type field [BLK-109]."""

    def test_default_task_type_is_extraction(self):
        from src.definitions.base import AgentDefinition, AgentConfig
        defn = AgentDefinition(
            id="test-def",
            name="Test",
            skill_id="invoice",
            template_id="invoice",
        )
        assert defn.task_type == "extraction"

    def test_task_type_can_be_overridden(self):
        from src.definitions.base import AgentDefinition
        defn = AgentDefinition(
            id="test-graph",
            name="Test Graph",
            skill_id="pid",
            template_id="pid",
            task_type="graph_extraction",
        )
        assert defn.task_type == "graph_extraction"


class TestTaskValidatorDispatch:
    """Verify TaskValidator dispatches by task_type [BLK-109]."""

    def test_extraction_dispatch(self):
        from src.templates.invoice import InvoiceTemplate
        from src.tools.base import FieldValue, Grounding

        validator = TaskValidator()
        contract = InvoiceTemplate
        result = FieldExtractionResult(
            is_complete=False,
            field_values={},
        )
        gap_report = validator.validate(
            result=result,
            contract=contract,
            invariants=[],
            config=ValidatorConfig(),
        )
        assert isinstance(gap_report, GapReport)
        # Empty extraction should have gaps (missing fields)
        assert not gap_report.is_complete

    def test_graph_extraction_dispatch(self):
        validator = TaskValidator()
        contract = GraphExtractionContract(
            output_formats=["graphml"],
        )
        result = GraphExtractionResult(is_complete=False)
        gap_report = validator.validate(
            result=result,
            contract=contract,
        )
        assert isinstance(gap_report, GapReport)
        # Empty graph should have gaps
        assert not gap_report.is_complete
        gap_types = [g.gap_type for g in gap_report.gaps]
        assert GapType.NODE_MISSING in gap_types
        assert GapType.EDGE_MISSING in gap_types

    def test_graph_validation_passes_with_complete_graph(self):
        validator = TaskValidator()
        contract = GraphExtractionContract(
            output_formats=["graphml"],
        )
        result = GraphExtractionResult(
            is_complete=True,
            graph={
                "nodes": [
                    {"id": "n1", "type": "valve"},
                    {"id": "n2", "type": "pipe"},
                ],
                "edges": [
                    {"source": "n1", "target": "n2"},
                ],
            },
            node_grounding={
                "n1": (0, 0, 10, 10),
                "n2": (20, 20, 30, 30),
            },
            serialized_output={"graphml": "<graphml/>"},
        )
        gap_report = validator.validate(
            result=result,
            contract=contract,
        )
        assert gap_report.is_complete
        assert len(gap_report.gaps) == 0

    def test_graph_validation_detects_orphan_node(self):
        validator = TaskValidator()
        contract = GraphExtractionContract(
            output_formats=["graphml"],
        )
        result = GraphExtractionResult(
            is_complete=False,
            graph={
                "nodes": [
                    {"id": "n1", "type": "valve"},
                    {"id": "n2", "type": "pipe"},
                    {"id": "n3", "type": "instrument"},
                ],
                "edges": [
                    {"source": "n1", "target": "n2"},
                ],
            },
            node_grounding={
                "n1": (0, 0, 10, 10),
                "n2": (20, 20, 30, 30),
                "n3": (40, 40, 50, 50),
            },
            serialized_output={"graphml": "<graphml/>"},
        )
        gap_report = validator.validate(
            result=result,
            contract=contract,
        )
        assert not gap_report.is_complete
        topology_gaps = [g for g in gap_report.gaps if g.gap_type == GapType.TOPOLOGY_VIOLATION]
        assert len(topology_gaps) == 1
        assert "n3" in topology_gaps[0].field

    def test_graph_validation_detects_missing_serialization(self):
        validator = TaskValidator()
        contract = GraphExtractionContract(
            output_formats=["dexpi", "graphml"],
        )
        result = GraphExtractionResult(
            is_complete=False,
            graph={
                "nodes": [{"id": "n1", "type": "valve"}],
                "edges": [],
            },
            node_grounding={"n1": (0, 0, 10, 10)},
            serialized_output={"graphml": "<graphml/>"},
        )
        gap_report = validator.validate(
            result=result,
            contract=contract,
        )
        assert not gap_report.is_complete
        serialization_gaps = [g for g in gap_report.gaps if g.gap_type == GapType.SERIALIZATION_FAILED]
        assert len(serialization_gaps) == 1
        assert "dexpi" in serialization_gaps[0].field

    def test_unknown_task_type_raises(self):
        validator = TaskValidator()

        class UnknownContract:
            task_type = "classification"

        with pytest.raises(ValueError, match="Unknown task_type"):
            validator.validate(
                result=FieldExtractionResult(is_complete=False),
                contract=UnknownContract(),
            )
