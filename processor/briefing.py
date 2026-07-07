"""
BriefingProcessor — Phase 4

매일 아침 vault의 최신 변화를 요약해 Slack에 자동 게시.
TODO: 구현 예정
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "HermesVault"


class BriefingProcessor:
    def run(self, date: str | None = None, channel: str | None = None) -> dict:
        raise NotImplementedError("BriefingProcessor is not yet implemented (Phase 4)")
