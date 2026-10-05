"""Head-to-head P&ID evaluation of the two engines (ADE-31): `python -m src.eval.pid_compare`.

The runner here is pure: it takes engines (anything with `name` and `run(image_path, drawing)`),
drawings with ADE-15 ground truth, and optionally a `UsageMeter`. It records every run, summarises
spread per engine and drawing, and writes a git-ignored results file. The real engines and the CLI
wiring live in `pid_engines.py` and `main()` below.

Failures keep the exception TYPE only: provider error messages can echo secrets.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from src.eval.pid_ground_truth import GroundTruth
from src.eval.pid_scoring import CATEGORIES, score_extraction
from src.eval.usage_meter import SpendCapReached, UsageMeter

DEFAULT_RESULTS_DIR = Path(".adep") / "eval"
SECRET_ENV_VARS = ("OPENAI_API_KEY", "AZURE_API_KEY")


class UnparseableOutput(ValueError):
    """An engine returned something with none of the five category lists."""


class Engine(Protocol):
    name: str

    def run(self, image_path: Path, drawing: str) -> dict[str, Any]:
        """Return the extraction as a dict of category lists, or raise."""
        ...


@dataclass
class Drawing:
    name: str
    image_path: Path
    truth: GroundTruth


@dataclass
class RunRecord:
    engine: str
    drawing: str
    repetition: int
    status: str  # ok | failed | skipped_budget
    seconds: float | None = None
    error: str | None = None
    score: dict[str, Any] | None = None
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


# --- running ----------------------------------------------------------------------------------


def _call_with_timeout(fn: Callable[[], Any], timeout: float | None) -> Any:
    if timeout is None:
        return fn()
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(fn)
    try:
        return future.result(timeout=timeout)
    except FutureTimeout:
        raise TimeoutError("run timed out") from None
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _validated(extraction: Any) -> dict[str, Any]:
    if not isinstance(extraction, dict) or not any(
        isinstance(extraction.get(c), list) for c in CATEGORIES
    ):
        raise UnparseableOutput("no category lists in the output")
    return extraction


def run_comparison(
    engines: Sequence[Engine],
    drawings: Sequence[Drawing],
    runs: int,
    *,
    score_fn: Callable[[dict[str, Any], GroundTruth], Any] = score_extraction,
    clock: Callable[[], float] = time.perf_counter,
    meter: UsageMeter | None = None,
    timeout: float | None = 600.0,
    on_record: Callable[[RunRecord], None] | None = None,
) -> list[RunRecord]:
    """Run every engine on every drawing `runs` times, interleaved within each repetition."""
    records: list[RunRecord] = []
    for drawing in drawings:
        for repetition in range(1, runs + 1):
            for engine in engines:
                record = _one_run(engine, drawing, repetition, score_fn, clock, meter, timeout)
                records.append(record)
                if on_record:
                    on_record(record)
    return records


def _one_run(
    engine: Engine,
    drawing: Drawing,
    repetition: int,
    score_fn: Callable[[dict[str, Any], GroundTruth], Any],
    clock: Callable[[], float],
    meter: UsageMeter | None,
    timeout: float | None,
) -> RunRecord:
    record = RunRecord(engine.name, drawing.name, repetition, status="ok")
    if meter is not None and meter.exhausted:
        record.status = "skipped_budget"
        return record
    before = meter.snapshot() if meter is not None else (0, 0, 0)
    started = clock()
    try:
        extraction = _validated(
            _call_with_timeout(lambda: engine.run(drawing.image_path, drawing.name), timeout)
        )
        record.score = score_fn(extraction, drawing.truth).to_dict()
    except SpendCapReached:
        record.status = "skipped_budget"
    except Exception as exc:  # noqa: BLE001 - one bad run must not stop the comparison
        record.status = "failed"
        record.error = type(exc).__name__
    finally:
        record.seconds = clock() - started
        if meter is not None:
            after = meter.snapshot()
            record.calls = after[0] - before[0]
            record.prompt_tokens = after[1] - before[1]
            record.completion_tokens = after[2] - before[2]
    if record.status == "skipped_budget":
        record.seconds = None
    return record


# --- summarising ------------------------------------------------------------------------------


def _spread(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "stdev": None, "min": None, "max": None}
    mean = sum(values) / len(values)
    stdev = (
        math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))
        if len(values) > 1
        else None
    )
    return {"mean": mean, "stdev": stdev, "min": min(values), "max": max(values)}


def _stats(records: list[RunRecord]) -> dict[str, Any]:
    ok = [r for r in records if r.status == "ok" and r.score is not None]
    recall = [r.score["mean_count_recall"] for r in ok if r.score["mean_count_recall"] is not None]
    precision = [r.score["label_precision"] for r in ok if r.score["label_precision"] is not None]
    categories: dict[str, float | None] = {}
    for category in CATEGORIES:
        values = [
            r.score["categories"][category]["recall"]
            for r in ok
            if r.score["categories"][category]["recall"] is not None
        ]
        categories[category] = sum(values) / len(values) if values else None
    return {
        "n_ok": len(ok),
        "n_failed": sum(1 for r in records if r.status == "failed"),
        "n_skipped": sum(1 for r in records if r.status == "skipped_budget"),
        "errors": sorted({r.error for r in records if r.error}),
        "recall": _spread(recall),
        "label_precision": _spread(precision),
        "seconds": _spread([r.seconds for r in ok if r.seconds is not None]),
        "tokens": _spread([float(r.tokens) for r in ok]),
        "prompt_tokens_mean": _spread([float(r.prompt_tokens) for r in ok])["mean"],
        "completion_tokens_mean": _spread([float(r.completion_tokens) for r in ok])["mean"],
        "category_recall": categories,
    }


def summarize(records: list[RunRecord]) -> dict[str, Any]:
    """Per engine per drawing, per engine overall; failed and skipped runs never enter the means."""
    engines = list(dict.fromkeys(r.engine for r in records))
    drawings = list(dict.fromkeys(r.drawing for r in records))
    return {
        "complete": not any(r.status == "skipped_budget" for r in records),
        "engines": engines,
        "drawings": drawings,
        "per_drawing": {
            e: {
                d: _stats([r for r in records if r.engine == e and r.drawing == d])
                for d in drawings
            }
            for e in engines
        },
        "overall": {e: _stats([r for r in records if r.engine == e]) for e in engines},
    }


def _fmt(spread: dict[str, float | None], digits: int = 2) -> str:
    if spread["mean"] is None:
        return "n/a"
    text = f"{spread['mean']:.{digits}f}"
    if spread["stdev"] is not None:
        text += f" ± {spread['stdev']:.{digits}f}"
    return f"{text} ({spread['min']:.{digits}f}-{spread['max']:.{digits}f})"


def format_table(summary: dict[str, Any], meta: dict[str, Any] | None = None) -> str:
    """Markdown table: one row per engine per drawing plus overall rows."""
    meta = meta or {}
    price_in, price_out = meta.get("price_in_per_m"), meta.get("price_out_per_m")
    priced = price_in is not None and price_out is not None
    header = (
        "| Drawing | Engine | ok/failed/skipped | count recall | label precision "
        "| seconds | tokens |"
    )
    sep = "|---|---|---|---|---|---|---|"
    if priced:
        header += " USD/run |"
        sep += "---|"
    lines = []
    if not summary["complete"]:
        lines.append("**INCOMPLETE: the spend cap was reached; some runs were skipped.**\n")
    lines += [header, sep]

    def row(label: str, engine: str, s: dict[str, Any]) -> str:
        cells = [
            label,
            engine,
            f"{s['n_ok']}/{s['n_failed']}/{s['n_skipped']}",
            _fmt(s["recall"]),
            _fmt(s["label_precision"]),
            _fmt(s["seconds"], 1),
            _fmt(s["tokens"], 0),
        ]
        if priced:
            if s["prompt_tokens_mean"] is None:
                cells.append("n/a")
            else:
                usd = (
                    s["prompt_tokens_mean"] * price_in + s["completion_tokens_mean"] * price_out
                ) / 1e6
                cells.append(f"{usd:.4f}")
        return "| " + " | ".join(cells) + " |"

    for drawing in summary["drawings"]:
        for engine in summary["engines"]:
            lines.append(row(drawing, engine, summary["per_drawing"][engine][drawing]))
    for engine in summary["engines"]:
        lines.append(row("**ALL**", engine, summary["overall"][engine]))
    return "\n".join(lines)


# --- results file -----------------------------------------------------------------------------


def _scrub(text: str) -> str:
    for var in SECRET_ENV_VARS:
        secret = os.environ.get(var, "").strip()
        if len(secret) >= 8:
            text = text.replace(secret, "[redacted]")
    return text


def default_results_path(now: datetime | None = None) -> Path:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_RESULTS_DIR / f"pid_compare_{stamp}.json"


def write_results(
    path: Path, meta: dict[str, Any], records: list[RunRecord], summary: dict[str, Any]
) -> Path:
    """Write meta, every record and the summary as JSON; any API key value is redacted."""
    payload = {
        "meta": meta,
        "records": [asdict(r) for r in records],
        "summary": summary,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_scrub(json.dumps(payload, indent=2, default=str)), encoding="utf-8")
    return path


# --- command line -----------------------------------------------------------------------------


@dataclass
class CompareArgs:
    refs: list[str] = field(default_factory=list)
    runs: int = 5
    engines: list[str] = field(default_factory=lambda: ["new", "old"])
    model: str = "gpt-5.4-mini"
    max_calls: int = 1500
    max_tokens: int = 5_000_000
    timeout: float = 600.0
    old_ocr: str = "paddle"
    out: Path | None = None
    price_in: float | None = None
    price_out: float | None = None


def parse_args(argv: Sequence[str] | None = None) -> CompareArgs:
    p = argparse.ArgumentParser(prog="python -m src.eval.pid_compare", description=__doc__)
    p.add_argument("--refs", default="", help="comma-separated reference names (default: first 3)")
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--engines", default="new,old", help="comma-separated: new, old")
    p.add_argument("--model", default="gpt-5.4-mini")
    p.add_argument(
        "--old-ocr",
        default="paddle",
        choices=["paddle", "tesseract", "none"],
        help="OCR/layout provider for the old engine (its native one is paddle)",
    )
    p.add_argument("--max-calls", type=int, default=1500)
    p.add_argument("--max-tokens", type=int, default=5_000_000)
    p.add_argument("--timeout", type=float, default=600.0)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--price-in", type=float, default=None, help="USD per million input tokens")
    p.add_argument("--price-out", type=float, default=None, help="USD per million output tokens")
    ns = p.parse_args(argv)
    if ns.runs < 1:
        p.error("--runs must be at least 1")
    if (ns.price_in is None) != (ns.price_out is None):
        p.error("give both --price-in and --price-out, or neither")
    engines = [e.strip() for e in ns.engines.split(",") if e.strip()]
    if not engines or any(e not in ("new", "old") for e in engines):
        p.error("--engines must be a comma-separated list of: new, old")
    return CompareArgs(
        refs=[r.strip() for r in ns.refs.split(",") if r.strip()],
        runs=ns.runs,
        engines=engines,
        model=ns.model,
        old_ocr=ns.old_ocr,
        max_calls=ns.max_calls,
        max_tokens=ns.max_tokens,
        timeout=ns.timeout,
        out=ns.out,
        price_in=ns.price_in,
        price_out=ns.price_out,
    )


def perception_notes(old_ocr: str) -> dict[str, str]:
    """What each engine used to see the drawing, recorded with the results (R8)."""
    return {
        "new": "VLM-based survey/crop/read tools; OCR tool falls back to the VLM without Tesseract",
        "old": f"ocr_provider={old_ocr}"
        + (" (no layout/OCR tool registered)" if old_ocr == "none" else ""),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    from src.config import settings
    from src.eval.pid_engines import build_engines, prepare_drawings

    settings.openai_chat_model = args.model
    if not settings.is_llm_configured():
        print("No model credentials configured (set OPENAI_API_KEY); nothing was run.")
        return 2
    try:
        drawings = prepare_drawings(args.refs)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Cannot load references: {exc}")
        return 2

    engines = build_engines(args.engines, args.old_ocr)
    meta = {
        "started": datetime.now(timezone.utc).isoformat(),
        "engines": args.engines,
        "model": settings.chat_model,
        "provider": settings.active_llm_provider,
        "runs_per_engine_per_drawing": args.runs,
        "drawings": [d.name for d in drawings],
        "max_calls": args.max_calls,
        "max_tokens": args.max_tokens,
        "timeout_seconds": args.timeout,
        "perception": {e: perception_notes(args.old_ocr)[e] for e in args.engines},
        "python": sys.version.split()[0],
        "price_in_per_m": args.price_in,
        "price_out_per_m": args.price_out,
    }
    out = args.out or default_results_path()

    def progress(r: RunRecord) -> None:
        detail = r.error or (r.score or {}).get("mean_count_recall")
        print(f"  {r.drawing} #{r.repetition} {r.engine}: {r.status} {detail}", flush=True)

    with UsageMeter(max_calls=args.max_calls, max_tokens=args.max_tokens) as meter:
        records = run_comparison(
            engines, drawings, args.runs, meter=meter, timeout=args.timeout, on_record=progress
        )
    summary = summarize(records)
    meta["total_calls"], meta["total_tokens"] = meter.calls, meter.total_tokens
    write_results(out, meta, records, summary)
    print(format_table(summary, meta))
    print(f"\nResults: {out}  (calls={meter.calls}, tokens={meter.total_tokens})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
