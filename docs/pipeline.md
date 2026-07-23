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
without credentials. This check is skipped when `HERMES_LOCAL_HEURISTIC=1` — see
[INSTALL.md](INSTALL.md#local-heuristic-mode-no-llm).

## LLM Backend Selection

`LLMClient` (`processor/llm/client.py`) picks a backend once per instantiation:
the OpenAI-compatible remote API by default, or `LocalHeuristicEngine`
(`processor/llm/local_engine.py`) when `HERMES_LOCAL_HEURISTIC=1`. All four
LLM-driven processors (summary, entity, keyword, related) and
`DescriptionFillProcessor` go through this same `ask()` call, so the backend
switch is transparent to them. `LocalHeuristicEngine.answer()` sniffs the fixed
template text of each prompt (before the injected document content) to route
to the right generator — summary/entity/keyword/related share a
`====================` content delimiter, while `description_fill_prompt.txt`
has its own `{entity_name}`/`{entity_type}`/`[기존 문서]`/`[새 자료]` shape and
is matched on a string unique to that template so it isn't misrouted to the
entity generator (both prompts open with the same "Obsidian Knowledge Graph"
line). Response cache keys are namespaced by backend+model so toggling this
flag can't replay a cached answer from the other backend.
