"""ChatGPT data-export provider — one-time bulk import. Reads the
conversations-*.json files out of an OpenAI "Export data" ZIP (or an already
unzipped directory) and lands one markdown file per conversation into
HermesVault, same shape as the other providers, for the existing
Markdown/Summary/Entity/Wiki pipeline to pick up.

Usage:
    python ingest/providers/chatgpt.py "C:\\path\\to\\export.zip"
"""

import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ingest.base import BaseProvider
from processor.paths import VAULT

STATE_FILE = VAULT / "index" / "chatgpt_state.json"
_UNSAFE_ID_CHARS = re.compile(r"[^A-Za-z0-9_-]")


class ChatGPTProvider(BaseProvider):

    def __init__(self, export_path: str):
        self.export_path = Path(export_path)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_state(self) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def connect(self):
        pass  # local export file, nothing to connect to

    def fetch(self):
        raw_conversations = list(self._iter_raw_conversations())
        if not raw_conversations:
            return None

        conversations = []
        for conv in raw_conversations:
            conv_id = conv.get("conversation_id") or conv.get("id")
            update_time = conv.get("update_time")
            if not conv_id:
                continue
            if conv_id in self.state and self.state[conv_id] == update_time:
                continue  # already imported, unchanged since

            turns = self._walk(conv.get("mapping") or {}, conv.get("current_node"))
            if not turns:
                continue

            conversations.append({
                "id": conv_id,
                "title": (conv.get("title") or "Untitled").strip(),
                "create_time": conv.get("create_time"),
                "update_time": update_time,
                "turns": turns,
            })

        return conversations or None

    def _iter_raw_conversations(self):
        if self.export_path.is_dir():
            for f in sorted(self.export_path.glob("conversations*.json")):
                yield from json.loads(f.read_text(encoding="utf-8"))
            return

        with zipfile.ZipFile(self.export_path) as zf:
            names = sorted(n for n in zf.namelist() if re.match(r"conversations.*\.json$", n))
            for name in names:
                with zf.open(name) as f:
                    yield from json.load(f)

    @staticmethod
    def _walk(mapping: dict, current_node) -> list:
        """Follow the parent chain from current_node back to the root — this
        is the branch the export's `current_node` points at, i.e. the final
        conversation as ChatGPT displays it, skipping abandoned regenerations."""
        turns = []
        node_id = current_node
        while node_id:
            node = mapping.get(node_id)
            if node is None:
                break
            msg = node.get("message")
            if msg:
                role = (msg.get("author") or {}).get("role")
                content = msg.get("content") or {}
                if role in ("user", "assistant") and content.get("content_type") == "text":
                    parts = content.get("parts") or []
                    text = "\n".join(p.strip() for p in parts if isinstance(p, str) and p.strip())
                    if text:
                        turns.append((role, text))
            node_id = node.get("parent")
        turns.reverse()
        return turns

    def save(self, data):
        for conv in data:
            create_time = conv.get("create_time") or conv.get("update_time")
            dt = datetime.fromtimestamp(create_time) if create_time else datetime.now()
            year, month, date = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%Y-%m-%d")

            vault_dir = VAULT / "chatgpt" / year / month
            vault_dir.mkdir(parents=True, exist_ok=True)

            safe_id = _UNSAFE_ID_CHARS.sub("_", conv["id"])
            filename = vault_dir / f"{date}-{safe_id}.md"

            with open(filename, "w", encoding="utf-8", newline="\n") as f:
                f.write(f"# {conv['title']}\n\n")
                f.write(f"Date: {date}\n")
                f.write(f"Conversation ID: {conv['id']}\n\n")
                f.write("---\n\n")
                for role, text in conv["turns"]:
                    label = "나 (Human)" if role == "user" else "ChatGPT"
                    f.write(f"### {label}\n\n{text}\n\n---\n\n")

            self.state[conv["id"]] = conv["update_time"]

        self._save_state()
        print(f"[ChatGPT] Saved {len(data)} conversations")


def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest/providers/chatgpt.py <export.zip | export-dir>")
        sys.exit(1)
    ChatGPTProvider(sys.argv[1]).run()


if __name__ == "__main__":
    main()
