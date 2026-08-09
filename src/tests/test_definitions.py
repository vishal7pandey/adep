"""Tests for AgentDefinition model [BLK-016, TS]."""

from __future__ import annotations

from src.definitions.base import AgentConfig, AgentDefinition


class TestAgentDefinition:
    """Verify AgentDefinition serialization and validation."""

    def test_create_minimal(self):
        d = AgentDefinition(
            id="def-test",
            name="Test Definition",
            skill_id="invoice",
            template_id="invoice",
        )
        assert d.id == "def-test"
        assert d.name == "Test Definition"
        assert d.skill_id == "invoice"
        assert d.template_id == "invoice"
        assert d.version == "1.0.0"
        assert d.tool_names == []
        assert d.system_prompt is None

    def test_create_full(self):
        d = AgentDefinition(
            id="def-invoice-v2",
            name="Invoice Extractor v2",
            skill_id="invoice",
            template_id="invoice",
            tool_names=["ocr", "vlm", "crop", "deskew"],
            agent_config=AgentConfig(
                max_cycles_per_field=3,
                max_cycles_per_document=20,
                confidence_threshold=0.85,
            ),
            system_prompt="Extract invoice data carefully.",
            version="2.0.0",
        )
        assert d.tool_names == ["ocr", "vlm", "crop", "deskew"]
        assert d.agent_config.max_cycles_per_field == 3
        assert d.agent_config.confidence_threshold == 0.85
        assert d.system_prompt == "Extract invoice data carefully."

    def test_serialization_roundtrip(self):
        d = AgentDefinition(
            id="def-roundtrip",
            name="Roundtrip Test",
            skill_id="invoice",
            template_id="invoice",
            tool_names=["ocr"],
        )
        json_str = d.model_dump_json()
        restored = AgentDefinition.model_validate_json(json_str)
        assert restored.id == d.id
        assert restored.name == d.name
        assert restored.tool_names == d.tool_names

    def test_agent_config_defaults(self):
        config = AgentConfig()
        assert config.max_cycles_per_field is None
        assert config.max_cycles_per_document is None
        assert config.confidence_threshold is None
