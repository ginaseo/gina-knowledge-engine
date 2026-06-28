"""Tests for retrieval — _keywords, _score, _search."""
import pytest

from processor.retrieval import _keywords, _score, _search


def test_keywords_lowercases_and_filters_stop_words():
    result = _keywords("What is the Hermes project?")
    assert "hermes" in result
    assert "project" in result
    # stop words removed
    assert "what" not in result
    assert "is" not in result
    assert "the" not in result


def test_keywords_filters_single_char():
    result = _keywords("a b c test")
    assert "test" in result
    assert "a" not in result
    assert "b" not in result
    assert "c" not in result


def test_score_exact_match():
    doc = {"title": "hermes agent", "folder": "knowledge/summary"}
    s = _score("What is the Hermes Agent?", doc)
    assert s > 0.0


def test_score_no_overlap():
    doc = {"title": "unrelated doc", "folder": "slack"}
    s = _score("What is Hermes?", doc)
    assert s == 0.0


def test_score_empty_question():
    doc = {"title": "hermes", "folder": "summary"}
    s = _score("", doc)
    assert s == 0.0


def test_search_returns_ranked_results():
    index = [
        {"title": "hermes agent overview", "folder": "summary"},
        {"title": "slack export guide", "folder": "docs"},
        {"title": "hermes pipeline config", "folder": "summary"},
    ]
    results = _search("hermes configuration", index, top_k=5)
    titles = [r["title"] for r in results]
    assert "hermes pipeline config" in titles
    assert "hermes agent overview" in titles


def test_search_top_k_limits_results():
    index = [{"title": f"hermes doc {i}", "folder": "summary"} for i in range(10)]
    results = _search("hermes", index, top_k=3)
    assert len(results) <= 3


def test_search_excludes_zero_score():
    index = [
        {"title": "completely unrelated", "folder": "other"},
        {"title": "hermes agent", "folder": "summary"},
    ]
    results = _search("hermes", index, top_k=5)
    titles = [r["title"] for r in results]
    assert "hermes agent" in titles
    # zero-score docs excluded
    assert "completely unrelated" not in titles
