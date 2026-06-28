"""Tests for Evaluator — file counting, health score, deductions, learning score."""
import pytest
from unittest.mock import patch
from pathlib import Path

from processor.evaluator import (
    Evaluator,
    KnowledgeStats,
    QualityMetrics,
    _count,
)


def test_count_missing_directory(tmp_path):
    assert _count(tmp_path / "nonexistent", "*.md") == 0


def test_count_matching_files(tmp_path):
    (tmp_path / "a.md").write_text("x")
    (tmp_path / "b.md").write_text("x")
    (tmp_path / "c.json").write_text("{}")
    assert _count(tmp_path, "*.md") == 2


def test_health_score_perfect():
    e = Evaluator()
    stats = KnowledgeStats(summaries=0, documents=0)
    quality = QualityMetrics()
    score, deductions = e._compute_health(stats, quality)
    assert score == 100.0
    assert deductions == []


def test_health_deduction_for_low_coverage():
    e = Evaluator()
    stats = KnowledgeStats(summaries=10, documents=10)
    quality = QualityMetrics(
        entity_coverage=0.0,
        keyword_coverage=0.0,
        relation_coverage=0.0,
        summary_coverage=0.0,
    )
    score, deductions = e._compute_health(stats, quality)
    assert score < 100.0
    assert len(deductions) > 0


def test_health_score_clamped_to_zero():
    e = Evaluator()
    stats = KnowledgeStats(summaries=10, documents=10)
    quality = QualityMetrics(
        entity_coverage=0.0,
        keyword_coverage=0.0,
        relation_coverage=0.0,
        summary_coverage=0.0,
        orphan_entities=100,
        broken_references=100,
        duplicate_entity_names=100,
    )
    score, _ = e._compute_health(stats, quality)
    assert score >= 0.0


def test_learning_score_no_growth():
    e = Evaluator()
    growth = {"7d": {"documents": 0, "summaries": 0, "entities": 0}}
    score = e._compute_learning(80.0, growth)
    assert score == round(80.0 * 0.7, 1)


def test_learning_score_with_growth_capped():
    e = Evaluator()
    growth = {"7d": {"documents": 100}}
    # health=100, growth_pts capped at 30 → min(100*0.7+30, 100) = 100
    score = e._compute_learning(100.0, growth)
    assert score == 100.0
