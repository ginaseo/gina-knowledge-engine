"""Tests for SummaryProcessor — LLM mocked, incremental + --force."""

from unittest.mock import MagicMock, patch

import pytest

import processor.processing_state as ps_module
import processor.summary_processor as sp_module
from processor.summary_processor import SummaryProcessor


@pytest.fixture(autouse=True)
def patch_paths(vault, monkeypatch, tmp_path):
    prompt_file = tmp_path / "summary_prompt.txt"
    prompt_file.write_text("Summarize: {markdown}", encoding="utf-8")

    monkeypatch.setattr(sp_module, "KNOWLEDGE_ROOT", vault / "knowledge")
    monkeypatch.setattr(sp_module, "OUTPUT", vault / "knowledge" / "summary")
    monkeypatch.setattr(sp_module, "PROMPT", prompt_file)
    monkeypatch.setattr(ps_module, "STATE_DIR", vault / "index")


def _mock_client(answer: str = "summary text"):
    """Return a MagicMock that behaves as `with LLMClient() as client:`."""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.ask.return_value = answer
    return mock


def test_no_files(caplog):
    SummaryProcessor().process()
    assert "No markdown files" in caplog.text


def test_all_skip_no_llm(vault, caplog):
    """If all files already processed, LLMClient must not be created."""
    src = vault / "knowledge" / "slack" / "f.md"
    src.write_text("body", encoding="utf-8")

    # First run to record state
    with patch("processor.summary_processor.LLMClient", return_value=_mock_client()):
        SummaryProcessor().process()

    caplog.clear()

    # Second run — no changes
    with patch("processor.summary_processor.LLMClient") as MockCls:
        SummaryProcessor().process()
        MockCls.assert_not_called()

    assert "[SKIP]" in caplog.text


def test_processes_file(vault):
    src = vault / "knowledge" / "slack" / "chat.md"
    src.write_text("message content", encoding="utf-8")

    mock = _mock_client("This is the summary.")
    with patch("processor.summary_processor.LLMClient", return_value=mock):
        SummaryProcessor().process()

    output = vault / "knowledge" / "summary" / "chat-summary.md"
    assert output.exists()
    assert output.read_text(encoding="utf-8") == "This is the summary."


def test_llm_failure_continues(vault, caplog):
    src = vault / "knowledge" / "slack" / "bad.md"
    src.write_text("data", encoding="utf-8")

    mock = _mock_client()
    mock.ask.side_effect = RuntimeError("API down")

    with patch("processor.summary_processor.LLMClient", return_value=mock):
        SummaryProcessor().process()  # Must not raise

    assert "[FAIL]" in caplog.text


def test_force_reprocesses(vault, caplog):
    src = vault / "knowledge" / "slack" / "x.md"
    src.write_text("data", encoding="utf-8")

    mock = _mock_client("summary")
    with patch("processor.summary_processor.LLMClient", return_value=mock):
        SummaryProcessor().process()
    caplog.clear()

    proc = SummaryProcessor()
    proc.force = True
    with patch("processor.summary_processor.LLMClient", return_value=mock):
        proc.process()

    assert "[SUMMARY]" in caplog.text
