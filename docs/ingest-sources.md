# Ingest Sources

## Slack

`SlackProvider` polls configured channels and lands raw messages under `HermesVault/slack/`.
Channel IDs are configured via `SLACK_CHANNEL_IDS` in `.env` (not committed).

## Claude Code Sessions

`ClaudeCodeProvider` (`ingest/providers/claude_code.py`) imports the transcript of the
session that just ended, via a Claude Code `SessionEnd` hook, into
`HermesVault/claude-code/<year>/<month>/<date>-<session-id-8>.md`. Each run is dedup'd
against `HermesVault/index/claude_code_state.json` (keyed by session ID + transcript
mtime), so a session already imported and unchanged since is skipped.

Wire it up as a `SessionEnd` hook in Claude Code settings, piping the hook's stdin JSON
(`transcript_path`, `session_id`, `cwd`) to:

```bash
python ingest/providers/claude_code.py
```

Once landed, the file flows through the same `MarkdownProcessor → SummaryProcessor →
EntityProcessor/WikiProcessor` pipeline as Slack messages — no separate processing path.

## ChatGPT Data Export

`ChatGPTProvider` (`ingest/providers/chatgpt.py`) reads the `conversations-*.json`
files out of a ChatGPT "Export data" ZIP (or an already-unzipped directory) and
lands one markdown file per conversation under
`HermesVault/chatgpt/<year>/<month>/<date>-<conversation-id>.md`. It reads the
`conversations-*.json` members straight out of the ZIP — no need to unzip it
first. Each conversation is reconstructed by following the `mapping`'s
`current_node` back to the root via `parent` — that's the branch actually
displayed, so abandoned regeneration branches are excluded automatically.

This is a one-time bulk import, not hook-wired like the other providers — run it
manually:

```bash
python ingest/providers/chatgpt.py "C:\path\to\export.zip"
```

Dedup'd against `HermesVault/index/chatgpt_state.json` (keyed by conversation ID +
`update_time`), so re-running against the same export is a no-op. Flows through
the same pipeline as the other sources once landed.

## Adding a New Source

1. Add a provider under `ingest/providers/` that writes raw `.md` files into
   `HermesVault/<source>/`
2. Register `(source_name, provider_name, raw_dir)` in `processor/markdown_processor.py`'s
   `SOURCES` list — `summary_processor.py` and `wiki_processor.py` pick it up
   automatically via the shared `SOURCE_NAMES`
