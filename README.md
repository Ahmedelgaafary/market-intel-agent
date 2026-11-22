# Autonomous Market Intelligence & Competitor Tracking Agent
https://github.com/user-attachments/assets/d4d662e3-e421-4532-8e82-d71082cfcb3e

A Python application that monitors a configured list of competitors, extracts structured developments from news articles, compares them with historical SQLite memory, and produces concise executive intelligence reports.

> **Project status:** v1 implementation. The application workflow and scheduled runner are provider-injected: you must initialize a LangChain-compatible chat model in your own launcher. No LLM provider SDK or model selection is included in this repository.

## What it does

A run follows this workflow:

1. Fetch recent articles for each configured competitor using NewsAPI.
2. Extract structured facts from article content using an injected LLM.
3. Compare extracted facts with SQLite memory using text similarity.
4. Persist facts that are considered new.
5. Decide whether there are new facts worth reporting.
6. Generate an executive summary subject to the configured word limit.
7. Send the report to Slack when a webhook is configured.
8. Save a local Markdown report when Slack is unavailable or delivery fails.
9. Persist run status, timestamps, metrics, and errors in SQLite.

The agent monitors only the competitor names configured in `config.yaml`; it does not discover competitors automatically.

## Architecture

The workflow is implemented as a LangGraph `StateGraph`. See [docs/architecture.md](docs/architecture.md) for the node responsibilities, state transitions, persistence behavior, and known boundaries.

## Technology

- Python 3.12+
- LangGraph and LangChain Core
- Pydantic
- NewsAPI
- HTTPX
- SQLite
- PyYAML and python-dotenv
- APScheduler
- pytest, pytest-cov, and Ruff

The LLM is passed into the application by the caller. The core repository does not assume OpenAI, Gemini, or another provider.

## Repository layout

```text
.
├── config.yaml
├── .env.example
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── docs/
│   ├── architecture.md
│   ├── configuration.md
│   ├── operations.md
│   └── demo/
├── scripts/
│   └── run_weekly.py
├── src/market_intel/
│   ├── application.py
│   ├── config.py
│   ├── graph.py
│   ├── main.py
│   ├── scheduler.py
│   ├── schemas.py
│   ├── state.py
│   ├── nodes/
│   ├── tools/
│   └── utils/
└── tests/
```

## Requirements

- Python 3.12 or newer.
- A NewsAPI key.
- A LangChain-compatible chat model that supports the structured-output interface used by the extraction workflow and `invoke()` for summary generation.
- A Slack incoming webhook if Slack delivery is required. Without it, the delivery node attempts a local Markdown fallback.

## Installation

Clone the repository:

```bash
git clone https://github.com/Ahmedelgaafary/market-intel-agent.git
cd market-intel-agent
```

Create and activate a virtual environment on Windows CMD:

```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate
```

Install the package and development tools:

```cmd
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Configuration

Copy the example environment file:

```cmd
copy .env.example .env
```

Set `NEWS_API_KEY` in `.env`. Set `SLACK_WEBHOOK_URL` if Slack delivery is wanted. `LLM_API_KEY` is a placeholder for the provider-specific model launcher; the core application does not read or instantiate a provider model from this variable.

Edit `config.yaml` to set competitors and workflow parameters. See [docs/configuration.md](docs/configuration.md).

Runtime environment variables:
- `NEWS_API_KEY`: required for `run_once`.
- `SLACK_WEBHOOK_URL`: optional; missing or failed Slack delivery triggers local fallback.
- `DATABASE_PATH`: optional; defaults to `db/facts.sqlite`.
- `REPORT_DIR`: optional; overrides `reporting.output_dir` in YAML, which defaults to `reports`.

## Running the application

### Execute one run

Initialize a compatible model in your own Python entry point, then call the runner:

```python
from market_intel.application import run_once
from market_intel.config import load_config

# `model` must be an initialized LangChain-compatible chat model.
config = load_config()
result = run_once(config=config, model=model)

print(result["run_id"])
print(result["status"])
```

The example deliberately does not instantiate a provider model: provider selection and credentials are the caller's responsibility.

### Start the weekly scheduler

```python
from market_intel.main import run_scheduled_agent

# `model` must already be initialized.
run_scheduled_agent(model=model)
```

The scheduler remains running in the foreground and executes according to `schedule.day`, `schedule.hour`, `schedule.minute`, and `schedule.timezone` in `config.yaml`. The host machine or process manager must keep the process running.

There is no provider-independent command-line model launcher in this repository. `scripts/run_weekly.py` is currently a placeholder and is not an executable CLI.

## Data and reports

- SQLite database: `db/facts.sqlite` by default.
- Local Markdown reports: `reports/` by default.
- Run history is available through `list_runs()` and `get_run()` in `market_intel.tools.db`.
- Generated database files and reports are runtime artifacts; do not commit private or operational data.

The SQLite `runs` table stores run ID, start/completion timestamps, status, article/fact metrics, and errors. Delivery-specific `delivery_status` and `report_path` are runtime graph state and are not separate columns in the current run table.

## Development and tests

Install development dependencies with `pip install -e ".[dev]"`.

Run tests:

```cmd
pytest
```

Run coverage:

```cmd
pytest --cov=market_intel --cov-report=term-missing
```

Lint and formatting:

```cmd
ruff check src tests
ruff format --check src tests
```

Apply formatting when intentionally changing code:

```cmd
ruff format src tests
```

Tests should mock external providers. Do not run real NewsAPI requests, send real Slack messages, or invoke a billable LLM from the automated test suite.

## Operational notes and limitations

- News coverage is limited by NewsAPI availability, quotas, and the articles returned for the query.
- Extraction and summaries are model-generated and require human judgment before business-critical decisions.
- Similarity-based duplicate detection is heuristic; semantically related facts may be missed or incorrectly matched.
- The system monitors a fixed competitor list and a configured lookback window.
- Slack delivery requires a valid incoming webhook.
- The weekly scheduler is an in-process scheduler. It is not a hosted service and does not survive process or machine shutdown.
- SQLite is appropriate for this single-application v1 workflow; concurrent multi-instance deployment is outside the v1 scope.
- The current audit table does not persist delivery channel/path metadata separately.


## License

This project is distributed under the MIT License. See [LICENSE](LICENSE).
