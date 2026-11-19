# Operations guide

## 1. Install

Use Python 3.12 or newer:

```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## 2. Configure

Copy `.env.example` to `.env` and set `NEWS_API_KEY`. Optionally set `SLACK_WEBHOOK_URL`. Review `config.yaml` for competitor names, retrieval limits, similarity threshold, summary length, report directory, and weekly schedule.

## 3. Initialize an LLM model

The repository intentionally does not select an LLM vendor. Create a provider-specific launcher outside the core package. It must construct a LangChain-compatible chat model supporting `with_structured_output(FactExtraction)` and `invoke(prompt)`.

Keep provider credentials in environment variables. Do not commit the launcher if it contains secrets.

## 4. Run once

From a Python entry point after initializing `model`:

```python
from market_intel.application import run_once
from market_intel.config import load_config

config = load_config()
result = run_once(config=config, model=model)
print(result["run_id"], result["status"])
```

`run_once` raises if `NEWS_API_KEY` is absent. External clients are managed with an `ExitStack` and are closed after graph invocation.

## 5. Start scheduled execution

```python
from market_intel.main import run_scheduled_agent

run_scheduled_agent(model=model)
```

The process remains in the foreground. Keep the host awake and the process running. Use an operating-system service manager or process supervisor if unattended operation is required. Such deployment automation is not part of this repository's v1 scope.

## 6. Inspect run history

Use the database helpers:

```python
from market_intel.tools.db import get_run, list_runs

recent = list_runs("db/facts.sqlite", limit=20)
one_run = get_run("RUN_ID_HERE", "db/facts.sqlite")
```

The run table records execution status, timestamps, article/fact metrics, and errors. It does not currently persist report path or delivery status as dedicated fields.

## 7. Find local reports

The default report directory is `reports/`. `REPORT_DIR` overrides `reporting.output_dir` in `config.yaml`. A local Markdown report is generated when Slack is not configured or Slack delivery fails and local report writing succeeds.

## 8. Troubleshooting

| Symptom | Checks |
|---|---|
| Missing NewsAPI credential | Confirm `NEWS_API_KEY` is set in `.env` or process environment |
| NewsAPI timeout / HTTP failure | Check network access, provider status, key validity, and quota |
| No facts extracted | Inspect article text quality, model response, and extraction warnings/errors |
| Summary fails | Inspect model availability and summary validation errors |
| Slack delivery fails | Verify webhook URL and network access; inspect local fallback report |
| No local report | Check report directory permissions and available disk space |
| SQLite error | Check database path, directory permissions, disk space, and whether another process is locking the database |
| Scheduler does not run | Confirm process is alive and schedule weekday/time/timezone are correct |

Do not paste API keys or webhook URLs into logs, issues, or support requests.

## 9. Stop

Stop the foreground scheduler with Ctrl+C. The scheduler catches the interruption and requests shutdown. Avoid forcibly terminating a run while it is writing to SQLite.
