"""Codex CLI session provider — bulk-imports rollout transcripts from every
known CODEX_HOME's sessions/**/*.jsonl into HermesVault, same shape as the
Claude Code provider, for the existing Markdown/Wiki/Summary/Entity pipeline
to pick up. Codex has no SessionEnd hook wired to this repo, so this is a
rescan you run manually (or on a schedule) rather than a per-session hook
like claude_code.py.

Two separate CODEX_HOME locations exist on Windows and both persist rollout
files (unlike the ephemeral app-server threads used by /codex:* slash
commands, which don't persist anywhere):
- ~/.codex — the standalone `codex` CLI (e.g. a VS Code extension shelling
  out to it)
- %LOCALAPPDATA%\\JetBrains\\<product+version>\\aia\\codex — JetBrains AI
  Assistant's own bundled codex binary, used by its Codex integration in
  IntelliJ/other JetBrains IDEs. Globbed generically since the version
  segment (e.g. IntelliJIdea2025.3) changes across IDE updates.

Usage:
    python ingest/providers/codex.py
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ingest.base import BaseProvider
from processor.paths import VAULT


def _session_dirs() -> list[Path]:
    dirs = [Path.home() / ".codex" / "sessions"]
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        dirs += sorted(Path(local_appdata).glob("JetBrains/*/aia/codex/sessions"))
    return [d for d in dirs if d.exists()]


STATE_FILE = VAULT / "index" / "codex_state.json"
FILENAME_RE = re.compile(r"^rollout-(\d{4}-\d{2}-\d{2})T.*-([0-9a-fA-F-]{36})$")


class CodexProvider(BaseProvider):

    def __init__(self):
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
        pass  # local session files, nothing to connect to

    def fetch(self):
        session_dirs = _session_dirs()
        if not session_dirs:
            return None

        sessions = []
        paths = [p for d in session_dirs for p in d.rglob("rollout-*.jsonl")]
        for path in sorted(paths):
            m = FILENAME_RE.match(path.stem)
            if not m:
                continue
            date, session_id = m.group(1), m.group(2)

            mtime = path.stat().st_mtime
            key = str(path.resolve())
            if self.state.get(key) == mtime:
                continue  # already imported, unchanged since

            turns = self._extract_turns(path)
            if not turns:
                continue

            sessions.append({
                "path": path,
                "date": date,
                "session_id": session_id,
                "turns": turns,
                "mtime": mtime,
            })

        return sessions or None

    @staticmethod
    def _extract_turns(path: Path) -> list:
        turns = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "response_item":
                    continue
                payload = entry.get("payload") or {}
                if payload.get("type") != "message":
                    continue
                role = payload.get("role")
                if role not in ("user", "assistant"):
                    continue
                text = CodexProvider._extract_text(payload.get("content"))
                if text:
                    turns.append((role, text))
        return turns

    @staticmethod
    def _extract_text(content) -> str:
        if not isinstance(content, list):
            return ""
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") in ("input_text", "output_text", "text")
        ]
        return "\n".join(p for p in parts if p).strip()

    def save(self, data):
        for session in data:
            year, month = session["date"][:4], session["date"][5:7]
            vault_dir = VAULT / "codex" / year / month
            vault_dir.mkdir(parents=True, exist_ok=True)

            short_id = session["session_id"][:8]
            filename = vault_dir / f"{session['date']}-{short_id}.md"

            with open(filename, "w", encoding="utf-8", newline="\n") as f:
                f.write(f"# Codex Session — {short_id}\n\n")
                f.write(f"Date: {session['date']}\n")
                f.write(f"Session ID: {session['session_id']}\n\n")
                f.write("---\n\n")
                for role, text in session["turns"]:
                    label = "나 (Human)" if role == "user" else "Codex"
                    f.write(f"### {label}\n\n{text}\n\n---\n\n")

            print(f"[Codex] Saved {filename.name} ({len(session['turns'])} turns)")
            self.state[str(session["path"].resolve())] = session["mtime"]

        self._save_state()


def main():
    CodexProvider().run()


if __name__ == "__main__":
    main()
