"""
TimelineProcessor — Phase 4

날짜별 Knowledge 축적을 타임라인으로 조회.
LLM 불필요 — vault_index.json 기반 정렬/필터.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "HermesVault"
INDEX_FILE = VAULT / "index" / "vault_index.json"


class TimelineProcessor:
    def run(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        entity: str | None = None,
        days: int = 30,
    ) -> dict:
        """
        Args:
            start_date: YYYY-MM-DD (default: days ago)
            end_date: YYYY-MM-DD (default: today)
            entity: 특정 엔티티 필터 (optional)
            days: start_date 미지정 시 최근 N일
        Returns:
            {"timeline": [{"date": "YYYY-MM-DD", "documents": [...], "count": N}]}
        """
        now = datetime.now(timezone.utc)

        if end_date:
            end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        else:
            end_dt = now

        if start_date:
            start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        else:
            start_dt = end_dt - timedelta(days=days)

        if not INDEX_FILE.exists():
            return {"timeline": [], "error": "vault_index.json not found"}

        docs = json.loads(INDEX_FILE.read_text(encoding="utf-8"))

        # 날짜별 그룹핑
        timeline: dict[str, list[str]] = {}
        for doc in docs:
            modified = doc.get("modified")
            if not modified:
                continue
            dt = datetime.fromtimestamp(modified, tz=timezone.utc)
            if not (start_dt <= dt <= end_dt):
                continue

            title = doc.get("title", "")
            if entity and entity.lower() not in title.lower():
                continue

            date_str = dt.strftime("%Y-%m-%d")
            timeline.setdefault(date_str, []).append(title)

        result = [
            {"date": date, "documents": titles, "count": len(titles)}
            for date, titles in sorted(timeline.items(), reverse=True)
        ]

        return {
            "timeline": result,
            "total_documents": sum(r["count"] for r in result),
            "period": {
                "start": start_dt.strftime("%Y-%m-%d"),
                "end": end_dt.strftime("%Y-%m-%d"),
            },
        }
