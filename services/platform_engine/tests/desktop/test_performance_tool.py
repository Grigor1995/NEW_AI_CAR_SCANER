"""Pure-function and report-contract tests for optional Phase 4 benchmarks.

These tests do not initialize Qt or launch frozen Windows processes.
"""
from __future__ import annotations

import json
import sys

import pytest

import importlib.util
from pathlib import Path

BENCHMARK_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "benchmark_desktop.py"
)

spec = importlib.util.spec_from_file_location(
    "desktop_benchmark_under_test",
    BENCHMARK_PATH,
)

assert spec is not None and spec.loader is not None

perf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(perf)



def test_percentile_interpolation_and_single_sample():
    assert perf.percentile([40, 10, 20, 30], 50) == 25
    assert perf.percentile([10, 20, 30, 40], 95) == pytest.approx(38.5)
    assert perf.percentile([0.8], 95) == pytest.approx(0.8)
    with pytest.raises(ValueError, match="must not be empty"):
        perf.percentile([], 95)


def test_describe_ms_keeps_actual_sample_count_and_upper_tail():
    result = perf.describe_ms([1.0, 2.0, 9.0, 20.0])
    assert result["samples"] == 4
    assert result["p50_ms"] == 5.5
    assert result["max_ms"] == 20.0
    assert result["p95_ms"] > result["p50_ms"]


@pytest.fixture
def mocked_benchmark(monkeypatch, tmp_path):
    monkeypatch.setattr(perf, "ROOT", tmp_path)
    monkeypatch.setattr(perf, "benchmark_qt_source", lambda count: {
        "mode": "mocked-test-measurement",
        "navigation_latency": {"p95_ms": 12.5},
        "qt_timer_turnaround": {"p95_ms": 3.0},
    })
    return tmp_path


def test_ungated_performance_report_is_measured_not_sla_pass(
    mocked_benchmark, monkeypatch
):
    monkeypatch.setattr(sys, "argv", ["benchmark_desktop.py", "--iterations", "10"])
    assert perf.main() == 0
    data = json.loads(
        (mocked_benchmark / "desktop-test-reports" / "performance.json").read_text()
    )
    assert data["status"] == "MEASURED"
    assert data["packaged_exe"] is None


def test_performance_sla_rejects_navigation_p95_violation(
    mocked_benchmark, monkeypatch
):
    monkeypatch.setattr(
        sys, "argv",
        ["benchmark_desktop.py", "--max-navigation-p95-ms", "10"]
    )
    assert perf.main() == 1
    data = json.loads(
        (mocked_benchmark / "desktop-test-reports" / "performance.json").read_text()
    )
    assert data["status"] == "FAIL"
    assert any("navigation p95" in item for item in data["violations"])


def test_performance_sla_uses_p95_not_max_or_mean(
    mocked_benchmark, monkeypatch
):
    monkeypatch.setattr(
        sys, "argv", ["benchmark_desktop.py", "--max-navigation-p95-ms", "20",
                      "--max-qt-p95-ms", "10"]
    )
    assert perf.main() == 0
    data = json.loads(
        (mocked_benchmark / "desktop-test-reports" / "performance.json").read_text()
    )
    assert data["status"] == "PASS"
    assert data["violations"] == []
