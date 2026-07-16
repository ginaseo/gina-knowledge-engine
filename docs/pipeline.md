# Processor Pipeline

```
slack/ (raw)          ─┐
claude-code/ (raw)     ├─→ MarkdownProcessor  →  knowledge/<source>/
                       └─→ WikiProcessor      →  wiki/<source>/

knowledge/<source>/ (slack, claude-code, ...)
  └─→ SummaryProcessor   →  knowledge/summary/

knowledge/summary/
  ├─→ EntityProcessor    →  knowledge/entity/ + projects/ + people/ + wiki/
  ├─→ KeywordProcessor   →  knowledge/keywords/
  └─→ RelatedProcessor   →  knowledge/related/

(always runs)
  ├─→ Cleaner            →  removes invalid/empty stubs
  ├─→ VaultIndexer       →  index/vault_index.json
  └─→ Validator          →  UTF-8 + JSON validation
```

## Folder Structure

```
hermes-knowledge-engine/
├── processor/
│   ├── config.py               # Centralized env config + fail-fast validation
│   ├── log.py                  # Logging setup (thread-local capture)
│   ├── processing_state.py     # Incremental state tracking
│   ├── runner.py               # CLI entry point (hermes)
│   ├── daemon.py               # Scheduled job runner (hermes daemon)
│   ├── history.py              # Job execution history persistence
│   ├── evaluator.py            # Knowledge stats, quality, health & learning
│   ├── retrieval.py            # Retrieval benchmark + question generation
│   ├── llm/
│   │   ├── client.py           # OpenAI-compatible LLM client
│   │   └── cache.py            # SHA256-keyed response cache
│   ├── mcp/
│   │   └── server.py           # MCP server (search/build_context/health) for Hermes
│   ├── markdown_processor.py
│   ├── wiki_processor.py
│   ├── summary_processor.py
│   ├── entity_processor.py
│   ├── keyword_processor.py
│   ├── related_processor.py
│   ├── validator.py
│   ├── vault_indexer.py
│   └── cleaner.py
├── ingest/
│   └── providers/               # SlackProvider, ClaudeCodeProvider, ...
├── tests/
├── HermesVault/                 # Output vault (gitignored)
│   ├── config/
│   │   └── schedule.yaml        # Daemon job schedule
│   ├── index/
│   │   ├── job_history.json     # Job execution history (rolling 500)
│   │   └── evaluation_history.json  # Evaluation history (rolling 365)
│   ├── benchmark/
│   │   └── questions.json       # Auto-generated retrieval benchmark questions
│   └── reports/
│       └── daily-learning.md    # Daily learning report
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## Incremental Processing

Each processor tracks file modification times in `HermesVault/index/<name>_state.json`.
A file is only reprocessed when its `mtime` changes. Use `--force` to bypass this.

## LLM Cache

Responses are cached by SHA256 hash of the prompt in `HermesVault/cache/llm_cache.json`.
Cache is written to disk once per processor run (not on every API call).

## Parallel Mode

`--parallel` runs `entity`, `keyword`, and `related` concurrently using `ThreadPoolExecutor`.
Console output is buffered per thread and flushed in original order — no interleaving.

## Watch Mode

`--watch` (or `watch` subcommand) polls the pipeline on a fixed interval. If a run
fails with an unhandled exception, the error is logged and the watch loop continues.
Incremental processing ensures only changed files are processed on each tick.

## Fail-Fast Configuration

Missing `HERMES_API_URL` or `HERMES_API_KEY` raises a clear `EnvironmentError` when
the first LLM processor runs — not an obscure API error buried in a traceback.
Processors that don't call the LLM (markdown, wiki, cleaner, index, validator) run
without credentials.
