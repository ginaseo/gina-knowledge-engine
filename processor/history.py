"""Job execution history — persistence and display."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from processor.log import get_logger
from processor.paths import VAULT

logger = get_logger(__name__)

HISTORY_FILE = VAULT / "index" / "job_history.json"
_MAX_RECORDS = 500


@dataclass
class JobRecord:
    name: str
    start_time: str
    finish_time: str
    duration: float
    status: str  # "ok" | "fail"
    exception: str | None = None
    retry_count: int = 0

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()


class JobHistory:

    def __init__(self) -> None:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[dict] = []
        if HISTORY_FILE.exists():
            try:
                self._records = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                self._records = []

    def append(self, record: JobRecord) -> None:
        self._records.append(asdict(record))
        if len(self._records) > _MAX_RECORDS:
            self._records = self._records[-_MAX_RECORDS:]
        HISTORY_FILE.write_text(
            json.dumps(self._records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def last_success(self, name: str) -> str | None:
        for r in reversed(self._records):
            if r["name"] == name and r["status"] == "ok":
                return r["finish_time"]
        return None

    def display(self, n: int = 20) -> None:
        recent = list(reversed(self._records[-n:]))
        if not recent:
            logger.info("No job history.")
            return
        logger.info("=" * 72)
        logger.info(" Job History (most recent first)")
        logger.info("=" * 72)
        logger.info(f"  {'Job':<14}  {'Status':<6}  {'Time':>8}  {'Retries':>7}  Finished")
        logger.info(f"  {'-'*14}  {'-'*6}  {'-'*8}  {'-'*7}  {'-'*19}")
        for r in recent:
            status = r["status"].upper()
            dur = f"{r['duration']:.2f}s"
            exc = f"  <- {str(r['exception'])[:40]}" if r.get("exception") else ""
            logger.info(
                f"  {r['name']:<14}  {status:<6}  {dur:>8}"
                f"  {r['retry_count']:>7}  {r['finish_time'][:19]}{exc}"
            )
        logger.info("=" * 72)
