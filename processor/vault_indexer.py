import json

from processor.log import get_logger
from processor.paths import VAULT
from processor.processing_state import ProcessingState

INDEX = VAULT / "index"

_SEARCH_FOLDERS = {"projects", "people", "wiki", "meeting", "daily"}

logger = get_logger(__name__)


class VaultIndexer:

    def __init__(self):
        self.force = False

    def process(self) -> None:
        INDEX.mkdir(parents=True, exist_ok=True)

        output = INDEX / "vault_index.json"
        state = ProcessingState("vault_index")
        current_state: dict[str, float] = {}
        documents = []

        for file in VAULT.rglob("*.md"):
            relative = file.relative_to(VAULT)
            if relative.parts[0] not in _SEARCH_FOLDERS:
                continue
            mtime = file.stat().st_mtime
            current_state[str(file.resolve())] = mtime
            documents.append(
                {
                    "title": file.stem,
                    "path": str(relative).replace("\\", "/"),
                    "folder": relative.parts[0],
                    "modified": mtime,
                }
            )

        if not self.force and state.state == current_state and output.exists():
            logger.info("[SKIP] Vault Index")
            return

        state.state = current_state
        state.save()

        output.write_text(
            json.dumps(documents, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
        logger.info(f"[INDEX] {len(documents)} document(s)")
        logger.info(f"[SAVE] {output}")
