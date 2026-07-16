import json

from processor.log import get_logger
from processor.paths import VAULT
from processor.processing_state import ProcessingState

logger = get_logger(__name__)


class Validator:

    def process(self) -> None:
        logger.info("=" * 60)
        logger.info(" Vault Validation ")
        logger.info("=" * 60)

        ok = True
        ok &= self.validate_utf8()
        ok &= self.validate_summary()
        ok &= self.validate_entity()

        logger.info("=" * 60)
        logger.info(" Validation Passed " if ok else " Validation Failed ")
        logger.info("=" * 60)

    def validate_utf8(self) -> bool:
        logger.info("\n[UTF8 CHECK]")
        state = ProcessingState("validator_utf8")
        failed = 0

        for file in VAULT.rglob("*"):
            if file.suffix not in (".md", ".json"):
                continue
            if not state.is_modified(file):
                continue
            try:
                file.read_text(encoding="utf-8")
                state.update(file)
            except UnicodeDecodeError:
                failed += 1
                logger.error(f"[FAIL] {file}")

        if failed == 0:
            logger.info("[PASS] UTF-8 Decode")

        state.save()
        return failed == 0

    def validate_summary(self) -> bool:
        folder = VAULT / "knowledge" / "summary"
        if not folder.exists():
            logger.warning("[WARN] Summary folder missing -- run SummaryProcessor first")
            return True
        count = len(list(folder.glob("*.md")))
        logger.info(f"[SUMMARY] {count} file(s)")
        return True

    def validate_entity(self) -> bool:
        folder = VAULT / "knowledge" / "entity"
        state = ProcessingState("validator_entity")
        failed = 0

        for file in folder.glob("*.json"):
            if not state.is_modified(file):
                continue
            try:
                json.loads(file.read_text(encoding="utf-8"))
                state.update(file)
            except Exception:
                failed += 1
                logger.error(f"[FAIL] {file}")

        if failed == 0:
            logger.info("[PASS] Entity JSON")

        state.save()
        return failed == 0
