"""P&ID ground truth loading, reference discovery and SVG rendering (ADE-15).

The XML and SVG here are tiny hand-authored fixtures in the Proteus/SVG style. No DEXPI e.V.
material
is in the repo; real reference files are only ever read from ADE_DEXPI_REF_DIR.
"""

from __future__ import annotations

import pytest

from src.eval.pid_ground_truth import (
    discover_references,
    load_ground_truth,
    reference_dir,
    svg_to_png,
)
from src.eval.pid_scoring import normalize_tag

XML = """<?xml version="1.0" encoding="UTF-8"?>
<PlantModel>
  <Equipment ID="E1" ComponentClass="Tank"/>
  <Equipment ID="E2" ComponentClass="Pump"/>
  <PipingNetworkSystem ID="S1">
    <PipingNetworkSegment ID="G1">
      <PipingComponent ID="V1" ComponentClass="BallValve"/>
      <PipingComponent ID="V2" ComponentClass="OperatedValve"/>
      <PipingComponent ID="F1" ComponentClass="Flange"/>
    </PipingNetworkSegment>
    <PipingNetworkSegment ID="G2"/>
    <PipeOffPageConnector ID="O1" ComponentClass="PipeOffPageConnector"/>
  </PipingNetworkSystem>
  <ProcessInstrumentationFunction ID="I1" ComponentClass="ProcessInstrumentationFunction"/>
  <Label ID="L1" ComponentClass="ValveLabel"/>
</PlantModel>
"""

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
  <text x="5" y="20">P-101</text>
  <text x="5" y="40"><tspan>XV</tspan><tspan> 104.01</tspan></text>
  <text x="5" y="60">   </text>
</svg>
"""


def write_pair(folder, name="A01"):
    (folder / f"{name}.xml").write_text(XML, encoding="utf-8")
    (folder / f"{name}.svg").write_text(SVG, encoding="utf-8")
    return folder / f"{name}.xml", folder / f"{name}.svg"


class TestLoad:
    def test_counts_by_category(self, tmp_path):
        xml, svg = write_pair(tmp_path)
        gt = load_ground_truth(xml, svg)
        assert gt.name == "A01"
        assert gt.counts == {
            "nodes": 2,
            "valves": 2,
            "instruments": 1,
            "off_page_connectors": 1,
            "edges": 2,
        }

    def test_label_classes_are_not_valves_and_flanges_are_not_valves(self, tmp_path):
        xml, svg = write_pair(tmp_path)
        assert load_ground_truth(xml, svg).counts["valves"] == 2

    def test_labels_are_normalised_and_blank_text_dropped(self, tmp_path):
        xml, svg = write_pair(tmp_path)
        labels = load_ground_truth(xml, svg).labels
        assert normalize_tag("P-101") in labels
        assert normalize_tag("XV 104.01") in labels
        assert "" not in labels

    def test_empty_plant_gives_zero_counts(self, tmp_path):
        (tmp_path / "e.xml").write_text("<PlantModel/>", encoding="utf-8")
        (tmp_path / "e.svg").write_text(SVG, encoding="utf-8")
        gt = load_ground_truth(tmp_path / "e.xml", tmp_path / "e.svg")
        assert sum(gt.counts.values()) == 0

    def test_malformed_xml_names_the_file(self, tmp_path):
        (tmp_path / "bad.xml").write_text("<PlantModel><oops>", encoding="utf-8")
        (tmp_path / "bad.svg").write_text(SVG, encoding="utf-8")
        with pytest.raises(ValueError, match="bad.xml"):
            load_ground_truth(tmp_path / "bad.xml", tmp_path / "bad.svg")

    def test_malformed_svg_names_the_file(self, tmp_path):
        (tmp_path / "b.xml").write_text(XML, encoding="utf-8")
        (tmp_path / "b.svg").write_text("<svg><text>", encoding="utf-8")
        with pytest.raises(ValueError, match="b.svg"):
            load_ground_truth(tmp_path / "b.xml", tmp_path / "b.svg")


class TestDiscover:
    def test_finds_pairs(self, tmp_path):
        write_pair(tmp_path, "A01")
        write_pair(tmp_path, "B02")
        refs, message = discover_references(tmp_path)
        assert [r.name for r in refs] == ["A01", "B02"]
        assert message == ""

    def test_xml_without_svg_is_skipped_with_a_message(self, tmp_path):
        write_pair(tmp_path, "A01")
        (tmp_path / "lonely.xml").write_text(XML, encoding="utf-8")
        refs, message = discover_references(tmp_path)
        assert [r.name for r in refs] == ["A01"]
        assert "lonely" in message

    def test_svg_in_a_svg_subfolder_is_found(self, tmp_path):
        (tmp_path / "svg").mkdir()
        (tmp_path / "A01.xml").write_text(XML, encoding="utf-8")
        (tmp_path / "svg" / "A01.svg").write_text(SVG, encoding="utf-8")
        refs, _ = discover_references(tmp_path)
        assert [r.name for r in refs] == ["A01"]

    def test_unset_or_missing_directory_gives_empty_list_and_message(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ADE_DEXPI_REF_DIR", raising=False)
        assert reference_dir() is None
        refs, message = discover_references(None)
        assert refs == [] and "ADE_DEXPI_REF_DIR" in message
        refs, message = discover_references(tmp_path / "nope")
        assert refs == [] and "nope" in message

    def test_env_var_is_used(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ADE_DEXPI_REF_DIR", str(tmp_path))
        assert reference_dir() == tmp_path


class TestRender:
    def test_renders_a_non_empty_png(self, tmp_path):
        _, svg = write_pair(tmp_path)
        out = svg_to_png(svg, tmp_path / "out.png", zoom=1.0)
        assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_zoom_scales_the_image(self, tmp_path):
        import fitz

        _, svg = write_pair(tmp_path)
        small = svg_to_png(svg, tmp_path / "s.png", zoom=1.0)
        big = svg_to_png(svg, tmp_path / "b.png", zoom=2.0)
        w1 = fitz.Pixmap(str(small)).width
        w2 = fitz.Pixmap(str(big)).width
        assert w2 == 2 * w1

    def test_missing_svg_raises_clearly(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="nope.svg"):
            svg_to_png(tmp_path / "nope.svg", tmp_path / "o.png")
