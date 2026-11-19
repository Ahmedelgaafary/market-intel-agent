# Configuration reference

The application reads YAML configuration through `market_intel.config.load_config()` and environment variables through `python-dotenv`.

## YAML configuration

The repository's `config.yaml` currently defines:

```yaml
application:
  name: market-intel-agent
  environment: development

competitors:
  - Microsoft
  - Google
  - Amazon

news:
  lookback_days: 7
  max_articles_per_competitor: 10
  language: en

memory:
  similarity_threshold: 0.85

summary:
  max_words: 300

reporting:
  output_dir: reports

schedule:
  day: monday
  hour: 9
  minute: 0
  timezone: Africa/Cairo
```

| Key | Meaning | Validation / behavior |
|---|---|---|
| `competitors` | Competitor names queried by the workflow | Non-empty list of non-empty strings; duplicate names rejected |
| `news.lookback_days` | News lookback window | Positive integer |
| `news.max_articles_per_competitor` | Article cap per competitor | Positive integer |
| `news.language` | NewsAPI language code | Non-empty string |
| `memory.similarity_threshold` | Similarity threshold for duplicate matching | Number from 0 through 1 |
| `summary.max_words` | Maximum summary length | Positive integer |
| `reporting.output_dir` | Local Markdown report directory | Defaults to `reports` |
| `schedule.day` | Weekly execution weekday | Short or full weekday name |
| `schedule.hour` | Local schedule hour | Integer 0–23 |
| `schedule.minute` | Schedule minute | Integer 0–59 |
| `schedule.timezone` | IANA timezone name | Must be recognized by `zoneinfo` |

The `application.name` and `application.environment` fields are descriptive in the current configuration; `load_config()` does not expose them as `AppConfig` fields.

## Environment variables

| Variable | Required? | Default / purpose |
|---|---|---|
| `NEWS_API_KEY` | Yes for `run_once()` | NewsAPI credential |
| `SLACK_WEBHOOK_URL` | No | Slack incoming webhook; without it, delivery uses local fallback |
| `DATABASE_PATH` | No | Defaults to `db/facts.sqlite` |
| `REPORT_DIR` | No | Overrides `reporting.output_dir`; otherwise YAML value or `reports` |
| `LLM_API_KEY` | Provider-dependent | Example placeholder only; core code does not read it directly |
| `LOG_PATH` | Not consumed by current core configuration | Present as an example placeholder; no file logger is configured by `load_config()` |

Environment variables are loaded from `.env` when present. Existing process environment values are not overwritten.

## Example setup

On Windows CMD:

```cmd
copy .env.example .env
notepad .env
```

Set a valid `NEWS_API_KEY`. Add a Slack webhook only if Slack delivery is desired. Never commit `.env`.
