"""Tests for MarkdownProcessor — incremental + --force behavior."""

import pytest

import processor.markdown_processor as mp_module
import processor.processing_state as ps_module
from processor.markdown_processor import MarkdownProcessor


@pytest.fixture(autouse=True)
def patch_paths(vault, monkeypatch):
    monkeypatch.setattr(mp_module, "SOURCES", [("slack", "SlackProvider", vault / "slack")])
    monkeypatch.setattr(mp_module, "SOURCE_NAMES", ["slack"])
    monkeypatch.setattr(mp_module, "KNOWLEDGE_ROOT", vault / "knowledge")
    monkeypatch.setattr(ps_module, "STATE_DIR", vault / "index")


def test_no_files(caplog):
    proc = MarkdownProcessor()
    proc.process()
    assert "No markdown files" in caplog.text


def test_processes_file(vault):
    (vault / "slack" / "chat.md").write_text("hello world", encoding="utf-8")

    MarkdownProcessor().process()

    output = vault / "knowledge" / "slack" / "chat.md"
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "source: slack" in content
    assert "hello world" in content
    assert "original_file: chat.md" in content


def test_output_has_frontmatter(vault):
    (vault / "slack" / "msg.md").write_text("body", encoding="utf-8")
    MarkdownProcessor().process()

    content = (vault / "knowledge" / "slack" / "msg.md").read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "provider: SlackProvider" in content


def test_incremental_skip(vault, caplog):
    src = vault / "slack" / "a.md"
    src.write_text("data", encoding="utf-8")

    MarkdownProcessor().process()
    caplog.clear()
    MarkdownProcessor().process()  # Second run — nothing changed

    assert "[SKIP]" in caplog.text


def test_force_reprocesses(vault, caplog):
    src = vault / "slack" / "b.md"
    src.write_text("data", encoding="utf-8")

    MarkdownProcessor().process()
    caplog.clear()

    proc = MarkdownProcessor()
    proc.force = True
    proc.process()

    assert "[PROCESS]" in caplog.text
    assert "[SKIP]" not in caplog.text


def test_multiple_files(vault):
    for i in range(3):
        (vault / "slack" / f"file{i}.md").write_text(f"content {i}", encoding="utf-8")

    MarkdownProcessor().process()

    outputs = list((vault / "knowledge" / "slack").glob("*.md"))
    assert len(outputs) == 3
