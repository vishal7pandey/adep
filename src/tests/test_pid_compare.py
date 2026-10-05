"""Head-to-head runner: records, spread, failure isolation, budget, results file (ADE-31)."""

import json
import subprocess
import time
from pathlib import Path

import pytest

from src.eval.pid_compare import (
    CATEGORIES,
    DEFAULT_RESULTS_DIR,
    Drawing,
    RunRecord,
    default_results_path,
    format_table,
    parse_args,
    run_comparison,
    summarize,
    write_results,
)
from src.eval.pid_ground_truth import GroundTruth
from src.eval.usage_meter import SpendCapReached, UsageMeter

REPO_ROOT = Path(__file__).resolve().parents[2]


def _truth(**counts: int) -> GroundTruth:
    full = dict.fromkeys(CATEGORIES, 0)
    full.update(counts)
    return GroundTruth(name="t", counts=full, labels={"v-101", "p-201"})


def _drawing(name: str = "D1") -> Drawing:
    return Drawing(name, Path(f"{name}.png"), _truth(nodes=4, valves=2))


def _good(nodes: int = 2, valves: int = 1) -> dict:
    return {
        "nodes": [{"tag": "V-101"}] * nodes,
        "valves": [{"tag": "P-201"}] * valves,
        "instruments": [],
        "off_page_connectors": [],
        "edges": [],
    }


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class StubEngine:
    """Records the order of calls in a shared log; each run advances the fake clock."""

    def __init__(
        self, name, log, clock, *, output=None, step=3.0, tokens=0, meter=None, fail_on=None
    ):
        self.name, self.log, self.clock = name, log, clock
        self.output, self.step, self.tokens, self.meter = output, step, tokens, meter
        self.fail_on = fail_on or {}
        self.calls = 0

    def run(self, image_path, drawing):
        self.calls += 1
        self.log.append((self.name, drawing))
        self.clock.now += self.step
        if self.meter is not None:
            self.meter.prompt_tokens += self.tokens
        if self.calls in self.fail_on:
            raise self.fail_on[self.calls]
        return self.output if self.output is not None else _good()


def _rec(engine, drawing, rep, recall, precision=None, status="ok", seconds=1.0, tokens=100):
    score = {
        "mean_count_recall": recall,
        "label_precision": precision,
        "categories": {c: {"recall": recall} for c in CATEGORIES},
    }
    ok = status == "ok"
    return RunRecord(
        engine,
        drawing,
        rep,
        status,
        seconds=seconds if ok else None,
        score=score if ok else None,
        prompt_tokens=tokens if ok else 0,
        error="RuntimeError" if status == "failed" else None,
    )


class TestRunComparison:
    def test_each_engine_runs_n_times_per_drawing_interleaved_with_clock_and_tokens(self):
        log, clock, meter = [], Clock(), UsageMeter()
        a = StubEngine("A", log, clock, tokens=10, meter=meter)
        b = StubEngine("B", log, clock, tokens=20, meter=meter)
        records = run_comparison(
            [a, b], [_drawing("D1"), _drawing("D2")], 3, clock=clock, meter=meter, timeout=None
        )
        assert (a.calls, b.calls) == (6, 6)
        assert len(records) == 12
        assert [e for e, d in log if d == "D1"] == ["A", "B"] * 3
        assert [e for e, d in log if d == "D2"] == ["A", "B"] * 3
        first_a, first_b = records[0], records[1]
        assert (first_a.engine, first_a.drawing, first_a.repetition) == ("A", "D1", 1)
        assert first_a.seconds == 3.0 and first_a.status == "ok"
        assert first_a.tokens == 10 and first_b.tokens == 20
        assert first_a.score["categories"]["nodes"]["found"] == 2

    def test_single_run_single_engine(self):
        log, clock = [], Clock()
        records = run_comparison(
            [StubEngine("A", log, clock)], [_drawing()], 1, clock=clock, timeout=None
        )
        assert len(records) == 1 and records[0].tokens == 0


class TestSummarize:
    def test_mean_sample_stdev_min_max(self):
        records = [_rec("A", "D1", i, r) for i, r in enumerate((0.5, 0.7, 0.9), 1)]
        spread = summarize(records)["overall"]["A"]["recall"]
        assert spread["mean"] == pytest.approx(0.7)
        assert spread["stdev"] == pytest.approx(0.2)
        assert (spread["min"], spread["max"]) == (0.5, 0.9)

    def test_single_success_has_no_stdev_and_zero_successes_has_no_stats(self):
        one = summarize([_rec("A", "D1", 1, 0.6)])["overall"]["A"]
        assert one["recall"]["mean"] == 0.6 and one["recall"]["stdev"] is None
        none = summarize([_rec("A", "D1", 1, 0.0, status="failed")])["overall"]["A"]
        assert none["n_ok"] == 0 and none["n_failed"] == 1
        assert none["recall"] == {"mean": None, "stdev": None, "min": None, "max": None}

    def test_failed_runs_are_excluded_from_means_but_counted(self):
        records = [_rec("A", "D1", 1, 0.8), _rec("A", "D1", 2, 0.0, status="failed")]
        stats = summarize(records)["per_drawing"]["A"]["D1"]
        assert stats["recall"]["mean"] == 0.8
        assert (stats["n_ok"], stats["n_failed"], stats["errors"]) == (1, 1, ["RuntimeError"])

    def test_none_precision_values_are_skipped(self):
        records = [_rec("A", "D1", 1, 0.8, precision=None), _rec("A", "D1", 2, 0.8, precision=0.5)]
        assert summarize(records)["overall"]["A"]["label_precision"]["mean"] == 0.5


class TestFailureIsolation:
    def test_a_raising_engine_is_recorded_with_its_type_only_and_the_rest_complete(self, tmp_path):
        secret = "sk-secret-123"
        log, clock = [], Clock()
        bad = StubEngine("A", log, clock, fail_on={2: RuntimeError(secret)})
        records = run_comparison([bad], [_drawing()], 3, clock=clock, timeout=None)
        assert [r.status for r in records] == ["ok", "failed", "ok"]
        assert records[1].error == "RuntimeError"
        summary = summarize(records)
        path = write_results(tmp_path / "r.json", {}, records, summary)
        blob = json.dumps([r.__dict__ for r in records]) + path.read_text() + format_table(summary)
        assert secret not in blob

    @pytest.mark.parametrize("output", [{"foo": 1}, None, "text", {"nodes": "not a list"}])
    def test_output_without_category_lists_is_unparseable(self, output):
        class Raw:
            name = "A"

            def run(self, image_path, drawing):
                return output

        (record,) = run_comparison([Raw()], [_drawing()], 1, timeout=None)
        assert (record.status, record.error) == ("failed", "UnparseableOutput")

    def test_valid_but_empty_lists_is_a_success_with_zero_recall(self):
        empty = {c: [] for c in CATEGORIES}
        log, clock = [], Clock()
        (record,) = run_comparison(
            [StubEngine("A", log, clock, output=empty)], [_drawing()], 1, clock=clock, timeout=None
        )
        assert record.status == "ok" and record.score["mean_count_recall"] == 0.0

    def test_a_hung_engine_times_out_and_the_next_run_proceeds(self):
        class Slow:
            name = "A"
            calls = 0

            def run(self, image_path, drawing):
                self.calls += 1
                if self.calls == 1:
                    time.sleep(0.5)
                return _good()

        records = run_comparison([Slow()], [_drawing()], 2, timeout=0.05)
        assert [(r.status, r.error) for r in records] == [("failed", "TimeoutError"), ("ok", None)]


class TestBudget:
    def test_runs_after_the_cap_are_skipped_and_flagged_incomplete(self):
        log, clock, meter = [], Clock(), UsageMeter(max_tokens=100)
        eng = StubEngine("A", log, clock, tokens=60, meter=meter)
        records = run_comparison([eng], [_drawing()], 4, clock=clock, meter=meter, timeout=None)
        assert [r.status for r in records] == ["ok", "ok", "skipped_budget", "skipped_budget"]
        assert eng.calls == 2
        summary = summarize(records)
        assert summary["complete"] is False
        assert summary["overall"]["A"]["n_ok"] == 2 and summary["overall"]["A"]["n_skipped"] == 2
        assert "INCOMPLETE" in format_table(summary)

    def test_cap_already_hit_skips_everything_without_crashing(self):
        meter = UsageMeter(max_calls=0)
        log, clock = [], Clock()
        eng = StubEngine("A", log, clock, meter=meter)
        records = run_comparison([eng], [_drawing()], 2, clock=clock, meter=meter, timeout=None)
        assert all(r.status == "skipped_budget" for r in records) and eng.calls == 0

    def test_engine_raising_spend_cap_marks_that_run_skipped_not_failed(self):
        log, clock = [], Clock()
        eng = StubEngine("A", log, clock, fail_on={1: SpendCapReached("cap")})
        (record,) = run_comparison([eng], [_drawing()], 1, clock=clock, timeout=None)
        assert record.status == "skipped_budget" and record.error is None


class TestResultsAndTable:
    def _records(self):
        return [_rec("A", "D1", 1, 0.5, 0.9), _rec("B", "D1", 1, 0.7, 0.8)]

    def test_results_file_has_meta_records_and_summary(self, tmp_path):
        records = self._records()
        path = write_results(
            tmp_path / "out" / "r.json", {"model": "m"}, records, summarize(records)
        )
        data = json.loads(path.read_text())
        assert data["meta"] == {"model": "m"}
        assert len(data["records"]) == 2 and data["summary"]["engines"] == ["A", "B"]

    def test_default_results_dir_is_git_ignored(self):
        probe = default_results_path()
        assert probe.parent == DEFAULT_RESULTS_DIR
        result = subprocess.run(
            ["git", "check-ignore", "-q", probe.as_posix()], cwd=REPO_ROOT, capture_output=True
        )
        assert result.returncode == 0

    def test_api_key_value_is_redacted_from_the_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-key-123")
        records = self._records()
        meta = {"note": "leaked sk-fake-key-123 here"}
        path = write_results(tmp_path / "r.json", meta, records, summarize(records))
        text = path.read_text()
        assert "sk-fake-key-123" not in text and "[redacted]" in text

    def test_table_has_per_drawing_and_overall_rows_with_counts(self):
        table = format_table(summarize(self._records()))
        rows = [line for line in table.splitlines() if line.startswith("| D1") or "ALL" in line]
        assert len(rows) == 4  # A and B on D1, A and B overall
        assert "1/0/0" in rows[0] and "USD" not in table and "INCOMPLETE" not in table

    def test_prices_add_a_dollar_column(self):
        table = format_table(
            summarize(self._records()), {"price_in_per_m": 1.0, "price_out_per_m": 4.0}
        )
        assert "USD/run" in table and "0.0001" in table  # 100 prompt tokens at $1/M

    def test_scores_are_real_ade15_scores_when_not_stubbed(self):
        log, clock = [], Clock()
        (record,) = run_comparison(
            [StubEngine("A", log, clock, output=_good(nodes=2, valves=2))],
            [_drawing()],
            1,
            clock=clock,
            timeout=None,
        )
        assert record.score["categories"]["nodes"]["recall"] == 0.5
        assert record.score["categories"]["valves"]["recall"] == 1.0


class TestArguments:
    def test_defaults(self):
        args = parse_args([])
        assert (args.runs, args.engines, args.model) == (5, ["new", "old"], "gpt-5.4-mini")
        assert args.max_calls > 0 and args.max_tokens > 0
        assert args.old_ocr == "paddle"

    def test_perception_notes_name_what_each_engine_used(self):
        from src.eval.pid_compare import perception_notes

        assert perception_notes("paddle")["old"] == "ocr_provider=paddle"
        assert "no layout/OCR tool" in perception_notes("none")["old"]
        assert "VLM" in perception_notes("paddle")["new"]

    @pytest.mark.parametrize(
        "argv",
        [
            ["--runs", "0"],
            ["--engines", "new,legacy"],
            ["--price-in", "1"],
            ["--engines", ""],
            ["--old-ocr", "bogus"],
        ],
    )
    def test_bad_arguments_exit_before_anything_runs(self, argv):
        with pytest.raises(SystemExit):
            parse_args(argv)
