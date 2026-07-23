# Installation

## Requirements

- Python 3.13+
- An OpenAI-compatible LLM endpoint

## Option A — Install as a package (recommended)

```bash
# 1. Clone the repository
git clone https://github.com/ginaseo/hermes-knowledge-engine.git
cd hermes-knowledge-engine

# 2. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS

# 3. Install (exposes the `hermes` CLI command)
pip install .

# 4. Configure environment variables
cp .env.example .env
# Edit .env and set HERMES_API_URL and HERMES_API_KEY

# 5. Run the pipeline
hermes run
```

## Option B — Run without installing

```bash
pip install -r requirements.txt
python -m processor.runner
```

## Development Setup

```bash
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Lint
ruff check processor/ tests/

# Format check
black --check processor/ tests/
```

## Environment Variables

Create a `.env` file in the project root:

```dotenv
HERMES_API_URL=https://your-llm-endpoint/v1
HERMES_API_KEY=your-api-key

# Optional
HERMES_VAULT=./HermesVault   # custom vault path
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR
HERMES_LOCAL_HEURISTIC=1     # skip the LLM entirely (see below)
```

Missing `HERMES_API_URL` or `HERMES_API_KEY` causes a clear error message when the
first LLM processor starts. Non-LLM processors (markdown, wiki, cleaner, etc.) run
without credentials.

### Local heuristic mode (no LLM)

Set `HERMES_LOCAL_HEURISTIC=1` to make `LLMClient` skip the network entirely and
generate summaries/entities/keywords/related-doc links with a deterministic
TF-IDF + dictionary engine (`processor/llm/local_engine.py`) instead. `HERMES_API_URL`
and `HERMES_API_KEY` are not required in this mode — `cfg.validate_llm()` skips that
check when local mode is on. Quality is lower than an LLM (no real semantic
understanding) but the run costs nothing and never hits the network. Cache entries
are namespaced by backend (`local-heuristic-v1` vs. `remote:<model>`), so switching
this flag on and off doesn't serve stale results from the other backend.

## Vault Structure

The pipeline reads from and writes to `HermesVault/` in the project root.
Create the required input folder before first run:

```bash
mkdir -p HermesVault/slack
# Place your Slack markdown exports in HermesVault/slack/
```
