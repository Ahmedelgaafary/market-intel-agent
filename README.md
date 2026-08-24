# Autonomous Market Intelligence & Competitor Tracking Agent

An autonomous AI agent that monitors competitors, extracts meaningful changes from recent news and articles, compares them against persistent memory, and delivers concise weekly intelligence reports to Slack.

The system is designed around a reliable, stateful workflow rather than a single LLM prompt.

## Overview

The agent automates the competitive-intelligence loop:

```text
Fetch → Extract → Compare → Decide → Summarize → Deliver → Remember
```

A scheduled run automatically:

1. Fetches recent articles for a defined set of competitors.
2. Extracts structured facts using an LLM.
3. Compares extracted facts against previously stored information.
4. Filters duplicate or previously reported events.
5. Decides whether a report is necessary.
6. Generates an executive-style summary from new facts.
7. Delivers the report to Slack.
8. Saves newly reported facts to persistent memory.
9. Records the complete run in an audit log.

## Architecture

```text
                  Weekly Scheduler
                         │
                         ▼
                ┌─────────────────┐
                │    LangGraph    │
                │   State Graph   │
                └────────┬────────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Fetch Articles│
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Extract Facts │
                 │  LLM + Schema │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │ Check Memory  │
                 │ SQLite + Sim. │
                 └───────┬───────┘
                         │
                    New facts?
                    /       \
                  No         Yes
                  │           │
                  ▼           ▼
               Log Run   Write Summary
                              │
                              ▼
                        Post to Slack
                              │
                              ▼
                         Save Memory
```

## Why LangGraph?

The v1 system intentionally uses a single-agent state graph rather than multi-agent orchestration.

The workflow has a clear sequence of operations with explicit state, conditional branching, tool calls, and failure handling. LangGraph provides these capabilities while keeping the system deterministic and easy to debug.

Multi-agent orchestration is intentionally deferred to a future version where independent roles, tools, or objectives would justify the additional complexity.

## Core Components

| Component          | Responsibility                                   |
| ------------------ | ------------------------------------------------ |
| LangGraph          | Agent orchestration and state transitions        |
| LLM                | Structured fact extraction and report generation |
| News API           | Recent competitor news                           |
| SQLite             | Persistent fact memory                           |
| Slack Webhook      | Weekly report delivery                           |
| APScheduler / cron | Autonomous scheduling                            |
| Pydantic           | Structured data validation                       |
| Pytest             | Automated testing                                |
| Ruff               | Linting                                          |
| GitHub Actions     | Continuous integration                           |

## Memory

The agent maintains persistent structured memory in SQLite.

Each fact contains information such as:

```text
competitor
fact
category
date
source_url
first_seen_at
```

Before a fact reaches the final report, it is compared against previously stored facts.

For v1, deduplication combines deterministic metadata filtering with lightweight text similarity. A vector database is intentionally avoided because the expected memory size does not justify the additional infrastructure.

## Failure Handling

The system is designed to continue operating when individual components fail.

| Failure                | Behavior                              |
| ---------------------- | ------------------------------------- |
| News API failure       | Skip affected competitor and continue |
| LLM extraction failure | Retry once, then skip article         |
| No new facts           | Skip summary and Slack delivery       |
| Duplicate fact         | Remove before reporting               |
| Slack failure          | Save report locally                   |
| Unexpected node error  | Record error in run history           |

Every scheduled run produces an audit-log entry, including runs where no new information is discovered.

## Repository Structure

```text
market-intel-agent/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── config.yaml
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── src/
│   └── market_intel/
│       ├── graph.py
│       ├── state.py
│       ├── schemas.py
│       │
│       ├── nodes/
│       │   ├── fetch.py
│       │   ├── extract.py
│       │   ├── memory.py
│       │   ├── decide.py
│       │   ├── write.py
│       │   └── deliver.py
│       │
│       ├── tools/
│       │   ├── news_api.py
│       │   ├── slack.py
│       │   └── db.py
│       │
│       └── utils/
│           ├── logging.py
│           └── similarity.py
│
├── tests/
├── db/
├── logs/
└── scripts/
    └── run_weekly.py
```

## Development Status

### v1 Foundation

* [x] Repository structure
* [x] Python 3.12 configuration
* [x] Development dependencies
* [x] Environment configuration
* [x] Ruff configuration
* [x] Pytest configuration
* [x] GitHub Actions CI
* [ ] Domain schemas
* [ ] LangGraph state
* [ ] SQLite memory
* [ ] News API integration
* [ ] LLM fact extraction
* [ ] Fact deduplication
* [ ] Summary generation
* [ ] Slack delivery
* [ ] Failure recovery
* [ ] Weekly scheduler
* [ ] End-to-end tests

## Testing

Run the test suite locally:

```bash
pytest -v
```

Run linting:

```bash
ruff check .
```

GitHub Actions runs the same checks automatically on pushes and pull requests.

## Configuration

Copy the environment template:

```bash
cp .env.example .env
```

Then configure the required API credentials.

Secrets are never committed to the repository.

## Roadmap

### v1

A reliable autonomous weekly competitor-monitoring pipeline with:

* 3–5 competitors
* News API ingestion
* Structured LLM extraction
* SQLite memory
* Duplicate detection
* Executive summaries
* Slack delivery
* Failure recovery
* Automated scheduling
* CI and tests

### v2+

Potential extensions include:

* Direct competitor website scraping
* Playwright for JavaScript-heavy sites
* Vector-based semantic memory
* Human approval before delivery
* Multi-agent orchestration
* PDF reports
* Email delivery
* Multi-channel reporting
* Financial and stock-data integration

## Engineering Principles

This project prioritizes:

* **Explicit state over hidden agent behavior**
* **Structured extraction over free-form fact generation**
* **Deterministic verification and memory logic**
* **Isolated, testable tools**
* **Graceful failure handling**
* **Persistent auditability**
* **Minimal infrastructure for the actual problem**
* **Multi-agent complexity only when justified**

The goal is not to demonstrate the largest possible number of AI frameworks.

The goal is to demonstrate how to build a **reliable autonomous AI workflow that can operate repeatedly without human intervention**.
