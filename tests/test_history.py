"""Tests for JobHistory — persistence, rolling window, last_success."""
import json
import pytest
from unittest.mock import patch
from pathlib import Path

from processor.history import JobHistory, JobRecord, _MAX_RECORDS


def _record(name="test", status="ok", finish="2026-01-01T00:00:00+00:00") -> JobRecord:
    return JobRecord(
        name=name,
        start_time="2026-01-01T00:00:00+00:00",
        finish_time=finish,
        duration=1.0,
        status=status,
    )


@pytest.fixture
def history(tmp_path, monkeypatch):
    hist_file = tmp_path / "job_history.json"
    monkeypatch.setattr("processor.history.HISTORY_FILE", hist_file)
    return JobHistory()


def test_empty_display_logs_no_history(history, caplog):
    history.display(n=20)
    assert "No job history" in caplog.text


def test_append_persists_to_disk(history, tmp_path, monkeypatch):
    hist_file = tmp_path / "job_history.json"
    monkeypatch.setattr("processor.history.HISTORY_FILE", hist_file)
    h = JobHistory()
    h.append(_record("markdown", "ok"))
    data = json.loads(hist_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["name"] == "markdown"


def test_rolling_window_caps_at_max(tmp_path, monkeypatch):
    hist_file = tmp_path / "job_history.json"
    monkeypatch.setattr("processor.history.HISTORY_FILE", hist_file)
    h = JobHistory()
    for i in range(_MAX_RECORDS + 5):
        h.append(_record(name=f"job{i}"))
    data = json.loads(hist_file.read_text(encoding="utf-8"))
    assert len(data) == _MAX_RECORDS
    # Most recent records kept
    assert data[-1]["name"] == f"job{_MAX_RECORDS + 4}"


def test_last_success_returns_most_recent_ok(tmp_path, monkeypatch):
    hist_file = tmp_path / "job_history.json"
    monkeypatch.setattr("processor.history.HISTORY_FILE", hist_file)
    h = JobHistory()
    h.append(_record("wiki", "ok", finish="2026-01-01T10:00:00+00:00"))
    h.append(_record("wiki", "fail", finish="2026-01-01T11:00:00+00:00"))
    h.append(_record("wiki", "ok", finish="2026-01-01T12:00:00+00:00"))
    result = h.last_success("wiki")
    assert result == "2026-01-01T12:00:00+00:00"


def test_last_success_returns_none_when_no_ok(tmp_path, monkeypatch):
    hist_file = tmp_path / "job_history.json"
    monkeypatch.setattr("processor.history.HISTORY_FILE", hist_file)
    h = JobHistory()
    h.append(_record("wiki", "fail"))
    assert h.last_success("wiki") is None
