"""P&ID extraction scoring against DEXPI ground truth (ADE-15).

Two complementary metrics, because the two ground-truth sources answer different questions:

**Count recall** (vs the Proteus XML): did the extraction find the right *number* of each kind of
entity? Reported as recall and, separately, over-extraction, so a flood of guesses cannot look like
recall. F1 over object ids is deliberately not used: ids such as "BallValve-1" are not visible on
the drawing, so they cannot be matched against what an engine reads.

**Label precision** (vs the SVG text): of the tags the extraction reports, how many are strings
actually printed on the drawing? This is the honest test of reading accuracy and it catches
hallucinated tags.

Tags are compared after normalisation because the same physical label is written inconsistently
across sources: the drawing shows "SV 104.01", an engine reports "SV104.01".

Pure functions, no model and no network.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.eval.pid_ground_truth import GroundTruth

# Output lists an extraction is expected to carry (the new engine's pid-dexpi-digitizer schema).
CATEGORIES = ("nodes", "valves", "instruments", "off_page_connectors", "edges")
# Categories whose items carry a printed tag that can be checked against the drawing text.
TAGGED_CATEGORIES = ("nodes", "valves", "instruments")

_SUPERSCRIPTS = {
    "⁺": "+",
    "⁻": "-",
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
}


def normalize_tag(tag: Any) -> str:
    """Normalise a tag for comparison across drawing text and engine output.

    Case, whitespace, separators and unicode superscripts are ignored. Different tags stay different
    ("PI-101" vs "PI-102"); the one accepted collision is separator-only differences
    ("1-2" vs "12").
    """
    text = str(tag or "")
    for src, dst in _SUPERSCRIPTS.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKD", text)
    return re.sub(r"[^A-Z0-9.]", "", text.upper())


def tag_parts(tag: Any) -> list[str]:
    """Split a tag into its letter and number runs: 'PI 4712.01' -> ['PI', '4712.01']."""
    return [p for p in re.findall(r"[A-Z]+|[0-9][0-9.]*", normalize_tag(tag)) if p]


def _tag_on_drawing(tag: Any, labels: set[str]) -> bool:
    """A tag is on the drawing if it is a label, or if all its parts are printed as labels.

    Instrument bubbles print the function letters and the loop number as separate text runs, so a
    drawing's label set holds "PI" and "4712.01" but never "PI4712.01".
    """
    norm = normalize_tag(tag)
    if not norm:
        return False
    if norm in labels:
        return True
    parts = tag_parts(tag)
    return len(parts) > 1 and all(p in labels for p in parts)


@dataclass
class CategoryScore:
    found: int
    truth: int
    recall: float | None  # None when truth is 0: not applicable, never a flattering 1.0
    over_extraction: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "found": self.found,
            "truth": self.truth,
            "recall": self.recall,
            "over_extraction": self.over_extraction,
        }


@dataclass
class PidScore:
    categories: dict[str, CategoryScore] = field(default_factory=dict)
    label_precision: float | None = None
    tags_reported: int = 0
    tags_on_drawing: int = 0

    @property
    def mean_count_recall(self) -> float | None:
        values = [c.recall for c in self.categories.values() if c.recall is not None]
        return sum(values) / len(values) if values else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "categories": {k: v.to_dict() for k, v in self.categories.items()},
            "mean_count_recall": self.mean_count_recall,
            "label_precision": self.label_precision,
            "tags_reported": self.tags_reported,
            "tags_on_drawing": self.tags_on_drawing,
        }


def _items(extraction: dict[str, Any], category: str) -> list[dict[str, Any]]:
    raw = extraction.get(category)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def score_extraction(extraction: dict[str, Any], truth: GroundTruth) -> PidScore:
    """Score one extraction (lists keyed by CATEGORIES) against one ground truth."""
    score = PidScore()
    for category in CATEGORIES:
        found = len(_items(extraction, category))
        expected = int(truth.counts.get(category, 0))
        if expected > 0:
            recall: float | None = min(found, expected) / expected
            over: float | None = max(0, found - expected) / expected
        else:
            recall = over = None
        score.categories[category] = CategoryScore(found, expected, recall, over)

    reported: dict[str, Any] = {}
    for category in TAGGED_CATEGORIES:
        for item in _items(extraction, category):
            tag = item.get("tag")
            norm = normalize_tag(tag)
            if norm:
                reported.setdefault(norm, tag)
    score.tags_reported = len(reported)
    score.tags_on_drawing = sum(
        1 for tag in reported.values() if _tag_on_drawing(tag, truth.labels)
    )
    score.label_precision = (
        score.tags_on_drawing / score.tags_reported if score.tags_reported else None
    )
    return score
