# Operations

## Daemon Mode

`hermes daemon` reads `HermesVault/config/schedule.yaml` and runs processors on their
configured intervals. If the file doesn't exist, a default schedule is created.
The schedule is hot-reloaded when the file changes. Jobs are retried with configurable
backoff. Every execution is recorded to `HermesVault/index/job_history.json`.

```yaml
# HermesVault/config/schedule.yaml
jobs:
  summary:
    every: 10m
  entity:
    every: 10m
  index:
    every: hour
  cleaner:
    every: day

retry:
  count: 3
  delay: 30s
  backoff: exponential  # or linear, fixed
```

Interval formats: `30s`, `5m`, `2h`, `1d`, `hour`, `day`, `sunday`

## Knowledge Evaluation

`hermes evaluate` scans the vault and prints:
- **Knowledge Statistics** — document, summary, entity, keyword, relation, project, people, wiki counts
- **Knowledge Growth** — new items in the last 1/7/30 days
- **Knowledge Quality** — coverage percentages, missing files, orphan entities, broken references
- **Graph Metrics** — nodes, edges, density, connected components, isolated nodes
- **Health Score** (0–100) — weighted deductions for quality gaps
- **Learning Score** (0–100) — health × 0.7 + growth bonus (capped at 100)

Results are saved to `HermesVault/index/evaluation_history.json` and a daily report is
written to `HermesVault/reports/daily-learning.md`.

## Retrieval Benchmark

`hermes benchmark-retrieval` evaluates the keyword-based search quality:
- Auto-generates questions from entity JSON files if none exist
- Reports Top-1 / Top-3 / Top-5 accuracy, Recall, Precision, F1 Score

## Deployment

The pipeline is designed to run unattended on a small always-on host (e.g. a cloud VM):

- A gateway/API process and a dashboard process, each behind their own port
- `hermes watch` (or `hermes daemon`) running as a long-lived service (systemd unit,
  supervisor, container restart policy — whatever fits your host)
- A separate scheduled job for each ingest source (e.g. Slack collector) on its own
  interval

Actual host, ports, and filesystem paths are environment-specific and intentionally
not documented here — configure them via `.env` / your process manager's unit files
for your own deployment.
