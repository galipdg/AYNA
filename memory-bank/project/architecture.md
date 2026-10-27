# Architecture

Last reviewed: 2026-10-25. Change via PR; architectural changes need an ADR.

## Components

```
Each test machine (Windows)                    Shared, on the closed network
┌──────────────────────────────┐   REST/WS    ┌───────────────────────────────┐
│ Electron client (TS, React)  │◀────────────▶│ Server (Java, Spring Boot)    │
│ Spy, editor, NL chat,        │              │ projects, tests, repository,  │
│ healing approval, reports    │              │ runs, rule book, users        │
└──────────────┬───────────────┘              └──────┬─────────────┬──────────┘
   JSON-RPC over│localhost WebSocket            Bolt │             │ HTTP, authoring only
┌──────────────▼───────────────┐              ┌──────▼──────┐ ┌────▼─────────────┐
│ Automation agent (Python)    │              │ Neo4j       │ │ AI service (Py)  │
│ pywinauto uia/win32, waits,  │              │ graph +     │ │ Ollama/llama.cpp │
│ snapshots, healing scorer    │              │ vector index│ │ + embeddings     │
└──────────────┬───────────────┘              └─────────────┘ └──────────────────┘
   UI Automation│                             CI runner: CLI + headless agent,
        Application under test                pulls suites, writes JUnit XML
```

- Only the agent touches the application under test.
- The AI service is called by the server, and only while a test is being written. Playback is deterministic and never calls a model.
- Screenshots are files on the server disk; the graph stores their paths.
- Nothing calls a service outside the closed network (no CDN, no telemetry, no auto-update).

## Contracts (frozen at G1, week 7)

| Contract | Location | Between |
|---|---|---|
| Step schema | `schemas/step.schema.json` | editor, NL assistant, recorder, agent, server |
| Element / snapshot schema | `schemas/element.schema.json`, `schemas/snapshot.schema.json` | agent ↔ server |
| REST API | `docs/api/openapi.yaml` (generated) | client ↔ server |
| Agent JSON-RPC | `docs/agent-rpc.md` | client ↔ agent |
| AI service HTTP API | `ai/API.md` | server ↔ AI service |
| Graph schema | `server/src/main/resources/neo4j/migrations/` + `docs/graph-model.md` | server ↔ Neo4j |

## Graph data model (v0)

| Node | Key properties | Main relationships |
|---|---|---|
| Application, AppVersion | name, version, technology | `(Application)-[:HAS_VERSION]->(AppVersion)-[:HAS_WINDOW]->(Window)` |
| Window, Element | AutomationId, Name, ControlType, ClassName, bounds, snapshot id | `(Window)-[:CONTAINS]->(Element)-[:CONTAINS]->(Element)`, `(Element)-[:LABELLED_BY]->(Element)` |
| RepoObject | logical name, primary + fallback properties, embedding | `(RepoObject)-[:RESOLVES_TO {version}]->(Element)` |
| TestCase, Step | order, keyword, value, checkpoint | `(TestCase)-[:HAS_STEP {order}]->(Step)-[:TARGETS]->(RepoObject)` |
| Run, StepResult | status, duration, screenshot path | `(Run)-[:OF]->(TestCase)`, `(Run)-[:HAS_RESULT]->(StepResult)-[:FOR]->(Step)` |
| HealingProposal, Rule | score, per-property contributions, decision | `(HealingProposal)-[:FOR]->(RepoObject)`, `-[:CANDIDATE {score}]->(Element)`, `(Rule)-[:LEARNED_FROM]->(HealingProposal)` |

## Repository layout

| Path | What | Owner |
|---|---|---|
| `agent/` | Python automation agent + CLI runner | hasan (recognition, playback, cli), galip (heal, rpc) |
| `client/` | Electron + React client | omer |
| `server/` | Spring Boot server, Neo4j migrations | omer |
| `ai/` | Python AI service (NL → steps, retrieval) | galip |
| `schemas/` | JSON Schemas (frozen contracts) | all |
| `eval/` | sample apps, experiment versions, measurement scripts, datasets | hasan (`eval/nl/`: galip) |
| `docs/` | RS, SDD, generated API docs, guides | hasan; `rs/` and `report/`: galip; `sdd/`: omer (sections by component owner) |
| `docker-compose.yml` | one `docker compose up` for the whole backend (server, Neo4j, later AI service, nginx) | omer |
| `docker/` | extra container config (e.g. nginx) used by the root compose file | omer |
