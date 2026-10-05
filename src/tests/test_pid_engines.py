"""Old-engine graph mapping, answer parsing and adapter hygiene for the head-to-head (ADE-31)."""

import pytest

from src.eval import pid_compare
from src.eval.pid_compare import CATEGORIES, UnparseableOutput
from src.eval.pid_engines import (
    OldEngineAdapter,
    graph_to_extraction,
    parse_json_object,
    prepare_drawings,
)


def _node(kind, tag=None):
    return {"id": f"n_{kind}_{tag}", "type": kind, "tag": tag}


class TestGraphToExtraction:
    def test_maps_typed_nodes_onto_the_five_categories_and_carries_tags(self):
        graph = {
            "nodes": [
                _node("vessel", "V-101"),
                _node("pump", "P-201"),
                _node("valve", "XV-1"),
                _node("control_valve", "FCV-2"),
                _node("instrument", "FT-10"),
                _node("sensor", "PT-11"),
                _node("off_page_connector", "OPC-1"),
                _node("pipe"),
                _node("fitting"),
            ],
            "edges": [{"id": f"e{i}", "type": "pipe"} for i in range(4)],
        }
        out = graph_to_extraction(graph)
        assert {k: len(v) for k, v in out.items()} == {
            "nodes": 2,
            "valves": 2,
            "instruments": 2,
            "off_page_connectors": 1,
            "edges": 4,
        }
        assert [n["tag"] for n in out["nodes"]] == ["V-101", "P-201"]
        assert out["valves"][1]["tag"] == "FCV-2"

    def test_unknown_node_type_counts_as_equipment_and_type_is_case_insensitive(self):
        out = graph_to_extraction({"nodes": [_node("Heat_Exchanger", "E-1"), _node("VALVE", "V")]})
        assert (len(out["nodes"]), len(out["valves"])) == (1, 1)

    @pytest.mark.parametrize(
        "graph",
        [
            None,
            {},
            {"nodes": None, "edges": None},
            {"nodes": ["x", 3, None], "edges": ["y", 7]},
            {"nodes": [{"type": None}], "edges": {}},
            "not a graph",
        ],
    )
    def test_malformed_graph_never_raises(self, graph):
        out = graph_to_extraction(graph)
        assert set(out) == set(CATEGORIES)
        assert out["edges"] == [] and out["valves"] == []


class TestParseJsonObject:
    @pytest.mark.parametrize(
        "text",
        ['{"nodes": []}', '```json\n{"nodes": []}\n```', 'Here you go:\n{"nodes": []}\nDone.'],
    )
    def test_accepts_plain_fenced_and_chatty_answers(self, text):
        assert parse_json_object(text) == {"nodes": []}

    def test_passes_a_dict_through(self):
        assert parse_json_object({"a": 1}) == {"a": 1}

    @pytest.mark.parametrize("text", ["", None, "no json here", "[1, 2]", "{broken"])
    def test_rejects_non_objects(self, text):
        with pytest.raises(UnparseableOutput):
            parse_json_object(text)


class TestOldEngineAdapterHygiene:
    def _run_failing(self, tmp_path, monkeypatch, adapter_ocr):
        """Run the adapter with a graph build that fails; return what the setting was inside."""
        import src.agent.graph as agent_graph
        from src.config import settings

        image = tmp_path / "d.png"
        image.write_bytes(b"x")
        seen = {}

        def boom(**kwargs):
            seen["ocr"] = settings.ocr_provider
            raise RuntimeError("graph build failed")

        monkeypatch.setattr(agent_graph, "build_react_graph", boom)
        monkeypatch.setattr(settings, "ocr_provider", "paddle")
        with pytest.raises(RuntimeError):
            OldEngineAdapter(adapter_ocr).run(image, "D")
        return seen["ocr"], settings.ocr_provider

    def test_run_uses_the_configured_ocr_provider_and_restores_it_after_a_failure(
        self, tmp_path, monkeypatch
    ):
        during, after = self._run_failing(tmp_path, monkeypatch, "tesseract")
        assert (during, after) == ("tesseract", "paddle")

    def test_default_is_the_old_engines_native_provider(self):
        assert OldEngineAdapter().ocr_provider == "paddle"


class TestPreflight:
    def test_unknown_reference_is_a_clear_error_before_any_model_call(self, monkeypatch, tmp_path):
        (tmp_path / "A.xml").write_text("<x/>")
        (tmp_path / "A.svg").write_text("<svg/>")
        monkeypatch.setenv("ADE_DEXPI_REF_DIR", str(tmp_path))
        with pytest.raises(ValueError, match="unknown reference"):
            prepare_drawings(["NOPE"])

    def test_missing_reference_dir_is_a_clear_error(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ADE_DEXPI_REF_DIR", str(tmp_path / "missing"))
        with pytest.raises(FileNotFoundError):
            prepare_drawings([])

    def test_main_without_credentials_runs_nothing(self, monkeypatch, capsys):
        from src.config import settings

        monkeypatch.setattr(settings, "llm_provider", "openai")
        monkeypatch.setattr(settings, "openai_api_key", "")
        assert pid_compare.main(["--runs", "1"]) == 2
        assert "nothing was run" in capsys.readouterr().out
