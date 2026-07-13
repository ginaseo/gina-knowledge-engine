"""Tests for the Hermes MCP server — search/build_context/health, error contract."""

import asyncio
import json
import time

import pytest
from mcp.server.fastmcp.exceptions import ToolError

import processor.evaluator as evaluator_module
import processor.mcp.server as srv_module
from processor.mcp.server import build_context, evaluate, health, mcp, search


@pytest.fixture(autouse=True)
def patch_paths(vault, monkeypatch):
    monkeypatch.setattr(srv_module, "VAULT", vault)
    monkeypatch.setattr(srv_module.retrieval, "INDEX_FILE", vault / "index" / "vault_index.json")


def _write_index(vault, docs):
    (vault / "index" / "vault_index.json").write_text(
        json.dumps(docs, ensure_ascii=False), encoding="utf-8"
    )


def _doc(title, path, folder="wiki"):
    return {"title": title, "path": path, "folder": folder, "modified": 1.0}


def _error_code(exc: ToolError) -> str:
    return json.loads(str(exc))["error"]["code"]


def test_search_returns_ranked_results(vault):
    (vault / "wiki" / "Kafka.md").write_text("kafka content", encoding="utf-8")
    _write_index(vault, [_doc("Kafka", "wiki/Kafka.md")])

    result = search("kafka")
    assert result["schema_version"] == "1.0"
    assert result["total"] == 1
    assert result["results"][0]["id"] == "wiki/Kafka.md"


def test_search_empty_query_raises_invalid_argument():
    with pytest.raises(ToolError) as exc:
        search("")
    assert _error_code(exc.value) == "INVALID_ARGUMENT"


def test_search_no_match_returns_empty_results_not_error(vault):
    _write_index(vault, [_doc("unrelated", "wiki/Unrelated.md")])
    result = search("zzz_no_such_keyword_anywhere")
    assert result["total"] == 0
    assert result["results"] == []


def test_search_vault_missing_raises_vault_unavailable(vault, monkeypatch):
    monkeypatch.setattr(srv_module, "VAULT", vault / "does-not-exist")
    with pytest.raises(ToolError) as exc:
        search("kafka")
    assert _error_code(exc.value) == "VAULT_UNAVAILABLE"


def test_build_context_assembles_related(vault):
    (vault / "wiki" / "Kafka.md").write_text("Kafka body [[Java]]", encoding="utf-8")
    (vault / "wiki" / "Java.md").write_text("Java body", encoding="utf-8")
    _write_index(
        vault,
        [_doc("Kafka", "wiki/Kafka.md"), _doc("Java", "wiki/Java.md")],
    )

    result = build_context("wiki/Kafka.md")
    assert "Kafka body" in result["context"]
    assert "Java body" in result["context"]
    assert "wiki/Java.md" in result["sources"]
    assert result["truncated"] is False


def test_build_context_invalid_id_raises_not_found(vault):
    with pytest.raises(ToolError) as exc:
        build_context("wiki/DoesNotExist.md")
    assert _error_code(exc.value) == "NOT_FOUND"


def test_build_context_rejects_path_traversal(vault):
    with pytest.raises(ToolError) as exc:
        build_context("../../etc/passwd")
    assert _error_code(exc.value) == "INVALID_ARGUMENT"


def test_build_context_max_tokens_truncates(vault):
    (vault / "wiki" / "Big.md").write_text("x" * 10000, encoding="utf-8")
    _write_index(vault, [_doc("Big", "wiki/Big.md")])

    result = build_context("wiki/Big.md", max_tokens=200)
    assert result["truncated"] is True
    assert len(result["context"]) <= 200 * 4


def test_health_ok(vault):
    result = health()
    assert result["schema_version"] == "1.0"
    assert result["status"] == "ok"
    assert result["vault_accessible"] is True
    assert result["uptime_s"] >= 0


def test_health_degraded_when_vault_missing(vault, monkeypatch):
    monkeypatch.setattr(srv_module, "VAULT", vault / "does-not-exist")
    result = health()
    assert result["status"] == "degraded"
    assert result["vault_accessible"] is False


def test_search_timeout(vault, monkeypatch):
    _write_index(vault, [_doc("Kafka", "wiki/Kafka.md")])
    monkeypatch.setattr(srv_module, "SEARCH_TIMEOUT", 0.0001)

    def _slow_search(*a, **k):
        time.sleep(0.05)
        return []

    monkeypatch.setattr(srv_module.retrieval, "_search", _slow_search)
    with pytest.raises(ToolError) as exc:
        search("kafka")
    assert _error_code(exc.value) == "TIMEOUT"


def test_mcp_server_registers_tools():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"search", "build_context", "health"} <= names


def test_evaluate_matches_dataclass_field_names(vault, monkeypatch):
    """Regression test: evaluate() once referenced field names that didn't
    exist on QualityMetrics/GraphMetrics (e.g. quality.coverage_pct,
    graph.nodes), raising AttributeError on every real call."""
    monkeypatch.setattr(evaluator_module, "VAULT", vault)

    result = evaluate()

    assert result["quality"].keys() == {
        "entity_coverage",
        "keyword_coverage",
        "relation_coverage",
        "summary_coverage",
        "missing_summaries",
        "missing_keywords",
        "missing_relations",
        "orphan_entities",
        "broken_refs",
    }
    assert result["graph"].keys() == {"nodes", "edges", "density", "components", "isolated"}
    assert isinstance(result["health_score"], float)
    assert isinstance(result["learning_score"], float)
