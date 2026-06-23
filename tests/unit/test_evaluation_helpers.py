"""Unit tests for deterministic evaluation report aggregation."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evals import helpers
from evals.schemas import ScoreSchema

pytestmark = pytest.mark.unit


def test_format_messages_handles_tool_call_variants() -> None:
    """Evaluation formatting supports tool calls from both LangChain shapes."""
    rendered = helpers.format_messages(
        [
            {"type": "assistant", "content": "Searching", "additional_kwargs": {"tool_calls": [{"function": {"arguments": "{\\\"q\\\": \\\"rain\\\"}"}}]}},
            {"type": "tool", "name": "search", "content": "result"},
            {"type": "assistant", "content": "Final answer"},
        ]
    )

    assert "tool search: result" in rendered
    assert "assistant: Final answer" in rendered


def test_get_input_output_returns_none_for_non_dict_output() -> None:
    """Malformed traces are skipped rather than breaking an evaluation run."""
    trace = SimpleNamespace(output="not a trace output")

    assert helpers.get_input_output(trace) == (None, None)


def test_report_aggregation_tracks_success_and_failure() -> None:
    """Scores contribute to per-metric averages and trace outcome details."""
    report = helpers.initialize_report("test-model")
    helpers.initialize_metrics_summary(report, [{"name": "helpfulness"}])
    trace_results = {"trace-1": {"metrics_succeeded": 0, "metrics_evaluated": 1, "metrics_results": {}}}

    helpers.update_success_metrics(
        report,
        "trace-1",
        "helpfulness",
        ScoreSchema(score=0.8, reasoning="grounded"),
        trace_results,
    )
    helpers.process_trace_results(report, "trace-1", trace_results, metrics_count=1)
    helpers.calculate_avg_scores(report)

    assert report["successful_traces"] == 1
    assert report["metrics_summary"]["helpfulness"]["avg_score"] == 0.8


def test_generate_report_writes_json_to_configured_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Evaluation reports are persisted as JSON and linked from the report object."""
    monkeypatch.setattr(helpers.os.path, "dirname", lambda _: str(tmp_path))
    report = {"model": "test-model"}

    report_path = Path(helpers.generate_report(report))

    assert report_path.exists()
    assert json.loads(report_path.read_text(encoding="utf-8"))["model"] == "test-model"
    assert report["generate_report_path"] == str(report_path)
