# AYNA

**Akıllı, Yerli, Nesne Tabanlı Arayüz Testi** — a codeless, closed-network UI test automation platform for Windows desktop applications. Senior capstone project, Ankara University Computer Engineering (COM 4061-4062), advisor Prof. Dr. Gazi Erkan Bostancı.

Team: Galip Enes Doğan · Ömerfaruk Sarıbal · Hasan Berk Yanıkkaya

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
3. Tell it which issue to work on, e.g. `Work on #21.` The agent follows the session-start steps in `AGENTS.md`.
4. When the agent says it is a good moment for a new session, start one with the prompt it gives you.

Tasks live in GitHub Issues and the **AYNA** project board; weeks are milestones.
