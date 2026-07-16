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

## Adding a New Source

1. Add a provider under `ingest/providers/` that writes raw `.md` files into
   `HermesVault/<source>/`
2. Register `(source_name, provider_name, raw_dir)` in `processor/markdown_processor.py`'s
   `SOURCES` list — `summary_processor.py` and `wiki_processor.py` pick it up
   automatically via the shared `SOURCE_NAMES`
