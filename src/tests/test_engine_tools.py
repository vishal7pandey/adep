"""Tests for the new-engine perception tools (ADE-38).

survey_layout/survey_region are new code; crop_and_read/ocr_page are thin wrappers around ade's
existing src.providers.vlm_azure.vlm, src.providers.image_cv.crop, src.providers.ocr_tesseract.ocr —
proven by monkeypatching those exact provider functions, not a parallel reimplementation.

Hermetic: a real small PNG fixture, every provider call mocked, no network, no live Azure/Tesseract.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image

from src.engine import tools as engine_tools
from src.providers import image_cv, ocr_tesseract, vlm_azure
from src.tools.base import ToolResult

IMAGE_W, IMAGE_H = 2000, 1000


class _FakeStore:
    """Stands in for DocumentStore: maps (doc_id, page_num) -> image path."""

    def __init__(self, pages: dict[tuple[str, int], str]):
        self._pages = pages

    def get_page_path(self, doc_id: str, page_num: int):
        key = (doc_id, page_num)
        if key not in self._pages:
            raise FileNotFoundError(f"Page {page_num} not found for document '{doc_id}'")
        return self._pages[key]


@pytest.fixture
def page_image(tmp_path):
    path = tmp_path / "page_1.png"
    Image.new("RGB", (IMAGE_W, IMAGE_H), color="white").save(path, "PNG")
    return path


@pytest.fixture
def fake_store(page_image, monkeypatch):
    store = _FakeStore({("doc-1", 1): page_image})
    monkeypatch.setattr(engine_tools, "get_document_store", lambda: store)
    return store


# --- AC1: survey_layout converts normalized -> original pixel space -------------------------------


def test_survey_layout_converts_normalized_to_original_pixel_space(fake_store, monkeypatch):
    zones = [
        {"id": "zone_1", "type": "equipment", "bbox": [0.1, 0.2, 0.3, 0.4], "description": "tank"}
    ]

    def fake_vlm(image_path, question, **kwargs):
        return ToolResult(ok=True, data=json.dumps(zones), tool="vlm")

    monkeypatch.setattr(vlm_azure, "vlm", fake_vlm)

    result = engine_tools.survey_layout("doc-1", page_num=1)

    assert result["image_size"] == [IMAGE_W, IMAGE_H]
    assert result["zone_count"] == 1
    zone = result["zones"][0]
    # ymin=0.1,xmin=0.2,ymax=0.3,xmax=0.4 against the ORIGINAL 2000x1000 image
    # (well above _MAX_SURVEY_DIM=1024, so this fails if bbox math used the
    # downscaled working image's dims instead) -> x1=400,y1=100,x2=800,y2=300
    assert zone["bbox"] == (400, 100, 800, 300)
    assert zone["type"] == "equipment"


# --- AC2: survey_region translates crop-relative -> full-page pixel space -------------------------


def test_survey_region_translates_crop_relative_to_full_page_pixels(fake_store, monkeypatch):
    # region bbox on the full page: x1=20,y1=10,x2=120,y2=60 (100x50 crop)
    region_bbox = (20, 10, 120, 60)
    elements = [
        {
            "id": "elem_1",
            "type": "valve",
            "bbox": [0.0, 0.0, 0.5, 0.5],
            "tag": "V1",
            "description": "d",
        }
    ]

    def fake_vlm(image_path, question, **kwargs):
        return ToolResult(ok=True, data=json.dumps(elements), tool="vlm")

    monkeypatch.setattr(vlm_azure, "vlm", fake_vlm)

    result = engine_tools.survey_region("doc-1", region_bbox, page_num=1)

    assert result["crop_size"] == [100, 50]
    assert result["element_count"] == 1
    elem = result["elements"][0]
    # crop-relative [ymin=0,xmin=0,ymax=0.5,xmax=0.5] over a crop at (20,10)-(120,60):
    # full-page x = 20 + frac*(120-20), y = 10 + frac*(60-10)
    assert elem["bbox"] == (20, 10, 70, 35)
    assert elem["tag"] == "V1"


# --- AC3: crop_and_read / ocr_page delegate to the real providers ---------------------------------


def test_crop_and_read_calls_the_real_providers(fake_store, monkeypatch):
    crop_calls = []
    vlm_calls = []

    def fake_crop(image_path, bbox, **kwargs):
        crop_calls.append((image_path, bbox))
        return ToolResult(ok=True, data="/tmp/cropped.png", tool="crop")

    def fake_vlm(image_path, question, **kwargs):
        vlm_calls.append((image_path, question))
        return ToolResult(ok=True, data="there is a valve here", tool="vlm")

    monkeypatch.setattr(image_cv, "crop", fake_crop)
    monkeypatch.setattr(vlm_azure, "vlm", fake_vlm)

    result = engine_tools.crop_and_read("doc-1", (10, 10, 50, 50), "what is this?", page_num=1)

    assert len(crop_calls) == 1
    assert crop_calls[0][1] == (10, 10, 50, 50)
    assert len(vlm_calls) == 1
    assert vlm_calls[0] == ("/tmp/cropped.png", "what is this?")
    assert result["answer"] == "there is a valve here"
    assert result["grounding"].bbox == (10, 10, 50, 50)
    assert result["grounding"].source_tool == "crop_and_read"


def test_ocr_page_calls_the_real_ocr_provider(fake_store, monkeypatch):
    ocr_calls = []

    def fake_ocr(image_path, **kwargs):
        ocr_calls.append(image_path)
        return ToolResult(ok=True, data="some extracted text", tool="ocr")

    monkeypatch.setattr(ocr_tesseract, "ocr", fake_ocr)

    result = engine_tools.ocr_page("doc-1", page_num=1)

    assert len(ocr_calls) == 1
    assert result["text"] == "some extracted text"
    assert result["engine"] == "tesseract"
    assert "warning" not in result


# --- AC4: ocr_page falls back to vlm when Tesseract is unavailable --------------------------------


def test_ocr_page_falls_back_to_vlm_when_tesseract_unavailable(fake_store, monkeypatch):
    def fake_ocr(image_path, **kwargs):
        return ToolResult(ok=False, error="pytesseract not installed", tool="ocr")

    def fake_vlm(image_path, question, **kwargs):
        return ToolResult(ok=True, data="transcribed via vlm", tool="vlm")

    monkeypatch.setattr(ocr_tesseract, "ocr", fake_ocr)
    monkeypatch.setattr(vlm_azure, "vlm", fake_vlm)

    result = engine_tools.ocr_page("doc-1", page_num=1)

    assert result["text"] == "transcribed via vlm"
    assert result["engine"] == "vlm_fallback"
    assert "warning" in result and "downsampled" in result["warning"].lower()


# --- AC5: a missing document/page returns a structured error, never an exception ------------------


def test_missing_document_or_page_returns_structured_error_not_an_exception(fake_store):
    assert "error" in engine_tools.survey_layout("doc-1", page_num=99)
    assert "error" in engine_tools.survey_region("doc-1", (0, 0, 10, 10), page_num=99)
    assert "error" in engine_tools.crop_and_read("doc-1", (0, 0, 10, 10), "q?", page_num=99)
    assert "error" in engine_tools.ocr_page("doc-1", page_num=99)

    assert "error" in engine_tools.survey_layout("no-such-doc", page_num=1)


# --- AC6: malformed VLM JSON does not crash ------------------------------------------------------


def test_malformed_vlm_json_returns_empty_list_not_a_crash(fake_store, monkeypatch):
    def fake_vlm(image_path, question, **kwargs):
        return ToolResult(ok=True, data="this is not json at all {{{", tool="vlm")

    monkeypatch.setattr(vlm_azure, "vlm", fake_vlm)

    result = engine_tools.survey_layout("doc-1", page_num=1)
    assert result["zones"] == []
    assert result["zone_count"] == 0

    result = engine_tools.survey_region("doc-1", (0, 0, 50, 50), page_num=1)
    assert result["elements"] == []
    assert result["element_count"] == 0


def test_vlm_call_failure_is_a_structured_error_not_a_crash(fake_store, monkeypatch):
    def fake_vlm(image_path, question, **kwargs):
        return ToolResult(ok=False, error="rate limited", tool="vlm")

    monkeypatch.setattr(vlm_azure, "vlm", fake_vlm)

    result = engine_tools.survey_layout("doc-1", page_num=1)
    assert "error" in result
