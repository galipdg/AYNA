# Conventions

Last reviewed: 2026-10-25. Tool versions and exact commands are pinned in each module's `AGENTS.md` once the module is scaffolded (#1–#4).

## General

- English everywhere in the repo: code, comments, commit messages, issues, PRs, memory.
- Small, focused changes; one issue per branch and PR.
- Tests live next to the module (`agent/tests/`, `server/src/test/`, `client/src/**/__tests__/`, `ai/tests/`).
- Configuration through environment variables; document every variable in `.env.example`. Never commit `.env`.
- Line endings: LF in the repo (`.gitattributes`); editors on Windows must not convert.

## Python (`agent/`, `ai/`, `eval/`)

- Python 3.11+, virtual environment per module, dependencies in `pyproject.toml`.
- Lint and format with `ruff` (`ruff check`, `ruff format`); type hints on public functions.
- Tests with `pytest`. Windows-only tests (real UI Automation) are marked `@pytest.mark.windows`.

## Java (`server/`)

- Java 21, Spring Boot 4, Spring Data Neo4j, Maven wrapper (`server/mvnw`, decided in #4).
- Packages by feature (`apps`, `repository`, `tests`, `runs`, `healing`), not by layer.
- Unit tests with JUnit 5; integration tests against a real Neo4j via Testcontainers.

## JavaScript (`client/`)

- Electron + React + Vite. `contextIsolation: true`, `nodeIntegration: false`; the renderer talks to main only through a typed preload API.
- Lint with ESLint, format with Prettier.

## Naming

- Logical names of repository objects: `screen.element` in lowerCamelCase, e.g. `login.userNameInput`.
- Branches: `<id>/<issue>-<short-slug>`, e.g. `hasan/39-playback-v1`.
- ADR files: `YYYY-MM-DD-short-slug.md`. Task notes: `<issue>-<short-slug>.md`.

## Commits and PRs

- Conventional Commits with the issue number: `feat(server): import snapshot API (#14)`.
- Scopes: `agent ai client server schemas eval docs memory ci build`.
- PR body: what changed, how it was tested, which acceptance criteria are met, `Closes #<n>`.
- Merge after one approving review from someone other than the author; the PR author's human merges.

## Project board

The "AYNA" GitHub Project (`galipdg`, project 1) has Status `Todo` → `In progress` → `Done`. Closing an issue moves it to Done automatically; moving it to In progress when work starts is manual (AGENTS.md §3):

```
item=$(gh project item-list 1 --owner galipdg --limit 300 --format json -q '.items[] | select(.content.number==<n>) | .id')
gh project item-edit --project-id PVT_kwHOCI8tT84Boop9 --id "$item" \
  --field-id PVTSSF_lAHOCI8tT84Boop9zhnH0ac --single-select-option-id 47fc9ee4
```

Option ids: Todo `f75ad846` · In progress `47fc9ee4` · Done `98236657`. If they stop working, re-read them with `gh project field-list 1 --owner galipdg --format json`. Needs the `project` scope (`gh auth refresh -s project`).
