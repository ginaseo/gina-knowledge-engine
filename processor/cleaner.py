from pathlib import Path

from processor.log import get_logger
from processor.paths import VAULT

logger = get_logger(__name__)


class Cleaner:

    INVALID_PREFIX = ("?", " ", "湲", "臾")

    def process(self) -> None:
        logger.info("=" * 60)
        logger.info(" Vault Cleanup ")
        logger.info("=" * 60)

        removed = 0

        for folder in (VAULT / "wiki", VAULT / "projects", VAULT / "people"):
            if not folder.exists():
                continue
            for file in folder.rglob("*.md"):
                if self._remove_invalid(file) or self._remove_empty(file):
                    removed += 1

        logger.info(f"[CLEAN] Removed : {removed} file(s)")

    def _remove_invalid(self, file: Path) -> bool:
        if any(file.stem.startswith(p) for p in self.INVALID_PREFIX):
            file.unlink()
            logger.info(f"[DELETE] {file.name}")
            return True
        return False

    def _remove_empty(self, file: Path) -> bool:
        if not file.read_text(encoding="utf-8").strip():
            file.unlink()
            logger.info(f"[DELETE] {file.name}")
            return True
        return False
