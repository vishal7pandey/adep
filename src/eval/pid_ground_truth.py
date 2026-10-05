"""Ground truth for P&ID evaluation, read from DEXPI reference files (ADE-15).

Each reference is a pair: a Proteus XML file (the model: what exists) and an SVG (the drawing:
what is printed). They are third-party material (DEXPI e.V.) and are NEVER stored in this
repository: they are read from the directory named by the environment variable ADE_DEXPI_REF_DIR
(or an argument). Nothing here copies, moves or modifies them.

Category mapping from the Proteus XML (checked by hand against real reference files):
  nodes               <Equipment>
  valves              elements whose ComponentClass ends in "Valve"
                      (label classes end in "Label"; flanges do not end in "Valve")
  instruments         <ProcessInstrumentationFunction>
  off_page_connectors <PipeOffPageConnector>
  edges               <PipingNetworkSegment>
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from src.eval.pid_scoring import CATEGORIES, normalize_tag

REF_ENV = "ADE_DEXPI_REF_DIR"
_SVG_TEXT = "{http://www.w3.org/2000/svg}text"


@dataclass
class GroundTruth:
    name: str
    counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(CATEGORIES, 0))
    labels: set[str] = field(default_factory=set)  # normalised strings printed on the drawing


@dataclass
class Reference:
    name: str
    xml: Path
    svg: Path


def _parse(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError(f"cannot parse {path.name}: {exc}") from exc


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def load_ground_truth(xml_path: Path | str, svg_path: Path | str) -> GroundTruth:
    """Count entities in the Proteus XML and collect the normalised text labels from the SVG."""
    xml_path, svg_path = Path(xml_path), Path(svg_path)
    counts = dict.fromkeys(CATEGORIES, 0)
    for el in _parse(xml_path).iter():
        tag = _local(el.tag)
        cls = el.attrib.get("ComponentClass", "")
        if tag == "Equipment":
            counts["nodes"] += 1
        elif tag == "ProcessInstrumentationFunction":
            counts["instruments"] += 1
        elif tag == "PipeOffPageConnector":
            counts["off_page_connectors"] += 1
        elif tag == "PipingNetworkSegment":
            counts["edges"] += 1
        elif cls.endswith("Valve"):
            counts["valves"] += 1
    labels: set[str] = set()
    for text in _parse(svg_path).iter():
        if text.tag == _SVG_TEXT or _local(text.tag) == "text":
            norm = normalize_tag("".join(text.itertext()).strip())
            if norm:
                labels.add(norm)
    return GroundTruth(name=xml_path.stem, counts=counts, labels=labels)


def reference_dir() -> Path | None:
    """The configured reference directory, or None when ADE_DEXPI_REF_DIR is unset."""
    value = os.environ.get(REF_ENV)
    return Path(value) if value else None


def discover_references(directory: Path | str | None = None) -> tuple[list[Reference], str]:
    """Find XML+SVG pairs. Returns (references, message); never raises for a missing directory.

    The SVG may sit next to the XML or in an `svg/` subfolder. An XML with no SVG is skipped and
    named in the message.
    """
    root = Path(directory) if directory is not None else reference_dir()
    if root is None:
        return (
            [],
            f"no reference directory: set {REF_ENV} to a folder holding DEXPI .xml and .svg pairs",
        )
    if not root.is_dir():
        return [], f"reference directory not found: {root}"
    refs: list[Reference] = []
    skipped: list[str] = []
    for xml in sorted(root.glob("*.xml")):
        svg = next(
            (
                p
                for p in (root / f"{xml.stem}.svg", root / "svg" / f"{xml.stem}.svg")
                if p.is_file()
            ),
            None,
        )
        if svg is None:
            skipped.append(xml.stem)
        else:
            refs.append(Reference(xml.stem, xml, svg))
    message = f"skipped (no svg): {', '.join(skipped)}" if skipped else ""
    if not refs and not message:
        message = f"no .xml files in {root}"
    return refs, message


def svg_to_png(svg_path: Path | str, png_path: Path | str, zoom: float = 2.0) -> Path:
    """Render an SVG to a PNG (to feed an engine) using PyMuPDF, which is already a dependency."""
    import fitz  # PyMuPDF

    svg_path, png_path = Path(svg_path), Path(png_path)
    if not svg_path.is_file():
        raise FileNotFoundError(f"SVG not found: {svg_path}")
    doc = fitz.open(str(svg_path))
    try:
        pixmap = doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        png_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(png_path))
    finally:
        doc.close()
    return png_path
