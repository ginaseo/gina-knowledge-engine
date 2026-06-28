"""Retrieval benchmark — evaluates search quality; auto-generates question dataset."""
from __future__ import annotations

import json
import re
from pathlib import Path

from processor.log import get_logger

logger = get_logger(__name__)

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "HermesVault"
QUESTIONS_FILE = VAULT / "benchmark" / "questions.json"
INDEX_FILE = VAULT / "index" / "vault_index.json"

_STOP = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "what", "who", "how", "when", "where", "why", "which",
    "in", "on", "at", "to", "of", "for", "and", "or", "not", "do",
})


def _keywords(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in tokens if t not in _STOP and len(t) > 1}


def _score(question: str, doc: dict) -> float:
    qkw = _keywords(question)
    doc_text = f"{doc.get('title', '')} {doc.get('folder', '')}".lower()
    dkw = _keywords(doc_text)
    if not qkw:
        return 0.0
    return len(qkw & dkw) / len(qkw)


def _search(question: str, index: list[dict], top_k: int = 5) -> list[dict]:
    """Return top-K documents ranked by keyword overlap with the question."""
    scored = sorted(
        ((doc, _score(question, doc)) for doc in index),
        key=lambda x: x[1],
        reverse=True,
    )
    return [doc for doc, s in scored[:top_k] if s > 0]


def generate_questions(save: bool = True) -> list[dict]:
    """Auto-generate benchmark questions from entity JSON files."""
    questions: list[dict] = []
    entity_dir = VAULT / "knowledge" / "entity"
    if not entity_dir.exists():
        return questions

    for ef in sorted(entity_dir.glob("*.json")):
        try:
            data = json.loads(ef.read_text(encoding="utf-8"))
        except Exception:
            continue
        entities = data if isinstance(data, list) else data.get("entities", [])
        stem = ef.stem.removesuffix("-summary")
        for e in entities[:3]:
            name = (e.get("name") or "").strip()
            if not name:
                continue
            questions.append({
                "question": f"What is {name}?",
                "expected_docs": [stem],
                "expected_entities": [name],
                "expected_keywords": [],
                "expected_projects": [name] if e.get("type") == "Project" else [],
            })

    if questions and save:
        QUESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        QUESTIONS_FILE.write_text(
            json.dumps(questions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"[BENCHMARK] Generated {len(questions)} question(s) -> {QUESTIONS_FILE}")

    return questions


class RetrievalBenchmark:

    def run(self) -> None:
        logger.info("=" * 60)
        logger.info(" Retrieval Benchmark")
        logger.info("=" * 60)

        # Load or generate questions
        if QUESTIONS_FILE.exists():
            try:
                questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"[BENCHMARK] Failed to load questions: {e}")
                return
        else:
            logger.info("[BENCHMARK] No questions file -- generating from vault.")
            questions = generate_questions(save=True)

        if not questions:
            logger.info("[BENCHMARK] No questions available. Add documents and run `hermes run` first.")
            return

        # Build search index: vault index + summary files
        index: list[dict] = []
        if INDEX_FILE.exists():
            try:
                index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

        summary_dir = VAULT / "knowledge" / "summary"
        if summary_dir.exists():
            existing = {d["title"] for d in index}
            for sf in summary_dir.glob("*.md"):
                if sf.stem not in existing:
                    index.append({
                        "title": sf.stem,
                        "path": str(sf.relative_to(VAULT)).replace("\\", "/"),
                        "folder": "knowledge/summary",
                    })

        if not index:
            logger.info("[BENCHMARK] Index is empty. Run `hermes run` first.")
            return

        # Evaluate
        top1 = top3 = top5 = 0
        sum_precision = sum_recall = 0.0
        valid = 0

        for q in questions:
            expected = set(q.get("expected_docs", []))
            if not expected:
                continue
            valid += 1

            results = _search(q["question"], index, top_k=5)
            titles = [r["title"] for r in results]
            titles_set = set(titles)

            top1 += int(bool(titles) and titles[0] in expected)
            top3 += int(any(t in expected for t in titles[:3]))
            top5 += int(any(t in expected for t in titles[:5]))

            tp = len(titles_set & expected)
            sum_precision += tp / len(titles_set) if titles_set else 0.0
            sum_recall += tp / len(expected)

        if valid == 0:
            logger.info("[BENCHMARK] No valid questions to evaluate.")
            return

        p = sum_precision / valid * 100
        r = sum_recall / valid * 100
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

        logger.info("")
        logger.info(f"  Questions      : {valid}")
        logger.info(f"  Top-1 Accuracy : {top1 / valid * 100:.1f}%")
        logger.info(f"  Top-3 Accuracy : {top3 / valid * 100:.1f}%")
        logger.info(f"  Top-5 Accuracy : {top5 / valid * 100:.1f}%")
        logger.info(f"  Recall         : {r:.1f}%")
        logger.info(f"  Precision      : {p:.1f}%")
        logger.info(f"  F1 Score       : {f1:.1f}%")
        logger.info("")
        logger.info("=" * 60)
