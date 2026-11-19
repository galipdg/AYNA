# AYNA

**Akıllı, Yerli, Nesne Tabanlı Arayüz Testi** — a codeless, closed-network UI test automation platform for Windows desktop applications. Senior capstone project, Ankara University Computer Engineering (COM 4061-4062).

Team: Galip Enes Doğan · Ömerfaruk Sarıbal · Hasan Berk Yanıkkaya

**Demo:** [`DEMO.md`](DEMO.md) (Turkish) starts the client with one command and walks through what is built so far.

## Repository layout

| Path | What |
|---|---|
| `agent/` | Python automation agent (pywinauto) and CLI runner |
| `client/` | Electron + React desktop client |
| `server/` | Java Spring Boot server, Neo4j migrations |
| `ai/` | Python AI service (Turkish NL → test steps) |
| `schemas/` | JSON Schemas shared by all components |
| `eval/` | Sample apps, experiment versions, measurement scripts |
| `docs/` | RS, SDD, API docs, guides |
| `memory-bank/` | Shared project memory for humans and coding agents |

## Working with coding agents

1. Copy `CLAUDE.local.md.example` to `CLAUDE.local.md` and set your id (`galip`, `omer` or `hasan`).
2. Start your agent in the repo root. Claude Code loads `CLAUDE.md`, which imports `AGENTS.md`; Codex, Cursor and others read `AGENTS.md` directly.
3. Just say `continue` (or `devam`). The agent reads your `active.md`, resumes the issue you were on, or proposes your next assigned issue. You can also name one: `Work on #22.`
4. When the agent says it is a good moment for a new session, start one with the prompt it gives you.

Tasks live in GitHub Issues and the **AYNA** project board; weeks are milestones.
