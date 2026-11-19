# Architecture

## Execution boundary

`run_once()` in `market_intel.application` is the application boundary. It creates a run ID, prepares runtime directories, opens the NewsAPI client and optional Slack client using an `ExitStack`, builds the graph, and invokes it with an initial `AgentState`. The injected model is passed to the graph; provider construction is deliberately outside this package.

## Workflow

The compiled graph in `market_intel.graph.build_graph` executes:

1. `audit_start`
2. `fetch`
3. `extract`
4. `memory`
5. `decide`
6. `summary` when `report_required` is true
7. `delivery` when summary generation produced a summary
8. `audit_finish`

The no-report path skips summary and delivery and proceeds to final audit.

## Node responsibilities

| Node | Responsibility |
|---|---|
| `fetch` | Fetch articles for configured competitors through the NewsAPI client. |
| `extract` | Convert article content into validated structured facts using the injected model. |
| `memory` | Compare facts with stored competitor facts, identify duplicates, and persist new facts. |
| `decide` | Determine whether newly discovered facts require a report. |
| `summary` | Generate a concise summary from new facts and enforce the configured word limit. |
| `delivery` | Send the report to Slack or write a local Markdown fallback. |
| `audit_start` / `audit_finish` | Initialize and finalize the SQLite run record. |

Unexpected exceptions from guarded workflow nodes are written to the run audit as `failed` before being re-raised. Handled provider or delivery failures may instead be represented in the state and result in `completed_with_errors`.

## Shared state

`AgentState` carries the run ID, start time, competitors, articles, extracted facts, new facts, metrics, errors, report decision, summary, and delivery outcome. It is the transient state shared between graph nodes; it is not itself a database record.

## Persistence

`market_intel.tools.db` uses SQLite. The `facts` table stores competitor, fact text, category, event date, source URL, and first-seen timestamp. The `runs` table stores run ID, start and completion timestamps, status, article/fact metrics, and serialized errors.

The current `runs` schema does not have dedicated columns for `delivery_status` or `report_path`. Those values are present in graph state but are not persisted as separate audit fields.

## Memory comparison

`market_intel.tools.memory.process_facts` compares incoming facts with stored facts for the same competitor. Similarity normalization and matching are implemented in `market_intel.utils.similarity`. The threshold is configurable. This is heuristic duplicate detection, not semantic retrieval or a vector database.

## Failure boundaries

- News retrieval and extraction have component-level error handling.
- Unexpected node errors are guarded and audited where possible.
- Summary-generation failure prevents delivery and is reflected in run state.
- Slack failure triggers a local Markdown report attempt.
- Failure of both Slack and local report writing is represented as a delivery failure.
- Scheduler-level exceptions are logged so a failed scheduled invocation does not terminate the scheduler loop.

If SQLite itself is unavailable, audit persistence cannot be guaranteed. The application does not claim otherwise.
